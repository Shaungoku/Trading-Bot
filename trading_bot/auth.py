"""
IndStocks authentication helpers.

Reads the access token from the environment and validates it on startup
by issuing a single LTP quote request. Exposes get_headers() which all
REST callers use to attach the bearer token.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Dict

import requests
from dotenv import load_dotenv

from config import HTTP_TIMEOUT, NIFTY_SCRIP_CODE, QUOTE_LTP

load_dotenv()

log = logging.getLogger(__name__)

_TOKEN: str = os.getenv("INDSTOCKS_ACCESS_TOKEN", "").strip()


def get_headers() -> Dict[str, str]:
    """Return the Authorization header dict for IndStocks REST/WS requests."""
    if not _TOKEN:
        raise RuntimeError("INDSTOCKS_ACCESS_TOKEN is not set in .env")
    return {"Authorization": f"Bearer {_TOKEN}"}


def get_token() -> str:
    """Return the raw access token (for WebSocket query params / headers)."""
    return _TOKEN


def _print_auth_help() -> None:
    """Print the user-facing help block for missing/expired tokens."""
    print(
        "Authentication failed. Your IndStocks access token is missing or expired.\n"
        "1. Log in to your IndStocks account at https://indstocks.com\n"
        "2. Navigate to API settings and generate a new access token\n"
        "3. Paste it in your .env file as: INDSTOCKS_ACCESS_TOKEN=your_token_here\n"
        "4. Restart the bot."
    )


def validate_token() -> bool:
    """
    Verify the access token by making a single LTP request for Nifty 50.

    Returns True on HTTP 200. Prints a guided help block and exits on
    401/403. Any other error is printed with status + body and exits.
    """
    if not _TOKEN:
        _print_auth_help()
        sys.exit(1)

    try:
        resp = requests.get(
            QUOTE_LTP,
            params={"scrip-codes": NIFTY_SCRIP_CODE},
            headers={"Authorization": f"Bearer {_TOKEN}"},
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException as exc:
        print(f"Network error contacting IndStocks: {exc}")
        sys.exit(1)

    if resp.status_code == 200:
        print("\u2713 IndStocks authentication successful")
        return True

    if resp.status_code in (401, 403):
        _print_auth_help()
        sys.exit(1)

    print(f"Unexpected auth response HTTP {resp.status_code}: {resp.text[:400]}")
    sys.exit(1)
