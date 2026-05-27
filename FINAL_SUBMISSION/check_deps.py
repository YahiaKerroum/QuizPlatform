import json, re

with open('FinalSubmissionReviewed.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, c in enumerate(nb['cells']):
    if c['cell_type'] == 'code':
        src = ''.join(c['source'])
        # Look for file paths being loaded
        matches = re.findall(r'[\'"](.*?\.(?:csv|json|xlsx|txt|pkl|md))[\'"]', src)
        if matches:
            print(f'Cell {i} references files:', matches)
