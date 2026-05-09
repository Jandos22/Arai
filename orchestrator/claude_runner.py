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
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .evidence import EvidenceLogger

log = logging.getLogger(__name__)


class ClaudeRunError(RuntimeError):
    pass


@dataclass
class ClaudeRunner:
    project_dir: Path
    evidence: EvidenceLogger
    timeout: float = 180.0
    binary: str = "claude"
    extra_args: tuple[str, ...] = ()

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
