import alpaca_trade_api as tradeapi
import getpass
import pandas as pd
import numpy as np
import gym
import finrl
from stable_baselines3 import PPO
import tensorflow as tf

# Verify Alpaca API
print(f'Alpaca API Version: {tradeapi.__version__}')

# Verify GetPass
print(f'GetPass Version: Not Available')

# Verify Pandas
print(f'Pandas Version: {pd.__version__}')

# Verify NumPy
print(f'NumPy Version: {np.__version__}')

# Verify Gym
print(f'Gym Version: {gym.__version__}')

# Print FinRL version if available
if hasattr(finrl, "__version__"):
    print(f'FinRL Version: {finrl.__version__}')
else:
    print('FinRL Version: Not Available')

# Print Stable Baselines3 version if available
if hasattr(PPO, "__version__"):
    print(f'Stable Baselines3 Version: {PPO.__version__}')
else:
    print('Stable Baselines3 Version: Not Available')

# Verify TensorFlow
print(f'TensorFlow Version: {tf.__version__}')
