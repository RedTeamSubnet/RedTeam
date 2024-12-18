from unittest.mock import MagicMock, patch

from neurons.validator.validator import Validator


def test_validator_instantiation():
    config = MagicMock()
    def _setup_bt_objects(self):
        self.metagraph = MagicMock()
        self.wallet = MagicMock()

    # Mocking outside dependencies for now this should be fixed later with refactoring of the code
    with (patch('neurons.validator.validator.Thread') as threading_mock,
          patch('neurons.validator.validator.StorageManager') as storage_manager_mock,
          patch('redteam_core.validator.validator.SubstrateInterface') as substrate_mock):
        # Mocking inner functions for now
        with (patch('neurons.validator.validator.Validator.setup_logging') as logging_mock,
              patch('neurons.validator.validator.Validator.setup_bittensor_objects', new=_setup_bt_objects) as bt_objects_mock):

            validator = Validator(config)
            assert isinstance(validator, Validator), "Validator should be instantiated"