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
import ipaddress
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, field

try:
    import requests
    USE_REQUESTS = True
except ImportError:
    USE_REQUESTS = False


__version__ = "0.2.0"
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
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        key_server_url: Optional[str] = None,
        relay_url: Optional[str] = None,
        timeout: float = 30.0,
        retries: int = 3,
    ):
        self.email = email or os.environ.get("CLAREMONT_EMAIL")
        self._password = password or os.environ.get("CLAREMONT_PASSWORD")
        self._api_key = api_key or os.environ.get("CLAREMONT_API_KEY")
        self.key_server_url = (
            key_server_url
            or os.environ.get("CLAREMONT_KEY_SERVER_URL")
            or "https://api.claremontcomputer.net"
        )
        self.relay_url = (
            relay_url
            or os.environ.get("CLAREMONT_RELAY_URL")
            or "https://api.claremontcomputer.net"
        )
        self.timeout = timeout
        self.retries = retries
        self._token: Optional[str] = None
        self._authenticated = False

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
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        hdrs = dict(headers or {})
        hdrs["Content-Type"] = "application/json"
        if self._token:
            hdrs["Authorization"] = f"Bearer {self._token}"
        elif self._api_key:
            hdrs["X-API-Key"] = self._api_key
        
        # Use json= if provided, else data=
        body = json if json is not None else data

        if USE_REQUESTS:
            last_err: Optional[Exception] = None
            for attempt in range(1, self.retries + 1):
                try:
                    resp = requests.request(
                        method, url, json=body, headers=hdrs,
                        timeout=self.timeout, verify=True
                    )
                    resp.raise_for_status()
                    return resp.json() if resp.text else {}
                except requests.exceptions.RequestException as exc:
                    last_err = exc
                    if getattr(exc, "response", None) and exc.response.status_code == 401:
                        self._token = None
                    time.sleep(min(2 ** attempt, 8))
            raise ClaremontError(f"Request failed after {self.retries} retries: {last_err}")
        else:
            body = json.dumps(data).encode() if data else None
            req = urllib.request.Request(url, data=body, headers=hdrs, method=method)

            last_err = None
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
        Authenticate with the Claremont API.

        Supports three methods:
        1. Email + password: login with email and password
        2. API key: use existing API key (X-API-Key header)
        3. Key Server: fetch API key from Key Server using email

        Prefer email/password if both are available.
        """
        # Method 1: Email + password login
        if self.email and self._password:
            result = self._request(
                "POST",
                f"{self.relay_url}/api/auth/login",
                json={"email": self.email, "password": self._password}
            )
            self._token = result.get("access_token") or result.get("token")
            self._authenticated = True
            return result

        # Method 2: API key auth
        self._ensure_api_key()
        result = self._request("POST", f"{self.relay_url}/api/auth/login", json={})
        self._token = result.get("access_token") or result.get("token")
        self._authenticated = True
        return result

    def login(self, password: str) -> Dict[str, Any]:
        """
        Login with email and password.
        """
        if not self.email:
            raise AuthError("Email required for password login")
        self._password = password
        return self.authenticate()

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

    # ---------------------------------------------------------------------------
    # BYOIP Support (from secure-relay)
    # ---------------------------------------------------------------------------

    BYOIP_NETWORK = ipaddress.IPv4Network("23.142.172.0/24")

    def configure_byoip(self, ip_address: str, domain: str = None) -> Dict[str, Any]:
        """Configure BYOIP binding for anycast configurations."""
        self._ensure_api_key()
        ipaddress.IPv4Address(ip_address)
        return self._request("POST", f"{self.relay_url}/api/byoip/configure", data={
            "ip_address": ip_address,
            "domain": domain,
        })

    def list_byoip_ranges(self) -> List[Dict[str, Any]]:
        """List available BYOIP ranges."""
        self._ensure_api_key()
        return self._request("GET", f"{self.relay_url}/api/byoip/ranges").get("ranges", [])

    def configure_exit_node(self, enabled: bool = True) -> Dict[str, Any]:
        """Configure this as an exit node for traffic routing."""
        self._ensure_api_key()
        return self._request("POST", f"{self.relay_url}/api/exit-node/configure", data={
            "enabled": enabled,
        })

    def configure_subnet_router(self, network: str, description: str = None) -> Dict[str, Any]:
        """Expose a local network to remote clients."""
        self._ensure_api_key()
        net = ipaddress.IPv4Network(network, strict=False)
        return self._request("POST", f"{self.relay_url}/api/subnet/configure", data={
            "network": str(net),
            "description": description,
        })

    # ---------------------------------------------------------------------------
    # Telemetry (base)
    # ---------------------------------------------------------------------------

    def track_event(self, event_name: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Track an analytics event."""
        self._ensure_api_key()
        self._request("POST", f"{self.relay_url}/api/telemetry/events", data={
            "event": event_name,
            "properties": properties or {},
        })

    def track_tunnel_created(self, tunnel_id: str, local_port: int, remote_port: int) -> None:
        """Track tunnel creation event."""
        self.track_event("tunnel_created", {
            "tunnel_id": tunnel_id,
            "local_port": local_port,
            "remote_port": remote_port,
        })

    def track_tunnel_closed(self, tunnel_id: str) -> None:
        """Track tunnel closure event."""
        self.track_event("tunnel_closed", {"tunnel_id": tunnel_id})

    # ---------------------------------------------------------------------------
    # Simplified API (from simplify-client)
    # ---------------------------------------------------------------------------

    def register(self, email: str) -> Dict[str, Any]:
        """Register a new account."""
        return self._request("POST", f"{self.relay_url}/api/auth/register", data={
            "email": email,
        })

    def list_all(self) -> List[Tunnel]:
        """List all tunnels (simplified API)."""
        return self.list_tunnels()

    def status(self, tunnel_id: str = None) -> Dict[str, Any]:
        """Get tunnel status (simplified API)."""
        if tunnel_id:
            return self._request("GET", f"{self.relay_url}/api/tunnels/{tunnel_id}")
        return self._request("GET", f"{self.relay_url}/api/status")

    # ---------------------------------------------------------------------------
    # Downloads/Uploads
    # ---------------------------------------------------------------------------

    def list_downloads(self) -> List[Dict[str, Any]]:
        """List available downloads."""
        return self._request("GET", f"{self.relay_url}/api/downloads")

    def upload_file(self, file_path: str, *, filename: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file."""
        import os
        if not os.path.exists(file_path):
            raise ClaremontError(f"File not found: {file_path}")

        name = filename or os.path.basename(file_path)
        with open(file_path, "rb") as f:
            content = f.read()

        url = f"{self.relay_url}/api/upload"
        import io
        from urllib.parse import urlencode

        # Build multipart request manually
        boundary = "----ClaremontBoundary"
        body = io.BytesIO()
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'.encode())
        body.write(b"Content-Type: application/octet-stream\r\n\r\n")
        body.write(content)
        body.write(f"\r\n--{boundary}--\r\n".encode())

        hdrs = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        if self._token:
            hdrs["Authorization"] = f"Bearer {self._token}"

        if USE_REQUESTS:
            resp = requests.post(url, data=body.getvalue(), headers=hdrs, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        else:
            req = urllib.request.Request(url, data=body.getvalue(), headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())

    def download_file(self, filename: str) -> bytes:
        """Download a file."""
        url = f"{self.relay_url}/api/download/{filename}"
        hdrs = {}
        if self._token:
            hdrs["Authorization"] = f"Bearer {self._token}"

        if USE_REQUESTS:
            resp = requests.get(url, headers=hdrs, timeout=self.timeout)
            resp.raise_for_status()
            return resp.content
        else:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read()

    # ---------------------------------------------------------------------------
    # Admin API (requires admin access)
    # ---------------------------------------------------------------------------

    def list_users(self) -> List[Dict[str, Any]]:
        """List all users (admin only)."""
        return self._request("GET", f"{self.relay_url}/api/admin/users")

    def create_user(self, email: str, password: str = "default") -> Dict[str, Any]:
        """Create a new user (admin only)."""
        return self._request("POST", f"{self.relay_url}/api/admin/users", data={
            "email": email,
            "password": password,
        })

    def delete_user(self, user_id: int) -> Dict[str, Any]:
        """Delete a user (admin only)."""
        return self._request("DELETE", f"{self.relay_url}/api/admin/users/{user_id}")

    def list_telemetry(self) -> List[Dict[str, Any]]:
        """List telemetry records (admin only)."""
        return self._request("GET", f"{self.relay_url}/api/admin/telemetry")

    def admin_status(self) -> Dict[str, Any]:
        """Get admin API status (admin only)."""
        return self._request("GET", f"{self.relay_url}/api/admin/status")

    def list_secrets(self) -> List[Dict[str, Any]]:
        """List auth tokens/secrets (admin only)."""
        return self._request("GET", f"{self.relay_url}/api/admin/secrets")

    def list_api_keys(self) -> List[Dict[str, Any]]:
        """List API keys (admin only)."""
        return self._request("GET", f"{self.relay_url}/api/admin/keys")

    def create_api_key(self, name: str = "admin-key") -> Dict[str, Any]:
        """Create an API key (admin only)."""
        return self._request("POST", f"{self.relay_url}/api/admin/keys", data={"name": name})

    def delete_api_key(self, key_id: int) -> Dict[str, Any]:
        """Delete an API key (admin only)."""
        return self._request("DELETE", f"{self.relay_url}/api/admin/keys/{key_id}")

    def create_user_no_password(self, email: str, role: str = "user") -> Dict[str, Any]:
        """Create user without password - requires password reset on first login."""
        return self._request("POST", f"{self.relay_url}/api/admin/users/no-password", data={
            "email": email,
            "role": role,
        })

    def admin_upload_file(self, user_email: str, file_path: str) -> Dict[str, Any]:
        """Upload a file for a user (admin only)."""
        import os
        if not os.path.exists(file_path):
            raise ClaremontError(f"File not found: {file_path}")
        
        name = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            content = f.read()
        
        url = f"{self.relay_url}/api/admin/uploads/{user_email}"
        import io
        
        boundary = "----ClaremontBoundary"
        body = io.BytesIO()
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'.encode())
        body.write(b"Content-Type: application/octet-stream\r\n\r\n")
        body.write(content)
        body.write(f"\r\n--{boundary}--\r\n".encode())
        
        hdrs = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        if self._token:
            hdrs["Authorization"] = f"Bearer {self._token}"
        
        if USE_REQUESTS:
            resp = requests.post(url, data=body.getvalue(), headers=hdrs, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        else:
            req = urllib.request.Request(url, data=body.getvalue(), headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())

    def admin_list_user_files(self, user_email: str) -> List[Dict[str, Any]]:
        """List files for a user (admin only)."""
        return self._request("GET", f"{self.relay_url}/api/admin/files/{user_email}")

    def admin_delete_user_file(self, user_email: str, filename: str) -> Dict[str, Any]:
        """Delete a file for a user (admin only)."""
        return self._request("DELETE", f"{self.relay_url}/api/admin/files/{user_email}/{filename}")

    def admin_get_chats(self, user_email: str) -> List[Dict[str, Any]]:
        """List all chat messages for a user (admin only)."""
        return self._request("GET", f"{self.relay_url}/api/admin/chat/{user_email}")

    def admin_create_chat(self, user_email: str, message: str, timestamp: str = None) -> Dict[str, Any]:
        """Create a chat message for a user (admin only)."""
        data = {"message": message}
        if timestamp:
            data["timestamp"] = timestamp
        return self._request("POST", f"{self.relay_url}/api/admin/chat/{user_email}", json=data)

    def admin_get_chat(self, user_email: str, message_id: int) -> Dict[str, Any]:
        """Get a specific chat message (admin only)."""
        return self._request("GET", f"{self.relay_url}/api/admin/chat/{user_email}/{message_id}")

    def admin_update_chat(self, user_email: str, message_id: int, message: str) -> Dict[str, Any]:
        """Update a chat message (admin only)."""
        return self._request("PUT", f"{self.relay_url}/api/admin/chat/{user_email}/{message_id}", json={"message": message})

    def admin_delete_chat(self, user_email: str, message_id: int) -> Dict[str, Any]:
        """Delete a chat message (admin only)."""
        return self._request("DELETE", f"{self.relay_url}/api/admin/chat/{user_email}/{message_id}")
