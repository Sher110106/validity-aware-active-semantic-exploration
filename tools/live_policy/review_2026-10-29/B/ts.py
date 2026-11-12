import json, sys
d = json.load(sys.stdin)
for r in d.get('results', []):
    print('-', r.get('title'), '|', r.get('url'), '|', (r.get('date') or ''), '|', (r.get('snippet') or '')[:230].replace('\n', ' '))
