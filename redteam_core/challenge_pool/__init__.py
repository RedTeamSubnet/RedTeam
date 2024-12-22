import yaml
import importlib
import os

ACTIVE_CHALLENGES_FILE = os.getenv("ACTIVE_CHALLENGES_FILE", "redteam_core/challenge_pool/active_challenges.yaml")
CHALLENGE_CONFIGS = yaml.load(
    open(ACTIVE_CHALLENGES_FILE), yaml.FullLoader
)

print(CHALLENGE_CONFIGS)
def get_obj_from_str(string, reload=False, invalidate_cache=True):
    module, cls = string.rsplit(".", 1)
    if invalidate_cache:
        importlib.invalidate_caches()
    if reload:
        module_imp = importlib.import_module(module)
        importlib.reload(module_imp)
    return getattr(importlib.import_module(module, package=None), cls)

ACTIVE_CHALLENGES = {
    challenge_name: {
        "controller": get_obj_from_str(CHALLENGE_CONFIGS[challenge_name]["target"]), 
        **CHALLENGE_CONFIGS[challenge_name]
    }  for challenge_name in CHALLENGE_CONFIGS
}
