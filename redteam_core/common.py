import os
import bittensor as bt

from argparse import ArgumentParser


def get_config(parser=ArgumentParser()) -> bt.Config:
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.axon.add_args(parser)
    bt.logging.add_args(parser)
    parser.add_argument("--netuid", type=int)
    parser.add_argument("--neuron.fullpath", type=str, default="")
    parser.add_argument("--validator.cache_dir", type=str, default="./.cache/")
    parser.add_argument(
        "--validator.hf_repo_id", type=str, default="redteamsubnet61/storage"
    )
    parser.add_argument(
        "--validator.use_centralized_scoring",
        action="store_true",
        default=False,
        help="Opt-in to get scores of challenges from a centralized server. "
        "If not set, validators score themselves by default.",
    )
    config = bt.config(parser)
    bt.logging.check_config(config)
    full_path = os.path.expanduser(
        "{}/{}/{}/netuid-{}".format(
            config.logging.logging_dir,
            config.wallet.name,
            config.wallet.hotkey,
            config.netuid,
        )
    )
    print(config)
    print("full path:", full_path)
    config.neuron.fullpath = os.path.expanduser(full_path)
    if not os.path.exists(config.neuron.fullpath):
        os.makedirs(config.neuron.fullpath, exist_ok=True)
    return config


def generate_constants_docs(constants_class):
    """
    Generates Markdown documentation for the provided constants class.

    Args:
        constants_class: A Pydantic model class containing configuration constants.

    Returns:
        str: A Markdown formatted string representing the documentation.
    """
    docs = "# Configuration Constants\n\n"
    docs += f"**Class Name**: `{constants_class.__name__}`\n\n"
    docs += "## Description\n\n"
    docs += "Configuration constants for the application.\n\n"

    for field_name, field_info in constants_class.model_fields.items():
        docs += f"`{field_name}`\n"
        docs += f"  - Type: `{field_info.annotation.__name__}`\n"
        docs += f"  - Default: `{field_info.default}`\n"
        docs += f"  - Description: {field_info.description}\n\n"

    return docs
