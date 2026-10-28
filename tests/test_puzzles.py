import datetime
import random

import pytest

from mindspar import puzzles
from mindspar.puzzles import Puzzle, check, make, pick


@pytest.mark.parametrize("kind", puzzles.KINDS)
@pytest.mark.parametrize("level", puzzles.LEVELS)
@pytest.mark.parametrize("lang", puzzles.LANGS)
def test_every_question_knows_its_answer(kind, level, lang):
    rng = random.Random(f"{kind}{level}{lang}")
    for _ in range(25):
        puzzle = make(kind, level, lang, rng)
        assert puzzle.text and puzzle.hint and puzzle.explain
        assert check(puzzle, puzzle.solution), puzzle
        assert not check(puzzle, "")
        if puzzle.answer_type == "choice":
            assert puzzle.solution in puzzle.choices
            assert len(set(puzzle.choices)) == len(puzzle.choices)
            for other in puzzle.choices:
                assert check(puzzle, other) == (other == puzzle.solution)
        elif puzzle.answer_type == "int":
            assert puzzle.value > 0
            assert not check(puzzle, str(puzzle.value + 1))


def test_the_prompt_has_the_figure_and_the_hint():
    puzzle = make("count", "normal", "en", random.Random(1))
    prompt = puzzle.prompt()
    assert puzzle.figure in prompt and puzzle.hint in prompt
    assert puzzle.figure.count(puzzle.mark) == puzzle.value


def _target() -> Puzzle:
    return Puzzle("target", "normal", "zh", "", "expr", "", "", "", value=24, numbers=[8, 2, 4, 1])


@pytest.mark.parametrize(
    "answer",
    ["(8 - 2) * 4 * 1", "(8−2)×4×1", "（8－2）×４÷１", "(8 - 2) x 4 x 1", "4 * (8 - 2) / 1 = 24", "24 = (8-2)*4*1", "$(8-2)\\times 4\\times 1$"],
)
def test_a_calculation_is_read_however_it_is_written(answer):
    assert check(_target(), answer)


@pytest.mark.parametrize(
    "answer",
    ["24", "(8 - 2) * 4", "(8 - 2) * 4 * 1 * 1", "8 * 3 * 1", "(82 - 4) / 1", "6 * 4", "(8 - 2) * 4 + 1", "import os", "8/0+2*4*1"],
)
def test_a_calculation_must_use_each_number_once_and_be_right(answer):
    assert not check(_target(), answer)


def test_int_answers_take_the_first_number():
    puzzle = Puzzle("arith", "easy", "zh", "", "int", "1657", "", "", value=1657)
    assert check(puzzle, "1,657")
    assert check(puzzle, "答案是 １６５７")
    assert not check(puzzle, "1658")
    assert not check(puzzle, "約一千六百")


def test_weekdays_in_either_language():
    puzzle = make("calendar", "easy", "zh", random.Random(3), today=datetime.date(2026, 10, 29))
    day = puzzles.WEEKDAYS["zh"].index(puzzle.solution)
    assert check(puzzle, puzzles.WEEKDAYS["en"][day])
    assert check(puzzle, puzzles.WEEKDAYS["zh"][day].replace("星期", "週"))
    assert not check(puzzle, puzzles.WEEKDAYS["zh"][(day + 1) % 7])


def test_the_calendar_is_right():
    rng = random.Random(5)
    today = datetime.date(2026, 10, 29)  # a Thursday
    for level in puzzles.LEVELS:
        for _ in range(20):
            puzzle = make("calendar", level, "en", rng, today=today)
            assert puzzle.text.startswith("Today is Thursday")


def test_decimals_pick_the_number_named():
    puzzle = Puzzle("trick", "normal", "zh", "", "choice", "9.9", "", "", choices=["9.11", "9.9"])
    assert pick(puzzle, "9.9 比較大") == "9.9"
    assert pick(puzzle, "9.11") == "9.11"
    assert not check(puzzle, "9.11")
    assert check(puzzle, "答案：9.9")


def test_names_pick_the_first_one_mentioned():
    puzzle = Puzzle("order", "normal", "zh", "", "choice", "小華", "", "", choices=["小明", "小華"])
    assert check(puzzle, "小華")
    assert not check(puzzle, "小明比小華高")


def test_who_is_where_is_settled_by_the_clues():
    rng = random.Random(11)
    for level in puzzles.LEVELS:
        for _ in range(30):
            puzzle = make("order", level, "en", rng)
            assert set(puzzle.choices) <= set(puzzles.NAMES["en"])
            assert len(puzzle.choices) == {"easy": 4, "normal": 5, "hard": 6}[level]


def test_make_the_number_needs_more_than_adding():
    rng = random.Random(2)
    for level in ("easy", "hard"):
        for _ in range(20):
            puzzle = make("target", level, "en", rng)
            assert puzzle.value != 24
            assert puzzle.value not in {int(v) for v in puzzles._reach(puzzle.numbers, "+-") if v.denominator == 1}
