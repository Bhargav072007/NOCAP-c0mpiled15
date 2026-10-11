"""Recover original contiguous text when a model changed whitespace only."""
import re

def verbatim(fragment, text):
    if not isinstance(fragment,str) or not fragment:return fragment
    if fragment in text:return fragment
    pattern=''.join(r'\s+' if part.isspace() else re.escape(part)
                    for part in re.split(r'(\s+)',fragment) if part)
    matches=list(re.finditer(pattern,text))
    return matches[0].group() if len(matches)==1 else fragment
