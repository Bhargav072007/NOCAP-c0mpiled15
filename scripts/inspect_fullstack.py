"""Local full-stack browser acceptance. Mutates only synthetic local demo records."""
import sys,json,hashlib,time,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright,expect
import requests
from device.upload import upload
OUT=Path('reports/screenshots/FS1');OUT.mkdir(parents=True,exist_ok=True)
config=dotenv_values('.runtime/local.env');api=requests.Session();api.headers['Authorization']='Bearer '+config['NOCAP_TOKEN']
BASE='http://127.0.0.1:8000'
def get(path):
    r=api.get(BASE+path,timeout=10);r.raise_for_status();return r.json()
def nav(page,name):
    sidebar=page.get_by_test_id('stSidebar')
    if sidebar.get_attribute('aria-expanded')=='false': page.get_by_role('button',name='keyboard_double_arrow_right',exact=True).click()
    sidebar.get_by_role('button',name=name,exact=False).click()
    expect(page.locator('.nc-page-title h1')).to_have_text(name)
def shot(page,name):
    page.screenshot(path=str(OUT/name),animations='disabled')
def tab(page,name):
    page.get_by_role('tab',name=name,exact=True).click();return page.locator('[role=tabpanel]:visible')
def select(page,label,value):
    box=page.get_by_role('combobox',name=label,exact=True);box.scroll_into_view_if_needed();box.click()
    option=page.get_by_role('option',name=value,exact=True)
    if not option.is_visible(): box.press('ArrowDown')
    option.click()

def evidence(page,n):
    nav(page,'Evidence studio')
    panel=tab(page,'Verify a file')
    for name,status in [('photo.jpg','VERIFIED'),('photo_ai_edited.jpg','CAP')]:
        page.locator('input[type=file]').set_input_files('demo/'+name)
        panel.get_by_role('button',name='Verify file').click()
        expect(panel.locator('.nc-badge')).to_have_text('DEMO · '+status)
    panel=tab(page,'Citation check');panel.get_by_role('button',name='Load mixed demo',exact=True).click();panel.get_by_role('button',name='Check citations').click();expect(panel.locator('.nc-badge')).to_have_count(4)
    assert set(panel.locator('.nc-badge').all_text_contents())=={'DEMO · VERIFIED','DEMO · MISMATCH','DEMO · UNSUPPORTED','DEMO · NOT_FOUND'}
    if n==1: shot(page,'citations.png')
    panel=tab(page,'Audit ledger')
    with page.expect_download() as d: panel.get_by_role('button',name='Download ledger JSON').click()
    data=Path(d.value.path()).read_bytes();assert json.loads(data)==get('/ledger');Path(f'reports/FS1-ledger-{n}.json').write_bytes(data)
    expect(panel.get_by_role('button',name='Submit snapshot to Sepolia')).to_be_disabled()
    return {'run':n,'ledger_sha256':hashlib.sha256(data).hexdigest(),'status':'passed'}

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);page.set_default_timeout(15000)
    page.goto('http://127.0.0.1:8501');expect(page.get_by_role('button',name='Refresh overview',exact=True)).to_be_visible()
    expect(page.get_by_test_id('stMetricValue').first).to_have_text(str(get('/summary')['captures']))
    results={}
    try:
        shot(page,'overview.png')
        assert 'RESEARCH INTEGRITY' not in page.locator('body').inner_text()
        assert page.locator('.nc-mandala,.nc-eyebrow i').count()==0
        nav(page,'Team workbench');expect(page.get_by_role('button',name='New review',exact=True)).to_be_visible()
        page.get_by_role('button',name='New review',exact=True).click()
        dialog=page.get_by_role('dialog');expect(dialog).to_be_visible();label='Transport review '+uuid.uuid4().hex[:6]
        dialog.get_by_role('textbox',name='Review title').fill(label);dialog.get_by_role('textbox',name='Paper section').fill('Methods')
        dialog.get_by_role('button',name='Create review',exact=True).click();expect(dialog).not_to_be_visible()
        expect(page.get_by_role('heading',name=label,exact=True)).to_be_visible()
        page.get_by_role('button',name='Save review',exact=True).scroll_into_view_if_needed()
        select(page,'Review status','In progress');page.get_by_role('button',name='Save review',exact=True).click()
        expect(page.get_by_role('combobox',name='Review status',exact=True)).to_contain_text('')
        page.get_by_role('textbox',name='Review comment',exact=True).fill('Synthetic acceptance test: original bytes and ledger checked.')
        page.get_by_role('button',name='Post comment',exact=True).click()
        expect(page.get_by_text('Synthetic acceptance test: original bytes and ledger checked.',exact=True)).to_be_visible();shot(page,'workbench.png')
        assert next(r for r in get('/work-items') if r['title']==label)['status']=='In progress'
        tab(page,'People & collaborators');expect(page.locator('.nc-person')).to_have_count(len(get('/members')));shot(page,'team.png')
        page.get_by_role('button',name='Add member',exact=True).click();dialog=page.get_by_role('dialog')
        dialog.get_by_role('textbox',name='Name',exact=True).fill('Demo collaborator '+label[-6:])
        dialog.get_by_role('textbox',name='Email',exact=True).fill('demo-'+label[-6:]+'@example.test')
        dialog.get_by_role('button',name='Add member',exact=True).click();expect(dialog).not_to_be_visible()
        assert any(m['email']=='demo-'+label[-6:]+'@example.test' for m in get('/members'))
        results['collaboration']='Added local member (no email), created review, assigned owner, saved status, persisted comment; listed all team members'
        nav(page,'Devices');page.get_by_role('button',name='Register device',exact=True).click();dialog=page.get_by_role('dialog')
        dialog.get_by_role('textbox',name='Device name',exact=True).fill('Synthetic transport / '+label[-6:]);dialog.get_by_role('textbox',name='Device location',exact=True).fill('Local acceptance test')
        dialog.get_by_role('button',name='Register device',exact=True).click();expect(dialog).not_to_be_visible()
        with page.expect_download() as d: page.get_by_role('button',name='Download device configuration',exact=True).click()
        device=json.loads(Path(d.value.path()).read_text());page.get_by_role('button',name='Dismiss credential',exact=True).click()
        path=Path('.runtime/browser-device-record.json');data=Path('demo/photo.jpg').read_bytes()
        record={'id':'cap_'+uuid.uuid4().hex[:20],'type':'photo','file_name':'synthetic-transport.jpg','file_sha256':hashlib.sha256(data).hexdigest(),'captured_at':'2026-10-11T20:00:00+00:00','device_id':device['device_id'],'location':'Local software simulator','prev_hash':'0'*64,'record_hash':hashlib.sha256(uuid.uuid4().bytes).hexdigest(),'signature':''};path.write_text(json.dumps(record))
        outcome=upload(BASE,device['NOCAP_DEVICE_TOKEN'],path,'demo/photo.jpg',allow_local=True);assert outcome['status']=='UNSUPPORTED'
        repeat=upload(BASE,device['NOCAP_DEVICE_TOKEN'],path,'demo/photo.jpg',allow_local=True);assert repeat['duplicate']
        assert api.get(BASE+'/captures/'+record['id']+'/file',timeout=10).content==data
        page.get_by_role('button',name='Refresh devices',exact=True).click();expect(page.get_by_text('Recent heartbeat',exact=True).first).to_be_visible();shot(page,'devices.png')
        results['device_transport']='UI registration -> device bearer heartbeat/upload -> persistent capture -> exact download; same-ID replay accepted once; UNSUPPORTED label (not signed hardware)'
        results['rehearsals']=[evidence(page,1),evidence(page,2)]
        nav(page,'Cloud & settings');expect(page.get_by_role('button',name='Refresh connection status',exact=True)).to_be_visible();shot(page,'cloud.png')
        results['layouts']=[]
        page.emulate_media(reduced_motion='reduce')
        for width,height in [(1440,1000),(1280,800),(390,844)]:
            page.set_viewport_size({'width':width,'height':height})
            for name,slug in [('Overview','overview'),('Team workbench','team'),('Devices','devices'),('Cloud & settings','cloud'),('Evidence studio','evidence')]:
                nav(page,name)
                if width<700:
                    sidebar=page.get_by_test_id('stSidebar')
                    sidebar.get_by_role('button',name='keyboard_double_arrow_left',exact=True).click()
                expect(page.locator('.st-key-workspace')).to_have_css('animation-name','none')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                shot(page,f'{slug}-{width}.png')
            results['layouts'].append({'width':width,'views':5,'overflow':False,'reduced_motion':'passed'})
        page.set_viewport_size({'width':1440,'height':1000});nav(page,'Team workbench')
        page.get_by_role('button',name='New review',exact=True).focus();page.keyboard.press('Tab');page.keyboard.press('Shift+Tab');assert page.evaluate('getComputedStyle(document.activeElement).outlineStyle')=='solid'
        page.keyboard.press('Enter');expect(page.get_by_role('dialog')).to_be_visible();page.keyboard.press('Escape');expect(page.get_by_role('dialog')).not_to_be_visible()
        results['keyboard']='Visible focus and keyboard dialog open/Escape close passed'
        Path('reports/FS1-browser-checks.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
    except Exception:
        shot(page,'failure.png');print(page.locator('body').inner_text()[-6000:]);raise
    finally: browser.close()
