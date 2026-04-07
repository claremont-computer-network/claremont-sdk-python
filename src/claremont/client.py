import os
import urllib.request
import urllib.parse
import json
from typing import Optional, Any, Dict


class Claremont:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.environ.get("CLAREMONT_API_KEY")
        self.base_url = base_url or os.environ.get("CLAREMONT_BASE_URL", "https://api.claremontcomputer.net")
        self.timeout = timeout
        self._token = None

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        headers = kwargs.pop("headers", {})
        
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        elif self.api_key:
            headers["X-Api-Key"] = self.api_key
        
        headers["Content-Type"] = "application/json"

        url = f"{self.base_url}{path}"
        
        data = kwargs.pop("data", None)
        if data:
            data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> Dict[str, Any]:
        return self._request("POST", path, **kwargs)

    def login(self, api_key: str = None) -> Dict[str, Any]:
        """Login with API key, returns Bearer token. Uses self.api_key if not provided."""
        key = api_key or self.api_key
        if not key:
            raise ValueError("API key required")
        
        result = self.post("/api/auth/login", data={}, headers={"X-Api-Key": key})
        if "token" in result:
            self._token = result["token"]
        return result

    def logout(self) -> Dict[str, Any]:
        """Logout and invalidate token."""
        result = self.post("/api/auth/logout")
        self._token = None
        return result

    def register(self, email: str) -> Dict[str, Any]:
        """Register a new account. Note: Requires email verification on server."""
        data = urllib.parse.urlencode({"email": email}).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        url = f"{self.base_url}/submit"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return {"status": "registered", "email": email}


class KeyServer:
    """Client for fetching encrypted API keys from the Key Server."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://keys.claremontcomputer.net",
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        headers = kwargs.pop("headers", {})
        headers["X-API-Key"] = self.api_key
        headers["Content-Type"] = "application/json"

        url = f"{self.base_url}{path}"
        
        data = kwargs.pop("data", None)
        if data:
            data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_secret(self, name: str, environment: str = "production") -> Optional[str]:
        """Fetch a secret value by name."""
        try:
            result = self._request("GET", f"/api/v1/secrets/{name}")
            return result.get("value")
        except Exception:
            return None

    def list_secrets(self, category: str = None, environment: str = "production") -> list:
        """List all secrets."""
        path = "/api/v1/secrets"
        if category:
            path += f"?category={category}&environment={environment}"
        else:
            path += f"?environment={environment}"
        
        return self._request("GET", path)


class SecureRelay:
    """Client for SecureRelay tunnel management API."""
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://securerelay.claremontcomputer.net",
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.environ.get("CLAREMONT_API_KEY")
        self.base_url = base_url
        self.timeout = timeout
        self._token = None

    def login(self, api_key: str = None) -> Dict[str, Any]:
        """Login with API key, returns Bearer token."""
        key = api_key or self.api_key
        if not key:
            raise ValueError("API key required")
        
        try:
            result = self._request("POST", "/auth/login", data={"api_key": key})
            if "token" in result:
                self._token = result["token"]
            return result
        except Exception as e:
            return {"error": str(e)}

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        headers = kwargs.pop("headers", {})
        
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        
        headers["Content-Type"] = "application/json"

        url = f"{self.base_url}{path}"
        
        data = kwargs.pop("data", None)
        if data:
            data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def create_tunnel(self, destination: str, port: int = 51820) -> Dict[str, Any]:
        """Create a new tunnel."""
        if not self._token:
            return {"error": "Not authenticated. Call login() first."}
        
        return self._request("POST", "/tunnel/create", data={
            "destination": destination,
            "port": port
        })

    def get_tunnel_status(self, tunnel_id: str = None) -> Dict[str, Any]:
        """Get tunnel status."""
        if not self._token:
            return {"error": "Not authenticated. Call login() first."}
        
        if tunnel_id:
            return self._request("GET", f"/tunnel/{tunnel_id}/status")
        return self._request("GET", "/tunnel/status")
