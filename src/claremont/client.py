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
