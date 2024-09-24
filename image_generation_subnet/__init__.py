# Import all submodules.
from . import protocol
from . import base
from . import validator
from . import miner
from . import utils

__version__ = "0.1.7"
version_split = __version__.split(".")
__spec_version__ = (
    (1000 * int(version_split[0]))
    + (10 * int(version_split[1]))
    + (1 * int(version_split[2]))
)


__all__ = ["protocol", "base", "validator", "miner", "utils"]
