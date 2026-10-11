"""Settled handoff screenshots of the running local dashboard."""
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
out=Path('reports/screenshots/FS1')
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.goto('http://localhost:8501')
    expect(page.get_by_test_id('stMetricValue').first).not_to_be_empty()
    for name,slug,ready in [('Overview','overview','Refresh overview'),('Devices','devices','Refresh devices'),('Cloud & settings','cloud','Refresh connection status')]:
        page.get_by_test_id('stSidebar').get_by_role('button',name=name,exact=False).click()
        expect(page.locator('.nc-page-title h1')).to_have_text(name)
        expect(page.get_by_role('button',name=ready,exact=True)).to_be_attached()
        page.wait_for_function('document.querySelectorAll("[data-stale=true]").length === 0')
        page.locator('.nc-page-title').scroll_into_view_if_needed()
        page.screenshot(path=str(out/(slug+'-final.png')),animations='disabled')
    page.get_by_test_id('stSidebar').get_by_text('Preferences & demo states',exact=True).click()
    page.get_by_test_id('stSidebar').get_by_text('Reduce motion',exact=True).click()
    expect(page.locator('.st-key-workspace')).to_have_css('animation-name','none')
    page.get_by_test_id('stSidebar').get_by_text('Reduce transparency',exact=True).click()
    expect(page.locator('.nc-mode-banner')).to_have_css('background-color','rgb(20, 26, 16)')
    print('Settled final screenshots and explicit motion/transparency controls passed.')
    browser.close()
