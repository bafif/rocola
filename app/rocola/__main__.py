"""Punto de entrada: python3 -m rocola"""
from __future__ import annotations

import sys

from .app import RocolaApp


def main() -> int:
    try:
        RocolaApp().run()
        return 0
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
