"""Sync the shared visual workspace into the Python server without changing runtime behavior."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'sites/superturiya/dist'
for name in ['site.css','site.js','fonts.css','favicon.svg','workbench.css','workbench.js','demo-data.json']:
    shutil.copy2(SITE/'assets'/name,ROOT/'web/assets'/name)
html=(SITE/'demo/index.html').read_text()
html=html.replace('data-runtime="recorded"','data-runtime="operator"')
html=html.replace('href="/docs/" id="guide-link"','href="https://superturiya.piyushunt.chatgpt.site/docs/" id="guide-link"')
html=html.replace('href="/" id="home-link"','href="https://superturiya.piyushunt.chatgpt.site/" id="home-link"')
html=html.replace('<a href="https://superturiya.piyushunt.chatgpt.site/docs/" id="guide-link"', '<a href="/traces.html" id="traces-link">Your traces</a><a href="https://superturiya.piyushunt.chatgpt.site/docs/" id="guide-link"')
(ROOT/'web/index.html').write_text(html)
print('Shared UI synchronized; Python operator mode retained.')
