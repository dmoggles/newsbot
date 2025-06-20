import yaml  # type: ignore
from pathlib import Path
from typing import Any, Dict


def load_yaml(path: str) -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


def deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in b.items():
        if isinstance(v, dict) and k in a and isinstance(a[k], dict):
            a[k] = deep_merge(a[k], v)
        else:
            a[k] = v
    return a


def load_config(config_path: str = "configs/config.yaml", secrets_path: str = "configs/secrets.yaml") -> Dict[str, Any]:
    """Load YAML configuration and secrets, merging secrets into config."""
    config = load_yaml(config_path)
    secrets = load_yaml(secrets_path)
    return deep_merge(config, secrets)
