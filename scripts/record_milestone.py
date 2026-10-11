"""Maintain the implementation sections; never replace the source baseline/log."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re

p = argparse.ArgumentParser()
p.add_argument('milestone')
p.add_argument('status')
p.add_argument('report')
p.add_argument('state')
a = p.parse_args()
brain = Path('context.md')
text = brain.read_text()
report = Path(a.report).read_text()
now = datetime.now(timezone.utc).isoformat(timespec='seconds')
text = re.sub(rf'^(\| {a.milestone} \| [^|]+\|)[^\n]+',
              rf'\1 {a.status} | [{a.report}]({a.report}) |', text, flags=re.M)
state = f'## Current implementation state\n\n{a.state}\n\n'
text = re.sub(r'## Current implementation state\n.*?(?=## Milestone tracker)',state,text, flags=re.S)
text = text.replace('## Current state and milestone tracker',
                    '## Historical state at first blocked attempt (superseded by tracker above)')
text += f'\n### {a.milestone} — {now}\n\n{report}\n\nReport: [{a.report}]({a.report}).\n'
brain.write_text(text)
