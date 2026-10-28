# Mindspar 腦力擂台 🧠⚔️

A quiz duel against an AI. You and the AI get **the same question at the same moment** and answer on your own; bet your confidence, and see who is quicker and right more often. Seven kinds of questions each test one thing a language model may or may not be good at, and every match is kept **per model**, so you can switch the model and compare.

Built with [Reflex](https://reflex.dev/) for the [re-ddns](https://github.com/milochen0418/re_ddns) Agentic App Store. The opponent is whatever model the [AI Hub](https://github.com/milochen0418/ai_hub) sets for this app (a local Ollama model such as `qwen3.5:9b`, Claude, …): Mindspar holds no model and no key.

## 🎮 How a match goes

1. The lobby shows your opponent (the model the AI Hub answers with), the level (time per question: easy 60 s, normal 90 s, hard 150 s) and the length (3 quick questions, or 7: one of each kind).
2. A question appears for both of you. The AI is asked at that moment, through the hub; you see it thinking, and when it has answered (but not what, until you have answered too).
3. You answer by typing (Enter) or by picking a choice, with your **confidence ×1, ×2 or ×3**. The AI gives its own confidence. Right scores 100 × confidence, wrong loses 50 × confidence, no answer when the time is up scores 0. When both are right, whoever answered first gets 50 more.
4. The reveal: the right answer and why, both answers, the points, the AI's one-line reason (and a note when it ran out of time, failed or didn't keep to the format).
5. The result: who won, every question in a table, and how the AI did (right, average time, right when it bet ×3, replies off the format). The match goes onto the lobby's **model scoreboard**.

## 🧩 The seven kinds of questions

Every question is made fresh from random numbers, with its answer known, so neither side can have seen it before.

| Kind | Example | What it tests in a model |
|------|---------|--------------------------|
| Mental math 心算 | `47 × 38 − 129 = ?` | calculating exactly |
| Make the number 湊數字 | use 7, 3, 9, 2 once each to make 24 | trying combinations (any right calculation counts) |
| Sequences 數列 | `9, 7, 16, 23, 39, 62, ?` | spotting a rule |
| Who's where 推理排名 | "Amy is taller than Ben. … Who is the 2nd tallest?" | step-by-step deduction |
| Counting 數字母 | how many `r` in `abdrrbardrea…` | seeing single characters (models read text in chunks) |
| Day of the week 星期幾 | "Today is Thursday, October 29, 2026. What day is April 16, 2021?" | date arithmetic |
| Trick questions 陷阱題 | "A bat and a ball cost 110 …", "All but 9 sheep run away …" | not falling for the catch |

The levels change the numbers (bigger products, five people instead of four, 56 letters instead of 24 digits, dates years away) and the time.

## 🏆 Comparing models

The scoreboard keeps every finished match per model: matches, your wins / the AI's / draws, how often the AI was right, its average time, how often it was right when it said it was certain (×3), and its right answers per kind. To try another model, change it on the AI Hub's page (*What each app's AI uses* → `mindspar`), reload the lobby and play again.

## 🛠️ How it is built

- `mindspar/puzzles.py`: the seven kinds, each made with its answer, an explanation and how the AI should write its answer; `check()` reads answers however they are written (`(8−2)×4`, `（8－2）÷4`, `$4\times 6$`, a weekday in either language, …).
- `mindspar/opponent.py`: asks the AI Hub for the role `smart` through `reflex_ddns_auth.ai`; the AI answers in three lines (answer, confidence, reason) that `parse()` reads.
- `mindspar/state.py`: one background task per question asks the AI and runs the clock; the AI's answer stays on the server until the reveal.
- `mindspar/history.py`: finished matches as JSON lines in `MINDSPAR_DATA_DIR` (default `~/.local/share/mindspar`), summed per model.
- `mindspar/views.py`, `mindspar/i18n.py`: the page, in 繁體中文 and English.

## 🚀 Running it

**On re-ddns:** install *Mindspar* from the App Store (the AI Hub must be installed too). Then on the AI Hub's page pick the model for `mindspar` and open `https://mindspar.reflex-ddns.com`.

**Running it on its own** (for development): it needs an AI Hub to ask. Run one (see the AI Hub's README) and point the game at it with the same secret:

```bash
poetry env use python3.15
poetry install
DDNS_AI_HUB_URL=http://127.0.0.1:8172 DDNS_AUTH_SECRET=<the hub's secret> SERVICE_SUBDOMAIN=mindspar \
  MINDSPAR_DATA_DIR=/tmp/mindspar REFLEX_API_URL=http://localhost:8173 \
  poetry run reflex run --frontend-port 3173 --backend-port 8173
```

Without a hub the lobby says so and a match can't start.

## 🧪 Tests

```bash
poetry run pytest                                  # questions, answers, the AI's replies, the scoreboard
poetry run ./run_test_suite.sh smoke_home          # the lobby
DDNS_AI_HUB_URL=… DDNS_AUTH_SECRET=… SERVICE_SUBDOMAIN=mindspar \
  poetry run ./run_test_suite.sh play_match        # a whole match against the hub's model
```

See [testcases/README.md](testcases/README.md).

## License

MIT
