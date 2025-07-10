# config_loader.py
import json
import argparse
import warnings

_config = None  # Global variable to store parsed config


def load_config():
    global _config
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="IncrementalPipeline/configs/default.json")
    args, _ = parser.parse_known_args()

    with open(args.config) as f:
        _config = json.load(f)


def get_config():
    if _config is None:
        # warnings.warn("Config not loaded. Calling load_config().")
        load_config()
    return _config
