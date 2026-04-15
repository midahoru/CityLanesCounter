import os

import yaml

def get_settings():
    DEFAULT_PATH = 'configs/settings.yaml'
    # USER_PATH = os.getenv('USER_CONFIG', 'config/settings.user.yaml')
    # path = USER_PATH if os.path.exists(USER_PATH) else DEFAULT_PATH
    if not os.path.exists(DEFAULT_PATH):
        raise FileNotFoundError(f"Config not found: {DEFAULT_PATH}")
    with open(DEFAULT_PATH) as f:
        return yaml.safe_load(f)