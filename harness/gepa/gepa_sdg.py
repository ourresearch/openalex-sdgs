"""GEPA over Jev's SDG instructions: components = rule + 17 goal instructions. Score per instance in [0,1].
usage: gepa_sdg.py RUN_DIR [--train N] [--val N] [--max-calls N] [--minibatch N]
Needs train.jsonl and val.jsonl beside it (build_splits.py, from texts rebuilt with classifier/fetch_works.py),
`pip install gepa anthropic`, ANTHROPIC_API_KEY and a Jev client."""
# Record of the rejected GEPA experiment (harness/gepa/README.md). It ran with OpenAlex's internal asynchronous Jev
# client (`jevx`, not shipped); classifier/jev.py is the public, synchronous equivalent.
import asyncio, json, os, sys, random, time, collections
from jevx import JevClient  # internal; see the note above
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from classifier.jev_request import EVAL_RULE as RULE, eval_noul
label = lambda g: eval_noul(g, sdg9='seed')   # the September wording GEPA started from
import anthropic, gepa
from gepa.core.adapter import EvaluationBatch
args = sys.argv[1:]; RUN = args[0]
def opt(name, default): return int(args[args.index(name)+1]) if name in args else default
NTRAIN, NVAL, MAXCALLS, MB = opt('--train', 0), opt('--val', 0), opt('--max-calls', 80000), opt('--minibatch', 40)
os.makedirs(RUN, exist_ok=True)
LOG = open(os.path.join(RUN, 'log.txt'), 'a')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()
HERE = os.path.dirname(os.path.abspath(__file__))
train = [json.loads(l) for l in open(os.path.join(HERE, 'train.jsonl'))]; val = [json.loads(l) for l in open(os.path.join(HERE, 'val.jsonl'))]
if NTRAIN: train = train[:NTRAIN]
if NVAL: val = val[:NVAL]
REASON = {}
import gzip
for l in gzip.open(os.path.join(HERE, '..', '..', 'benchmarks', 'data', 'september', 'judge_opus5.jsonl.gz'), 'rt'):
    r = json.loads(l)
    if 'reason' in r: REASON[r['work_id']] = r['reason']
GOALS = list(range(1, 18))
def text_of(x, cap=3000): return f"Title: {x['title']}\nAbstract: {(x.get('abstract') or '')[:cap]}"
def score_of(x, p):
    if x['src'] == 'aurora':
        g = x['ask']; y = x['gold'][str(g)] if str(g) in x['gold'] else x['gold'][g]; return 1 - abs(float(y) - p[g])
    gold = {int(k): v for k, v in x['gold'].items()}
    pos = [p[g] for g in GOALS if gold[g]]; neg = [1 - p[g] for g in GOALS if not gold[g]]
    return (0.5 * sum(pos) / len(pos) + 0.5 * sum(neg) / len(neg)) if pos else sum(neg) / len(neg)
class JevSDGAdapter:
    propose_new_texts = None
    def __init__(self): self.calls = 0
    def evaluate(self, batch, candidate, capture_traces=False):
        qs = {f"sdg{g}": {'type': 'noul', 'instructions': candidate[f'sdg{g}']} for g in GOALS}
        async def run():
            async with JevClient(log_path=os.path.join(RUN, 'jev.raw.jsonl'), concurrency=20) as c:
                async def one(x):
                    r = await c.decide(candidate['rule'] + "\n\n" + text_of(x), qs, tag='gepa', meta={'id': x['id']})
                    if r.ok: return {g: float(r.answers[f"sdg{g}"]['noul']) for g in GOALS}
                    return None
                return await asyncio.gather(*(one(x) for x in batch))
        ps = asyncio.run(run()); self.calls += len(batch)
        outputs, scores, trajs = [], [], []
        for x, p in zip(batch, ps):
            if p is None: p = {g: 0.5 for g in GOALS}
            outputs.append(p); scores.append(score_of(x, p)); trajs.append({'x': x, 'p': p})
        return EvaluationBatch(outputs=outputs, scores=scores, trajectories=trajs if capture_traces else None)
    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        out = {}
        for comp in components_to_update:
            items = []
            for t in eval_batch.trajectories:
                x, p = t['x'], t['p']; gold = {int(k): v for k, v in x['gold'].items()}
                goals = [int(comp[3:])] if comp.startswith('sdg') else ([x['ask']] if x['src'] == 'aurora' else GOALS)
                for g in goals:
                    if g not in gold: continue
                    y = gold[g]; err = abs(float(y) - p[g])
                    if err < 0.35 and random.random() > 0.08: continue
                    src = f"expert votes {x.get('votes')}" if x['src'] == 'aurora' else "LLM judge" + (f": {REASON.get(x['id'], {}).get(str(g), '')}" if REASON.get(x['id']) else "")
                    verdict = 'CORRECT' if err < 0.35 else ('FALSE POSITIVE' if not y else 'FALSE NEGATIVE')
                    items.append({'Inputs': text_of(x, 1500), 'Generated Outputs': f"p(SDG {g} {label(g)[:40]}) = {p[g]:.2f}",
                                  'Feedback': f"{verdict}. Gold says {'YES' if y else 'NO'} for SDG {g} ({src}). Keep the definition: a work counts only if it substantively contributes to or studies the goal; mentioning a theme in passing is not contributing; most works contribute to no goal. Instructions must stay short (one or two sentences)."})
            random.shuffle(items); out[comp] = items[:30] if items else [{'Inputs': '(no errors in this batch)', 'Generated Outputs': '', 'Feedback': 'Nothing to fix; return the instruction unchanged.'}]
        return out
def select_component(state, trajectories, subsample_scores, candidate_idx, candidate):
    loss = collections.Counter()
    for t in trajectories:
        x, p = t['x'], t['p']; gold = {int(k): v for k, v in x['gold'].items()}
        for g in gold: loss[g] += abs(float(gold[g]) - p[g])
    if random.random() < 0.12 or not loss: return ['rule']
    top = sorted(loss.items(), key=lambda kv: -kv[1])[:3]; g = random.choice(top)[0]
    return [f'sdg{g}']
client = anthropic.Anthropic(max_retries=4, timeout=600)
def reflect(prompt):
    msgs = prompt if isinstance(prompt, list) else [{'role': 'user', 'content': prompt}]
    r = client.messages.create(model='claude-opus-5', max_tokens=6000, messages=msgs)
    txt = ''.join(b.text for b in r.content if getattr(b, 'type', '') == 'text')
    log(f"[reflect] in={r.usage.input_tokens} out={r.usage.output_tokens}"); return txt
TEMPLATE = """You are tuning one text component of a classifier, not an LLM prompt. The classifier is Jev, a decision model that reads a state (a rule sentence plus a paper's title and abstract) and answers 17 yes/no questions ("Nouls"), one per UN Sustainable Development Goal, each returning a probability. Each Noul has a short instruction naming the criterion, e.g. "SDG 7 Affordable and clean energy" or "SDG 16 Peace, justice and strong institutions: peace, reducing violence and crime, rule of law and access to justice, accountable institutions, corruption". The component you are editing is either that criterion string for one goal, or the shared rule sentence.

Current text of the component:
```
<curr_param>
```

Examples from the last batch: the paper text, Jev's probability for this component's goal, and feedback with the gold label (from an LLM judge with its reason, or from expert votes):
```
<side_info>
```

Write an improved component text. Constraints: it is a criterion, not a prompt; no "output", "probability", "score", format or role instructions; no markdown; at most 60 words; keep the goal number and name first for a goal component (e.g. "SDG 9 Industry, innovation and infrastructure: ..."); keep the definition (substantive contribution or study; passing mention is not contributing; most works contribute to no goal). Use the feedback to say concretely what counts and what does not, in the words the failing papers would contain. Provide the new text within ``` blocks."""

seed = {'rule': RULE, **{f'sdg{g}': label(g) for g in GOALS}}
adapter = JevSDGAdapter(); t0 = time.time()
log(f"start train={len(train)} val={len(val)} minibatch={MB} max_calls={MAXCALLS}")
res = gepa.optimize(seed_candidate=seed, trainset=train, valset=val, adapter=adapter, reflection_lm=reflect, module_selector=select_component, reflection_prompt_template=TEMPLATE,
                    reflection_minibatch_size=MB, max_metric_calls=MAXCALLS, run_dir=RUN, candidate_selection_strategy='pareto', display_progress_bar=False, raise_on_exception=False, seed=0)
best = res.best_candidate
json.dump({'best': best, 'val_scores': res.val_aggregate_scores, 'best_idx': res.best_idx, 'seed': seed}, open(os.path.join(RUN, 'result.json'), 'w'), indent=1)
log(f"done: {len(res.candidates)} candidates, best idx {res.best_idx}, val {res.val_aggregate_scores[res.best_idx]:.4f} vs seed {res.val_aggregate_scores[0]:.4f}, jev calls {adapter.calls}, {time.time()-t0:.0f}s")
for k in best:
    if best[k] != seed[k]: log(f"  {k}: {best[k]}")
