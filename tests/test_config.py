import datetime

import pytest

from redteam_core.config.main import MainConfig


def test_spec_version_calculated_from_version_string():
    config = MainConfig(VERSION="4.7.6")

    assert config.SPEC_VERSION == 4076


def test_spec_version_invalid_format_raises():
    with pytest.raises(Exception, match="Invalid version format"):
        MainConfig(VERSION="not-a-version")


def test_testnet_overrides_cooldown_epoch_and_stake():
    config = MainConfig(TESTNET=True)

    assert config.COMMIT_COOLDOWN == 30
    assert config.EPOCH_LENGTH == 100
    assert config.MIN_VALIDATOR_STAKE == -1


def test_non_testnet_keeps_defaults():
    config = MainConfig(TESTNET=False)

    assert config.COMMIT_COOLDOWN == 3600 * 24
    assert config.EPOCH_LENGTH == 1200
    assert config.MIN_VALIDATOR_STAKE == 10_000


def test_is_commit_on_time_testnet_always_true():
    config = MainConfig(TESTNET=True)
    future_timestamp = datetime.datetime.now(datetime.timezone.utc).timestamp() + 3600

    assert config.is_commit_on_time(future_timestamp) is True


def test_is_commit_on_time_recent_commit_is_false():
    config = MainConfig(TESTNET=False)
    just_now = datetime.datetime.now(datetime.timezone.utc).timestamp()

    assert config.is_commit_on_time(just_now) is False


def test_is_commit_on_time_old_commit_is_true():
    config = MainConfig(TESTNET=False)
    twenty_five_hours_ago = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=25)
    ).timestamp()

    assert config.is_commit_on_time(twenty_five_hours_ago) is True
