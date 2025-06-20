import yaml  # type: ignore
import logging
from pathlib import Path
from typing import Any, Dict, Mapping, cast

logger = logging.getLogger(__name__)


def load_yaml(path: str) -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        logger.warning(f"Configuration file not found: {path}")
        return {}
    
    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
            if data is None:
                data = {}
            result = cast(Dict[str, Any], data)
            logger.debug(f"Successfully loaded YAML from {path} with {len(result)} keys")
            return result
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        raise


def deep_merge(a: Dict[str, Any], b: Mapping[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with b taking precedence over a."""
    logger.debug(f"Deep merging {len(a)} keys from dict a with {len(b)} keys from dict b")
    
    for k, v in b.items():
        if (
            isinstance(v, dict)
            and k in a
            and isinstance(a[k], dict)
        ):
            logger.debug(f"Recursively merging key '{k}'")
            a[k] = deep_merge(cast(Dict[str, Any], a[k]), cast(Mapping[str, Any], v))
        else:
            if k in a:
                logger.debug(f"Overriding key '{k}' with value from dict b")
            else:
                logger.debug(f"Adding new key '{k}' from dict b")
            a[k] = v
    return a


def load_config(config_path: str = "configs/config.yaml", secrets_path: str = "configs/secrets.yaml") -> Dict[str, Any]:
    """Load YAML configuration and secrets, merging secrets into config."""
    logger.info(f"Loading configuration from {config_path} and secrets from {secrets_path}")
    
    try:
        config = load_yaml(config_path)
        secrets = load_yaml(secrets_path)
        
        result = deep_merge(config, secrets)
        logger.info(f"Successfully merged configuration: {len(config)} config keys + {len(secrets)} secret keys = {len(result)} total keys")
        
        return result
    except Exception as e:
        logger.error(f"Failed to load and merge configuration: {e}")
        raise
