"""
Claremont - A minimal Python SDK for the Claremont Computer Network API.

Usage:
    from claremont import Claremont
    
    # Basic API client
    client = Claremont(api_key="your-api-key")
    client.login()
    response = client.get("/api/user/info")
    
    # Key Server - fetch encrypted API keys
    from claremont import KeyServer
    keys = KeyServer(api_key="your-key-server-key")
    github_token = keys.get_secret("GITHUB_TOKEN")
    
    # SecureRelay - tunnel management
    from claremont import SecureRelay
    relay = SecureRelay(api_key="your-api-key")
    relay.login()
    tunnel = relay.create_tunnel("example.com", 51820)
"""

from .client import Claremont, KeyServer, SecureRelay

__version__ = "0.2.0"
__all__ = ["Claremont", "KeyServer", "SecureRelay"]
