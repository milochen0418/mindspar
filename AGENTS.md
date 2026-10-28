# AGENTS.md

This file describes how an AI coding agent (and humans) should work in this repository.

## 0) Always read the docs first

Before making changes or running commands, **read all README.md files in this repo** and follow them.

- Repo overview & dev workflow: `README.md`
- E2E test runner conventions: `testcases/README.md`

If you already read them earlier in the session, **re-check** when unsure.

## 1) Python / Poetry requirements (strict)

This project is developed on **Python 3.15**; the range allows 3.11 too, the Python of the
re_ddns App Store image (python:3.11).

- Prefer Poetry-managed environments.
- If Poetry selected another Python, switch it:

```bash
poetry env use python3.15
poetry env info
poetry install
```

If `python3.15` is not available on PATH, use an absolute path to the 3.15 executable.

## 2) Default rule: use `poetry run` for scripts

When running any repo scripts, prefer:

- `poetry run <command>`

This ensures the correct virtualenv + dependencies are used.

## 3) Running the app: prefer `reflex_rerun.sh`

When you need to start/restart the Reflex app during development, **prefer the repo helper script**.

Typical usage:

```bash
poetry run ./reflex_rerun.sh
```

Notes:
- Prefer `poetry run ./reflex_rerun.sh` over `poetry run reflex run`.
- It runs on the expected ports: frontend `3000`, backend `8000` (it kills whatever holds them).
- Other apps on this machine may own 3000/8000. Then run on other ports and point the frontend at the backend: `REFLEX_API_URL=http://localhost:8173 poetry run reflex run --frontend-port 3173 --backend-port 8173`.
- The opponent comes from an AI Hub: outside re-ddns, point the app at one with `DDNS_AI_HUB_URL` and the same `DDNS_AUTH_SECRET` (see README, "Running it on its own").
- Set `MINDSPAR_DATA_DIR` to a scratch folder when trying things, so test matches don't land on the real scoreboard.

## 4) Running E2E suites: prefer `run_test_suite.sh`

E2E suites live under `testcases/<suite_name>/run_test.py`.

Do **not** run Playwright suites by starting/stopping the server manually unless you have to.
Use the repo runner, which starts/stops the Reflex server, sets `OUTPUT_DIR` and `MINDSPAR_DATA_DIR`, and collects artifacts:

```bash
poetry run ./run_test_suite.sh smoke_home
```

Optional environment variables (see `testcases/README.md`): `BASE_URL`,
`FRONTEND_PORT` / `BACKEND_PORT`, `HEADLESS=0`.

Unit tests: `poetry run pytest`.

## 4.5) How Mindspar is put together

- **The questions** are made fresh from random numbers in `mindspar/puzzles.py`, each with its answer, an explanation and a format hint for the AI; `check()` reads an answer however it is written (a calculation with ×÷ or full-width signs, a weekday in either language, a name). A new kind needs: a maker, its words in `i18n.py` (`kind_*`, `test_*`), and a place in `KINDS`.
- **The opponent** is the AI Hub's role `smart` (`mindspar/opponent.py`, through `reflex_ddns_auth.ai`): the game holds no model, key or hub address. `ai.uses` in `mindspar.py` puts the game's row on the hub's page, where the model is chosen. The AI answers in three lines (answer, confidence 1–3, reason), read by `opponent.parse`.
- **A question is one background task** (`Game._run_round` in `mindspar/state.py`): it asks the AI and ticks the clock until both have answered or time is up; leaving the match or the next question bumps `_seq`, and the task stops (cancelling the hub request, which stops the model). The AI's answer stays in backend-only vars until the reveal.
- **Finished matches** are one JSON line each in `MINDSPAR_DATA_DIR/matches.jsonl` (`mindspar/history.py`), summed per model for the lobby's scoreboard.
- Words of the UI: `mindspar/i18n.py` (繁體中文, English).

## 4.6) The re-ddns dev-mode install

- `smart-app-mindspar` bind-mounts this checkout and hot-reloads on **any** file change in it. A reload restarts the backend and ends a match being played. Keep test output outside the checkout (`OUTPUT_DIR=...`) when testing against `https://mindspar.reflex-ddns.com`.
- `pyproject.toml`, `rxconfig.py`, `poetry.lock` are copied into the container at start: changes to them need `docker restart smart-app-mindspar`.
- Diagnose with `docker logs smart-app-mindspar`.

## 5) Expectations when acting as an agent

- Prefer the smallest, focused change set.
- After code changes, run the closest relevant check (at minimum the related suite via `run_test_suite.sh`).
- Report outcomes: what you ran, pass/fail, and where artifacts/logs were written.

## 6) Smart way to help the Agent to debug

```
poetry run ./reflex_rerun.sh --loglevel debug
```
