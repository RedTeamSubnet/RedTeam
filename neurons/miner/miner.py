from scriptcurity_core import Miner
import bittensor as bt
import time

with Miner() as miner:
    while True:
        time.sleep(10)
