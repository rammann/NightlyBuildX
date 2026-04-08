"""Minimal ANSI styling for regression runner CLI (TTY + NO_COLOR aware)."""

from __future__ import annotations

import os
import sys


def color_enabled() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR", "").strip()


class Theme:
    """Escape sequences; empty when colors disabled."""

    def __init__(self) -> None:
        self._on = color_enabled()

    def s(self, text: str, *codes: str) -> str:
        if not self._on or not codes:
            return text
        return "\033[" + ";".join(codes) + "m" + text + "\033[0m"

    def bold(self, text: str) -> str:
        return self.s(text, "1")

    def dim(self, text: str) -> str:
        return self.s(text, "2")

    def cyan(self, text: str) -> str:
        return self.s(text, "36")

    def green(self, text: str) -> str:
        return self.s(text, "32")

    def yellow(self, text: str) -> str:
        return self.s(text, "33")

    def red(self, text: str) -> str:
        return self.s(text, "31")

    def blue(self, text: str) -> str:
        return self.s(text, "34")

    def rule(self, width: int = 56) -> str:
        line = "─" * width
        return self.dim(line) if self._on else "-" * width
