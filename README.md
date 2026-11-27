# Claremont

A minimal Python SDK for the Claremont Computer Network API.

[![CI](https://github.com/claremont-computer-network/claremont-sdk-python/actions/workflows/ci.yml/badge.svg)](https://github.com/claremont-computer-network/claremont-sdk-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/claremont)](https://pypi.org/project/claremont/)

Full CWS documentation: <https://claremontcomputer.net/docs>

## Installation

```bash
pip install claremont
```

## Authentication

CWS API requests require explicit credentials. A passwordless browser session
is **not** API authentication.

- `Authorization: Bearer <JWT>` — API-issued JWT from `POST /api/auth/login`
  with a verified email and password, or a JWT passed directly to the SDK.
- `X-Api-Key: <key>` — API key created in the CWS dashboard.

Registration uses an email address and a LinkedIn profile URL. Registration
does not accept file uploads.

## Python usage

Use an API key:

```python
from claremont import Claremont

client = Claremont(api_key="cws_...")
client.authenticate()
print(client.list_downloads())
```

Use a Bearer JWT:

```python
from claremont import Claremont

client = Claremont(bearer_token="eyJ...")
print(client.list_downloads())
```

Exchange an email and password for an API JWT:

```python
from claremont import Claremont

client = Claremont(email="user@example.com", password="password123")
client.authenticate()
```

Registration is web-only. Use <https://claremontcomputer.net/login/register>; the SDK intentionally has no registration method.

## CLI usage

```bash
# Authenticate with an API key
claremont login --api-key cws_...

# Authenticate with a Bearer JWT
claremont login --token eyJ...

# Exchange email/password for an API JWT
claremont login user@example.com --password password123

# Clear local credentials
claremont logout

# Show version
claremont -v
```

## Configuration

```python
client = Claremont(
    api_key="cws_...",
    relay_url="https://api.claremontcomputer.net",
    timeout=30.0,
)
```

Environment variables:

```bash
export CLAREMONT_API_KEY="cws_..."
export CLAREMONT_TOKEN="eyJ..."
export CLAREMONT_EMAIL="user@example.com"
export CLAREMONT_PASSWORD="password123"
export CLAREMONT_RELAY_URL="https://api.claremontcomputer.net"
```

## API reference

### `Claremont(...)`

- `email` — used with `password` to obtain an API JWT.
- `password` — used only for explicit API login.
- `api_key` — sent as `X-Api-Key`.
- `bearer_token` — sent as `Authorization: Bearer <token>`.
- `relay_url` — defaults to `https://api.claremontcomputer.net`.
- `timeout` / `retries` — request behavior.

### Core methods

- `authenticate()` — validates explicit credentials.
- `login(password)` — exchanges email/password for an API JWT.
- `logout()` — invalidates a Bearer token and clears local credentials.
- `list_downloads()` / `download_file(filename)` / `upload_file(file_path)`.
- `create_tunnel(...)` / `list_tunnels()` / `close_tunnel(...)`.
- `get_secret(name)` / `list_secrets()`.

### Admin methods

Admin methods require an admin role and `ADMIN_ENABLED=true` on CWS.

```python
client.list_users()
client.create_user("new@example.com", "password123")
client.delete_user(user_id)
client.list_api_keys()
client.create_api_key("my-key")
client.list_telemetry()
client.admin_get_chats("user@example.com")
```

## JWT verification

Third-party services can verify JWTs using the public JWKS endpoint:

```bash
curl https://api.claremontcomputer.net/.well-known/jwks.json
```

The SDK does not verify JWTs locally; it passes them to CWS as Bearer tokens.

## Development and releases

Install development dependencies and run tests:

```bash
pip install -e '.[dev]'
pytest
python -m build
```

Releases are tag-driven:

1. Update `version` in `pyproject.toml` and `__version__` in `src/claremont/client.py`.
2. Merge the change to `main`.
3. Push a matching tag, for example `git tag v0.3.0 && git push origin v0.3.0`.
4. CI must pass before `.github/workflows/release.yml` creates a GitHub Release
   and publishes to PyPI via Trusted Publishing.

Configure PyPI Trusted Publishing once with these values:

- Owner: `claremont-computer-network`
- Repository: `claremont-sdk-python`
- Workflow: `release.yml`
- Environment: `pypi`

GitHub Packages does not provide a native Python/PyPI registry; PyPI is the
canonical package registry and GitHub Releases hold the built artifacts.

## License

GPL-3.0
