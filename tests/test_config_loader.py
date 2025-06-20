import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from config_loader import load_config
import yaml  # type: ignore

def write_yaml(path, data):
    with open(path, 'w') as f:
        yaml.dump(data, f)

def test_load_config_merges_secrets(tmp_path):
    config_data = {
        'fetcher': {'lookback_days': 1, 'search_string': 'test', 'language': 'en'},
        'filter': {'confirmed_sources': ['A'], 'accepted_sources': ['B']}
    }
    secrets_data = {
        'fetcher': {'lookback_days': 7},
        'filter': {'confirmed_sources': ['C']},
        'bluesky': {'handle': 'user', 'app_password': 'pw'}
    }
    config_path = tmp_path / 'config.yaml'
    secrets_path = tmp_path / 'secrets.yaml'
    write_yaml(config_path, config_data)
    write_yaml(secrets_path, secrets_data)
    merged = load_config(str(config_path), str(secrets_path))
    assert merged['fetcher']['lookback_days'] == 7  # secrets override config
    assert merged['filter']['confirmed_sources'] == ['C']
    assert merged['filter']['accepted_sources'] == ['B']
    assert merged['bluesky']['handle'] == 'user'
    assert merged['bluesky']['app_password'] == 'pw'

def test_load_config_missing_secrets(tmp_path):
    config_data = {'foo': 'bar'}
    config_path = tmp_path / 'config.yaml'
    write_yaml(config_path, config_data)
    merged = load_config(str(config_path), str(tmp_path / 'secrets.yaml'))
    assert merged['foo'] == 'bar'

def test_load_config_missing_config(tmp_path):
    secrets_data = {'foo': 'baz'}
    secrets_path = tmp_path / 'secrets.yaml'
    write_yaml(secrets_path, secrets_data)
    merged = load_config(str(tmp_path / 'config.yaml'), str(secrets_path))
    assert merged['foo'] == 'baz'
