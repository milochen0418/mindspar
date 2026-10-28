"""The page: the lobby, a question, its reveal and the result."""

from __future__ import annotations

import reflex as rx

from mindspar.history import KindCell, ModelRow
from mindspar.state import Game, Row

T = Game.t

CARD = "rounded-2xl border border-slate-800 bg-slate-900/70 p-4 sm:p-5"
YOU = "text-amber-300"
AI = "text-cyan-300"


def _chip(label: rx.Var | str, active: rx.Var | bool, on_click: rx.EventHandler, test_id: str) -> rx.Component:
    return rx.el.button(
        label,
        on_click=on_click,
        data_testid=test_id,
        class_name=rx.cond(
            active,
            "rounded-full border border-amber-300 bg-amber-300/15 px-3.5 py-1.5 text-sm font-medium text-amber-200",
            "rounded-full border border-slate-700 px-3.5 py-1.5 text-sm text-slate-300 hover:border-slate-500",
        ),
    )


def header() -> rx.Component:
    return rx.el.header(
        rx.el.div(
            rx.icon("swords", size=22, class_name="text-amber-300"),
            rx.el.span(T["app"], class_name="text-lg font-semibold tracking-wide"),
            class_name="flex items-center gap-2",
        ),
        rx.el.button(
            rx.icon("languages", size=16),
            T["lang_other"],
            on_click=Game.switch_lang,
            data_testid="lang",
            class_name="flex items-center gap-1.5 rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-300 hover:border-slate-500",
        ),
        class_name="flex items-center justify-between py-4",
    )


# ------------------------------------------------------------ the lobby


def opponent_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("bot", size=28, class_name=AI),
            rx.el.div(
                rx.el.div(T["opponent"], class_name="text-xs uppercase tracking-wider text-slate-400"),
                rx.match(
                    Game.hub_state,
                    ("asking", rx.el.div(T["asking_hub"], data_testid="asking", class_name="text-slate-300")),
                    ("ok", rx.el.div(Game.opponent, data_testid="opponent", class_name="font-mono text-lg font-semibold text-cyan-200 break-all")),
                    ("none", rx.el.div(T["no_hub"], class_name="text-rose-300")),
                    rx.el.div(T["hub_error"], " ", Game.hub_error, class_name="text-rose-300 break-words"),
                ),
                class_name="min-w-0",
            ),
            class_name="flex items-start gap-3",
        ),
        rx.el.p(T["change_model_help"], class_name="mt-3 text-sm leading-relaxed text-slate-400"),
        rx.cond(
            Game.hub_page != "",
            rx.el.a(
                T["change_model"],
                rx.icon("external-link", size=14),
                href=Game.hub_page,
                target="_blank",
                class_name="mt-2 inline-flex items-center gap-1 text-sm text-cyan-300 hover:underline",
            ),
        ),
        class_name=CARD,
    )


def settings_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(T["level"], class_name="mb-2 text-sm text-slate-400"),
            rx.el.div(
                _chip(T["easy"], Game.level == "easy", Game.set_level("easy"), "level-easy"),
                _chip(T["normal"], Game.level == "normal", Game.set_level("normal"), "level-normal"),
                _chip(T["hard"], Game.level == "hard", Game.set_level("hard"), "level-hard"),
                class_name="flex flex-wrap gap-2",
            ),
        ),
        rx.el.div(
            rx.el.div(T["length"], class_name="mb-2 text-sm text-slate-400"),
            rx.el.div(
                _chip(T["length_3"], Game.length == "3", Game.set_length("3"), "length-3"),
                _chip(T["length_7"], Game.length == "7", Game.set_length("7"), "length-7"),
                class_name="flex flex-wrap gap-2",
            ),
            class_name="mt-4",
        ),
        rx.el.button(
            rx.icon("swords", size=18),
            T["start"],
            on_click=Game.start,
            disabled=Game.hub_state != "ok",
            data_testid="start",
            class_name="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-amber-400 py-3 text-base font-semibold text-slate-950 hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-40",
        ),
        class_name=CARD,
    )


def rules_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(T["rules_title"], class_name="mb-2 font-semibold"),
        rx.el.ol(
            *[rx.el.li(T[f"rule_{i}"]) for i in range(1, 5)],
            class_name="list-decimal space-y-1.5 pl-5 text-sm leading-relaxed text-slate-300",
        ),
        class_name=CARD,
    )


def _kind_cell(cell: KindCell) -> rx.Component:
    return rx.el.div(
        rx.el.div(cell.label, class_name="truncate text-[11px] text-slate-400"),
        rx.el.div(
            cell.right,
            class_name=rx.match(
                cell.tone,
                ("good", "font-mono text-sm text-emerald-300"),
                ("fair", "font-mono text-sm text-amber-200"),
                ("poor", "font-mono text-sm text-rose-300"),
                "font-mono text-sm text-slate-500",
            ),
        ),
        class_name="min-w-0 rounded-lg bg-slate-800/60 px-2 py-1",
    )


def _stat(label: rx.Var | str, value: rx.Var | str) -> rx.Component:
    return rx.el.div(
        rx.el.div(label, class_name="text-[11px] text-slate-400"),
        rx.el.div(value, class_name="font-mono text-base text-slate-100"),
    )


def _model_row(row: ModelRow) -> rx.Component:
    return rx.el.div(
        rx.el.div(row.model, class_name="font-mono font-semibold text-cyan-200 break-all"),
        rx.el.div(
            _stat(T["col_matches"], row.matches),
            _stat(T["col_record"], rx.el.span(row.you_won, " / ", row.ai_won, " / ", row.draws)),
            _stat(T["col_ai_right"], row.ai_right),
            _stat(T["col_ai_secs"], row.ai_secs),
            _stat(T["col_sure"], row.sure_right),
            class_name="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-5",
        ),
        rx.el.div(T["col_kinds"], class_name="mt-3 text-xs text-slate-400"),
        rx.el.div(rx.foreach(row.kinds, _kind_cell), class_name="mt-1 grid grid-cols-4 gap-1.5 sm:grid-cols-7"),
        class_name="rounded-xl border border-slate-800 bg-slate-950/40 p-3",
    )


def board_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(rx.icon("trophy", size=18, class_name="text-amber-300"), T["board"], class_name="flex items-center gap-2 font-semibold"),
        rx.el.p(T["board_help"], class_name="mt-1 text-sm text-slate-400"),
        rx.cond(
            Game.board.length() > 0,
            rx.el.div(rx.foreach(Game.board, _model_row), data_testid="board", class_name="mt-3 space-y-3"),
            rx.el.p(T["board_empty"], class_name="mt-3 text-sm text-slate-500"),
        ),
        class_name=CARD,
    )


def lobby() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h1(T["app"], class_name="text-3xl font-bold sm:text-4xl"),
            rx.el.p(T["tagline"], class_name="mt-2 text-slate-300"),
            class_name="py-4",
        ),
        rx.el.div(
            rx.el.div(opponent_card(), settings_card(), class_name="space-y-4"),
            rules_card(),
            class_name="grid gap-4 md:grid-cols-2",
        ),
        rx.el.div(board_card(), class_name="mt-4"),
        data_testid="lobby",
    )


# ------------------------------------------------------------ a question


def scorebar() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(rx.icon("user", size=16), T["you"], rx.el.span(Game.my_score, data_testid="my-score", class_name="font-mono text-xl font-bold"), class_name=f"flex items-center gap-1.5 {YOU}"),
            rx.el.div(Game.round_title, class_name="text-sm text-slate-400"),
            rx.el.div(rx.el.span(Game.ai_score, data_testid="ai-score", class_name="font-mono text-xl font-bold"), T["ai"], rx.icon("bot", size=16), class_name=f"flex items-center gap-1.5 {AI}"),
            class_name="flex items-center justify-between",
        ),
        rx.el.div(
            rx.el.div(class_name="h-full bg-amber-400 transition-all duration-700", style={"width": Game.my_share}),
            class_name="mt-2 h-2 overflow-hidden rounded-full bg-cyan-400",
        ),
    )


def question_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(Game.q_label, class_name="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-medium text-slate-200"),
            rx.el.span(Game.q_tests, class_name="text-xs text-slate-500"),
            class_name="flex items-center gap-2",
        ),
        rx.el.p(Game.q_text, data_testid="question", class_name="mt-3 whitespace-pre-wrap text-xl leading-relaxed sm:text-2xl"),
        rx.cond(
            Game.q_figure != "",
            rx.cond(
                Game.phase == "reveal",
                rx.el.p(
                    rx.foreach(Game.segs, lambda s: rx.el.span(s.text, class_name=rx.cond(s.hit, "rounded bg-amber-300 text-slate-950", ""))),
                    class_name="mt-3 break-all font-mono text-xl tracking-[0.2em] sm:text-2xl",
                ),
                rx.el.p(Game.q_figure, data_testid="figure", class_name="mt-3 break-all font-mono text-xl tracking-[0.2em] sm:text-2xl"),
            ),
        ),
        class_name=CARD,
    )


def clock() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(class_name="h-full bg-slate-300 transition-all duration-1000 ease-linear", style={"width": Game.time_share}),
            class_name="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800",
        ),
        rx.el.span(rx.icon("timer", size=14), T["left"], " ", Game.left, " ", T["seconds"], data_testid="clock", class_name="flex items-center gap-1 whitespace-nowrap font-mono text-sm text-slate-300"),
        class_name="flex items-center gap-3",
    )


def wager_picker() -> rx.Component:
    return rx.el.div(
        rx.el.span(T["confidence"], class_name="text-sm text-slate-400"),
        _chip(T["wager_1"], Game.wager == 1, Game.set_wager(1), "wager-1"),
        _chip(T["wager_2"], Game.wager == 2, Game.set_wager(2), "wager-2"),
        _chip(T["wager_3"], Game.wager == 3, Game.set_wager(3), "wager-3"),
        class_name="flex flex-wrap items-center gap-2",
    )


def answer_box() -> rx.Component:
    return rx.cond(
        Game.q_type == "choice",
        rx.el.div(
            rx.foreach(
                Game.q_choices,
                lambda c: rx.el.button(
                    c,
                    on_click=Game.choose(c),
                    class_name="rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-2.5 text-base hover:border-amber-300 hover:text-amber-200",
                ),
            ),
            data_testid="choices",
            class_name="flex flex-wrap gap-2",
        ),
        rx.el.form(
            rx.el.input(
                name="answer",
                placeholder=rx.cond(Game.q_type == "expr", T["expr_answer"], T["your_answer"]),
                auto_focus=True,
                auto_complete="off",
                input_mode=rx.cond(Game.q_type == "int", "numeric", "text"),
                data_testid="answer",
                class_name="min-w-0 flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 font-mono text-lg outline-none focus:border-amber-300",
            ),
            rx.el.button(T["submit"], type="submit", data_testid="submit", class_name="rounded-xl bg-amber-400 px-5 font-semibold text-slate-950 hover:bg-amber-300"),
            on_submit=Game.submit,
            reset_on_submit=True,
            class_name="flex gap-2",
        ),
    )


def you_panel() -> rx.Component:
    return rx.el.div(
        rx.el.div(rx.icon("user", size=18), T["you"], class_name=f"flex items-center gap-2 font-semibold {YOU}"),
        rx.cond(
            Game.my_done,
            rx.el.div(
                rx.el.div(
                    rx.cond(Game.my_answer != "", rx.el.span(T["you_answered"], "：", rx.el.span(Game.my_answer, class_name="font-mono text-amber-200"), " ×", Game.wager), T["skipped"]),
                    " · ",
                    Game.my_secs,
                    " s",
                    class_name="text-slate-200",
                ),
                rx.cond(Game.ai_status == "thinking", rx.el.div(T["waiting_ai"], class_name="mt-1 text-sm text-slate-400")),
                data_testid="my-done",
                class_name="mt-3",
            ),
            rx.el.div(
                wager_picker(),
                rx.el.div(answer_box(), class_name="mt-3"),
                rx.el.button(T["skip"], on_click=Game.skip, data_testid="skip", class_name="mt-3 text-sm text-slate-500 hover:text-slate-300"),
                class_name="mt-3",
            ),
        ),
        class_name=CARD,
    )


def ai_panel() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("bot", size=18),
            T["ai"],
            rx.el.span(Game.model, class_name="truncate font-mono text-xs font-normal text-slate-400"),
            class_name=f"flex min-w-0 items-center gap-2 font-semibold {AI}",
        ),
        rx.match(
            Game.ai_status,
            (
                "thinking",
                rx.el.div(
                    rx.icon("loader-circle", size=18, class_name="animate-spin text-cyan-300"),
                    T["thinking"],
                    " ",
                    Game.limit - Game.left,
                    " s",
                    class_name="mt-3 flex items-center gap-2 text-slate-200",
                ),
            ),
            ("answered", rx.el.div(rx.icon("check", size=18, class_name="text-cyan-300"), T["ai_answered"], " · ", Game.ai_secs, " s", class_name="mt-3 flex flex-wrap items-center gap-1.5 text-slate-200")),
            ("timeout", rx.el.div(T["ai_timeout"], class_name="mt-3 text-slate-400")),
            rx.el.div(T["ai_failed"], class_name="mt-3 text-rose-300"),
        ),
        data_testid="ai-panel",
        class_name=CARD,
    )


def _result_card(who: rx.Var | str, icon: str, color: str, answered: rx.Var, answer: rx.Var, wager: rx.Var, ok: rx.Var, points: rx.Var, secs: rx.Var, first: rx.Var, extra: rx.Component, test_id: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(rx.icon(icon, size=18), who, class_name=f"flex items-center gap-2 font-semibold {color}"),
            rx.el.span(
                rx.cond(points > 0, "+", ""),
                points,
                " ",
                T["points"],
                class_name=rx.cond(points > 0, "font-mono text-lg font-bold text-emerald-300", rx.cond(points < 0, "font-mono text-lg font-bold text-rose-300", "font-mono text-lg font-bold text-slate-400")),
            ),
            class_name="flex items-center justify-between",
        ),
        rx.cond(
            answered,
            rx.el.div(
                rx.cond(ok, rx.icon("circle-check", size=18, class_name="text-emerald-300"), rx.icon("circle-x", size=18, class_name="text-rose-300")),
                rx.el.span(answer, class_name="font-mono break-all"),
                rx.el.span("×", wager, class_name="text-slate-400"),
                rx.el.span(secs, " s", class_name="text-slate-400"),
                class_name="mt-2 flex flex-wrap items-center gap-2",
            ),
            rx.el.div(T["no_answer"], class_name="mt-2 text-slate-400"),
        ),
        rx.cond(first, rx.el.div(rx.icon("zap", size=14), T["first"], class_name="mt-2 inline-flex items-center gap-1 rounded-full bg-amber-300/15 px-2 py-0.5 text-xs text-amber-200")),
        extra,
        data_testid=test_id,
        class_name=CARD,
    )


def reveal() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(T["answer_is"], class_name="text-xs uppercase tracking-wider text-slate-400"),
            rx.el.div(Game.solution, data_testid="solution", class_name="mt-1 font-mono text-2xl font-bold text-emerald-300 break-all"),
            rx.el.p(Game.explain, class_name="mt-1 text-sm leading-relaxed text-slate-300"),
            class_name=CARD,
        ),
        rx.el.div(
            _result_card(T["you"], "user", YOU, Game.my_answer != "", Game.my_answer, Game.wager, Game.my_ok, Game.my_points, Game.my_secs, Game.first == "you", rx.fragment(), "my-result"),
            _result_card(
                T["ai"],
                "bot",
                AI,
                Game.ai_answer != "",
                Game.ai_answer,
                Game.ai_wager,
                Game.ai_ok,
                Game.ai_points,
                Game.ai_secs,
                Game.first == "ai",
                rx.el.div(
                    rx.cond(Game.ai_reason != "", rx.el.p(rx.el.span(T["reason"], "：", class_name="text-slate-400"), Game.ai_reason, class_name="mt-2 text-sm leading-relaxed text-slate-300")),
                    rx.cond(Game.ai_note != "", rx.el.p(Game.ai_note, class_name="mt-2 text-sm text-rose-300 break-words")),
                ),
                "ai-result",
            ),
            class_name="grid gap-4 md:grid-cols-2",
        ),
        rx.el.button(
            rx.cond(Game.round_no >= Game.total, T["see_result"], T["next"]),
            rx.icon("arrow-right", size=18),
            on_click=Game.next_question,
            auto_focus=True,
            data_testid="next",
            class_name="flex w-full items-center justify-center gap-2 rounded-xl bg-amber-400 py-3 font-semibold text-slate-950 hover:bg-amber-300",
        ),
        class_name="space-y-4",
    )


def playing() -> rx.Component:
    return rx.el.div(
        scorebar(),
        question_card(),
        rx.cond(
            Game.phase == "question",
            rx.el.div(
                clock(),
                rx.el.div(you_panel(), ai_panel(), class_name="grid gap-4 md:grid-cols-2"),
                class_name="space-y-4",
            ),
            reveal(),
        ),
        rx.el.button(T["quit"], on_click=Game.leave, class_name="text-sm text-slate-500 hover:text-slate-300"),
        data_testid="playing",
        class_name="space-y-4",
    )


def warming() -> rx.Component:
    return rx.el.div(
        rx.icon("loader-circle", size=32, class_name="animate-spin text-cyan-300"),
        rx.el.p(T["warmup"], class_name="text-slate-300"),
        rx.el.p(Game.model, class_name="font-mono text-sm text-slate-500"),
        data_testid="warmup",
        class_name="flex flex-col items-center gap-3 py-24 text-center",
    )


# ------------------------------------------------------------ the result


def _row(row: Row) -> rx.Component:
    def tone(value: rx.Var) -> rx.Var:
        return rx.match(value, ("right", "text-emerald-300"), ("wrong", "text-rose-300"), "text-slate-500")

    return rx.el.tr(
        rx.el.td(row.no, class_name="py-2 pr-3 text-slate-500"),
        rx.el.td(row.kind, class_name="py-2 pr-3"),
        rx.el.td(row.solution, class_name="py-2 pr-3 font-mono break-all"),
        rx.el.td(row.you, class_name=tone(row.you_tone).to(str) + " py-2 pr-3 font-mono whitespace-nowrap"),
        rx.el.td(row.ai, class_name=tone(row.ai_tone).to(str) + " py-2 pr-3 font-mono whitespace-nowrap"),
        rx.el.td(row.ai_secs, class_name="py-2 font-mono text-slate-400"),
        class_name="border-t border-slate-800",
    )


def result() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.match(
                Game.winner,
                ("you", rx.el.div(rx.icon("trophy", size=36, class_name="text-amber-300"), rx.el.div(T["you_win"], class_name="text-3xl font-bold text-amber-200"), class_name="flex flex-col items-center gap-2")),
                ("ai", rx.el.div(rx.icon("bot", size=36, class_name="text-cyan-300"), rx.el.div(T["ai_wins"], class_name="text-3xl font-bold text-cyan-200"), class_name="flex flex-col items-center gap-2")),
                rx.el.div(rx.icon("handshake", size=36, class_name="text-slate-300"), rx.el.div(T["draw"], class_name="text-3xl font-bold"), class_name="flex flex-col items-center gap-2"),
            ),
            rx.el.div(
                rx.el.span(T["you"], " ", rx.el.span(Game.my_score, class_name="font-mono font-bold"), class_name=YOU),
                rx.el.span(":", class_name="text-slate-500"),
                rx.el.span(rx.el.span(Game.ai_score, class_name="font-mono font-bold"), " ", T["ai"], class_name=AI),
                class_name="mt-3 flex items-center justify-center gap-3 text-xl",
            ),
            rx.el.div(Game.model, class_name="mt-1 text-center font-mono text-sm text-slate-500"),
            data_testid="result",
            class_name=CARD + " py-8",
        ),
        rx.el.div(
            rx.el.div(T["ai_report"], class_name="font-semibold"),
            rx.el.div(
                _stat(T["rep_right"], Game.rep_right),
                _stat(T["rep_secs"], rx.el.span(Game.rep_secs, " s")),
                _stat(T["rep_sure"], Game.rep_sure),
                _stat(T["rep_format"], Game.rep_format),
                class_name="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4",
            ),
            class_name=CARD,
        ),
        rx.el.div(
            rx.el.div(T["this_match"], class_name="font-semibold"),
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            rx.el.th("#", class_name="py-2 pr-3 text-left font-normal"),
                            rx.el.th(T["col_kind"], class_name="py-2 pr-3 text-left font-normal"),
                            rx.el.th(T["col_answer"], class_name="py-2 pr-3 text-left font-normal"),
                            rx.el.th(T["col_you"], class_name="py-2 pr-3 text-left font-normal"),
                            rx.el.th(T["col_ai"], class_name="py-2 pr-3 text-left font-normal"),
                            rx.el.th(T["col_ai_time"], class_name="py-2 text-left font-normal"),
                            class_name="text-xs text-slate-400",
                        )
                    ),
                    rx.el.tbody(rx.foreach(Game.rows, _row)),
                    class_name="w-full text-sm",
                ),
                class_name="mt-2 overflow-x-auto",
            ),
            class_name=CARD,
        ),
        rx.el.div(
            rx.el.button(rx.icon("rotate-ccw", size=18), T["again"], on_click=Game.start, data_testid="again", class_name="flex flex-1 items-center justify-center gap-2 rounded-xl bg-amber-400 py-3 font-semibold text-slate-950 hover:bg-amber-300"),
            rx.el.button(T["lobby"], on_click=Game.leave, data_testid="to-lobby", class_name="flex-1 rounded-xl border border-slate-700 py-3 text-slate-200 hover:border-slate-500"),
            class_name="flex gap-3",
        ),
        class_name="space-y-4",
    )


def index() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            header(),
            rx.match(
                Game.phase,
                ("lobby", lobby()),
                ("warmup", warming()),
                ("result", result()),
                playing(),
            ),
            class_name="mx-auto max-w-4xl px-4 pb-16",
        ),
        class_name="min-h-screen bg-slate-950 text-slate-100",
    )
