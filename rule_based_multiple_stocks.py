#Python 3.10.11

import alpaca_trade_api as tradeapi
from alpaca_trade_api import TimeFrame
from datetime import datetime, timedelta
import getpass
import pandas as pd
import numpy as np
import time

# Stock class
class Stock:
    def __init__(self, symbol):
        self.holding_stock = False
        self.symbol = symbol

    def getSymbol(self):
        return self.symbol
    
    def isHolding(self):
        return self.holding_stock
    
    def bought(self):
        self.holding_stock = True

    def sold(self):
        self.holding_stock = False       

# Securely prompt the user for Alpaca API key and secret
api_key = getpass.getpass(prompt='Enter your Alpaca API key: ')
api_secret = getpass.getpass(prompt='Enter your Alpaca API secret: ')

# Alpaca API
base_url = 'https://paper-api.alpaca.markets'  # Use 'https://api.alpaca.markets' for live trading
api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')

# Moving average time period - adjust as needed
short_timeperiod = 10 # Original 50
long_timeperiod = 50 # Original 200

# Get start and end dates
def get_dates():
    today = datetime.now()
    end_date = today - timedelta(days=1)
    start_date = end_date - timedelta(days=long_timeperiod)

    # Format as strings
    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")

    return start_date_str, end_date_str

# Stocks to trade: define here
apple = Stock('AAPL')
tesla = Stock('TSLA')
microsoft = Stock('MSFT')
google = Stock('GOOGL')
amazon = Stock('AMZN')

# List that stores all stocks to trade
stocks = [apple, tesla, microsoft, google, amazon]

try:
    account_info = api.get_account()
    print("Login successful.")
except tradeapi.rest.APIError as e:
    print(f"Login failed. Error: {e}")
print("\n")

# Trading strategy function
def calculate_moving_averages(data, symbol):
    closing_prices = data['close']
    short_term_ma = np.mean(closing_prices[-short_timeperiod:])
    long_term_ma = np.mean(closing_prices[-long_timeperiod:])
    print(f'{symbol} - Short-term MA: {short_term_ma}, Long-term MA: {long_term_ma}')
    return short_term_ma, long_term_ma

# Run strategy
close_positions_on_exit = False  # Set to True if you want to close all positions when the program stops
trailing_stop_percent = 0.02 # 2% trailing stop
try:
    while True:
        for stock in stocks:
            # Get real-time historical data
            start_date_str, end_date_str = get_dates()
            historical_data = api.get_bars(stock.getSymbol(), TimeFrame.Day, start_date_str, end_date_str, adjustment='raw').df
            short_term_ma, long_term_ma = calculate_moving_averages(historical_data, stock.getSymbol())
            account_info = api.get_account()

            # Place buy/sell orders based on moving average
            if short_term_ma >  long_term_ma and not stock.isHolding():  # Buy
                # Determine the quantity of shares based on account balance and risk tolerance
                max_buy_amount = 0.1 * float(account_info.cash)  # Allow using 10% of cash
                current_price = float(api.get_latest_trade(stock.getSymbol()).price)  # Get the current price
                qty_to_buy = min(int(max_buy_amount / current_price), 10)  # Buy up to 10 shares

                # Check if the account balance is reasonable before placing the order
                if max_buy_amount > 0 and qty_to_buy > 0:
                    print(f'Buy signal for {stock.getSymbol()}. Quantity: {qty_to_buy}')
                    api.submit_order(
                        symbol=stock.getSymbol(),
                        qty=qty_to_buy,
                        side='buy',
                        type='market',
                        time_in_force='gtc',
                    )
                    stock.bought()
                else:
                    print('Insufficient funds or unreasonable order quantity. No buy order placed.')

            elif short_term_ma < long_term_ma and stock.isHolding():  # Sell
                # Determine the quantity of shares to sell based on the current position
                positions = api.list_positions()
                if positions:
                    qty_to_sell = min(int(positions[0].qty), 10)  # Sell up to 10 shares

                    # Check if the account has a position to sell and the order quantity is reasonable
                    if qty_to_sell > 0:
                        print(f'Sell signal for {stock.getSymbol()}. Quantity: {qty_to_sell}')
                        api.submit_order(
                            symbol=stock.getSymbol(),
                            qty=qty_to_sell,
                            side='sell',
                            type='market',
                            time_in_force='gtc',
                        )
                        stock.sold()
                    else:
                        print('No position to sell or unreasonable sell order quantity. No sell order placed.')

            # Risk management: Trailing stop
            positions = api.list_positions()
            for position in positions:  
                if position.symbol == stock.getSymbol() and stock.isHolding():
                    current_price = float(api.get_latest_trade(stock.getSymbol()).price)
                    entry_price = float(position.avg_entry_price)
                    stop_loss_price = entry_price * (1 - trailing_stop_percent)

                    # Update stop price
                    if current_price > stop_loss_price:
                        print(f'Updating trailing stop for {stock.getSymbol()} to {stop_loss_price}')
                        api.submit_order(
                            symbol=stock.getSymbol(),
                            qty=int(position.qty),
                            side='sell',
                            type='limit',
                            time_in_force='gtc',
                            limit_price=str(stop_loss_price),
                        )

            time.sleep(10)  # Adjust the time interval as needed, original 60
            print("\n")

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