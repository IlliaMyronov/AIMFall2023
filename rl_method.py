#Python 3.10.11

import alpaca_trade_api as tradeapi
from alpaca_trade_api import TimeFrame
import getpass
import pandas as pd
import numpy as np
import gym
from gym import spaces
from finrl import config
from finrl.meta import env_stock_trading # might be incorrect, check when running
from stable_baselines3 import PPO
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

print(historical_data)

# Define a custom gym environment using FinRL
env = gym.make('AlpacaPaperTradingEnv')
env.data = historical_data

# Initialize RL agent
model = PPO("MlpPolicy", env, verbose=1)

# Load the previously saved RL agent's model weights (if available)
try:
    model.load("rl_model")
    print("Loaded pre-existing model weights.")
except Exception as e:
    print(f"No pre-existing model found. Training a new model. Error: {e}")
    # Train the RL agent if no pre-existing model is found
    model.learn(total_timesteps=20000)

# Run the trading strategy
close_positions_on_exit = False  # Set to True if you want to close all positions when the program stops

try:
    while True:
        # Fetch account information
        account_info = api.get_account()

        # Use the RL agent to make trading decisions
        action, _ = model.predict(historical_data)

        # Execute buy/sell orders based on RL agent's actions and account balance
        if action == 0:  # Buy
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
            else:
                print('Insufficient funds or unreasonable order quantity. No buy order placed.')

        elif action == 1:  # Sell
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
                else:
                    print('No position to sell or unreasonable sell order quantity. No sell order placed.')

        # Implement risk management: Set a stop-loss sell order for the buy position
        positions = api.list_positions()
        if action == 0 and positions:
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

    # Save the RL agent's learned information (model weights)
    model.save("rl_model")
    print("Saved RL model weights.")

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

class AlpacaPaperTradingEnv(gym.Env):
    def __init__(self, api_key, api_secret, symbol, time_frame=TimeFrame.Day, initial_balance=10000):
        super(AlpacaPaperTradingEnv, self).__init__()

        # Initialize Alpaca API
        self.api = tradeapi.REST(api_key, api_secret, 'https://paper-api.alpaca.markets', api_version='v2')

        # Set the Alpaca trading symbol
        self.symbol = symbol

        # Set the time frame for historical data
        self.time_frame = time_frame

        # Observation space: Closing prices of the stock
        self.observation_space = spaces.Box(low=0, high=np.inf, shape=(5,), dtype=np.float32)

        # Action space: 0 for hold, 1 for buy, 2 for sell
        self.action_space = spaces.Discrete(3)

        # Initial balance for paper trading
        self.initial_balance = initial_balance

        # Current balance and position
        self.current_balance = initial_balance
        self.current_position = 0

        # Current step in historical data
        self.current_step = 0

    def reset(self):
        # Reset environment to the initial state
        self.current_balance = self.initial_balance
        self.current_position = 0
        self.current_step = 0

        # Fetch historical price data using Alpaca API
        historical_data = self.api.get_bars(self.symbol, self.time_frame, limit=500).df[self.symbol]
        historical_data.index = pd.to_datetime(historical_data.index)

        return historical_data.iloc[self.current_step].values

    def step(self, action):
        # Define the logic for the step function
        current_price = self.api.get_latest_trade(self.symbol).price

        if action == 1:  # Buy
            if self.current_balance >= current_price:
                # Buy as many shares as possible
                shares_bought = self.current_balance // current_price
                self.current_position += shares_bought
                self.current_balance -= shares_bought * current_price
        elif action == 2:  # Sell
            if self.current_position > 0:
                # Sell all shares
                self.current_balance += self.current_position * current_price
                self.current_position = 0

        # Move to the next time step
        self.current_step += 1

        # Calculate reward (for simplicity, use portfolio value as reward)
        portfolio_value = self.current_balance + (self.current_position * current_price)
        reward = portfolio_value - self.initial_balance

        # Check if the episode is done (reached the end of the data)
        done = self.current_step == len(historical_data) - 1

        # Additional info (can be used for logging)
        info = {
            'current_balance': self.current_balance,
            'current_position': self.current_position,
            'portfolio_value': portfolio_value,
        }

        # Return the next observation, reward, done, and additional info
        return historical_data.iloc[self.current_step].values, reward, done, info