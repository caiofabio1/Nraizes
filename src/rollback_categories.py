
import requests
import json
import os
import time
from dotenv import load_dotenv

load_dotenv(r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

def rollback():
    print("🚨 INICIANDO ROLLBACK DE CATEGORIAS...")
    
    # 1. Load Map
    map_file = r'c:\Users\caiof\NRAIZES\category_map.json'
    if not os.path.exists(map_file):
        print("❌ Map file not found.")
        return

    with open(map_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 2. Identify Candidates (IDs > 12000000)
    # Existing were 110xxxxx
    # New are 129xxxxx
    to_delete = []
    for name, cid in data.items():
        if cid > 11500000: # Safe threshold
            to_delete.append((cid, name))
    
    # Sort descending by ID to delete children first? 
    # Or does order matter? 
    # Bling might prevent deleting Parent if it has Children.
    # So we must delete Children First.
    # Assuming higher IDs are children (created later)? Yes, mostly.
    # Safe to reverse sort.
    to_delete.sort(key=lambda x: x[0], reverse=True)
    
    print(f"⚠️ Identificadas {len(to_delete)} categorias para exclusão.")
    
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    
    count = 0
    errors = 0
    
    for cid, name in to_delete:
        url = f'https://api.bling.com.br/Api/v3/categorias/produtos/{cid}'
        print(f"  🗑️ Apagando: {name} ({cid})...")
        
        r = requests.delete(url, headers=headers)
        
        if r.status_code == 204 or r.status_code == 200:
            count += 1
        elif r.status_code == 404:
            print("    (Já apagado)")
        else:
            print(f"    ❌ Erro {r.status_code}: {r.text}")
            errors += 1
            
        time.sleep(0.2)
        
    print("="*60)
    print(f"✅ Rollback concluído. Apagados: {count}. Erros: {errors}.")

if __name__ == "__main__":
    rollback()
