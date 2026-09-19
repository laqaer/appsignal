"""UI self-check: pipeline rows render, detail opens, no console errors."""
import sys
from playwright.sync_api import sync_playwright

port = sys.argv[1] if len(sys.argv) > 1 else "8903"
exe = sys.argv[2] if len(sys.argv) > 2 else None
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=exe) if exe else p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
    rows = page.locator("tr[data-id]").count()
    status = page.locator("#status").inner_text()
    assert rows >= 100, f"expected pipeline rows, got {rows}"
    assert "Live pipeline data" in status, status
    page.locator("tr[data-id]").first.click()
    page.wait_for_selector("#detail h2")
    detail = page.locator("#detail").inner_text()
    assert "Pipeline estimate" in detail, detail
    page.locator(".tabs button[data-t=onb]").click()
    tab = page.locator("#tab").inner_text()
    assert "App Store screenshots" in tab or "No screenshots" in tab, tab
    page.locator(".tabs button[data-t=ads]").click()
    ads = page.locator("#tab").inner_text()
    assert "Meta Ad Library" in ads, ads
    assert "demo" not in ads.lower() or "token required" in ads.lower()
    assert not errors, errors
    page.screenshot(path="data/verify.png", full_page=True)
    browser.close()
print(f"UI OK: {rows} rows, detail renders, no console errors")
