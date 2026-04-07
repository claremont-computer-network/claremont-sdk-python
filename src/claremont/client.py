"""
Claremont SDK for Python

Public client for SecureRelay tunnels, Key Server secrets, and Claremont services.
API keys are fetched encrypted from the Key Server — never stored in plaintext.

Usage:
    pip install claremont
    from claremont import Claremont

    # Authenticate with email + API key (fetched from Key Server)
    client = Claremont(email="you@claremontcomputer.net")

    # Create an encrypted tunnel
    tunnel = client.create_tunnel(local_port=8080, remote_host="internal.service")

    # Fetch an encrypted secret
    stripe_key = client.get_secret("STRIPE_KEY")
"""

from __future__ import annotations

import os
import time
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, field


__version__ = "2.0.0"
__all__ = ["Claremont", "Tunnel", "Secret", "ClaremontError", "AuthError", "SecretError"]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ClaremontError(Exception):
    """Base exception for all Claremont SDK errors."""

class AuthError(ClaremontError):
    """Authentication or authorization failed."""

class SecretError(ClaremontError):
    """Failed to retrieve or decrypt a secret."""

class TunnelError(ClaremontError):
    """Tunnel creation or management failed."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Tunnel:
    """Represents an active SecureRelay tunnel."""
    tunnel_id: str
    local_port: int
    remote_host: str
    remote_port: int
    status: str = "active"
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def url(self) -> str:
        return f"https://{self.remote_host}:{self.remote_port}"


@dataclass
class Secret:
    """Represents an encrypted secret from the Key Server."""
    name: str
    value: str
    category: str = ""
    environment: str = "production"
    expires_at: Optional[str] = None
    last_accessed: Optional[str] = None


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class Claremont:
    """
    Public client for Claremont services.

    Parameters
    ----------
    email : str, optional
        Your Claremont email (used as identity for Key Server lookup).
    api_key : str, optional
        Direct API key.  If omitted the SDK queries the Key Server
        using *email* to retrieve it encrypted.
    key_server_url : str, optional
        URL of the Claremont Key Server.  Defaults to
        ``https://keys.claremontcomputer.net``.
    relay_url : str, optional
        URL of the SecureRelay control plane.  Defaults to
        ``https://securerelay.claremontcomputer.net``.
    timeout : float
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        email: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        key_server_url: Optional[str] = None,
        relay_url: Optional[str] = None,
        timeout: float = 30.0,
        retries: int = 3,
    ):
        self.email = email or os.environ.get("CLAREMONT_EMAIL")
        self._api_key = api_key or os.environ.get("CLAREMONT_API_KEY")
        self.key_server_url = (
            key_server_url
            or os.environ.get("CLAREMONT_KEY_SERVER_URL")
            or "https://keys.claremontcomputer.net"
        )
        self.relay_url = (
            relay_url
            or os.environ.get("CLAREMONT_RELAY_URL")
            or "https://securerelay.claremontcomputer.net"
        )
        self.timeout = timeout
        self.retries = retries
        self._token: Optional[str] = None

    # -- bootstrap ----------------------------------------------------------

    def _ensure_api_key(self) -> None:
        """Fetch API key from Key Server if not already set."""
        if self._api_key:
            return
        if not self.email:
            raise AuthError(
                "Provide *email* or set CLAREMONT_EMAIL to fetch your API key "
                "from the Key Server, or pass *api_key* directly."
            )
        secret = self._fetch_key_server_secret(self.email)
        if not secret:
            raise AuthError(
                f"No API key found for {self.email} in the Key Server. "
                "Register at https://keys.claremontcomputer.net first."
            )
        self._api_key = secret

    # -- HTTP helpers -------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        hdrs = dict(headers or {})
        hdrs["Content-Type"] = "application/json"
        if self._token:
            hdrs["Authorization"] = f"Bearer {self._token}"
        elif self._api_key:
            hdrs["X-API-Key"] = self._api_key

        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)

        last_err: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as exc:
                last_err = exc
                if exc.code == 401:
                    self._token = None
                time.sleep(min(2 ** attempt, 8))
            except urllib.error.URLError as exc:
                last_err = exc
                time.sleep(min(2 ** attempt, 8))

        raise ClaremontError(f"Request failed after {self.retries} retries: {last_err}")

    # -- Key Server ---------------------------------------------------------

    def _fetch_key_server_secret(self, name: str) -> Optional[str]:
        """Retrieve a secret value from the Key Server."""
        url = f"{self.key_server_url}/api/v1/secrets/{name}"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                return data.get("value")
        except Exception:
            return None

    # -- Public API ---------------------------------------------------------

    def authenticate(self) -> Dict[str, Any]:
        """
        Authenticate with the SecureRelay control plane.

        If no *api_key* was provided at construction the SDK automatically
        fetches it encrypted from the Key Server.
        """
        self._ensure_api_key()
        result = self._request("POST", f"{self.relay_url}/api/auth/login", data={})
        if "token" in result:
            self._token = result["token"]
        return result

    # -- Tunnels ------------------------------------------------------------

    def create_tunnel(
        self,
        local_port: int,
        remote_host: str = "localhost",
        remote_port: int = 80,
        protocol: str = "tcp",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tunnel:
        """
        Create an encrypted SecureRelay tunnel.

        Parameters
        ----------
        local_port : int
            Local port to bind.
        remote_host : str
            Hostname or IP reachable from the relay node.
        remote_port : int
            Port on *remote_host* to forward to.
        protocol : str
            ``tcp`` or ``udp``.
        metadata : dict, optional
            Arbitrary key-value pairs attached to the tunnel.

        Returns
        -------
        Tunnel
        """
        self._ensure_api_key()
        payload = {
            "local_port": local_port,
            "remote_host": remote_host,
            "remote_port": remote_port,
            "protocol": protocol,
            "metadata": metadata or {},
        }
        result = self._request("POST", f"{self.relay_url}/api/tunnels", data=payload)
        return Tunnel(
            tunnel_id=result.get("tunnel_id", ""),
            local_port=local_port,
            remote_host=remote_host,
            remote_port=remote_port,
            status=result.get("status", "active"),
            created_at=result.get("created_at", ""),
            metadata=metadata or {},
        )

    def list_tunnels(self) -> List[Tunnel]:
        """List all active tunnels for the authenticated user."""
        self._ensure_api_key()
        result = self._request("GET", f"{self.relay_url}/api/tunnels")
        return [
            Tunnel(
                tunnel_id=t.get("id", ""),
                local_port=t.get("local_port", 0),
                remote_host=t.get("remote_host", ""),
                remote_port=t.get("remote_port", 0),
                status=t.get("status", ""),
                created_at=t.get("created_at", ""),
            )
            for t in result.get("tunnels", [])
        ]

    def close_tunnel(self, tunnel_id: str) -> Dict[str, Any]:
        """Close an active tunnel."""
        self._ensure_api_key()
        return self._request("DELETE", f"{self.relay_url}/api/tunnels/{tunnel_id}")

    # -- Secrets ------------------------------------------------------------

    def get_secret(self, name: str, *, environment: str = "production") -> Secret:
        """
        Fetch an encrypted secret from the Key Server.

        The value is returned decrypted.  The SDK never writes secrets to disk.
        """
        self._ensure_api_key()
        url = f"{self.key_server_url}/api/v1/secrets/{name}"
        result = self._request("GET", url)
        return Secret(
            name=result.get("name", name),
            value=result.get("value", ""),
            category=result.get("category", ""),
            environment=result.get("environment", environment),
            expires_at=result.get("expires_at"),
            last_accessed=result.get("last_accessed"),
        )

    def list_secrets(self, *, category: Optional[str] = None, environment: str = "production") -> List[Secret]:
        """List available secret names (values are **not** returned)."""
        self._ensure_api_key()
        params = {"environment": environment}
        if category:
            params["category"] = category
        qs = urllib.parse.urlencode(params)
        result = self._request("GET", f"{self.key_server_url}/api/v1/secrets?{qs}")
        return [
            Secret(
                name=s["name"],
                value="",
                category=s.get("category", ""),
                environment=s.get("environment", ""),
            )
            for s in result
        ]

    # -- Context manager ----------------------------------------------------

    def __enter__(self) -> "Claremont":
        self.authenticate()
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._token:
            try:
                self._request("POST", f"{self.relay_url}/api/auth/logout")
            except Exception:
                pass
            self._token = None
