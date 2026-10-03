"""Run Jev with a candidate (seed|best from run1_result.json) over an input jsonl -> {id, p}. usage: eval_candidate.py WHICH IN OUT MODE(work|excerpt)"""
# Record of the rejected GEPA experiment (harness/gepa/README.md). It ran with OpenAlex's internal asynchronous Jev
# client (`jevx`, not shipped); classifier/jev.py is the public, synchronous equivalent.
import asyncio, json, os, sys, time
from jevx import JevClient  # internal; see the note above
WHICH, IN, OUT, MODE = sys.argv[1:5]
cand = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run1_result.json')))[WHICH]
GOALS = list(range(1, 18))
def state_of(r):
    if MODE == 'excerpt': return cand['rule'].replace("judged from its title and abstract", "judged from the text excerpt below") + "\n\nText: " + r['text'][:3000]
    return cand['rule'] + f"\n\nTitle: {r['title']}\nAbstract: {(r.get('abstract') or '')[:3000]}"
async def main():
    done = set(json.loads(l)['id'] for l in open(OUT)) if os.path.exists(OUT) else set()
    rows = [json.loads(l) for l in open(IN)]; rows = [r for r in rows if r['id'] not in done]
    qs = {f"sdg{g}": {'type': 'noul', 'instructions': cand[f'sdg{g}']} for g in GOALS}
    out = open(OUT, 'a'); t0 = time.time(); n = [0, 0]
    async with JevClient(log_path=OUT + '.raw.jsonl', concurrency=20) as c:
        async def one(r):
            res = await c.decide(state_of(r), qs, tag='eval', meta={'id': r['id']})
            rec = {'id': r['id'], 'p': {g: float(res.answers[f"sdg{g}"]['noul']) for g in GOALS}} if res.ok else {'id': r['id'], 'error': str(res.error)[:200]}
            out.write(json.dumps(rec) + '\n'); out.flush(); n[0] += 1; n[1] += 'error' in rec
        await asyncio.gather(*(one(r) for r in rows))
        print(f"{WHICH} {IN}: {n[0]} rows, {n[1]} err, {time.time()-t0:.0f}s", file=sys.stderr)
asyncio.run(main())
