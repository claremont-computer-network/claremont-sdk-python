import argparse
import os
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
        except OSError:
            pass
        return "unknown"


from claremont import Claremont


def login(args):
    client = Claremont(
        email=args.email or os.environ.get("CLAREMONT_EMAIL"),
        password=args.password or os.environ.get("CLAREMONT_PASSWORD"),
        api_key=args.api_key or os.environ.get("CLAREMONT_API_KEY"),
        bearer_token=args.token or os.environ.get("CLAREMONT_TOKEN"),
        relay_url=args.url,
    )
    result = client.authenticate()
    print(f"Authenticated: {result.get('email', 'API credential')}")
    sys.exit(0)


def logout(args):
    client = Claremont(
        bearer_token=args.token or os.environ.get("CLAREMONT_TOKEN"),
        api_key=args.api_key or os.environ.get("CLAREMONT_API_KEY"),
        relay_url=args.url,
    )
    client.logout()
    print("Logged out successfully.")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(prog="claremont")
    parser.add_argument("-v", "--version", action="store_true", help="Show version")
    parser.add_argument(
        "--url",
        default=os.environ.get("CLAREMONT_RELAY_URL", "https://api.claremontcomputer.net"),
        help="Base URL for the CWS API",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    login_parser = subparsers.add_parser("login", help="Authenticate with explicit API credentials")
    login_parser.add_argument("email", nargs="?", help="Email address for password login")
    login_parser.add_argument("-p", "--password", help="Password for API login")
    login_parser.add_argument("--api-key", help="API key (or set CLAREMONT_API_KEY)")
    login_parser.add_argument("--token", help="Bearer JWT (or set CLAREMONT_TOKEN)")
    login_parser.set_defaults(func=login)

    logout_parser = subparsers.add_parser("logout", help="Clear local API credentials")
    logout_parser.add_argument("-t", "--token", help="Bearer token to invalidate")
    logout_parser.add_argument("--api-key", help="API key to clear")
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
