from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def backend_config_path() -> Path:
    return backend_root() / "config.toml"


def load_config() -> dict[str, Any]:
    path = backend_config_path()
    if not path.is_file():
        return {}

    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _format_toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, list):
        inner = ", ".join(_format_toml_value(item) for item in value)
        return f"[{inner}]"
    if value is None:
        return """"""
    raise TypeError(f"Unsupported TOML value type: {type(value)}")


def _serialize_section(data: dict[str, Any], prefix: str | None = None) -> list[str]:
    lines: list[str] = []
    scalar_keys = [k for k, v in data.items() if not isinstance(v, (dict, list))]
    if prefix is not None and scalar_keys:
        lines.append(f"[{prefix}]")
        for key in scalar_keys:
            lines.append(f"{key} = {_format_toml_value(data[key])}")

    for key, value in data.items():
        if isinstance(value, dict):
            section = f"{prefix}.{key}" if prefix else key
            lines.append("")
            lines.extend(_serialize_section(value, section))
        elif (
            isinstance(value, list)
            and value
            and all(isinstance(item, dict) for item in value)
        ):
            section = f"{prefix}.{key}" if prefix else key
            for item in value:
                lines.append("")
                lines.append(f"[[{section}]]")
                for item_key, item_value in item.items():
                    lines.append(f"{item_key} = {_format_toml_value(item_value)}")
        elif isinstance(value, list) and not value:
            if prefix is None:
                lines.append(f"{key} = []")
            else:
                if key in scalar_keys:
                    continue
                lines.append("")
                lines.append(f"[{prefix}]")
                lines.append(f"{key} = []")

    return lines


def save_config(config: dict[str, Any]) -> None:
    lines: list[str] = []
    for key, value in config.items():
        if isinstance(value, dict):
            lines.append("")
            lines.extend(_serialize_section(value, key))
        elif (
            isinstance(value, list)
            and value
            and all(isinstance(item, dict) for item in value)
        ):
            lines.append("")
            for item in value:
                lines.append(f"[[{key}]]")
                for item_key, item_value in item.items():
                    lines.append(f"{item_key} = {_format_toml_value(item_value)}")
        else:
            lines.append(f"{key} = {_format_toml_value(value)}")
    path = backend_config_path()
    path.write_text(
        "\n".join(line for line in lines if line is not None) + "\n", encoding="utf-8"
    )
