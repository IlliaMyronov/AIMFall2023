#Python 3.10.11

import alpaca_trade_api as tradeapi
from alpaca_trade_api import TimeFrame
import getpass
import pandas as pd
import numpy as np
import time

# Prompt the user for Alpaca API key and secret
api_key = getpass.getpass(prompt='Enter your Alpaca API key: ')
api_secret = getpass.getpass(prompt='Enter your Alpaca API secret: ')

# Initialize Alpaca API
base_url = 'https://paper-api.alpaca.markets'  # Use 'https://api.alpaca.markets' for live trading
api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')

# Fetch historical price data using Alpaca API
symbol = 'AAPL'
historical_data = api.get_bars(symbol, TimeFrame.Day, "2022-11-14", "2023-11-14", adjustment='raw').df
# TODO: make method for getting yesterdays date and 200 days before yesterday
# TODO: test on previous historical data to see if it is making gains, or leave it running

try:
    account_info = api.get_account()
    print("Login successful.")
except tradeapi.rest.APIError as e:
    print(f"Login failed. Error: {e}")
print("\n")

print(historical_data)
print("\n")

# Trading strategy function
def moving_average_crossover_strategy(data):
    closing_prices = data['close']
    short_term_ma = np.mean(closing_prices[-50:])
    long_term_ma = np.mean(closing_prices[-200:])
    print(f'{symbol} - Short-term MA: {short_term_ma}, Long-term MA: {long_term_ma}')
    return short_term_ma, long_term_ma

# Run the trading strategy
close_positions_on_exit = False  # Set to True if you want to close all positions when the program stops

holding_stock = False

try:
    while True:
        short_term_ma, long_term_ma = moving_average_crossover_strategy(historical_data)
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

        # Implement risk management: Set a stop-loss sell order for the buy position
        positions = api.list_positions()
        if holding_stock and positions:
            stop_loss_price = float(positions[0].avg_entry_price) * 0.95  # Example: 5% stop-loss
            print(f'Set a stop-loss order at {stop_loss_price}')
            api.submit_order(
                symbol=symbol,
                qty=int(positions[0].qty),
                side='sell',
                type='limit',
                time_in_force='gtc',
                limit_price=str(stop_loss_price),
            )

        time.sleep(60)  # Adjust the time interval as needed

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