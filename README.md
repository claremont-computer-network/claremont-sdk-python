# Claremont

A minimal Python SDK for the Claremont Computer Network API.

## Installation

```bash
pip install claremont
```

## Quick Start

```python
from claremont import Claremont

# Initialize with API key
client = Claremont(api_key="your-api-key")

# Login to get Bearer token
client.login()

# Verify token
client.verify()

# Make authenticated requests
response = client.get("/api/user/info")

# Logout
client.logout()
```

## Configuration

### Environment Variables

```bash
export CLAREMONT_API_KEY="your-api-key"
export CLAREMONT_BASE_URL="https://api.claremontcomputer.net"
```

### Programmatic

```python
client = Claremont(
    api_key="your-api-key",
    base_url="https://api.claremontcomputer.net",
    timeout=30.0
)
```

## API Reference

### Claremont

The main client class.

#### Parameters

- `api_key` (str, optional): API key for authentication. Can also set via `CLAREMONT_API_KEY` env var.
- `base_url` (str, optional): Base URL for the API. Defaults to `https://api.claremontcomputer.net`.
- `timeout` (float, optional): Request timeout in seconds. Defaults to 30.0.

### Methods

#### `login(api_key=None)`

Login with API key and obtain a Bearer token.

```python
client.login("your-api-key")
# Or use the one from constructor
client.login()
```

Returns: `{"token": "...", "email": "..."}`

#### `logout()`

Logout and invalidate the Bearer token.

```python
client.logout()
```

Returns: `{"message": "Logged out"}`

#### `register(email)`

Register a new account. Note: Requires email verification on server.

```python
client.register("user@example.com")
```

Returns: `{"status": "registered", "email": "..."}`

#### `get(path, **kwargs)`

Make a GET request.

```python
response = client.get("/api/user/info")
```

#### `post(path, **kwargs)`

Make a POST request.

```python
response = client.post("/api/data", data={"key": "value"})
```

## CLI Usage

```bash
# Show version
claremont -v
```

## Examples

### Full Authentication Flow

```python
from claremont import Claremont

# Initialize
client = Claremont(api_key="your-api-key")

# Login
result = client.login()
print(f"Logged in as: {result['email']}")

# Make authenticated request
user_info = client.get("/api/user/info")
print(user_info)

# Logout
client.logout()
```

### Using Context Manager

```python
from claremont import Claremont

with Claremont(api_key="your-api-key") as client:
    client.login()
    response = client.get("/api/user/info")
    # Token automatically invalidated on exit
```

### Register New User

```python
from claremont import Claremont

client = Claremont(api_key="admin-api-key")
client.register("newuser@example.com")
```

## CLI Usage

```bash
# Register a new account
claremont register user@example.com

# Login
claremont login user@example.com

# Logout (requires token from login)
claremont logout -t YOUR_TOKEN

# Specify custom URL
claremont --url https://api.claremontcomputer.net login user@example.com
```

## Requirements

- Python 3.7+
- No external dependencies (uses stdlib only)

## License

GPL-3.0
