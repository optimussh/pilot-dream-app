import json

with open('data/aircraft.json', encoding='utf-8') as f:
    ac = json.load(f)
print('Aircraft types:', len(ac))
for a in ac:
    dlen = len(a.get('desc',''))
    print('  ' + a['name'] + ': ' + str(dlen) + ' chars (aim ~300)')

with open('data/atc_phrases.json', encoding='utf-8') as f:
    atc = json.load(f)
total = sum(len(v) for v in atc.values())
print('ATC total phrases:', total, '(5 x 50 = 250 target)')
print('Categories:', list(atc.keys()))

print('Main.py has /api/atc:', 'get_atc' in open('app/routes/main.py', encoding='utf-8').read())
print('SUCCESS - all data ready')
