"""Decorative motion illustrations. Never reflect live data or verification."""


def motion_switch(surface):
    return f'''<div class="nc-motion-toggle"><input class="nc-sr-only" type="checkbox" id="nc-{surface}-motion"><label for="nc-{surface}-motion"><span class="nc-motion-running">Pause motion</span><span class="nc-motion-paused">Resume motion</span></label></div>'''


def evidence_flow(compact=False):
    variant = ' nc-flow-compact' if compact else ''
    copy = ('<div class="nc-flow-copy"><span class="nc-flow-caption">Workflow guide · illustration</span><h3>Keep the thread.</h3><p>Capture → Review → Export</p></div>' if compact else '<div class="nc-flow-copy"><span class="nc-flow-caption">The evidence journey · illustration</span><h2>Every file. <br>A thread to follow.</h2><p>From one original capture to a shared review and an inspectable audit trail.</p><a href="?page=login" target="_self">Explore the workspace <span aria-hidden="true">↗</span></a></div>')
    switch = motion_switch('workspace') if compact else ''
    return f'''<section class="nc-flow{variant}" aria-label="Illustrated capture, review and export workflow">{copy}{switch}
    <div class="nc-flow-art" aria-hidden="true">
      <div class="nc-flow-grid"></div>
      <div class="nc-flow-stack"><div class="nc-flow-sheet nc-flow-sheet-back"></div><div class="nc-flow-sheet nc-flow-sheet-mid"></div><div class="nc-flow-sheet nc-flow-sheet-front"><div class="nc-flow-file-mark"></div><i></i><i></i><i></i><div class="nc-flow-scan"></div></div></div>
      <div class="nc-flow-rail"><div class="nc-flow-packet"></div><div class="nc-flow-packet nc-flow-packet-two"></div></div>
      <div class="nc-flow-stops"><div><span class="nc-flow-node"></span><b>Capture</b><small>Original file</small></div><div><span class="nc-flow-node"></span><b>Review</b><small>Shared context</small></div><div><span class="nc-flow-node"></span><b>Export</b><small>Audit trail</small></div></div>
    </div></section>'''
