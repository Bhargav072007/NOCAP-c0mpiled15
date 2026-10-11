"""Original CSS motion components inspired by the selected Jitter UI examples.

The ambient ribbon is decorative, never a loading/verification indicator.
Only one instance is rendered on each page; interactions remain native controls.
"""

def ambient_ribbon(compact=False):
    variant = ' nc-ambient-compact' if compact else ''
    return f'''<div class="nc-ambient{variant}">
      <input type="checkbox" id="nc-pause-ambient" class="nc-ambient-checkbox" aria-label="Pause ambient animation">
      <div class="nc-ambient-art" aria-hidden="true"><div class="nc-aurora-ribbon"></div></div>
      <label for="nc-pause-ambient" class="nc-ambient-control" title="Pause or resume decorative animation">
        <span class="nc-pause-icon" aria-hidden="true">Ⅱ</span><span class="nc-play-icon" aria-hidden="true">▷</span>
        <span class="nc-pause-label">Pause animation</span><span class="nc-play-label">Resume animation</span>
      </label>
    </div>'''
