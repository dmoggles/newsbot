import logging
from pathlib import Path
from typing import Any, Dict, Mapping, cast
import yaml

logger = logging.getLogger(__name__)


def load_yaml(path: str) -> Dict[str, Any]:
    """
    Loads a YAML configuration file and returns its contents as a dictionary.
    Args:
        path (str): The file path to the YAML configuration file.
    Returns:
        Dict[str, Any]: The contents of the YAML file as a dictionary. Returns an empty dictionary if the file does not exist or is empty.
    Raises:
        yaml.YAMLError: If there is an error parsing the YAML file.
        Exception: If there is an error reading the file.
    Logs:
        - A warning if the configuration file is not found.
        - A debug message upon successful loading of the YAML file.
        - An error if there is an issue parsing or reading the file.
    """
    config_path = Path(path)
    if not config_path.exists():
        logger.warning("Configuration file not found: %s", path)
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data is None:
                data = {}
            result = cast(Dict[str, Any], data)
            logger.debug("Successfully loaded YAML from %s with %d keys", path, len(result))
            return result
    except yaml.YAMLError as e:
        logger.error("Error parsing YAML file %s: %s", path, e)
        raise
    except Exception as e:
        logger.error("Error reading file %s: %s", path, e)
        raise


def deep_merge(a: Dict[str, Any], b: Mapping[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with b taking precedence over a."""
    logger.debug("Deep merging %d keys from dict a with %d keys from dict b", len(a), len(b))

    for k, v in b.items():
        if isinstance(v, dict) and k in a and isinstance(a[k], dict):
            logger.debug("Recursively merging key '%s'", k)
            a[k] = deep_merge(cast(Dict[str, Any], a[k]), cast(Mapping[str, Any], v))
        else:
            if k in a:
                logger.debug("Overriding key '%s' with value from dict b", k)
            else:
                logger.debug("Adding new key '%s' from dict b", k)
            a[k] = v
    return a


def load_config(config_path: str = "configs/config.yaml", secrets_path: str = "configs/secrets.yaml") -> Dict[str, Any]:
    """Load YAML configuration and secrets, merging secrets into config."""
    logger.info("Loading configuration from %s and secrets from %s", config_path, secrets_path)

    try:
        config = load_yaml(config_path)
        secrets = load_yaml(secrets_path)

        result = deep_merge(config, secrets)
        logger.info(
            "Successfully merged configuration: %d config keys + %d secret keys = %d total keys",
            len(config),
            len(secrets),
            len(result),
        )

        return result
    except Exception as e:
        logger.error("Failed to load and merge configuration: %s", e)
        raise
