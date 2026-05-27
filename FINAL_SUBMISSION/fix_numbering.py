import json
import re

with open('FinalSubmissionReviewed.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

new_cells = []
for cell in nb['cells']:
    if cell['cell_type'] == 'markdown':
        src = ''.join(cell['source'])
        
        # Split glued heading §6 in Cell 36
        if '## §6: Borderline Analysis' in src:
            parts = src.split('## §6: Borderline Analysis & Robustness')
            cell['source'] = [line + '\n' for line in parts[0].strip().split('\n')]
            new_cells.append(cell)
            new_cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## §6: Borderline Analysis & Robustness\n"] + [line + '\n' for line in parts[1].strip().split('\n') if line]
            })
            continue
            
        # Split glued heading §6.6 in Cell 42
        elif '## §6.6: Sensitivity Analysis' in src:
            parts = src.split('## §6.6: Sensitivity Analysis: Difficulty Distribution Changes')
            cell['source'] = [line + '\n' for line in parts[0].strip().split('\n')]
            new_cells.append(cell)
            new_cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## §6.6: Sensitivity Analysis: Difficulty Distribution Changes\n"] + [line + '\n' for line in parts[1].strip().split('\n') if line]
            })
            continue
    
    new_cells.append(cell)

nb['cells'] = new_cells

# Pass 2: Search and Replace numbering text
for cell in nb['cells']:
    if not cell['source']: continue
    
    # We will modify lines directly to ensure exact match replacements
    new_source = []
    for line in cell['source']:
        # Fix missing Section 0
        if line.startswith('### §0.2: Feature Matrix Construction'):
            new_source.append('## §0: Data Pre-computation & Model Setup\n\n')
            new_source.append('### §0.1: Feature Matrix Construction\n')
            continue
        line = line.replace('### §0.3', '### §0.2')
        line = line.replace('### §0.4', '### §0.3')
        
        # Code cells
        line = line.replace('# §2.1 — Difficulty vs Success Rate', '# §1.1 — Difficulty vs Success Rate')
        
        # Section 3: Classifier selection was missing
        if line.startswith('### Design Decision: Why Logistic Regression?'):
            new_source.append('## §3: Classifier Selection\n\n')
            new_source.append(line)
            continue
            
        line = line.replace('# §4.2 — Ablated CV', '# §3.1 — Ablated CV')
        
        line = line.replace('## §5: Adaptive Strategy', '## §4: Adaptive Strategy')
        line = line.replace('# §5.7 — Simulated New Students', '# §4.1 — Simulated New Students')
        
        line = line.replace('## §6: Borderline Analysis', '## §5: Borderline Analysis')
        line = line.replace('# §6.5 — Robustness to Noisy Answers', '# §5.1 — Robustness to Noisy Answers')
        line = line.replace('## §6.6: Sensitivity Analysis', '## §6: Sensitivity Analysis')
        line = line.replace('# §6.6 — Sensitivity Analysis', '# §6.1 — Sensitivity Analysis')
        
        line = line.replace('## §7: Real Data: Data Mining Quizzes', '## §7: Real Data Validation: Data Mining')
        line = line.replace('# §8 — Real Data Validation: Data Mining Quizzes', '# §7.1 — Real Data Validation: Data Mining Quizzes')
        
        line = line.replace('## §8: Real Data: Operating Systems & ITE', '## §8: Real Data: Operating Systems & ITE')
        line = line.replace('# §9 — Real Data CV: Lectu/ENSIA', '# §8.1 — Real Data CV: Lectu/ENSIA')
        
        line = line.replace('## §10: Cross-Curriculum Generalisation', '## §9: Cross-Curriculum Generalisation')
        line = line.replace('# §10 — Cross-Curriculum Generalisation', '# §9.1 — Cross-Curriculum Generalisation')
        
        line = line.replace('## §12: Live Demo', '## §10: Live Demo & Integration')
        line = line.replace('# §13.1 — Feature Computation', '# §10.1 — Feature Computation')
        line = line.replace('# §13.2 — Predict Level', '# §10.2 — Predict Level, Adaptive Selection')
        
        line = line.replace('## Section 14 — Single-Module Adaptive', '## §11: Single-Module Adaptive Assessment Model')
        line = line.replace('### 14.8 Multi-module vs single-module', '### §11.1: Multi-module vs single-module')
        line = line.replace('### 14.9 Results', '### §11.2: Results')
        
        line = line.replace('## §15: Limitations & Honest Assessment', '## §12: Limitations & Honest Assessment')
        line = line.replace('## §16: Conclusion', '## §13: Conclusion')
        
        new_source.append(line)
        
    cell['source'] = new_source

with open('FinalSubmissionReviewed.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print('Notebook successfully reviewed, split, and renumbered!')
