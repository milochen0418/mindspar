# E2E testcases

Playwright end-to-end suites, one per folder:

- `testcases/<suite_name>/run_test.py`
- `testcases/<suite_name>/output/` (screenshots and logs, ignored by git)

Each `run_test.py` exits `0` on success and non-zero on failure, and writes its screenshots into
`OUTPUT_DIR` (provided by the runner). Shared helpers (opening a browser, the lobby) are in
`common.py`. The runner points `MINDSPAR_DATA_DIR` at a fresh folder in `OUTPUT_DIR`, so the
matches a suite plays don't land on your scoreboard.

## Suites

| Suite | What it checks |
|-------|----------------|
| `smoke_home` | The lobby: the opponent from the AI Hub (or the note that there is none, with Start off), level and length kept in the browser over a reload, the English switch, no sideways scrolling on a phone. |
| `play_match` | (Needs an AI Hub; skipped without one.) A match of three easy questions against the hub's model: an answer at ×2, a skipped question, an answer at ×3; each reveal shows the answer and both results, and the scores add up; the result's table; the model's row on the scoreboard. Takes a few minutes with a thinking model. |

## Running

Use the repo-level runner (it starts and stops the Reflex server and collects artifacts):

```bash
poetry run ./run_test_suite.sh smoke_home
DDNS_AI_HUB_URL=http://127.0.0.1:8172 DDNS_AUTH_SECRET=<the hub's secret> SERVICE_SUBDOMAIN=mindspar \
  poetry run ./run_test_suite.sh play_match
```

If ports 3000/8000 belong to another app, use others: `FRONTEND_PORT=3173 BACKEND_PORT=8173`.

To test a deployed instance (e.g. behind re-ddns), run a script directly:

```bash
BASE_URL=https://mindspar.reflex-ddns.com OUTPUT_DIR=/tmp/mindspar-e2e \
  poetry run python testcases/play_match/run_test.py
```

Keep `OUTPUT_DIR` outside the repo when the target is a re-ddns **dev-mode** install of this
checkout: that container watches the mounted source, so screenshots written under `testcases/`
hot-reload its backend in the middle of the match. A match played there goes onto that
scoreboard.

Optional env vars:
- `BASE_URL` (default `http://127.0.0.1:3000`)
- `HEADLESS=0` to watch the browser
- `PW_SLOWMO_MS=100` to slow actions down
- `PW_TIMEOUT_MS=60000` to increase Playwright timeouts
