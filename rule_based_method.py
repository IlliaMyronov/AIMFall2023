#Python 3.10.11

import alpaca_trade_api as tradeapi
from alpaca_trade_api import TimeFrame
from datetime import datetime, timedelta
import getpass
import pandas as pd
import numpy as np
import time

# Securely prompt the user for Alpaca API key and secret
api_key = getpass.getpass(prompt='Enter your Alpaca API key: ')
api_secret = getpass.getpass(prompt='Enter your Alpaca API secret: ')

# Initialize Alpaca API
base_url = 'https://paper-api.alpaca.markets'  # Use 'https://api.alpaca.markets' for live trading
api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')

# Moving average time period - adjust as needed
short_timeperiod = 10 # Original 50
long_timeperiod = 50 # Original 200

holding_stock = False

# Get start and end dates
def get_date():
    start_date = datetime.now() - timedelta(days=long_timeperiod)
    # Format as strings
    start_date_str = start_date.strftime("%Y-%m-%d")
    return start_date_str

# Symbol to trade
symbol = 'AAPL'

# Check if account already has position
existing_positions = api.list_positions()
for position in existing_positions:
    if position.symbol == symbol:
        holding_stock = True

try:
    account_info = api.get_account()
    print("Login successful.")
except tradeapi.rest.APIError as e:
    print(f"Login failed. Error: {e}")
print("\n")

# Trading strategy function
def calculate_moving_averages(data):
    closing_prices = data['close']
    short_term_ma = np.mean(closing_prices[-short_timeperiod:])
    long_term_ma = np.mean(closing_prices[-long_timeperiod:])
    print(f'{symbol} - Short-term MA: {short_term_ma}, Long-term MA: {long_term_ma}')
    return short_term_ma, long_term_ma

# Run the trading strategy
close_positions_on_exit = False  # Set to True if you want to close all positions when the program stops
trailing_stop_percent = 0.10 # 10% stop loss
try:
    while True:
        # Get real-time historical data
        start_date_str = get_date()
        historical_data = api.get_bars(symbol, TimeFrame.Day, start_date_str, adjustment='raw').df
        short_term_ma, long_term_ma = calculate_moving_averages(historical_data)
        account_info = api.get_account()
        # Execute buy/sell orders based on moving average crossover
        if short_term_ma >  long_term_ma and not holding_stock:  # Buy
            # Determine the quantity of shares based on account balance and risk tolerance
            max_buy_amount = 0.1 * float(account_info.cash)  # Example: Allow using 10% of cash
            current_price = float(api.get_latest_trade(symbol).price)  # Get the current price
            qty_to_buy = min(int(max_buy_amount / current_price), 10)  # Example: Buy up to 10 shares

            # Check if the account balance is reasonable before placing the order
            if max_buy_amount > 0 and qty_to_buy > 0:
                print(f'Buy signal for {symbol}. Quantity: {qty_to_buy}')
                # Place a market buy order using Alpaca API
                api.submit_order(
                    symbol=symbol,
                    qty=qty_to_buy,
                    side='buy',
                    type='market',
                    time_in_force='gtc',
                )
                holding_stock = True
            else:
                print('Insufficient funds or unreasonable order quantity. No buy order placed.')

        elif short_term_ma < long_term_ma and holding_stock:  # Sell
            # Determine the quantity of shares to sell based on the current position
            positions = api.list_positions()
            if positions:
                qty_to_sell = min(int(positions[0].qty), 10)  # Example: Sell up to 10 shares

                # Check if the account has a position to sell and the order quantity is reasonable
                if qty_to_sell > 0:
                    print(f'Sell signal for {symbol}. Quantity: {qty_to_sell}')
                    # Place a market sell order using Alpaca API
                    api.submit_order(
                        symbol=symbol,
                        qty=qty_to_sell,
                        side='sell',
                        type='market',
                        time_in_force='gtc',
                    )
                    holding_stock = False
                else:
                    print('No position to sell or unreasonable sell order quantity. No sell order placed.')

        # Risk management: Trailing stop-loss sell order for the buy position
        positions = api.list_positions()
        for position in positions:
            if position.symbol == symbol and holding_stock:
                    current_price = float(api.get_latest_trade(symbol).price)
                    entry_price = float(position.avg_entry_price)
                    stop_loss_price = entry_price * (1 - trailing_stop_percent)
                    stop_loss_price_rounded = round(stop_loss_price, 2)

                    # Update stop price
                    if current_price > stop_loss_price_rounded:
                        print(f'Updating trailing stop for {symbol} to {stop_loss_price_rounded}')
                        api.submit_order(
                            symbol=symbol,
                            qty=int(position.qty),
                            side='sell',
                            type='limit',
                            time_in_force='gtc',
                            limit_price=str(stop_loss_price_rounded),
                        )
                        holding_stock = False

        time.sleep(10)  # Adjust the time interval as needed

except KeyboardInterrupt:
    print("Program stopped by the user.")

    # Close all positions if specified
    if close_positions_on_exit:
        positions = api.list_positions()
        for position in positions:
            symbol_to_sell = position.symbol
            qty_to_sell = int(position.qty)
            print(f"Selling all shares of {symbol_to_sell} to close the position.")
            api.submit_order(
                symbol=symbol_to_sell,
                qty=qty_to_sell,
                side='sell',
                type='market',
                time_in_force='gtc',
            )
    else:
        print("Positions will be kept open.")
