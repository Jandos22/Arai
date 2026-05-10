"""Shared environment loading for repo-local and multi-worktree runs."""
from __future__ import annotations

import os
from pathlib import Path


def env_file_candidates(repo_root: Path) -> list[Path]:
    """Return env files in precedence order, without requiring them to exist."""
    paths: list[Path] = []
    override = os.environ.get("ARAI_ENV_FILE")
    if override:
        paths.append(Path(override).expanduser())
    paths.append(repo_root / ".env.local")
    paths.append(Path.home() / ".config" / "arai" / "env.local")
    return paths


def load_env(repo_root: Path) -> Path | None:
    """Load the first available env file without overriding existing env vars."""
    for env_file in env_file_candidates(repo_root):
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        return env_file
    return None
