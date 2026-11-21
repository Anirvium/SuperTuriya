"""Check public assets, internal destinations and the synthetic evidence contract."""
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from superturiya.adaptive import content_hash

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'sites/superturiya/dist'

class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.links=[]; self.ids=set(); self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if attrs.get('id'): self.ids.add(attrs['id'])
        for key in ['href','src']:
            if key in attrs: self.links.append(attrs[key])

def check():
    pages={p: Page(p.read_text()) for p in SITE.rglob('*.html')}
    for source,page in pages.items():
        for link in page.links:
            parsed=urlsplit(link)
            if parsed.scheme or parsed.netloc: continue
            dest=(SITE / unquote(parsed.path).lstrip('/')) if parsed.path.startswith('/') else source.parent / unquote(parsed.path)
            if not parsed.path: dest=source
            if dest.is_dir(): dest=dest/'index.html'
            assert dest.exists(), (source,link,'missing')
            if parsed.fragment and dest in pages: assert parsed.fragment in pages[dest].ids,(source,link,'missing anchor')
    bundle=json.loads((SITE/'assets/demo-data.json').read_text())
    digest=bundle.pop('content_sha256')
    assert content_hash(bundle)==digest,'evidence digest mismatch'
    assert len(bundle['cases'])==12
    encoded=json.dumps(bundle)
    assert '"prompt":' not in encoded and '"api_key":' not in encoded
    passed=[c['case_id'] for c in bundle['cases'] if c['reviewed']['replay']['verified_safe_recovery']]
    assert len(passed)==11 and 'eval-012' not in passed
    for c in bundle['cases']:
        assert c['prepared']['stored_intervention']['status']=='candidate'
        replay=c['reviewed']['replay']
        assert not replay['replay']['safety_regression']
        assert replay['case_id']==c['case_id']
        assert len(replay['replay']['invariants'])==7
    for filename in ['site.css','site.js','fonts.css','favicon.svg','workbench.css','workbench.js','demo-data.json']:
        assert (SITE/'assets'/filename).read_bytes()==(ROOT/'web/assets'/filename).read_bytes(),filename+' is out of sync'
    print('PASS: internal page links, asset references, evidence digest, 12 recorded outcomes, and shared UI synchronization')

if __name__=='__main__': check()
