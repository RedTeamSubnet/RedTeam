import bittensor as bt
from argparse import ArgumentParser
import os


def get_config(parser=ArgumentParser()):
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.axon.add_args(parser)
    bt.logging.add_args(parser)
    parser.add_argument("--netuid", type=int)

    config = bt.config(parser)
    bt.logging.check_config(config)
    full_path = os.path.expanduser(
        "{}/{}/{}/netuid-{}/{}".format(
            config.logging.logging_dir,
            config.wallet.name,
            config.wallet.hotkey,
            config.netuid,
            config.neuron.name,
        )
    )
    print("full path:", full_path)
    config.neuron.full_path = os.path.expanduser(full_path)
    if not os.path.exists(config.neuron.full_path):
        os.makedirs(config.neuron.full_path, exist_ok=True)
    return config
