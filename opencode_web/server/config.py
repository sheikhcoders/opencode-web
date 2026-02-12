"""Configuration management for OpenCode Web."""
import json
import os
import re
from typing import List, Optional, Any, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict

class ServerConfig(BaseSettings):
    """Configuration settings for the web server."""
    port: Optional[int] = None
    hostname: str = "127.0.0.1"
    mdns: bool = False
    mdns_domain: str = "opencode.local"
    cors: List[str] = []
    username: str = "opencode"
    password: Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="OPENCODE_SERVER_")

def strip_comments(text: str) -> str:
    """Strip // and /* */ comments from text."""
    # Strip // comments
    text = re.sub(r'//.*', '', text)
    # Strip /* */ comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return text

def substitute_variables(text: str) -> str:
    """Substitute {env:VAR} and {file:PATH} in text."""
    def replace_env(match):
        var_name = match.group(1)
        return os.environ.get(var_name, '')

    def replace_file(match):
        path = os.path.expanduser(match.group(1))
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        return ''

    text = re.sub(r'\{env:([a-zA-Z0-9_]+)\}', replace_env, text)
    text = re.sub(r'\{file:([^}]+)\}', replace_file, text)
    return text

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deeply merge two dictionaries."""
    for key, value in override.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            base[key] = deep_merge(base[key], value)
        else:
            base[key] = value
    return base

def find_project_config() -> Optional[str]:
    """Search for opencode.json in current directory or parents until .git."""
    curr = os.getcwd()
    while True:
        for ext in ['json', 'jsonc']:
            path = os.path.join(curr, f'opencode.{ext}')
            if os.path.exists(path):
                return path
        if os.path.exists(os.path.join(curr, '.git')):
            break
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return None

def load_config_file(path: str) -> Dict[str, Any]:
    """Load and process a single config file."""
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = strip_comments(content)
    content = substitute_variables(content)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}

def load_config(cli_overrides: Optional[Dict[str, Any]] = None) -> ServerConfig:
    """Load configuration with precedence and merging."""
    config_data: Dict[str, Any] = {}

    # 1. Remote config (placeholder)
    # 2. Global config
    global_path = os.path.expanduser("~/.config/opencode/opencode.json")
    if os.path.exists(global_path):
        deep_merge(config_data, load_config_file(global_path))

    # 3. Custom config path from env
    env_config_path = os.environ.get("OPENCODE_CONFIG")
    if env_config_path and os.path.exists(env_config_path):
        deep_merge(config_data, load_config_file(env_config_path))

    # 4. Project config
    project_path = find_project_config()
    if project_path:
        deep_merge(config_data, load_config_file(project_path))

    # 5. Inline config from env
    inline_content = os.environ.get("OPENCODE_CONFIG_CONTENT")
    if inline_content:
        processed_inline = substitute_variables(strip_comments(inline_content))
        try:
            deep_merge(config_data, json.loads(processed_inline))
        except json.JSONDecodeError:
            pass

    server_data = config_data.get("server", {})

    # Finally, create the ServerConfig object which also handles OPENCODE_SERVER_ environment variables
    config = ServerConfig(**server_data)

    # CLI overrides take highest precedence
    if cli_overrides:
        if cli_overrides.get('port') is not None:
            config.port = cli_overrides['port']
        if cli_overrides.get('hostname') is not None:
            config.hostname = cli_overrides['hostname']
        if cli_overrides.get('mdns') is not None:
            config.mdns = cli_overrides['mdns']
        if cli_overrides.get('mdns_domain') is not None:
            config.mdns_domain = cli_overrides['mdns_domain']
        if cli_overrides.get('cors'):
            config.cors = list(cli_overrides['cors'])

    return config
