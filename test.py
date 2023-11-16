import alpaca_trade_api as tradeapi
import getpass

# Prompt the user for Alpaca API key and secret
api_key = getpass.getpass(prompt='Enter your Alpaca API key: ')
api_secret = getpass.getpass(prompt='Enter your Alpaca API secret: ')

# Initialize Alpaca API
api = tradeapi.REST(api_key, api_secret, base_url='https://paper-api.alpaca.markets', api_version='v2')

# Symbol to trade (Apple Inc. in this case)
symbol = 'AAPL'

# Determine the quantity of shares to buy
qty_to_buy = 1  # You can adjust this quantity as needed

# Get the current price of the stock
current_price = float(api.get_latest_trade(symbol).price)

# Check if the account balance is reasonable before placing the order
account_info = api.get_account()
max_buy_amount = float(account_info.cash)  # Use the available cash in the account
if max_buy_amount > 0 and qty_to_buy > 0:
    print(f'Buying {qty_to_buy} shares of {symbol} at {current_price}')
    
    # Place a market buy order using Alpaca API
    api.submit_order(
        symbol=symbol,
        qty=qty_to_buy,
        side='buy',
        type='market',
        time_in_force='gtc',
    )
else:
    print('Insufficient funds or unreasonable order quantity. No buy order placed.')
