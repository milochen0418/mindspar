"""The questions of a match, each made fresh from random numbers with its answer known, so the
person and the AI get the very same question and the game can tell who is right.

Seven kinds, each testing one thing a model may or may not be good at:

- ``arith``: mental arithmetic (calculating exactly)
- ``target``: make a number from given numbers with + - x / (planning, trying combinations)
- ``sequence``: the next number of a sequence (spotting a rule)
- ``order``: who is taller, from a few comparisons (deduction)
- ``count``: how often a letter or digit appears in a string (seeing single characters, which
  models read in chunks)
- ``calendar``: the day of the week of a date (date arithmetic)
- ``trick``: questions with a catch (not answering on autopilot)

``make(kind, level, lang, rng)`` gives a :class:`Puzzle` (``level``: easy, normal or hard;
``lang``: zh or en); ``check(puzzle, answer)`` says whether an answer is right, given as the
person typed or picked it, or as the AI wrote it.
"""

from __future__ import annotations

import ast
import dataclasses
import datetime
import itertools
import math
import random
import re
import unicodedata
from fractions import Fraction
from typing import Callable

KINDS = ("arith", "target", "sequence", "order", "count", "calendar", "trick")
LEVELS = ("easy", "normal", "hard")
LANGS = ("zh", "en")


@dataclasses.dataclass
class Puzzle:
    kind: str
    level: str
    lang: str
    text: str  # the question
    answer_type: str  # "int", "expr" (a calculation) or "choice"
    solution: str  # the right answer, as shown at the end of the round
    explain: str  # why, in a line or two
    hint: str  # how the AI is to write its answer
    figure: str = ""  # a string shown in a fixed-width font under the question (count)
    choices: list[str] = dataclasses.field(default_factory=list)
    value: int = 0  # int: the answer
    numbers: list[int] = dataclasses.field(default_factory=list)  # expr: the numbers to use
    mark: str = ""  # count: the character counted, highlighted when the answer is shown

    def prompt(self) -> str:
        """The question as the AI gets it."""
        parts = [self.text]
        if self.figure:
            parts.append(self.figure)
        parts.append(self.hint)
        return "\n\n".join(parts)


def make(kind: str, level: str, lang: str, rng: random.Random | None = None, today: datetime.date | None = None) -> Puzzle:
    rng = rng or random.Random()
    level = level if level in LEVELS else "normal"
    lang = lang if lang in LANGS else "zh"
    if kind == "calendar":
        return _calendar(level, lang, rng, today or datetime.date.today())
    maker: Callable[[str, str, random.Random], Puzzle] = {
        "arith": _arith,
        "target": _target,
        "sequence": _sequence,
        "order": _order,
        "count": _count,
        "trick": _trick,
    }[kind]
    return maker(level, lang, rng)


def _z(lang: str, zh: str, en: str) -> str:
    return zh if lang == "zh" else en


HINT_INT = {"zh": "答案只寫一個整數。", "en": "Answer with one whole number."}


def _int_puzzle(kind: str, level: str, lang: str, text: str, value: int, explain: str, figure: str = "", mark: str = "") -> Puzzle:
    return Puzzle(kind, level, lang, text, "int", str(value), explain, HINT_INT[lang], figure=figure, value=value, mark=mark)


# ------------------------------------------------------------ arith


def _arith(level: str, lang: str, rng: random.Random) -> Puzzle:
    if level == "easy":
        a, b, c = rng.randint(12, 49), rng.randint(3, 9), rng.randint(11, 99)
        value = a * b + c
        text = f"{a} × {b} + {c} = ?"
        explain = f"{a} × {b} = {a * b}，{a * b} + {c} = {value}" if lang == "zh" else f"{a} × {b} = {a * b}, {a * b} + {c} = {value}"
    elif level == "normal":
        while True:
            a, b, c = rng.randint(13, 99), rng.randint(13, 99), rng.randint(101, 999)
            if a * b > c:
                break
        value = a * b - c
        text = f"{a} × {b} − {c} = ?"
        explain = f"{a} × {b} = {a * b}，{a * b} − {c} = {value}" if lang == "zh" else f"{a} × {b} = {a * b}, {a * b} − {c} = {value}"
    else:
        while True:
            a, b, c, d = rng.randint(101, 999), rng.randint(13, 99), rng.randint(13, 99), rng.randint(13, 99)
            if a * b > c * d:
                break
        value = a * b - c * d
        text = f"{a} × {b} − {c} × {d} = ?"
        sep = "，" if lang == "zh" else ", "
        explain = sep.join([f"{a} × {b} = {a * b}", f"{c} × {d} = {c * d}", f"{a * b} − {c * d} = {value}"])
    return _int_puzzle("arith", level, lang, _z(lang, "算算看：", "Work it out: ") + text, value, explain)


# ------------------------------------------------------------ target


_ADD, _MUL, _ATOM = 1, 2, 3


def _wrap(expr: str, prec: int, need: int) -> str:
    return f"({expr})" if prec < need else expr


def _reach(numbers: list[int], ops: str = "+-*/") -> dict[Fraction, str]:
    """Every value the numbers make, each used once, with one way to write it."""
    out: dict[Fraction, str] = {}

    def go(items: list[tuple[Fraction, str, int]]) -> None:
        if len(items) == 1:
            out.setdefault(items[0][0], items[0][1])
            return
        for i, j in itertools.combinations(range(len(items)), 2):
            rest = [it for k, it in enumerate(items) if k not in (i, j)]
            for (a, ea, pa), (b, eb, pb) in (items[i], items[j]), (items[j], items[i]):
                made = []
                if "+" in ops and a >= b:  # + and x once per pair
                    made.append((a + b, f"{ea} + {eb}", _ADD))
                if "*" in ops and a >= b:
                    made.append((a * b, f"{_wrap(ea, pa, _MUL)} × {_wrap(eb, pb, _MUL)}", _MUL))
                if "-" in ops:
                    made.append((a - b, f"{ea} − {_wrap(eb, pb, _MUL)}", _ADD))
                if "/" in ops and b != 0:
                    made.append((a / b, f"{_wrap(ea, pa, _MUL)} ÷ {_wrap(eb, pb, _ATOM)}", _MUL))
                for value, expr, prec in made:
                    go([*rest, (value, expr, prec)])

    go([(Fraction(n), str(n), _ATOM) for n in numbers])
    return out


def _target(level: str, lang: str, rng: random.Random) -> Puzzle:
    while True:
        if level == "easy":
            numbers = [rng.randint(2, 9) for _ in range(3)]
        else:
            numbers = [rng.randint(1, 13) for _ in range(4)]
        reach = _reach(numbers)
        if level == "normal":
            target = 24
            if Fraction(24) in reach:
                break
            continue
        plain = _reach(numbers, "+-")  # what needs no x or /: too easy
        low, high = (10, 40) if level == "easy" else (30, 99)
        options = sorted(int(v) for v in reach if v.denominator == 1 and low <= v <= high and v not in plain and v != 24)
        if options:
            target = rng.choice(options)
            break
    shown = "、".join(map(str, numbers)) if lang == "zh" else ", ".join(map(str, numbers))
    text = _z(
        lang,
        f"用 {shown} 這 {len(numbers)} 個數，每個剛好用一次，加減乘除和括號隨你用，算出 {target}。",
        f"Use the numbers {shown}, each exactly once, with + − × ÷ and brackets as you like, to make {target}.",
    )
    hint = _z(lang, "答案寫成算式，例如 (8 − 2) × 4，不要寫等號。", "Answer with the calculation, such as (8 − 2) × 4, without an equals sign.")
    solution = reach[Fraction(target)]
    explain = _z(lang, f"例如 {solution} = {target}（別的算法也算對）", f"For example {solution} = {target} (other ways count too)")
    return Puzzle("target", level, lang, text, "expr", solution, explain, hint, value=target, numbers=numbers)


_FULLWIDTH = str.maketrans({"×": "*", "x": "*", "X": "*", "÷": "/", "−": "-", "–": "-", "—": "-", "（": "(", "）": ")", "［": "(", "］": ")", "[": "(", "]": ")"})


def _calc(answer: str) -> tuple[Fraction, list[int]] | None:
    """The value of a calculation and the numbers written in it (None if it isn't one)."""
    text = unicodedata.normalize("NFKC", answer).translate(_FULLWIDTH)
    text = text.replace("\\times", "*").replace("\\div", "/").replace("\\cdot", "*").replace("·", "*").replace("$", "")
    text = re.sub(r"\\left|\\right", "", text)
    sides = [s for s in text.split("=") if re.search(r"[-+*/]", s)]
    if not sides:
        return None
    text = sides[0]
    if not re.fullmatch(r"[\d\s+\-*/().]+", text):
        return None
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError:
        return None
    used: list[int] = []

    def value(node: ast.AST) -> Fraction:
        if isinstance(node, ast.Expression):
            return value(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            used.append(node.value)
            return Fraction(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -value(node.operand)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = value(node.left), value(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if right == 0:
                raise ZeroDivisionError
            return left / right
        raise ValueError(type(node).__name__)

    try:
        return value(tree), used
    except (ValueError, ZeroDivisionError, RecursionError):
        return None


# ------------------------------------------------------------ sequence


def _sequence(level: str, lang: str, rng: random.Random) -> Puzzle:
    zh = lang == "zh"
    family = rng.choice({"easy": ["add", "times", "square"], "normal": ["gaps", "sum2", "alternate"], "hard": ["interleave", "affine", "cube", "doubling_gaps"]}[level])
    shown = 5
    if family == "add":
        a, d = rng.randint(1, 30), rng.randint(3, 15)
        terms = [a + i * d for i in range(6)]
        rule = f"每次加 {d}" if zh else f"add {d} each time"
    elif family == "times":
        a, r = rng.randint(1, 5), rng.choice([2, 3])
        terms = [a * r**i for i in range(6)]
        rule = f"每次乘 {r}" if zh else f"multiply by {r} each time"
    elif family == "square":
        n0 = rng.randint(1, 7)
        terms = [(n0 + i) ** 2 for i in range(6)]
        rule = f"{n0}², {n0 + 1}², {n0 + 2}²… 平方數" if zh else f"the squares {n0}², {n0 + 1}², {n0 + 2}²…"
    elif family == "gaps":
        a, d, c = rng.randint(1, 12), rng.randint(1, 6), rng.randint(2, 4)
        terms = [a]
        for i in range(5):
            terms.append(terms[-1] + d + i * c)
        gaps = ", ".join(str(d + i * c) for i in range(5))
        rule = f"相鄰兩數差 {gaps}（每次多 {c}）" if zh else f"the gaps are {gaps} (growing by {c})"
    elif family == "sum2":
        a, b = rng.sample(range(1, 10), 2)
        terms = [a, b]
        while len(terms) < 7:
            terms.append(terms[-1] + terms[-2])
        shown = 6
        rule = "每個數是前兩個數相加" if zh else "each number is the sum of the two before it"
    elif family == "alternate":
        a, p, q = rng.randint(1, 6), rng.randint(2, 6), rng.choice([2, 3])
        terms = [a]
        for i in range(6):
            terms.append(terms[-1] + p if i % 2 == 0 else terms[-1] * q)
        shown = 6
        rule = f"輪流 +{p}、×{q}" if zh else f"alternately +{p} and ×{q}"
    elif family == "interleave":
        a, d1, b, d2 = rng.randint(1, 15), rng.randint(2, 9), rng.randint(30, 60), -rng.randint(2, 7)
        first = [a + i * d1 for i in range(4)]
        second = [b + i * d2 for i in range(4)]
        terms = [x for pair in zip(first, second) for x in pair]
        shown = 7
        rule = (
            f"兩組數交錯：{', '.join(map(str, first))}…（每次 +{d1}）和 {', '.join(map(str, second))}…（每次 {d2}）"
            if zh
            else f"two sequences take turns: {', '.join(map(str, first))}… (+{d1}) and {', '.join(map(str, second))}… ({d2})"
        )
    elif family == "affine":
        while True:  # growing, and above zero
            k, c, a = rng.choice([2, 3]), rng.choice([-3, -2, -1, 1, 2, 3, 4, 5]), rng.randint(1, 5)
            if a * (k - 1) + c > 0:
                break
        terms = [a]
        for _ in range(5):
            terms.append(terms[-1] * k + c)
        rule = f"每次 ×{k} 再 {'+' if c > 0 else '−'}{abs(c)}" if zh else f"each time ×{k}, then {'+' if c > 0 else '−'}{abs(c)}"
    elif family == "cube":
        while True:
            n0, c = rng.randint(1, 3), rng.choice([-2, -1, 1, 2, 3])
            if n0**3 + c > 0:
                break
        terms = [(n0 + i) ** 3 + c for i in range(6)]
        rule = f"立方數 {n0}³, {n0 + 1}³… 再 {'+' if c > 0 else '−'}{abs(c)}" if zh else f"the cubes {n0}³, {n0 + 1}³… {'+' if c > 0 else '−'} {abs(c)}"
    else:  # doubling_gaps
        a, d = rng.randint(1, 20), rng.randint(1, 3)
        terms = [a]
        for i in range(5):
            terms.append(terms[-1] + d * 2**i)
        gaps = ", ".join(str(d * 2**i) for i in range(5))
        rule = f"相鄰兩數差 {gaps}（每次乘 2）" if zh else f"the gaps are {gaps} (doubling)"
    value = terms[shown]
    text = _z(lang, f"下一個數是多少？ {', '.join(map(str, terms[:shown]))}, ?", f"What comes next? {', '.join(map(str, terms[:shown]))}, ?")
    return _int_puzzle("sequence", level, lang, text, value, rule)


# ------------------------------------------------------------ order


NAMES = {"zh": ["小明", "小華", "小美", "阿傑", "小芳", "阿志", "小玲", "阿凱"], "en": ["Amy", "Ben", "Cara", "Dan", "Eva", "Finn", "Gina", "Hugo"]}
_ZH_NUM = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
_EN_ORD = ["0th", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th"]

# (above, below) said both ways; the question at the top, at position k, at the bottom
_THEMES = {
    "height": {
        "zh": ("{a}比{b}高", "{b}比{a}矮", "誰最高？", "誰第{k}高？", "誰最矮？", "由高到矮"),
        "en": ("{a} is taller than {b}", "{b} is shorter than {a}", "Who is the tallest?", "Who is the {k} tallest?", "Who is the shortest?", "tallest to shortest"),
    },
    "age": {
        "zh": ("{a}比{b}年紀大", "{b}比{a}年紀小", "誰年紀最大？", "誰的年紀排第{k}大？", "誰年紀最小？", "由大到小"),
        "en": ("{a} is older than {b}", "{b} is younger than {a}", "Who is the oldest?", "Who is the {k} oldest?", "Who is the youngest?", "oldest to youngest"),
    },
    "race": {
        "zh": ("{a}比{b}先到終點", "{b}比{a}晚到終點", "誰第一個到終點？", "誰第{k}個到終點？", "誰最後到終點？", "到終點的順序"),
        "en": ("{a} finished before {b}", "{b} finished after {a}", "Who finished first?", "Who finished {k}?", "Who finished last?", "finishing order"),
    },
}


def _closure(n: int, clues: list[tuple[int, int]]) -> list[set[int]]:
    """below[i]: everyone known to be below i (i, j are places in the true order)."""
    below = [set() for _ in range(n)]
    for a, b in clues:
        below[a].add(b)
    changed = True
    while changed:
        changed = False
        for i in range(n):
            more = set().union(*(below[j] for j in below[i])) - below[i] if below[i] else set()
            if more:
                below[i] |= more
                changed = True
    return below


def _settled(n: int, clues: list[tuple[int, int]], k: int) -> bool:
    """Whether the clues alone put the person at place k there: they are compared with everyone."""
    below = _closure(n, clues)
    above = {i for i in range(n) if k in below[i]}
    return len(above) + len(below[k]) == n - 1


def _order(level: str, lang: str, rng: random.Random) -> Puzzle:
    n = {"easy": 4, "normal": 5, "hard": 6}[level]
    names = rng.sample(NAMES[lang], n)  # names[0] is at the top
    theme = rng.choice(list(_THEMES))
    above_said, below_said, q_top, q_k, q_bottom, order_word = _THEMES[theme][lang]
    if level == "easy":
        k = rng.choice([0, n - 1])
    elif level == "normal":
        k = rng.choice([1, n - 2])
    else:
        k = rng.choice([2, 3])
    pairs = list(itertools.combinations(range(n), 2))
    rng.shuffle(pairs)
    clues: list[tuple[int, int]] = []
    for pair in pairs:
        clues.append(pair)
        if _settled(n, clues, k):
            break
    for pair in list(clues):  # as few as needed
        fewer = [c for c in clues if c != pair]
        if _settled(n, fewer, k):
            clues = fewer
    if level != "hard":  # one that says nothing new, to read past
        extra = [p for p in pairs if p not in clues]
        if extra:
            clues.append(rng.choice(extra))
    rng.shuffle(clues)
    said = []
    for a, b in clues:
        pattern = above_said if rng.random() < 0.5 else below_said
        said.append(pattern.format(a=names[a], b=names[b]))
    if k == 0:
        question = q_top
    elif k == n - 1:
        question = q_bottom
    else:
        question = q_k.format(k=_ZH_NUM[k + 1] if lang == "zh" else _EN_ORD[k + 1])
    text = "。".join(said) + "。" + question if lang == "zh" else ". ".join(said) + ". " + question
    below = _closure(n, clues)
    over = [names[i] for i in range(n) if k in below[i]]
    under = [names[j] for j in sorted(below[k])]
    if lang == "zh":
        parts = []
        if over:
            parts.append(f"排在{names[k]}前面的：{'、'.join(over)}")
        if under:
            parts.append(f"排在後面的：{'、'.join(under)}")
        explain = "，".join(parts) + f"（{order_word}）"
    else:
        parts = []
        if over:
            parts.append(f"ahead of {names[k]}: {', '.join(over)}")
        if under:
            parts.append(f"behind: {', '.join(under)}")
        explain = "; ".join(parts) + f" ({order_word})"
    choices = sorted(names, key=lambda name: text.index(name))
    hint = _z(lang, "答案只寫一個名字。", "Answer with one name only.")
    return Puzzle("order", level, lang, text, "choice", names[k], explain, hint, choices=choices)


# ------------------------------------------------------------ count


def _count(level: str, lang: str, rng: random.Random) -> Puzzle:
    if level == "easy":
        alphabet, length, low, high = "0123456789", 24, 3, 6
    elif level == "normal":
        alphabet, length, low, high = "abder", 36, 6, 10
    else:
        alphabet, length, low, high = "aeinrst", 56, 8, 14
    mark = rng.choice(alphabet)
    times = rng.randint(low, high)
    others = [c for c in alphabet if c != mark]
    chars = [mark] * times + [rng.choice(others) for _ in range(length - times)]
    rng.shuffle(chars)
    figure = "".join(chars)
    kind_word = _z(lang, "數字" if level == "easy" else "字母", "digits" if level == "easy" else "letters")
    text = _z(lang, f"下面這串{kind_word}裡，「{mark}」出現了幾次？", f"How many times does “{mark}” appear in the {kind_word} below?")
    explain = _z(lang, f"「{mark}」出現 {times} 次", f"“{mark}” appears {times} times")
    return _int_puzzle("count", level, lang, text, times, explain, figure=figure, mark=mark)


# ------------------------------------------------------------ calendar


WEEKDAYS = {"zh": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"], "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}


def _date(day: datetime.date, lang: str) -> str:
    return f"{day.year} 年 {day.month} 月 {day.day} 日" if lang == "zh" else day.strftime("%B %-d, %Y")


def _calendar(level: str, lang: str, rng: random.Random, today: datetime.date) -> Puzzle:
    names = WEEKDAYS[lang]
    now = names[today.weekday()]
    if level == "easy":
        days = rng.randint(9, 60)
        other = today + datetime.timedelta(days=days)
        text = _z(lang, f"今天是{now}。{days} 天後是星期幾？", f"Today is {now}. What day of the week is it {days} days from now?")
    else:
        span = (10, 200) if level == "normal" else (500, 2200)
        days = rng.randint(*span) * rng.choice([1, 1, -1])
        other = today + datetime.timedelta(days=days)
        text = _z(
            lang,
            f"今天是 {_date(today, lang)}，{now}。{_date(other, lang)}是星期幾？",
            f"Today is {now}, {_date(today, lang)}. What day of the week is {_date(other, lang)}?",
        )
    answer = names[other.weekday()]
    gap = abs(days)
    step = gap % 7
    if lang == "zh":
        way = "往後" if days > 0 else "往前"
        explain = f"相差 {gap} 天 = 7 × {gap // 7} + {step}，{now}{way} {step} 天是{answer}"
    else:
        way = "forward" if days > 0 else "back"
        explain = f"{gap} days apart = 7 × {gap // 7} + {step}; {now} moved {step} days {way} is {answer}"
    hint = _z(lang, "答案只寫星期幾，例如：星期三。", "Answer with the day only, such as: Wednesday.")
    return Puzzle("calendar", level, lang, text, "choice", answer, explain, hint, choices=list(names))


_DAY_WORDS = {
    0: ["星期一", "週一", "周一", "禮拜一", "monday", "mon"],
    1: ["星期二", "週二", "周二", "禮拜二", "tuesday", "tue"],
    2: ["星期三", "週三", "周三", "禮拜三", "wednesday", "wed"],
    3: ["星期四", "週四", "周四", "禮拜四", "thursday", "thu"],
    4: ["星期五", "週五", "周五", "禮拜五", "friday", "fri"],
    5: ["星期六", "週六", "周六", "禮拜六", "saturday", "sat"],
    6: ["星期日", "星期天", "週日", "周日", "禮拜日", "禮拜天", "sunday", "sun"],
}


def _weekday_of(answer: str) -> int | None:
    text = answer.lower()
    found = [(text.find(w), day) for day, words in _DAY_WORDS.items() for w in words if w in text]
    if found:
        return min(found)[1]
    return None


# ------------------------------------------------------------ trick


def _trick(level: str, lang: str, rng: random.Random) -> Puzzle:
    zh = lang == "zh"
    name = rng.choice({"easy": ["sheep", "overtake", "rope", "pond"], "normal": ["decimal", "bat", "loop", "machines"], "hard": ["snail", "machines2", "decimal3"]}[level])
    if name == "sheep":
        n = rng.randint(15, 40)
        k = rng.randint(3, n - 6)
        text = f"農夫有 {n} 隻羊，除了 {k} 隻以外全部跑掉了。農夫還剩幾隻羊？" if zh else f"A farmer has {n} sheep. All but {k} run away. How many sheep are left?"
        explain = f"「除了 {k} 隻以外都跑掉」＝留下 {k} 隻" if zh else f"“All but {k} run away” leaves {k}"
        value = k
    elif name == "overtake":
        k = rng.randint(2, 9)
        text = f"賽跑時，你超過了第 {k} 名。你現在是第幾名？（只寫數字）" if zh else f"In a race you overtake the runner in {_EN_ORD[k]} place. What place are you in now? (a number)"
        explain = f"超過第 {k} 名，就站上他的位置：第 {k} 名" if zh else f"You take their place: {_EN_ORD[k]}"
        value = k
    elif name == "rope":
        n = rng.randint(3, 9)
        text = f"把一條直直的繩子剪 {n} 刀（每刀剪斷一個地方），會變成幾段？" if zh else f"You cut a straight piece of rope at {n} places. How many pieces do you get?"
        explain = f"直的繩子剪 {n} 刀會多出 {n} 段：{n} + 1 = {n + 1}" if zh else f"{n} cuts in a straight rope make {n} + 1 = {n + 1} pieces"
        value = n + 1
    elif name == "pond":
        n = rng.randint(10, 60)
        text = f"池塘的浮萍每天長成前一天的兩倍，第 {n} 天剛好蓋滿整個池塘。第幾天時蓋滿一半？" if zh else f"Duckweed on a pond doubles every day and covers the whole pond on day {n}. On which day did it cover half the pond?"
        explain = f"再長一天就變兩倍，所以前一天是一半：第 {n - 1} 天" if zh else f"It doubles in a day, so it was half the day before: day {n - 1}"
        value = n - 1
    elif name == "bat":
        ball, more = rng.randint(5, 45), rng.choice([100, 200, 300, 500])
        total = more + 2 * ball
        text = f"一支球拍加一顆球共 {total} 元，球拍比球貴 {more} 元。球是幾元？" if zh else f"A bat and a ball cost {total} dollars together. The bat costs {more} dollars more than the ball. How much is the ball?"
        explain = f"球 {ball} 元、球拍 {ball + more} 元，加起來 {total} 元（不是 {total - more} 元）" if zh else f"The ball is {ball}, the bat {ball + more}: {total} together (not {total - more})"
        value = ball
    elif name == "loop":
        n = rng.randint(3, 9)
        text = f"把一個橡皮筋圈剪 {n} 刀（每刀剪斷一個地方），會變成幾段？" if zh else f"You cut a rubber band (a closed loop) at {n} places. How many pieces do you get?"
        explain = f"圈圈沒有頭尾，剪 {n} 刀就是 {n} 段" if zh else f"A loop has no ends: {n} cuts make {n} pieces"
        value = n
    elif name == "machines":
        n, m = rng.randint(3, 9), rng.choice([20, 50, 100, 200])
        text = f"{n} 台機器 {n} 分鐘做出 {n} 個零件。{m} 台機器做 {m} 個零件要幾分鐘？" if zh else f"{n} machines make {n} parts in {n} minutes. How many minutes do {m} machines need to make {m} parts?"
        explain = f"每台機器 {n} 分鐘做 1 個，所以還是 {n} 分鐘" if zh else f"Each machine makes 1 part in {n} minutes, so still {n} minutes"
        value = n
    elif name == "machines2":
        n, m, j = rng.randint(3, 9), rng.randint(2, 12), rng.randint(2, 9)
        parts = m * j
        if parts == m:
            parts += m
            j += 1
        text = f"{n} 台機器 {n} 分鐘做出 {n} 個零件。{m} 台機器做 {parts} 個零件要幾分鐘？" if zh else f"{n} machines make {n} parts in {n} minutes. How many minutes do {m} machines need to make {parts} parts?"
        explain = f"每台機器 {n} 分鐘做 1 個；{m} 台每 {n} 分鐘做 {m} 個，{parts} 個要 {j} 輪：{n} × {j} = {n * j} 分鐘" if zh else f"Each machine makes 1 part per {n} minutes; {m} machines make {m} per {n} minutes, so {parts} take {j} rounds: {n} × {j} = {n * j}"
        value = n * j
    elif name == "snail":
        while True:
            depth, up = rng.randint(10, 30), rng.randint(3, 6)
            down = rng.randint(1, up - 1)
            if depth > up:
                break
        day = math.ceil((depth - up) / (up - down)) + 1
        text = (
            f"井深 {depth} 公尺。蝸牛白天往上爬 {up} 公尺，晚上滑下 {down} 公尺。牠在第幾天爬出井口？"
            if zh
            else f"A well is {depth} m deep. A snail climbs {up} m up each day and slides {down} m back each night. On which day does it get out?"
        )
        before = (day - 1) * (up - down)
        explain = (
            f"每過一整天升 {up - down} 公尺；第 {day - 1} 天晚上在 {before} 公尺，第 {day} 天白天再爬 {up} 公尺就到頂（不用再滑下來）"
            if zh
            else f"It gains {up - down} m a full day; after night {day - 1} it is at {before} m, and on day {day} it climbs {up} m to the top (no sliding back)"
        )
        value = day
    else:  # decimal, decimal3
        whole = rng.randint(1, 19)
        while True:
            short = rng.randint(2, 9)  # one decimal: whole.short
            two = rng.randint(10, 99)  # two decimals: whole.two (looks bigger: more digits)
            if two // 10 != short and two % 10 != 0:
                break
        numbers = [f"{whole}.{short}", f"{whole}.{two}"]
        if name == "decimal3":
            three = rng.randint(100, 999)
            if three % 10 == 0:
                three += 1
            numbers.append(f"{whole}.{three:03d}")
        rng.shuffle(numbers)
        biggest = max(numbers, key=Fraction)
        joined = ("、" if zh else ", ").join(numbers[:-1]) + (" 和 " if zh else " and ") + numbers[-1]
        text = f"{joined}，哪個最大？" if zh else f"Which is the biggest: {joined}?"
        explain = f"小數點後逐位比：{biggest} 最大" if zh else f"Compare digit by digit after the point: {biggest} is the biggest"
        hint = _z(lang, "答案只寫那個數。", "Answer with that number only.")
        return Puzzle("trick", level, lang, text, "choice", biggest, explain, hint, choices=numbers)
    return _int_puzzle("trick", level, lang, text, value, explain)


# ------------------------------------------------------------ checking


def _first_int(answer: str) -> int | None:
    text = unicodedata.normalize("NFKC", answer).replace(",", "").replace("−", "-")
    match = re.search(r"-?\d+", text)
    return int(match.group()) if match else None


def check(puzzle: Puzzle, answer: str) -> bool:
    """Whether ``answer`` is right (an empty one never is)."""
    answer = (answer or "").strip()
    if not answer:
        return False
    if puzzle.answer_type == "int":
        return _first_int(answer) == puzzle.value
    if puzzle.answer_type == "expr":
        made = _calc(answer)
        return made is not None and made[0] == puzzle.value and sorted(made[1]) == sorted(puzzle.numbers)
    return pick(puzzle, answer) == puzzle.solution


def pick(puzzle: Puzzle, answer: str) -> str:
    """The choice an answer names ("" when none): the first one it mentions."""
    if puzzle.kind == "calendar":
        day = _weekday_of(answer)
        return WEEKDAYS[puzzle.lang][day] if day is not None else ""
    text = unicodedata.normalize("NFKC", answer)
    if all(re.fullmatch(r"\d+\.\d+", c) for c in puzzle.choices):
        for number in re.findall(r"\d+\.\d+", text):
            if number in puzzle.choices:
                return number
        return ""
    found = [(text.find(c), c) for c in puzzle.choices if c in text]
    return min(found)[1] if found else ""
