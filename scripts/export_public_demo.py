"""Export synthetic, reproducible demonstration records without exposing an API."""
import json
import tempfile
from pathlib import Path
from superturiya.intelligence import SuperTuriyaEngine
from superturiya.store import SuperTuriyaStore
from superturiya.adaptive import content_hash

ROOT = Path(__file__).resolve().parents[1]

def export():
    with tempfile.TemporaryDirectory() as directory:
        store = SuperTuriyaStore(str(Path(directory) / 'demo.db'))
        engine = SuperTuriyaEngine(store)
        cases = []
        for case in engine.adaptive_runner.cases:
            if case['split'] != 'held_out':
                continue
            prepared = engine.prepare_hackathon_case({'case_id': case['case_id'], 'mode': 'frozen'})
            reviewed = engine.review_hackathon_intervention({'intervention_id': prepared['stored_intervention']['intervention_id'], 'decision': 'approved', 'reviewer_id': 'public-demo-export', 'note': 'Synthetic recorded demonstration only.'})
            guidance = engine.repair_guided_case({'case_id': case['case_id'], 'mode': 'frozen'})
            cases.append({'case_id':case['case_id'], 'title':case['title'], 'goal':case['goal'], 'difficult':case['difficult'], 'prepared':prepared, 'reviewed':reviewed, 'guidance':guidance})
        def public_projection(value):
            if isinstance(value, dict):
                return {k: public_projection(v) for k, v in value.items() if k not in {'prompt', 'raw_response'}}
            if isinstance(value, list):
                return [public_projection(v) for v in value]
            return value
        data = {'schema':'superturiya-public-demo-v1', 'mode':'recorded-frozen', 'disclosure':'Synthetic, recorded Python verifier results. Browser interactions do not run model inference, change server policy, or deploy repairs.', 'cases':public_projection(cases)}
        data['content_sha256'] = content_hash(data)
        for target in [ROOT/'sites/superturiya/dist/assets/demo-data.json', ROOT/'web/assets/demo-data.json']:
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
        store.close()
        print('Exported',len(cases),'synthetic cases; digest',data['content_sha256'])

if __name__=='__main__': export()
