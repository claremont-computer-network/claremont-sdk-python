"""
Claremont - A minimal Python SDK for the Claremont Computer Network API.

Usage:
    from claremont import Claremont
    
    client = Claremont(api_key="your-api-key")
    client.login()
    response = client.get("/api/user/info")
"""

from .client import Claremont

__version__ = "0.2.0"
__all__ = ["Claremont"]
