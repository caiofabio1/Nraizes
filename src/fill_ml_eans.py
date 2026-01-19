
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))  # NRAIZES root

# Import EANFinder from src.ean_finder (needs to be importable)
# The file is at c:\Users\caiof\NRAIZES\src\ean_finder.py
from src.ean_finder import EANFinder

def main():
    # Input file: waits for the enriched file from previous step
    input_path = r'c:\Users\caiof\NRAIZES\produtos_refinados_v2.xlsx'
    
    if not os.path.exists(input_path):
        print(f"❌ Arquivo {input_path} não encontrado. Aguarde o passo anterior terminar.")
        return

    print(f"📂 Carregando {input_path}...")
    df = pd.read_excel(input_path)
    
    finder = EANFinder()
    
    # Identify rows without GTIN/EAN
    # Column name in Excel is likely 'GTIN/EAN'
    target_col = 'GTIN/EAN'
    if target_col not in df.columns:
        print(f"❌ Coluna {target_col} não encontrada.")
        return

    missing_ean_indices = df[df[target_col].isna() | (df[target_col].astype(str).str.strip() == '')].index
    
    print(f"🔍 Encontrados {len(missing_ean_indices)} produtos sem EAN.")
    
    print(f"🔍 Encontrados {len(missing_ean_indices)} produtos sem EAN.")
    
    updates = {}
    completed = 0
    total_missing = len(missing_ean_indices)
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Define tasks
    tasks = []
    for idx in missing_ean_indices:
        row = df.loc[idx]
        task_data = {
            'idx': idx,
            'desc': row['Descrição'],
            'codigo': row.get('Código', ''),
            'preco': row.get('Preço', 0)
        }
        tasks.append(task_data)
        
    def process_row(task):
        p_dict = {'nome': task['desc'], 'codigo': task['codigo'], 'preco': task['preco']}
        cands = finder.find_ean(p_dict)
        if cands and cands[0].confidence >= 0.7:
            return task['idx'], cands[0]
        return task['idx'], None

    # Run parallel
    print(f"🚀 Buscando EANs em paralelo (3 threads)...")
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_row, t): t for t in tasks}
        
        for future in as_completed(futures):
            idx, best_cand = future.result()
            completed += 1
            
            if best_cand:
                updates[idx] = best_cand.ean
                print(f"[{completed}/{total_missing}] ✅ EAN encontrado: {best_cand.ean}")
            else:
                print(f"[{completed}/{total_missing}] ❌ Não encontrado")

            if completed % 5 == 0:
                # Save partial
                for i, ean in updates.items():
                    df.at[i, target_col] = ean
                df.to_excel(input_path, index=False)
                
    # Final apply
    for i, ean in updates.items():
        df.at[i, target_col] = ean
        
    df.to_excel(input_path, index=False)
    print(f"\n🎉 Processo finalizado! {len(updates)} novos EANs preenchidos.")

if __name__ == "__main__":
    main()
