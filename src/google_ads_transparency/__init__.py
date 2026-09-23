"""Google Ads Transparency Center data from Python, through the Apify Actor
``firsthand/google-ads-transparency-report``."""
from .client import ACTOR_ID, ACTOR_URL, Client, ConfigError, Result, build_input

__all__ = ["ACTOR_ID", "ACTOR_URL", "Client", "ConfigError", "Result", "build_input"]
__version__ = "0.1.0"
