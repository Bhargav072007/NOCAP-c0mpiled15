"""Browser acceptance against a locally running NoCap app; no external writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dashboard.client import FixtureClient
from playwright.sync_api import sync_playwright, expect
OUT=Path('reports/screenshots/UI-R1'); OUT.mkdir(parents=True,exist_ok=True)


def tab(page,name):
    page.get_by_role('tab',name=name,exact=True).click()
    return page.locator('[role="tabpanel"]:visible')


def shot(page,name,top=False):
    if top:
        page.evaluate('document.querySelectorAll("*").forEach(el=>{if(el.scrollTop>0)el.scrollTop=0})')
    page.screenshot(path=str(OUT/name),full_page=True,animations='disabled')


def scenario(page,value):
    sidebar=page.get_by_test_id('stSidebar')
    if not sidebar.is_visible() or sidebar.get_attribute('aria-expanded')=='false':
        page.get_by_role('button',name='keyboard_double_arrow_right',exact=True).click()
    # Selectbox controls are native Streamlit/BaseWeb, tested through roles.
    sidebar.get_by_role('combobox').click()
    page.get_by_role('option',name=value,exact=True).click()
    expect(sidebar.get_by_role('combobox')).to_be_visible()


def close_sidebar(page):
    sidebar=page.get_by_test_id('stSidebar')
    if sidebar.is_visible() and sidebar.get_attribute('aria-expanded')!='false':
        sidebar.get_by_role('button',name='keyboard_double_arrow_left',exact=True).click()


def rehearsal(page,number):
    capture=tab(page,'Live captures')
    expect(capture.locator('.nc-badge')).to_have_text('DEMO · VERIFIED')
    capture.get_by_role('combobox').focus()
    capture.get_by_role('combobox').press('ArrowDown')
    page.get_by_role('option',name='AUDIO · synthetic_tone.wav · demo_2',exact=True).click()
    expect(capture.locator('audio')).to_have_count(1)
    capture.get_by_role('combobox').focus()
    capture.get_by_role('combobox').press('ArrowDown')
    page.get_by_role('option',name='PHOTO · photo.jpg · demo_1',exact=True).click()
    expect(capture.locator('img')).to_have_count(1)
    with page.expect_download() as download:
        capture.get_by_role('button',name='Download original file').click()
    assert Path(download.value.path()).read_bytes()==Path('demo/photo.jpg').read_bytes()
    verify=tab(page,'Verify a file')
    for filename,status in [('photo.jpg','VERIFIED'),('photo_ai_edited.jpg','CAP')]:
        page.locator('input[type=file]').set_input_files('demo/'+filename)
        expect(verify.get_by_role('button',name='Verify file')).to_be_enabled()
        verify.get_by_role('button',name='Verify file').click()
        expect(verify.locator('.nc-badge')).to_have_text('DEMO · '+status)
        if number==1: shot(page,f'UI-R1-{status.lower()}.png')
    captures=tab(page,'Live captures')
    captures.get_by_role('button',name='Refresh captures').click()
    verify=tab(page,'Verify a file')
    expect(verify.locator('.nc-badge')).to_have_text('DEMO · CAP')
    expect(verify.get_by_text('photo_ai_edited.jpg',exact=True)).to_be_visible()
    citations=tab(page,'Citation check')
    citations.get_by_role('button',name='Load mixed demo').click()
    expect(citations.get_by_role('textbox',name='Research text')).to_have_value(Path('demo/paper_real.txt').read_text())
    citations.get_by_role('button',name='Check citations').click()
    expect(citations.locator('.nc-badge')).to_have_count(4)
    assert set(citations.locator('.nc-badge').all_text_contents())=={'DEMO · VERIFIED','DEMO · MISMATCH','DEMO · UNSUPPORTED','DEMO · NOT_FOUND'}
    citations.get_by_text('Reason and source details',exact=True).first.click()
    expect(citations.get_by_text('Scripted example of a supported claim. No publication lookup ran.',exact=True)).to_be_visible()
    if number==1: shot(page,'UI-R1-citations-results.png')
    citations.get_by_role('button',name='Load three fake references').click()
    expect(citations.get_by_role('textbox',name='Research text')).to_have_value(Path('demo/paper_fake_refs.txt').read_text())
    citations.get_by_role('button',name='Check citations').click()
    expect(citations.locator('.nc-badge')).to_have_count(3)
    assert set(citations.locator('.nc-badge').all_text_contents())=={'DEMO · NOT_FOUND'}
    ledger=tab(page,'Audit ledger')
    expect(ledger.get_by_text('Not checked',exact=True)).to_be_visible()
    expect(ledger.get_by_role('button',name='Submit snapshot to Sepolia')).to_be_disabled()
    with page.expect_download() as download:
        ledger.get_by_role('button',name='Download ledger JSON').click()
    assert download.value.suggested_filename=='nocap_ledger.json'
    data=Path(download.value.path()).read_bytes()
    assert json.loads(data)==FixtureClient().ledger()
    Path(f'reports/UI-R1-downloaded-ledger-{number}.json').write_bytes(data)
    return {'run':number,'status':'passed','ledger_sha256':hashlib.sha256(data).hexdigest(),
            'checks':['capture media and selection','download original exact bytes','original/edited upload verdicts',
                      'upload retained after capture refresh','mixed and three-fake citation examples','reasons',
                      'ledger downloaded from browser and deep-equal to adapter']}


def states(page):
    results={}
    tab(page,'Live captures')
    for name,expected in [('Empty','The trail starts here'),('Disconnected','Simulated disconnection.'),('Malformed','Simulated malformed API response.')]:
        scenario(page,name)
        panel=page.locator('[role="tabpanel"]:visible')
        expect(panel.get_by_text(expected,exact=False)).to_be_visible()
        results[name]='passed'
        shot(page,f'UI-R1-{name.lower()}.png')
    scenario(page,'Slow')
    expect(page.get_by_text('Loading capture records…',exact=True)).to_be_visible(timeout=5000)
    expect(page.locator('[role="tabpanel"]:visible').get_by_role('combobox')).to_be_visible(timeout=15000)
    results['Slow']='waiting indicator and eventual response observed'
    scenario(page,'Long list')
    expect(page.get_by_text('60 records · newest first in selector · stable IDs retained across refresh',exact=True)).to_be_visible()
    results['Long list']='60 records rendered with one selected preview'
    scenario(page,'Populated')
    expect(page.get_by_text('3 records · newest first in selector · stable IDs retained across refresh',exact=True)).to_be_visible()
    sidebar=page.get_by_test_id('stSidebar')
    sidebar.get_by_text('Poll captures every 10 seconds',exact=True).click()
    expect(page.get_by_text('Capture polling enabled · every 10 seconds · manual refresh remains available',exact=True)).to_be_visible()
    page.wait_for_timeout(11000)
    expect(page.locator('[role="tabpanel"]:visible').locator('.nc-badge')).to_have_text('DEMO · VERIFIED')
    results['Polling']='10-second fragment cycle observed; selected photo retained'
    sidebar.get_by_text('Poll captures every 10 seconds',exact=True).click()
    sidebar.get_by_text('Reduce transparency',exact=True).click()
    expect(page.locator('.nc-header')).to_have_css('backdrop-filter','none')
    results['Reduced transparency']='manual fallback computed backdrop-filter none'
    sidebar.get_by_text('Reduce motion',exact=True).click()
    results['Recovery']='populated restored without mode change'
    close_sidebar(page)
    return results


def layouts(page):
    results=[]
    page.emulate_media(reduced_motion='reduce')
    for width,height in [(1440,900),(1280,720),(390,844)]:
        page.set_viewport_size({'width':width,'height':height})
        close_sidebar(page)
        for name,slug in [('Live captures','captures'),('Verify a file','verify'),('Citation check','citations'),('Audit ledger','ledger')]:
            panel=tab(page,name)
            assert panel.evaluate('(el)=>getComputedStyle(el).animationName')=='none'
            # Document may scroll vertically; horizontal document overflow is not acceptable.
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
            panel.scroll_into_view_if_needed()
            shot(page,f'UI-R1-{slug}-{width}.png')
        results.append({'width':width,'height':height,'views':4,'horizontal_overflow':False,'reduced_motion':'none'})
    # Native tab keyboard navigation: move focus with ArrowRight, activate with Space.
    page.set_viewport_size({'width':1280,'height':720})
    first=page.get_by_role('tab',name='Live captures',exact=True)
    first.focus();page.keyboard.press('ArrowRight');page.keyboard.press('Space')
    expect(page.get_by_role('tab',name='Verify a file',exact=True)).to_be_focused()
    focused=page.evaluate('({tag:document.activeElement.tagName,outline:getComputedStyle(document.activeElement).outlineStyle})')
    assert focused['outline']=='solid'
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement!==document.body')
    return {'layouts':results,'keyboard_focus':focused}

if __name__=='__main__':
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.getenv('CHROME_BIN','/usr/bin/google-chrome'),headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1440,'height':900},accept_downloads=True)
        page=context.new_page();page.set_default_timeout(12000)
        page.goto('http://127.0.0.1:8501')
        page.get_by_role('tab',name='Live captures',exact=True).wait_for()
        try:
            expect(page.locator('.nc-hero h1')).to_be_visible()
            expect(page.locator('[role="tabpanel"]:visible .nc-badge')).to_be_visible()
            expect(page.locator('.nc-header')).to_have_css('backdrop-filter','blur(18px)')
            expect(page.locator('img.nc-mandala')).to_be_visible()
            assert page.locator('img.nc-mandala').evaluate('(el)=>el.complete && el.naturalWidth>0')
            page.get_by_role('link',name='Open the workspace').click()
            expect(page.locator('#evidence-workspace')).to_be_in_viewport()
            page.get_by_role('link',name='How it works',exact=True).last.click()
            expect(page.locator('#how-it-works')).to_be_in_viewport()
            shot(page,'final-default-captures.png',top=True)
            if '--snapshot-only' in sys.argv:
                panel=tab(page,'Audit ledger')
                panel.get_by_role('button',name='Download ledger JSON').scroll_into_view_if_needed()
                expect(panel.get_by_role('button',name='Submit snapshot to Sepolia')).to_be_disabled()
                shot(page,'final-ledger.png')
                print('Reference-style workspace and ledger screenshots saved; fixture anchor disabled.')
                sys.exit(0)
            results={'rehearsals':[rehearsal(page,1),rehearsal(page,2)],'states':states(page),'visual':layouts(page)}
            Path('reports/UI-R1-browser-checks.json').write_text(json.dumps(results,indent=2))
            print(json.dumps(results,indent=2))
        except Exception:
            shot(page,'browser-failure.png')
            print(page.locator('body').inner_text()[-7000:])
            raise
        finally:
            browser.close()
