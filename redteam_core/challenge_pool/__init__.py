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

import yaml

from redteam_core.validator.challenge_manager import ChallengeManager


ACTIVE_CHALLENGES_FILE = os.getenv(
    "ACTIVE_CHALLENGES_FILE", "redteam_core/challenge_pool/active_challenges.yaml"
)
CHALLENGE_CONFIGS = yaml.load(open(ACTIVE_CHALLENGES_FILE), yaml.FullLoader)
CHALLENGE_CONFIGS = json.loads(os.path.expandvars(json.dumps(CHALLENGE_CONFIGS)))
print(CHALLENGE_CONFIGS)


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
        "comparer": get_obj_from_str(
            CHALLENGE_CONFIGS[challenge_name].get("comparer", None)
        ),
        "challenge_manager": get_obj_from_str(
            CHALLENGE_CONFIGS[challenge_name].get("challenge_manager", None)
        ) if CHALLENGE_CONFIGS[challenge_name].get("challenge_manager", None) else ChallengeManager,
    }
    for challenge_name in CHALLENGE_CONFIGS
}
