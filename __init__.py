# flake8: noqa

try:
    from .src.redteam_core import *
except ImportError:
    from src.redteam_core import *
