"""A match, per browser tab: the lobby, each question's clock with the AI answering at the same
time, the reveal and the result.

Each question is played by one background task: it asks the AI (``_ask``) and ticks the clock
until both sides have answered or time is up. The AI's answer stays on the server until the
reveal, so it can't be peeked at in the browser.
"""

from __future__ import annotations

import asyncio
import dataclasses
import math
import random
import time
from typing import Any
from urllib.parse import urlsplit

import reflex as rx
from reflex_ddns_auth import ai

from mindspar import history, opponent, puzzles
from mindspar.i18n import TEXT, kind_labels

# Seconds per question, the same for both sides. A thinking model (qwen3.5:9b) takes 10-100 s
# on a normal question and sometimes thinks in circles: that shows up as time running out.
LIMITS = {"easy": 60, "normal": 90, "hard": 150}
TICK = 0.25
WARMUP_TIMEOUT = 90.0


@dataclasses.dataclass
class Asked:
    """What came back from the hub for one question."""

    text: str = ""
    model: str = ""
    stop: str = ""
    error: str = ""
    secs: float = 0.0


async def _ask(puzzle: puzzles.Puzzle, started: float) -> Asked:
    out = Asked()
    try:
        reply = ai.stream(opponent.ROLE, opponent.SYSTEM[puzzle.lang], opponent.messages(puzzle), max_tokens=opponent.MAX_TOKENS)
        out.text = "".join([piece async for piece in reply])
        out.model, out.stop = reply.model, reply.stop
    except ai.HubUnavailable as e:
        out.error = str(e)
    except Exception as e:  # noqa: BLE001 - whatever it was, the round goes on without the AI
        out.error = f"{type(e).__name__}: {e}"
    out.secs = round(time.time() - started, 1)
    return out


@dataclasses.dataclass
class Seg:
    """A piece of the counted string, highlighted when it is the counted character."""

    text: str
    hit: bool


@dataclasses.dataclass
class Row:
    """One question in the result's table."""

    no: int
    kind: str
    solution: str
    you: str
    you_tone: str  # right, wrong or none
    ai: str
    ai_tone: str
    ai_secs: str


def _points(points: int) -> str:
    return f"+{points}" if points > 0 else f"−{-points}" if points < 0 else "0"


class Game(rx.State):
    lang: str = rx.LocalStorage("", name="mindspar_lang")
    level: str = rx.LocalStorage("normal", name="mindspar_level")
    length: str = rx.LocalStorage("7", name="mindspar_length")

    # the lobby
    hub_state: str = "asking"  # asking, ok, none (no hub) or error
    hub_error: str = ""
    opponent: str = ""  # what answers, e.g. "Ollama (qwen3.5:9b)"
    opponent_local: bool = False
    board: list[history.ModelRow] = []

    # the match
    phase: str = "lobby"  # lobby, warmup, question, reveal or result
    model: str = ""
    round_no: int = 0
    total: int = 0
    my_score: int = 0
    ai_score: int = 0

    # the question
    q_kind: str = ""
    q_text: str = ""
    q_figure: str = ""
    q_type: str = ""  # int, expr or choice
    q_choices: list[str] = []
    limit: int = 60
    left: int = 60

    # the person
    wager: int = 1
    my_done: bool = False
    my_answer: str = ""
    my_secs: float = 0.0

    # the AI, while the question is open: whether and when it answered, never what
    ai_status: str = ""  # thinking, answered, timeout or failed
    ai_secs: float = 0.0

    # the reveal
    solution: str = ""
    explain: str = ""
    segs: list[Seg] = []
    my_ok: bool = False
    my_points: int = 0
    ai_answer: str = ""
    ai_wager: int = 0
    ai_reason: str = ""
    ai_ok: bool = False
    ai_points: int = 0
    ai_note: str = ""
    first: str = ""  # who got the 50 for answering first: you, ai or ""

    # the result
    rows: list[Row] = []
    rep_right: str = ""
    rep_secs: str = ""
    rep_sure: str = ""
    rep_format: int = 0

    _seq: int = 0  # a new number for every question and match: older tasks see it and stop
    _plan: list[str] = []
    _puzzle: puzzles.Puzzle | None = None
    _started: float = 0.0
    _move: opponent.Move | None = None
    _ai_error: str = ""
    _rounds: list[dict[str, Any]] = []

    # ------------------------------------------------------------ words

    @rx.var
    def t(self) -> dict[str, str]:
        return TEXT.get(self.lang, TEXT["zh"])

    @rx.var
    def q_label(self) -> str:
        return self.t.get(f"kind_{self.q_kind}", "")

    @rx.var
    def q_tests(self) -> str:
        return self.t.get(f"test_{self.q_kind}", "")

    @rx.var
    def round_title(self) -> str:
        if self.lang == "en":
            return f"Question {self.round_no} of {self.total}"
        return f"第 {self.round_no} / {self.total} 題"

    @rx.var
    def my_share(self) -> str:
        """How far the person's colour reaches on the score bar."""
        spread = max(abs(self.my_score) + abs(self.ai_score), 400)
        share = 50 + 50 * (self.my_score - self.ai_score) / spread
        return f"{min(95, max(5, share)):.0f}%"

    @rx.var
    def time_share(self) -> str:
        return f"{100 * self.left / max(self.limit, 1):.0f}%"

    @rx.var
    def winner(self) -> str:
        return "you" if self.my_score > self.ai_score else "ai" if self.ai_score > self.my_score else "draw"

    @rx.var
    def hub_page(self) -> str:
        """The AI Hub's page, next to this app on the same domain ("" when run on its own)."""
        parts = urlsplit(self.router.headers.origin or "")
        host = parts.hostname or ""
        if "." not in host or host.replace(".", "").isdigit():
            return ""
        return f"{parts.scheme}://ai.{host.split('.', 1)[1]}"

    # ------------------------------------------------------------ the lobby

    @rx.event
    def on_load(self):
        if self.lang not in TEXT:
            self.lang = "zh" if "zh" in (self.router.headers.accept_language or "").lower() else "en"
        # A restart of the server (a hot reload) ends the task that ran the question: its clock
        # would never move again, so a long-past one goes back to the lobby.
        late = time.time() - self._started
        if (self.phase == "question" and late > self.limit + 10) or (self.phase == "warmup" and late > WARMUP_TIMEOUT + 10):
            self._seq += 1
            self.phase = "lobby"
        self._load_board()
        if self.phase == "lobby":
            return Game.check_opponent

    def _load_board(self) -> None:
        self.board = history.board(history.load(), kind_labels(self.lang))

    @rx.event
    def switch_lang(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self._load_board()

    @rx.event
    def set_level(self, level: str):
        if level in puzzles.LEVELS:
            self.level = level

    @rx.event
    def set_length(self, length: str):
        if length in ("3", "7"):
            self.length = length

    @rx.event(background=True)
    async def check_opponent(self):
        async with self:
            self.hub_state = "asking"
        status = await ai.status(opponent.ROLE)
        async with self:
            if status is None:
                self.hub_state, self.opponent = "none", ""
            elif status.get("ok"):
                self.hub_state, self.opponent = "ok", str(status.get("model") or "")
                self.opponent_local = bool(status.get("local"))
            else:
                self.hub_state, self.opponent = "error", ""
                self.hub_error = str(status.get("error") or "")

    # ------------------------------------------------------------ a match

    @rx.event
    def start(self):
        if self.hub_state != "ok" or self.phase not in ("lobby", "result"):
            return
        kinds = list(puzzles.KINDS)
        random.shuffle(kinds)
        self._plan = kinds[:3] if self.length == "3" else kinds
        self.total = len(self._plan)
        self.round_no = self.my_score = self.ai_score = 0
        self.rows, self._rounds = [], []
        self.model = self.opponent
        self._seq += 1
        self._started = time.time()
        self.phase = "warmup"
        return Game.warm_up

    @rx.event(background=True)
    async def warm_up(self):
        """Loads a local model before the first question, so its loading isn't counted as
        thinking; a model in the cloud needs none."""
        async with self:
            seq, local = self._seq, self.opponent_local
        if local:
            try:
                await asyncio.wait_for(ai.complete(opponent.ROLE, "Reply with OK.", [{"role": "user", "content": "OK?"}], max_tokens=1), WARMUP_TIMEOUT)
            except Exception:  # noqa: BLE001 - the first question will say what is wrong
                pass
        async with self:
            if self._seq != seq or self.phase != "warmup":
                return
            setup = self._setup_round()
        await self._run_round(*setup)

    @rx.event(background=True)
    async def next_question(self):
        async with self:
            if self.phase != "reveal":
                return
            if self.round_no >= self.total:
                self._finish()
                return
            setup = self._setup_round()
        await self._run_round(*setup)

    def _setup_round(self) -> tuple[int, puzzles.Puzzle, float, int]:
        """Shows the next question (under the state's lock)."""
        self._seq += 1
        puzzle = puzzles.make(self._plan[self.round_no], self.level, self.lang)
        self.round_no += 1
        self._puzzle, self._move, self._ai_error = puzzle, None, ""
        self.q_kind, self.q_text, self.q_figure = puzzle.kind, puzzle.text, puzzle.figure
        self.q_type, self.q_choices = puzzle.answer_type, list(puzzle.choices)
        self.wager, self.my_done, self.my_answer, self.my_secs = 1, False, "", 0.0
        self.ai_status, self.ai_secs = "thinking", 0.0
        self.limit = self.left = LIMITS.get(self.level, 60)
        self.phase = "question"
        self._started = time.time()
        return self._seq, puzzle, self._started, self.limit

    async def _run_round(self, seq: int, puzzle: puzzles.Puzzle, started: float, limit: int) -> None:
        asking = asyncio.create_task(_ask(puzzle, started))
        deadline = started + limit
        try:
            while True:
                await asyncio.wait({asking}, timeout=TICK)
                now = time.time()
                async with self:
                    if self._seq != seq:
                        return
                    if asking.done() and self.ai_status == "thinking":
                        self._take(asking.result())
                    left = max(0, math.ceil(deadline - now))
                    if left != self.left:
                        self.left = left
                    if (self.my_done and self.ai_status != "thinking") or now >= deadline:
                        if self.ai_status == "thinking":
                            self.ai_status = "timeout"
                        self._reveal()
                        return
        finally:
            if not asking.done():
                asking.cancel()  # ends the hub's request, so the model stops too

    def _take(self, asked: Asked) -> None:
        self.ai_secs = asked.secs
        if asked.model:
            self.model = asked.model
        if asked.error:
            self.ai_status, self._ai_error = "failed", asked.error
        elif not asked.text.strip():
            self.ai_status = "failed"
            self._ai_error = self.t["ai_cut"] if asked.stop == "max_tokens" else self.t["ai_empty"]
        else:
            self.ai_status, self._move = "answered", opponent.parse(asked.text)

    # ------------------------------------------------------------ the person's answer

    @rx.event
    def set_wager(self, wager: int):
        if self.phase == "question" and not self.my_done and wager in (1, 2, 3):
            self.wager = wager

    @rx.event
    def submit(self, form: dict[str, Any]):
        self._answer(str(form.get("answer") or ""))

    @rx.event
    def choose(self, choice: str):
        self._answer(choice)

    @rx.event
    def skip(self):
        self._answer("", skip=True)

    def _answer(self, text: str, skip: bool = False) -> None:
        text = text.strip()[:200]
        if self.phase != "question" or self.my_done or (not text and not skip):
            return
        now = time.time()
        if now > self._started + self.limit:
            return
        self.my_answer, self.my_done, self.my_secs = text, True, round(now - self._started, 1)

    # ------------------------------------------------------------ the reveal and the result

    def _reveal(self) -> None:
        puzzle, move = self._puzzle, self._move
        if puzzle is None:
            return
        self.my_ok = bool(self.my_answer) and puzzles.check(puzzle, self.my_answer)
        self.my_points = ((100 if self.my_ok else -50) * self.wager) if self.my_answer else 0
        ai_answered = move is not None and bool(move.answer)
        self.ai_answer = move.answer if move else ""
        self.ai_wager = move.wager if move else 0
        self.ai_reason = move.reason if move else ""
        self.ai_ok = ai_answered and puzzles.check(puzzle, move.answer)
        self.ai_points = ((100 if self.ai_ok else -50) * move.wager) if ai_answered else 0
        self.ai_note = {
            "timeout": self.t["ai_timeout"],
            "failed": f"{self.t['ai_failed']}：{self._ai_error}" if self.lang == "zh" else f"{self.t['ai_failed']}: {self._ai_error}",
        }.get(self.ai_status, "")
        if move is not None and not move.well_formed:
            self.ai_note = self.t["bad_format"]
        self.first = ""
        if self.my_ok and self.ai_ok:
            self.first = "you" if self.my_secs <= self.ai_secs else "ai"
            if self.first == "you":
                self.my_points += 50
            else:
                self.ai_points += 50
        self.my_score += self.my_points
        self.ai_score += self.ai_points
        self.solution, self.explain = puzzle.solution, puzzle.explain
        self.segs = [Seg(c, c == puzzle.mark) for c in puzzle.figure] if puzzle.mark else []

        def said(answered: bool, ok: bool, points: int) -> tuple[str, str]:
            if not answered:
                return "—", "none"
            return f"{'✓' if ok else '✗'} {_points(points)}", "right" if ok else "wrong"

        you, you_tone = said(bool(self.my_answer), self.my_ok, self.my_points)
        them, them_tone = said(ai_answered, self.ai_ok, self.ai_points)
        ai_secs = f"{self.ai_secs:.1f}" if self.ai_status in ("answered", "failed") else "—"
        self.rows.append(Row(self.round_no, self.q_label, puzzle.solution, you, you_tone, them, them_tone, ai_secs))
        self._rounds.append(
            {
                "kind": puzzle.kind,
                "you_ok": self.my_ok,
                "you_points": self.my_points,
                "you_secs": self.my_secs if self.my_answer else None,
                "ai_ok": self.ai_ok,
                "ai_points": self.ai_points,
                "ai_secs": self.ai_secs if self.ai_status == "answered" else None,
                "ai_wager": self.ai_wager,
                "ai_answered": ai_answered,
                "ai_well_formed": bool(move and move.well_formed),
            }
        )
        self.phase = "reveal"

    def _finish(self) -> None:
        rounds = self._rounds
        history.save({"at": round(time.time()), "model": self.model, "level": self.level, "lang": self.lang, "you": self.my_score, "ai": self.ai_score, "rounds": rounds})
        right = sum(1 for r in rounds if r["ai_ok"])
        timed = [r["ai_secs"] for r in rounds if r["ai_secs"] is not None]
        sure = [r for r in rounds if r["ai_answered"] and r["ai_wager"] == 3]
        self.rep_right = f"{right} / {len(rounds)}"
        self.rep_secs = f"{sum(timed) / len(timed):.1f}" if timed else "—"
        self.rep_sure = f"{sum(1 for r in sure if r['ai_ok'])} / {len(sure)}" if sure else "—"
        self.rep_format = sum(1 for r in rounds if r["ai_answered"] and not r["ai_well_formed"])
        self.phase = "result"
        self._load_board()

    @rx.event
    def leave(self):
        """Back to the lobby (a match left halfway isn't kept)."""
        self._seq += 1
        self.phase = "lobby"
        self._load_board()
        return Game.check_opponent
