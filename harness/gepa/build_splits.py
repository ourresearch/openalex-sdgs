"""Rebuild train/val/test splits (seed 11) from the September judge's labels, the 600 September works' texts, and the
Aurora survey pairs with their papers' texts. As run in September 2026 the inputs were local files with titles and
abstracts (sample.jsonl, bench/aurora_in.jsonl), which the repo does not ship; splits.json holds the resulting ids, and
classifier/fetch_works.py rebuilds the texts."""
import json, random
random.seed(11)
sample = {json.loads(l)['work_id']: json.loads(l) for l in open('../sample.jsonl')}
judged = []
for l in open('../judge.jsonl'):
    r = json.loads(l)
    if 'yes' not in r or r['work_id'] not in sample: continue
    w = sample[r['work_id']]
    judged.append({'id': r['work_id'], 'src': 'judge', 'title': w['title'], 'abstract': w.get('abstract') or '', 'gold': {int(g): bool(v) for g, v in r['yes'].items()}, 'ask': None})
random.shuffle(judged)
aur_in = {json.loads(l)['id']: json.loads(l) for l in open('../bench/aurora_in.jsonl')}
pairs = []
for l in open('../bench/aurora_pairs.jsonl'):
    r = json.loads(l)
    if r['doi'] in aur_in and r['yes'] != r['no']:
        w = aur_in[r['doi']]
        pairs.append({'id': f"{r['doi']}|{r['sdg']}", 'src': 'aurora', 'title': w['title'], 'abstract': w['abstract'], 'gold': {r['sdg']: r['yes'] > r['no']}, 'ask': r['sdg'], 'votes': f"{r['yes']} yes / {r['no']} no"})
random.shuffle(pairs)
splits = {'train': judged[:250] + pairs[:2500], 'val': judged[250:400] + pairs[2500:3700], 'test': judged[400:] + pairs[3700:]}
for k, v in splits.items():
    with open(f'{k}.jsonl', 'w') as f:
        for x in v: f.write(json.dumps(x) + '\n')
    print(k, len(v))
test = splits['test']
with open('test_judged.jsonl', 'w') as f:
    for x in test:
        if x['src'] == 'judge': f.write(json.dumps({'id': x['id'], 'title': x['title'], 'abstract': x['abstract'], 'gold': x['gold']}) + '\n')
seen = set()
with open('test_aurora_docs.jsonl', 'w') as f:
    for x in test:
        if x['src'] == 'aurora':
            doi = x['id'].split('|')[0]
            if doi in seen: continue
            seen.add(doi); f.write(json.dumps({'id': doi, 'title': x['title'], 'abstract': x['abstract']}) + '\n')
