import argparse
import sys

try:
    from importlib.metadata import version
    def get_version():
        return version("claremont")
except ImportError:
    from pathlib import Path
    def get_version():
        try:
            pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
            for line in pyproject.read_text().splitlines():
                if line.startswith("version ="):
                    return line.split("=")[1].strip().strip('"')
        except:
            pass
        return "unknown"

from claremont import Claremont


def login(args):
    client = Claremont(api_key=args.email, base_url=args.url)
    result = client.login()
    print(f"Logged in as: {result.get('email')}")
    print(f"Token: {result.get('token')}")
    print("\nToken saved to CLAREMONT_TOKEN environment variable")
    sys.exit(0)


def register(args):
    client = Claremont(base_url=args.url)
    result = client.register(args.email)
    print(f"Registered: {result.get('email')}")
    print("Please check your email to verify your account.")
    sys.exit(0)


def logout(args):
    import os
    client = Claremont(base_url=args.url)
    # Try to get token from env var or stdin
    token = os.environ.get("CLAREMONT_TOKEN") or getattr(args, 'token', None)
    if not token:
        print("Error: No token. Run 'claremont login' first.")
        sys.exit(1)
    client._token = token
    try:
        client.logout()
        print("Logged out successfully.")
    except Exception as e:
        print(f"Logout failed: {e}")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(prog="claremont")
    parser.add_argument("-v", "--version", action="store_true", help="Show version")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for API")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Login command
    login_parser = subparsers.add_parser("login", help="Login with email")
    login_parser.add_argument("email", help="Email address")
    login_parser.set_defaults(func=login)
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Register a new account")
    register_parser.add_argument("email", help="Email address")
    register_parser.set_defaults(func=register)
    
    # Logout command
    logout_parser = subparsers.add_parser("logout", help="Logout")
    logout_parser.add_argument("-t", "--token", help="Token from login")
    logout_parser.set_defaults(func=logout)
    
    args = parser.parse_args()
    
    if args.version:
        print(f"claremont {get_version()}")
        return
    
    if args.command:
        args.func(args)
    else:
        parser.print_usage()


if __name__ == "__main__":
    main()
