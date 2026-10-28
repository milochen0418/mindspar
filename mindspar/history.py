"""Every finished match, kept per model, so models can be compared: one JSON line per match in
``MINDSPAR_DATA_DIR`` (``~/.local/share/mindspar`` by default; the App Store keeps it in a
volume).

A match is ``{"at", "model", "level", "lang", "you", "ai", "rounds": [...]}``; a round is
``{"kind", "you_ok", "you_points", "you_secs", "ai_ok", "ai_points", "ai_secs", "ai_wager",
"ai_answered", "ai_well_formed"}`` (``*_secs`` is null for no answer).
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from mindspar.puzzles import KINDS

logger = logging.getLogger(__name__)
_lock = threading.Lock()


def data_dir() -> Path:
    return Path(os.environ.get("MINDSPAR_DATA_DIR") or Path.home() / ".local" / "share" / "mindspar")


def _file() -> Path:
    return data_dir() / "matches.jsonl"


def save(match: dict[str, Any]) -> None:
    path = _file()
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(match, ensure_ascii=False) + "\n")


def load() -> list[dict[str, Any]]:
    path = _file()
    if not path.exists():
        return []
    out = []
    with _lock, path.open(encoding="utf-8") as f:
        for line in f:
            try:
                match = json.loads(line)
            except ValueError:
                continue
            if isinstance(match, dict) and isinstance(match.get("rounds"), list):
                out.append(match)
    return out


@dataclasses.dataclass
class KindCell:
    kind: str
    label: str
    right: str  # "3/4", or "–" when the AI never got this kind
    tone: str  # good, fair, poor or none


@dataclasses.dataclass
class ModelRow:
    model: str
    matches: int
    you_won: int
    ai_won: int
    draws: int
    ai_right: str  # "64%"
    ai_secs: str  # "14.2"
    sure_right: str  # when it bet x3: "4/5" ("–" when it never did)
    kinds: list[KindCell]


def _tone(right: int, asked: int) -> str:
    if not asked:
        return "none"
    share = right / asked
    return "good" if share >= 0.75 else "fair" if share >= 0.4 else "poor"


def board(matches: list[dict[str, Any]], labels: dict[str, str]) -> list[ModelRow]:
    """A row per model, the most played first; ``labels`` names each kind."""
    by_model: dict[str, list[dict[str, Any]]] = {}
    for match in matches:
        by_model.setdefault(str(match.get("model") or "?"), []).append(match)
    rows = []
    for model, played in by_model.items():
        rounds = [r for m in played for r in m["rounds"]]
        right = sum(1 for r in rounds if r.get("ai_ok"))
        timed = [r["ai_secs"] for r in rounds if isinstance(r.get("ai_secs"), (int, float))]
        sure = [r for r in rounds if r.get("ai_wager") == 3 and r.get("ai_answered")]
        kinds = []
        for kind in KINDS:
            of_kind = [r for r in rounds if r.get("kind") == kind]
            ok = sum(1 for r in of_kind if r.get("ai_ok"))
            kinds.append(KindCell(kind, labels.get(kind, kind), f"{ok}/{len(of_kind)}" if of_kind else "–", _tone(ok, len(of_kind))))
        rows.append(
            ModelRow(
                model=model,
                matches=len(played),
                you_won=sum(1 for m in played if m.get("you", 0) > m.get("ai", 0)),
                ai_won=sum(1 for m in played if m.get("ai", 0) > m.get("you", 0)),
                draws=sum(1 for m in played if m.get("ai", 0) == m.get("you", 0)),
                ai_right=f"{round(100 * right / len(rounds))}%" if rounds else "–",
                ai_secs=f"{sum(timed) / len(timed):.1f}" if timed else "–",
                sure_right=f"{sum(1 for r in sure if r.get('ai_ok'))}/{len(sure)}" if sure else "–",
                kinds=kinds,
            )
        )
    rows.sort(key=lambda row: (-row.matches, row.model))
    return rows
