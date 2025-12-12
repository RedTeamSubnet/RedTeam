# import logging

# import pytest

# try:
#     from redteam_core import RedTeamCore
# except ImportError:
#     from src.redteam_core import RedTeamCore


# logger = logging.getLogger(__name__)


# @pytest.fixture
# def redteam_core_obj():
#     _redteam_core_obj = RedTeamCore()

#     yield _redteam_core_obj

#     del _redteam_core_obj


# def test_init(redteam_core_obj):
#     logger.info("Testing initialization of 'RedTeamCore'...")

#     assert isinstance(redteam_core_obj, RedTeamCore)

#     logger.info("Done: Initialization of 'RedTeamCore'.\n")
