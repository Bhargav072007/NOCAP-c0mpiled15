from pathlib import Path
import json
from playwright.sync_api import sync_playwright
out=Path('reports/reference');out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.goto('https://meghyanai.com/',wait_until='networkidle',timeout=60000)
    page.screenshot(path=str(out/'meghyan-hero.png'))
    (out/'page.html').write_text(page.content())
    for i,title in enumerate(["Built for the people who can't afford to be wrong","One number that tells you if your AI is ready","See it in action, no signup required."]):
        page.get_by_text(title,exact=True).scroll_into_view_if_needed()
        page.wait_for_timeout(900)
        page.screenshot(path=str(out/f'meghyan-section-{i}.png'))
    print('Styles:',page.locator('style').all_text_contents())
    print('SVGs:',page.locator('svg').count())
    text=page.locator('body').inner_text()
    (out/'text.txt').write_text(text)
    print(text[:200])
    values=page.evaluate('''() => Array.from(document.querySelectorAll('h1,h2,h3,button,input,nav,aside,header,a')).slice(0,100).map(el=>{let s=getComputedStyle(el);return {tag:el.tagName,text:el.innerText||el.getAttribute('placeholder'),font:s.fontFamily,size:s.fontSize,color:s.color,bg:s.backgroundColor,border:s.border,borderRadius:s.borderRadius,href:el.getAttribute('href')}})''')
    (out/'styles.json').write_text(json.dumps(values,indent=2))
    print(json.dumps(values)[:100])
    print('Links:',page.locator('a').evaluate_all('(els)=>els.map(e=>({text:e.textContent,href:e.href}))'))
    browser.close()
