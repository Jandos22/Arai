"""Subprocess wrapper for ``claude -p`` headless invocations.

Each agent (sales, ops, marketing) is its own Claude Code project under
``agents/<role>/`` with a project-scoped ``.mcp.json`` and ``CLAUDE.md``.
The orchestrator delegates LLM reasoning by shelling into that directory
and running ``claude -p "<prompt>"``.

We capture stdout, log the prompt + a result summary to evidence, and return
the model's textual response. Errors propagate but are also logged.
"""
from __future__ import annotations

import logging
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .evidence import EvidenceLogger

log = logging.getLogger(__name__)


def _resolve_claude_binary(name: str = "claude") -> str:
    """Find the ``claude`` CLI even when invoked from a sparse PATH (e.g. a
    non-interactive ssh session whose PATH is ``/usr/bin:/bin:...``).

    Search order:
      1. Honour ``CLAUDE_BINARY`` env var if set (escape hatch for prod)
      2. ``shutil.which`` against the inherited PATH
      3. Common install locations: ``~/.local/bin/claude``, Homebrew, npm
    """
    override = os.environ.get("CLAUDE_BINARY")
    if override and Path(override).exists():
        return override

    found = shutil.which(name)
    if found:
        return found

    home = Path.home()
    candidates = [
        home / ".local" / "bin" / name,
        Path("/opt/homebrew/bin") / name,
        Path("/usr/local/bin") / name,
        home / ".bun" / "bin" / name,
    ]
    for path in candidates:
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
    # Last resort: return bare name. subprocess will surface a clean
    # FileNotFoundError that tells the user to set CLAUDE_BINARY.
    return name


class ClaudeRunError(RuntimeError):
    pass


@dataclass
class ClaudeRunner:
    project_dir: Path
    evidence: EvidenceLogger
    timeout: float = 180.0
    binary: str = ""  # resolved lazily in __post_init__
    extra_args: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.binary:
            self.binary = _resolve_claude_binary()

    def run(self, prompt: str, *, label: str = "claude_p") -> str:
        cmd = [self.binary, *self.extra_args, "-p", prompt]
        log.debug("ClaudeRunner: %s in %s", shlex.join(cmd), self.project_dir)
        env = os.environ.copy()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            self.evidence.write(
                "claude_run",
                label=label,
                project=str(self.project_dir),
                ok=False,
                error=f"timeout after {self.timeout}s",
            )
            raise ClaudeRunError(f"claude -p timed out: {exc}") from exc

        if proc.returncode != 0:
            self.evidence.write(
                "claude_run",
                label=label,
                project=str(self.project_dir),
                ok=False,
                error=proc.stderr[:500],
                exitCode=proc.returncode,
            )
            raise ClaudeRunError(
                f"claude -p exit {proc.returncode}: {proc.stderr[:300]}"
            )

        response = proc.stdout.strip()
        self.evidence.write(
            "claude_run",
            label=label,
            project=str(self.project_dir),
            ok=True,
            promptPreview=prompt[:200],
            responsePreview=response[:300],
            responseLen=len(response),
        )
        return response
