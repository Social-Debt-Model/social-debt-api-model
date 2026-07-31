import json
import os
import glob

notebooks = glob.glob("Modelo_adaptativo_deuda_social_julio/**/*.ipynb", recursive=True)
os.makedirs("scratch", exist_ok=True)

for nb in notebooks:
    with open(nb, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    code = []
    for cell in data.get('cells', []):
        if cell.get('cell_type') == 'code':
            source = ''.join(cell.get('source', []))
            code.append(source)
    
    nb_name = os.path.basename(nb).replace('.ipynb', '.py')
    with open(os.path.join("scratch", nb_name), 'w', encoding='utf-8') as f:
        f.write('\n\n# ---\n\n'.join(code))
    print(f"Extracted {nb_name}")
