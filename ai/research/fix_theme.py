import json

with open('FinalSubmissionCleaned.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code' and 'sns.set_theme' in ''.join(cell['source']):
        src = ''.join(cell['source'])
        
        # Split at plt.rcParams.update
        parts = src.split('plt.rcParams.update({')
        pre_rc = parts[0]
        rest = 'plt.rcParams.update({' + parts[1]
        
        # Split the rest to find where sns.set_theme is
        parts2 = rest.split('# Seaborn — keep consistent with rcParams')
        rc_block = parts2[0]
        sns_block = '# Seaborn — keep consistent with rcParams' + parts2[1]
        
        # Now rearrange: pre_rc + sns_block + \n + rc_block
        new_src = pre_rc.rstrip() + '\n\n' + sns_block.rstrip() + '\n\n' + rc_block.strip()
        
        cell['source'] = [line + '\n' for line in new_src.split('\n')]
        cell['source'][-1] = cell['source'][-1].rstrip()
        
        print('Cell modified successfully.')

with open('FinalSubmissionCleaned.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
