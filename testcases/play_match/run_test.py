"""A whole match of three questions against the AI the AI Hub sets (skipped without one):
an answer at ×2, a skipped question, an answer at ×3; each reveal shows the answer and both
results and adds them to the scores; the result's table and report; the model's row on the
lobby's scoreboard."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import Page, sync_playwright  # noqa: E402

from common import finish, launch, log, new_page, open_lobby, shot, wait_for  # noqa: E402

LIMIT = 200  # the longest a question may take, the AI's thinking included


def points(page: Page, test_id: str) -> int:
    text = page.locator(f"[data-testid={test_id}]").inner_text()
    match = re.search(r"([+−-]?\d+)\s*分", text)
    assert match, text
    return int(match.group(1).replace("−", "-"))


def score(page: Page, who: str) -> int:
    return int(page.locator(f"[data-testid={who}-score]").inner_text())


errors: list[str] = []
with sync_playwright() as pw:
    browser = launch(pw)
    page = new_page(browser, errors)
    opponent = open_lobby(page)
    if not opponent:
        log("SKIP: no AI Hub opponent here")
        raise SystemExit(0)
    log("opponent:", opponent)
    page.click("[data-testid=level-easy]")
    page.click("[data-testid=length-3]")
    page.click("[data-testid=start]")
    mine = theirs = 0
    for no in range(1, 4):
        page.wait_for_selector("[data-testid=question]", timeout=120000)
        wait_for(lambda: page.locator("[data-testid=ai-panel]").count() == 1, "the question is open", 30)
        question = page.locator("[data-testid=question]").inner_text()
        log(f"Q{no}:", question.replace("\n", " ")[:100])
        shot(page, f"{no}a_question")
        if no == 2:
            page.click("[data-testid=skip]")
        else:
            page.click(f"[data-testid=wager-{2 if no == 1 else 3}]")
            if page.locator("[data-testid=choices]").count():
                page.locator("[data-testid=choices] button").first.click()
            else:
                page.fill("[data-testid=answer]", "12")
                page.keyboard.press("Enter")
        page.wait_for_selector("[data-testid=my-done]")
        page.wait_for_selector("[data-testid=solution]", timeout=LIMIT * 1000)
        mine += points(page, "my-result")
        theirs += points(page, "ai-result")
        assert score(page, "my") == mine and score(page, "ai") == theirs, (score(page, "my"), mine, score(page, "ai"), theirs)
        log(f"  answer {page.locator('[data-testid=solution]').inner_text()!r}; AI: {page.locator('[data-testid=ai-result]').inner_text()!r}")
        if no == 2:
            assert "沒作答" in page.locator("[data-testid=my-result]").inner_text()
        shot(page, f"{no}b_reveal")
        page.click("[data-testid=next]")

    page.wait_for_selector("[data-testid=result]")
    assert page.locator("[data-testid=result] tbody tr").count() == 0  # the banner has no table
    assert page.locator("tbody tr").count() == 3
    log("result:", page.locator("[data-testid=result]").inner_text().replace("\n", " "))
    shot(page, "4_result")
    page.click("[data-testid=to-lobby]")
    page.wait_for_selector("[data-testid=board]")
    assert opponent in page.locator("[data-testid=board]").inner_text()
    shot(page, "5_board")
    browser.close()
finish(errors)
