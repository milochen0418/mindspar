"""The lobby: the opponent from the AI Hub (or the note that there is none), the settings kept
in the browser, the language switch."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright  # noqa: E402

from common import finish, launch, log, new_page, open_lobby, shot, wait_for  # noqa: E402

errors: list[str] = []
with sync_playwright() as pw:
    browser = launch(pw)
    page = new_page(browser, errors)
    opponent = open_lobby(page)
    log("opponent:", opponent or "(none)")
    assert page.locator("h1").inner_text() == "腦力擂台"
    if opponent:
        assert page.locator("[data-testid=start]").is_enabled()
    else:
        assert not page.locator("[data-testid=start]").is_enabled(), "no opponent, no match"
    shot(page, "01_lobby_zh")

    # The settings stay in this browser.
    page.click("[data-testid=level-hard]")
    page.click("[data-testid=length-3]")
    wait_for(lambda: "amber" in (page.locator("[data-testid=length-3]").get_attribute("class") or ""), "3 questions picked")
    page.reload()
    page.wait_for_selector("[data-testid=lobby]")
    wait_for(lambda: "amber" in (page.locator("[data-testid=level-hard]").get_attribute("class") or ""), "hard kept")
    assert "amber" in (page.locator("[data-testid=length-3]").get_attribute("class") or "")
    log("settings kept")

    page.click("[data-testid=lang]")
    wait_for(lambda: page.locator("h1").inner_text() == "Mindspar", "English")
    assert page.get_by_text("Start the match").count() == 1
    shot(page, "02_lobby_en")
    page.click("[data-testid=lang]")
    wait_for(lambda: page.locator("h1").inner_text() == "腦力擂台", "back in Chinese")

    # A phone.
    phone = new_page(browser, errors, width=390, height=844)
    open_lobby(phone)
    assert phone.evaluate("document.documentElement.scrollWidth") <= 390, "no sideways scrolling"
    shot(phone, "03_lobby_phone")
    browser.close()
finish(errors)
