"""Interactive, CSS-only workflow illustration. Never presented as live evidence."""
from dashboard.motion import ambient_ribbon


def workflow_demo():
    return f'''<section id="demo" class="nc-demo" aria-label="Interactive sample workflow">
      <div class="nc-demo-heading"><div><span class="nc-eyebrow">A LOOK INSIDE NOCAP</span><h2>Evidence in motion.</h2></div>{ambient_ribbon(compact=True)}</div>
      <fieldset class="nc-demo-player"><legend class="nc-sr-only">Preview a workflow step</legend>
        <input class="nc-demo-input" type="radio" name="demo-step" id="nc-demo-auto" checked><label class="nc-demo-tab" for="nc-demo-auto">Play tour</label>
        <input class="nc-demo-input" type="radio" name="demo-step" id="nc-demo-capture"><label class="nc-demo-tab" for="nc-demo-capture">01 Capture</label>
        <input class="nc-demo-input" type="radio" name="demo-step" id="nc-demo-review"><label class="nc-demo-tab" for="nc-demo-review">02 Review</label>
        <input class="nc-demo-input" type="radio" name="demo-step" id="nc-demo-export"><label class="nc-demo-tab" for="nc-demo-export">03 Export</label>
        <input class="nc-demo-input" type="checkbox" id="nc-demo-pause" aria-label="Pause workflow animation"><label class="nc-demo-pause" for="nc-demo-pause"><span class="nc-demo-pause-text">Ⅱ Pause</span><span class="nc-demo-resume-text">▷ Resume</span></label>
        <div class="nc-demo-stage" aria-hidden="true"><div class="nc-demo-rig">
          <div class="nc-demo-plane nc-demo-plane-back"></div><div class="nc-demo-plane nc-demo-plane-mid"></div>
          <article class="nc-demo-card nc-demo-capture"><div class="nc-demo-card-top"><span class="nc-demo-file-icon">↗</span><span>ORIGINAL CAPTURE</span><b>01</b></div><h3>Start at the source.</h3><p>field-sample-014.csv</p>
            <div class="nc-demo-chart"><div class="nc-demo-chart-label"><span>Sample signal</span><span>0 — 12 s</span></div><div class="nc-demo-signal"><div class="nc-demo-wave"></div></div></div>
            <div class="nc-demo-meta"><div><span>SOURCE</span><strong>One NoCap device</strong></div><div><span>RECORD</span><strong>Original preserved</strong></div></div>
            <div class="nc-demo-card-foot"><span class="nc-demo-mini-icon">↳</span> A source record for every file</div>
          </article>
          <article class="nc-demo-card nc-demo-review"><div class="nc-demo-card-top"><span class="nc-demo-file-icon">≋</span><span>TEAM REVIEW</span><b>02</b></div><h3>Keep the context.</h3><p>Findings and decisions, together.</p><div class="nc-demo-checklist"><div><span class="nc-demo-check">↗</span><span>Original source</span><small>Attached</small></div><div><span class="nc-demo-check">≋</span><span>Supporting reference</span><small>For review</small></div><div><span class="nc-demo-check">↳</span><span>Section owner</span><small>Assigned</small></div></div><div class="nc-demo-comment"><span>R</span><p>“Keep the source with the finding.”<small>Example reviewer note</small></p></div></article>
          <article class="nc-demo-card nc-demo-export"><div class="nc-demo-card-top"><span class="nc-demo-file-icon">↓</span><span>AUDIT EXPORT</span><b>03</b></div><h3>Leave a clear trail.</h3><p>A record your team can inspect.</p><div class="nc-demo-ledger"><div><span>01</span><b>Source record</b><small>Included</small></div><div><span>02</span><b>Review history</b><small>Included</small></div><div><span>03</span><b>Record hashes</b><small>Included</small></div></div><div class="nc-demo-export-file"><span>↓</span><div>audit-ledger.json<small>Illustrative export preview</small></div><b>JSON</b></div></article>
        </div><div class="nc-demo-floor"></div></div>
        <div class="nc-demo-description"><p class="nc-demo-desc-auto">One source. Every step connected.</p><p class="nc-demo-desc-capture">Keep the original file and its source record together.</p><p class="nc-demo-desc-review">Assign a review and keep the discussion with the evidence.</p><p class="nc-demo-desc-export">Export the audit trail for your team to inspect.</p></div>
      </fieldset>
      <div class="nc-demo-footer"><span>INTERACTIVE PREVIEW <b>Sample data</b></span><a href="?page=login" target="_self">Try the workspace <span aria-hidden="true">↗</span></a></div>
    </section>'''
