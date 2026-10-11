"""Generate deterministic synthetic calibration assets, never real evidence."""
import hashlib
import json
from pathlib import Path
import math
import struct
import wave
from PIL import Image, ImageDraw, ImageFont

out=Path(__file__).resolve().parents[1]/'demo'
out.mkdir(exist_ok=True)
font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def font(size):
    return ImageFont.truetype(font_path,size) if Path(font_path).exists() else ImageFont.load_default()
img=Image.new('RGB',(960,600),'#172126');d=ImageDraw.Draw(img)
for x in range(0,960,40): d.line((x,0,x,600),fill='#202e34')
for y in range(0,600,40): d.line((0,y,960,y),fill='#202e34')
d.rounded_rectangle((65,60,895,540),radius=30,fill='#25343a',outline='#617277',width=2)
d.text((100,90),'NOCAP / CALIBRATION TARGET',font=font(22),fill='#c8f53b')
for i,col in enumerate(['#c8f53b','#7f9fa6','#d6dfcc','#bc7f59','#5d7782']):
 x=100+i*152
 d.rounded_rectangle((x,162,x+120,350),radius=12,fill=col)
 d.text((x,372),f'SAMPLE {i+1:02d}',font=font(15),fill='#e4edef')
d.text((100,440),'SYNTHETIC DEMO ASSET',font=font(27),fill='#f4f7f8')
d.text((100,483),'Generated graphic / no camera, signature or lab capture',font=font(16),fill='#c2ccd0')
img.save(out/'photo.jpg',quality=90)
edited=img.copy();ed=ImageDraw.Draw(edited)
ed.rounded_rectangle((252,162,372,350),radius=12,fill='#b45353')
ed.text((580,440),'EDITED COPY',font=font(24),fill='#ffb0b0')
edited.save(out/'photo_ai_edited.jpg',quality=90)
with wave.open(str(out/'synthetic_tone.wav'),'wb') as f:
 f.setparams((1,2,8000,0,'NONE','not compressed'))
 f.writeframes(b''.join(struct.pack('<h',int(5000*math.sin(2*math.pi*440*i/8000))) for i in range(8000)))
(out/'reading.json').write_text(json.dumps({'fixture':True,'sample':'synthetic calibration','value':21.5,'unit':'C'},indent=2)+'\n')
paper='''SYNTHETIC CITATION DEMO — these are fictional references, not real publications.
Calibration specimen A is stable [Demo Reference A].
The edited image matches the original [Demo Reference B].
A universal effect was observed [Demo Reference C].
The result repeats indefinitely [Demo Reference D].
'''
(out/'paper_real.txt').write_text(paper)
(out/'paper_fake_refs.txt').write_text('SYNTHETIC FAKE-REFERENCE DEMO — three planted fictional references.\n[Invented Alpha 2099]\n[Invented Beta 2099]\n[Invented Gamma 2099]\n')
records=[];prev='0'*64
for i,(name,kind) in enumerate([('photo.jpg','photo'),('synthetic_tone.wav','audio'),('reading.json','reading')],1):
 r={'id':f'demo_{i}','type':kind,'file_name':name,'file_sha256':hashlib.sha256((out/name).read_bytes()).hexdigest(),
    'captured_at':f'2026-10-11T12:0{i}:00+00:00','device_id':'synthetic-generator','location':'Demo workspace / no physical location',
    'prev_hash':prev}
 # A deterministic identifier for the fixture, NOT Sanjay's signing implementation.
 r['record_hash']=hashlib.sha256(('fixture:'+json.dumps(r,sort_keys=True)).encode()).hexdigest()
 r.update(signature='',status='VERIFIED',fixture=True,reason='Demo registry match only. No signature or hardware verification.')
 prev=r['record_hash'];records.append(r)
(out/'captures.json').write_text(json.dumps(records,indent=2)+'\n')
print('Generated 3 unsigned fixtures, original/edited images, tone and two fictional texts')
