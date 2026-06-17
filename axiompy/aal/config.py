# @!code-style,testing

from __future__ import annotations

from pathlib import Path

from axiompy.aal.constants import AAL_CONFIG_FILE, DEFAULT_CONFIG, cursor_config_dir_name


def cursor_config_dir(root: Path) -> Path:
    return root / cursor_config_dir_name()


def load_config(root: Path) -> dict:
    config = dict(DEFAULT_CONFIG)
    cfg_path = cursor_config_dir(root) / AAL_CONFIG_FILE
    if not cfg_path.exists():
        return config
    try:
        import yaml

        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        config.update({k: v for k, v in data.items() if v is not None})
    except ImportError:
        pass
    return config
