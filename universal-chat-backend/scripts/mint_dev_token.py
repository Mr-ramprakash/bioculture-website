"""Print a short-lived tenant token for local API smoke testing only."""

from __future__ import annotations

import argparse
import time

from dotenv import load_dotenv

from chatbot.config import Settings
from chatbot.auth import mint_tenant_token


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("tenant_id", nargs="?", default="BIOMAN")
    parser.add_argument("--origin")
    args = parser.parse_args()
    settings = Settings.from_environment()
    key = settings.signing_keys.get(args.tenant_id)
    if not key:
        parser.error("tenant is not configured")
    print(mint_tenant_token(args.tenant_id, key, expires_at=int(time.time()) + 300, origin=args.origin))


if __name__ == "__main__":
    main()
