import yaml
import importlib
import os
import json
from pathlib import Path

# Set workspace directory environment variable
WORKSPACE_DIR = os.getenv("RT_WORKSPACE_DIR")
if not WORKSPACE_DIR:
    # Get the absolute path of the current file
    current_file = Path(__file__).resolve()
    # Navigate up to the RedTeam root directory (3 levels up from challenge_pool)
    workspace_dir = current_file.parent.parent.parent
    WORKSPACE_DIR = str(workspace_dir)
    os.environ["RT_WORKSPACE_DIR"] = WORKSPACE_DIR


from redteam_core.validator.challenge_manager import ChallengeManager  # noqa: E402

current_dir = Path(__file__).parent.resolve()
ACTIVE_CHALLENGES_FILE = os.getenv(
    "ACTIVE_CHALLENGES_FILE", f"{current_dir}/active_challenges.yaml"
)


def _expand_environment_variables(value):
    if isinstance(value, dict):
        return {
            key: _expand_environment_variables(item) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_expand_environment_variables(item) for item in value]
    if isinstance(value, str):
        return os.path.expandvars(value)
    return value


def _format_container_environment(environment):
    formatted_environment = {}
    for key, value in environment.items():
        if isinstance(value, str):
            try:
                structured_value = yaml.safe_load(value)
            except yaml.YAMLError:
                structured_value = value
        else:
            structured_value = value

        if isinstance(structured_value, (dict, list)):
            value = json.dumps(structured_value, separators=(",", ":"))

        formatted_environment[key] = value

    return formatted_environment


def _format_challenge_container_environments(challenge_configs):
    for challenge_config in challenge_configs.values():
        run_kwargs = challenge_config.get("challenge_container_run_kwargs", {})
        environment = run_kwargs.get("environment")
        if isinstance(environment, dict):
            run_kwargs["environment"] = _format_container_environment(environment)

    return challenge_configs


CHALLENGE_CONFIGS = yaml.load(open(ACTIVE_CHALLENGES_FILE), yaml.FullLoader)
CHALLENGE_CONFIGS = _expand_environment_variables(CHALLENGE_CONFIGS)
CHALLENGE_CONFIGS = _format_challenge_container_environments(CHALLENGE_CONFIGS)


def get_obj_from_str(string, reload=False, invalidate_cache=True):
    if string is None:
        return None
    module, cls = string.rsplit(".", 1)
    if invalidate_cache:
        importlib.invalidate_caches()
    if reload:
        module_imp = importlib.import_module(module)
        importlib.reload(module_imp)
    return getattr(importlib.import_module(module, package=None), cls)


ACTIVE_CHALLENGES = {
    challenge_name: {
        **CHALLENGE_CONFIGS[challenge_name],
        "controller": get_obj_from_str(
            CHALLENGE_CONFIGS[challenge_name].get("target", None)
        ),
        "challenge_manager": (
            get_obj_from_str(
                CHALLENGE_CONFIGS[challenge_name].get("challenge_manager", None)
            )
            if CHALLENGE_CONFIGS[challenge_name].get("challenge_manager", None)
            else ChallengeManager
        ),
    }
    for challenge_name in CHALLENGE_CONFIGS
}
