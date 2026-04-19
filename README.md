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

## Admin API Methods

The SDK supports admin-only operations. These require:
- Admin role (set in `role.txt` file or database)
- `ADMIN_ENABLED=true` environment variable on CWS server

### User Management

```python
# List all users (admin only)
users = client.list_users()

# Create a new user
user = client.create_user("new@example.com", "password123")

# Delete a user
client.delete_user(user_id)

# Create user without password (must reset on first login)
client.create_user_no_password("user@example.com", "user")
```

### Chat Management

```python
# List all chat messages for a user
chats = client.admin_get_chats("user@example.com")

# Create a chat message for a user
chat = client.admin_create_chat("user@example.com", "Hello!", "2026-04-18T12:00:00")

# Get a specific chat message
chat = client.admin_get_chat("user@example.com", chat_id)

# Update a chat message
chat = client.admin_update_chat("user@example.com", chat_id, "Updated message!")

# Delete a chat message
client.admin_delete_chat("user@example.com", chat_id)
```

### Other Admin Operations

```python
# Get admin status
status = client.admin_status()

# List telemetry
telemetry = client.list_telemetry()

# List API keys
keys = client.list_api_keys()

# Create API key
new_key = client.create_api_key("my-key")

# Delete API key
client.delete_api_key(key_id)

# Upload file for user
client.admin_upload_file("user@example.com", "/path/to/file.txt")

# List user's files
files = client.admin_list_user_files("user@example.com")

# Delete user's file
client.admin_delete_user_file("user@example.com", "filename.txt")
```

## Configuration

### Default API URL

The SDK defaults to `https://api.claremontcomputer.net`. You can override:

```python
client = Claremont(
    email="user@example.com",
    password="password123",
    relay_url="http://ec2-54-89-192-212.compute-1.amazonaws.com:8000"
)
```

Or via environment:

```bash
export CLAREMONT_RELAY_URL="http://ec2-54-89-192-212.compute-1.amazonaws.com:8000"
```

### Authentication

The SDK supports three authentication methods:

1. **Email + Password** (recommended for interactive use):
```python
client = Claremont(email="user@example.com", password="password123")
result = client.authenticate()  # Returns Bearer token (JWT)
```

2. **API Key** (via Key Server):
```python
client = Claremont(email="user@example.com")
result = client.authenticate()  # Fetches key from Key Server
```

3. **Direct API Key**:
```python
client = Claremont(api_key="cws_...")
```

#### JWT Support

As of this version, the CWS API issues JWT tokens (JSON Web Tokens) for authentication. The SDK handles these transparently as Bearer tokens.

**How JWT works in the SDK:**
1. When you authenticate via email/password, the SDK receives a JWT from the `/api/auth/login` endpoint
2. The SDK stores this token and automatically includes it in the `Authorization: Bearer <token>` header for subsequent requests
3. The CWS API verifies the JWT signature using its private key
4. Any third-party service can also verify the token using the public JWKS endpoint

**JWT Verification (for third-party services):**

Any service can verify Claremont JWT tokens without calling the Claremont API by using the public JWKS endpoint:

```bash
# Get the public key set
curl https://api.claremontcomputer.net/.well-known/jwks.json
```

Example payload structure of a Claremont JWT:
```json
{
  "sub": "user_123",                    // User ID
  "email": "user@example.com",          // User email
  "role": "admin",                      // User role
  "iss": "claremontcomputer.net",       // Issuer
  "aud": "any",                         // Audience
  "exp": 1713456000,                    // Expiration (Unix timestamp)
  "iat": 1713369600                     // Issued at (Unix timestamp)
}
```

**Note:** The SDK does not need to verify JWTs itself - it simply passes them through as Bearer tokens to the CWS API, which handles verification.

## Troubleshooting

### DNS Resolution Issue

If `api.claremontcomputer.net` fails to resolve (Cloudflare Tunnel IPv6 issue), use the EC2 endpoint directly:

```python
client = Claremont(
    email="user@example.com",
    password="password123",
    relay_url="http://ec2-54-89-192-212.compute-1.amazonaws.com:8000"
)
```

### 401 Unauthorized

Make sure to call `authenticate()` before making authenticated requests:

```python
client = Claremont(email="user@example.com", password="password123")
client.authenticate()  # Must call this first
chats = client.admin_get_chats("user@example.com")
```

## Requirements

- Python 3.7+
- `requests` library (optional, uses stdlib if not available)

## License

GPL-3.0
