import pytest

from claremont import Claremont
from claremont.client import AuthError


def test_bearer_token_header():
    client = Claremont(bearer_token="jwt-token")
    assert client._auth_headers() == {"Authorization": "Bearer jwt-token"}


def test_api_key_header():
    client = Claremont(api_key="cws_key")
    assert client._auth_headers() == {"X-Api-Key": "cws_key"}


def test_email_alone_cannot_authenticate():
    client = Claremont(email="user@example.com")
    with pytest.raises(AuthError):
        client.authenticate()


def test_api_key_authentication_checks_user_info(monkeypatch):
    client = Claremont(api_key="cws_key")
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return {"email": "user@example.com"}

    monkeypatch.setattr(client, "_request", fake_request)
    result = client.authenticate()

    assert result["email"] == "user@example.com"
    assert calls[0][0] == "GET"
    assert calls[0][1].endswith("/api/user/info")


def test_register_requires_linkedin_url():
    client = Claremont()
    with pytest.raises(AuthError):
        client.register("user@example.com", "")


def test_register_posts_email_and_linkedin_url_without_file(monkeypatch):
    client = Claremont()
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return {"status": "ok"}

    monkeypatch.setattr(client, "_request", fake_request)
    client.register("user@example.com", "https://www.linkedin.com/in/user")

    assert calls[0][0] == "POST"
    assert calls[0][2]["json"] == {
        "email": "user@example.com",
        "linkedin_url": "https://www.linkedin.com/in/user",
    }
    assert "files" not in calls[0][2]


def test_logout_clears_credentials(monkeypatch):
    client = Claremont(bearer_token="jwt-token")

    def fake_request(method, url, **kwargs):
        return {}

    monkeypatch.setattr(client, "_request", fake_request)
    client.logout()

    assert client._token is None
    assert client._authenticated is False
