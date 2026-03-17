# Claremont

A minimal Python SDK for the Claremont Computer Network API.

## Installation

```bash
pip install claremont
```

## CLI Usage

```bash
# Register a new account
claremont register user@example.com

# Login
claremont login user@example.com

# Logout (requires token from login)
claremont logout -t YOUR_TOKEN

# Show version
claremont -v

# Specify custom URL
claremont --url https://api.claremontcomputer.net login user@example.com
```

## Python Usage

```python
from claremont import Claremont

# Initialize with API key
client = Claremont(api_key="your-email")

# Login to get Bearer token
client.login()

# Make authenticated requests
response = client.get("/api/some-endpoint")

# Logout
client.logout()
```

## Configuration

### Environment Variables

```bash
export CLAREMONT_API_KEY="your-email"
export CLAREMONT_BASE_URL="https://api.claremontcomputer.net"
```

### Programmatic

```python
client = Claremont(
    api_key="your-email",
    base_url="https://api.claremontcomputer.net",
    timeout=30.0
)
```

## API Reference

### Claremont(api_key=None, base_url=None, timeout=30.0)

- `api_key` (str, optional): Email for authentication
- `base_url` (str, optional): Base URL for the API. Defaults to `https://api.claremontcomputer.net`
- `timeout` (float, optional): Request timeout in seconds. Defaults to 30.0

### Methods

#### `login(api_key=None)`

Login with email and obtain a Bearer token.

```python
client.login("your-email")
# Or use the one from constructor
client.login()
```

#### `logout()`

Logout and invalidate the Bearer token.

```python
client.logout()
```

#### `register(email)`

Register a new account. Requires email verification.

```python
client.register("user@example.com")
```

#### `get(path, **kwargs)`

Make a GET request.

```python
response = client.get("/api/endpoint")
```

#### `post(path, **kwargs)`

Make a POST request.

```python
response = client.post("/api/endpoint", data={"key": "value"})
```

## Requirements

- Python 3.7+
- No external dependencies (uses stdlib only)

## License

GPL-3.0
