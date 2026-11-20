"""Parser tekstowych ramek wysyłanych przez ESP32."""
from __future__ import annotations

import json
import re
from typing import Any


_NUMBER = re.compile(r"^[+-]?(?:(?:\d+(?:[.,]\d*)?)|(?:[.,]\d+))(?:[eE][+-]?\d+)?$")
_NAMED = re.compile(
    r"([A-Za-z_ąćęłńóśźżĄĆĘŁŃÓŚŹŻ][\w .\-/ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]*?)\s*[:=]\s*"
    r"([+-]?(?:(?:\d+(?:[.,]\d*)?)|(?:[.,]\d+))(?:[eE][+-]?\d+)?)"
)


class DataParser:
    """Rozpoznaje JSON, pola key:value/key=value oraz CSV."""

    def __init__(self) -> None:
        self.headers: list[str] | None = None

    @staticmethod
    def _number(value: Any) -> float | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.strip()
            if _NUMBER.fullmatch(text):
                try:
                    return float(text.replace(",", "."))
                except ValueError:
                    return None
        return None

    @staticmethod
    def _clean_name(name: str, fallback: str) -> str:
        cleaned = re.sub(r"\s+", " ", name.strip()).strip(" ,;")
        return cleaned[:40] or fallback

    def parse(self, line: str) -> dict[str, float] | None:
        text = line.strip().lstrip("\ufeff")
        if not text or text.startswith("#"):
            return None

        if text.startswith("{"):
            parsed = self._parse_json(text)
            if parsed:
                return parsed

        named = self._parse_named(text)
        if named:
            return named

        return self._parse_csv(text)

    def _parse_json(self, text: str) -> dict[str, float] | None:
        try:
            payload = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None

        if isinstance(payload, list):
            values = [self._number(value) for value in payload]
            if values and all(value is not None for value in values):
                return {
                    f"CH{index + 1}": value
                    for index, value in enumerate(values)
                    if value is not None
                }
            return None

        if not isinstance(payload, dict):
            return None

        result: dict[str, float] = {}
        for key, value in payload.items():
            number = self._number(value)
            if number is not None and str(key).lower() not in {
                "time", "timestamp", "czas", "millis", "ms"
            }:
                result[self._clean_name(str(key), "DANE")] = number
        return result or None

    def _parse_named(self, text: str) -> dict[str, float] | None:
        matches = list(_NAMED.finditer(text))
        if not matches:
            return None

        result: dict[str, float] = {}
        for match in matches:
            key = self._clean_name(match.group(1), f"CH{len(result) + 1}")
            value = self._number(match.group(2))
            if value is not None:
                result[key] = value
        return result or None

    def _parse_csv(self, text: str) -> dict[str, float] | None:
        delimiter = ";" if ";" in text else ("," if "," in text else "\t")
        tokens = [token.strip() for token in text.split(delimiter)]
        if not tokens or any(token == "" for token in tokens):
            return None

        values = [self._number(token) for token in tokens]

        if all(value is not None for value in values):
            numeric_values = [float(value) for value in values if value is not None]
            if self.headers and len(self.headers) == len(numeric_values):
                names = self.headers
            else:
                names = [f"CH{index + 1}" for index in range(len(numeric_values))]
            return dict(zip(names, numeric_values))

        # Pierwszy tekstowy wiersz może być nagłówkiem CSV.
        if self.headers is None and len(tokens) > 1:
            possible_names = [
                self._clean_name(token, f"CH{index + 1}")
                for index, token in enumerate(tokens)
            ]
            if all(
                not re.search(r"[^A-Za-z0-9_ąćęłńóśźżĄĆĘŁŃÓŚŹŻ .\-/]", name)
                for name in possible_names
            ):
                self.headers = possible_names
        return None
