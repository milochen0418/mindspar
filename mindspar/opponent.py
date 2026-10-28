"""The AI across the table: it gets the same question as the person, from the AI Hub.

Mindspar holds no model and no key. It asks the hub for the role ``smart``
(``reflex_ddns_auth.ai``), and the hub answers with whatever model its page sets for this
app's opponent: switching models there is how one model is tried against another.

The AI writes three lines, which :func:`parse` reads::

    Answer: (8 − 2) × 4
    Confidence: 3
    Reason: 6 × 4 is 24.
"""

from __future__ import annotations

import dataclasses
import re
import unicodedata

from mindspar.puzzles import Puzzle

ROLE = "smart"
# What the hub's page says this app asks the role for (reflex_ddns_auth.ai.uses).
USES = {ROLE: "The AI opponent: it answers each question of a match, against the person playing"}
# Thinking models (qwen3.5, say) spend most of these thinking; a round's clock stops them sooner.
MAX_TOKENS = 12000

SYSTEM = {
    "zh": (
        "你正在玩「腦力擂台」，和一個人同時解同一題，每題只有一個正確答案。"
        "答對得 100 分 × 把握，答錯扣 50 分 × 把握；兩邊都答對時，先答的一方再加 50 分。\n"
        "只回覆下面三行，不要寫別的：\n"
        "答案：（你的答案）\n"
        "把握：（1、2 或 3。1＝不太確定，2＝有把握，3＝很確定）\n"
        "理由：（一句話）"
    ),
    "en": (
        "You are playing Mindspar: you and a person solve the same question at the same time, "
        "and each question has one right answer. A right answer scores 100 × your confidence, a "
        "wrong one loses 50 × your confidence, and when both are right, whoever answered first gets 50 more.\n"
        "Reply with exactly these three lines and nothing else:\n"
        "Answer: (your answer)\n"
        "Confidence: (1, 2 or 3. 1 = unsure, 2 = fairly sure, 3 = certain)\n"
        "Reason: (one sentence)"
    ),
}

_ANSWER = re.compile(r"^(?:答案|最終答案|answer|final answer)\s*[:：]\s*(.*)$", re.IGNORECASE)
_CONFIDENCE = re.compile(r"^(?:把握|信心|確定程度|confidence)\s*[:：]\s*(.*)$", re.IGNORECASE)
_REASON = re.compile(r"^(?:理由|原因|reason|why)\s*[:：]\s*(.*)$", re.IGNORECASE)
_THINKING = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


@dataclasses.dataclass
class Move:
    """What the AI answered to one question."""

    answer: str
    wager: int  # its confidence, 1 to 3: what it bets
    reason: str
    well_formed: bool  # it kept to the three lines


def messages(puzzle: Puzzle) -> list[dict[str, str]]:
    return [{"role": "user", "content": puzzle.prompt()}]


def parse(text: str) -> Move:
    """The AI's answer, confidence and reason, read as leniently as is fair: a missing confidence
    counts as 1, and an answer without its label is taken from the whole reply."""
    text = _THINKING.sub("", text or "").strip()  # kept as written: "4²" stays 4², not 42
    answer = reason = ""
    wager = 0
    found_answer = False
    rest = []
    for raw in text.splitlines():
        line = raw.strip().strip("*`#>-").strip().replace("**", "")
        if not line:
            continue
        if m := _ANSWER.match(line):
            if not found_answer:
                answer, found_answer = m.group(1).strip().strip("*`").strip(), True
        elif m := _CONFIDENCE.match(line):
            digits = re.findall(r"[123]", unicodedata.normalize("NFKC", m.group(1)))
            wager = wager or (int(digits[0]) if digits else 0)
        elif m := _REASON.match(line):
            reason = reason or m.group(1).strip()
        else:
            rest.append(line)
    if not found_answer:
        answer = " ".join(rest)
    return Move(answer=answer[:300], wager=wager or 1, reason=reason[:400], well_formed=found_answer and wager > 0)
