from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import json
import os

class ServerConfig(BaseSettings):
    port: Optional[int] = None
    hostname: str = "127.0.0.1"
    mdns: bool = False
    mdns_domain: str = "opencode.local"
    cors: List[str] = []
    username: str = "opencode"
    password: Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="OPENCODE_SERVER_")

def load_config(config_path: str = "opencode.json") -> ServerConfig:
    data = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            full_config = json.load(f)
            data = full_config.get("server", {})

    # Environment variables take precedence over config file in pydantic-settings by default
    # But we want CLI flags to take precedence over both.
    return ServerConfig(**data)
