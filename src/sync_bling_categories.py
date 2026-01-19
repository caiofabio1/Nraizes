
import requests
import os
import json
import pandas as pd
import time
from dotenv import load_dotenv

load_dotenv(r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

class BlingCategoryManager:
    def __init__(self):
        self.headers = {'Authorization': f'Bearer {ACCESS_TOKEN}', 'Content-Type': 'application/json'}
        self.cache = {} # "path > name": id  (normalized lower)
        self.id_to_name = {}

    def normalize(self, text):
        return text.strip().lower()

    def fetch_current_tree(self):
        print("📥 Buscando árvore atual de categorias...")
        page = 1
        raw_cats = []
        while True:
            url = f'https://api.bling.com.br/Api/v3/categorias/produtos?pagina={page}&limite=100'
            try:
                r = requests.get(url, headers=self.headers)
                data = r.json().get('data', [])
                if not data: break
                raw_cats.extend(data)
                page += 1
            except Exception as e:
                print(f"Erro fetch: {e}")
                break
        
        # Build path map
        # Need multiple passes or recursion because parent info is just ID
        temp_map = {c['id']: c for c in raw_cats}
        
        def get_full_path(cid):
            curr = temp_map.get(cid)
            parts = []
            while curr:
                parts.insert(0, curr['descricao'])
                pid = curr.get('categoriaPai', {}).get('id', 0)
                if pid and pid != 0:
                    curr = temp_map.get(pid)
                else:
                    curr = None
            return " > ".join(parts)

        for c in raw_cats:
            full_path = get_full_path(c['id'])
            # key: normalized full path
            self.cache[self.normalize(full_path)] = c['id']
            self.id_to_name[c['id']] = full_path
            
        print(f"✅ Cache inicializado: {len(self.cache)} categorias.")

    def create_category(self, name, parent_id=0):
        url = 'https://api.bling.com.br/Api/v3/categorias/produtos'
        payload = {"descricao": name}
        if parent_id != 0:
            payload["categoriaPai"] = {"id": parent_id}
            
        # print(f"  🆕 Criando: {name} (Pai: {parent_id})")
        r = requests.post(url, headers=self.headers, json=payload)
        
        if r.status_code == 201:
            return r.json()['data']['id']
        elif r.status_code == 429:
            time.sleep(2)
            return self.create_category(name, parent_id)
        else:
            print(f"  ❌ Erro ao criar '{name}': {r.text}")
            return None

    def ensure_path(self, path_str):
        # path_str: "A > B > C" with original casing
        parts = [p.strip() for p in path_str.split('>')]
        current_parent_id = 0
        current_path_str = ""
        
        for part in parts:
            if current_path_str:
                current_path_str += " > " + part
            else:
                current_path_str = part
                
            key = self.normalize(current_path_str)
            
            if key in self.cache:
                current_parent_id = self.cache[key]
            else:
                # Create
                print(f"  ✨ Criando categoria: {part} (em {current_path_str})")
                new_id = self.create_category(part, current_parent_id)
                if new_id:
                    self.cache[key] = new_id
                    current_parent_id = new_id
                    time.sleep(0.3) # Rate limit safe
                else:
                    return None
        
        return current_parent_id

def main():
    print("🚀 Sincronizador de Categorias Bling v3")
    
    # 1. Load Excel
    file_path = r'c:\Users\caiof\NRAIZES\produtos_refinados_v2.xlsx'
    df = pd.read_excel(file_path)
    
    unique_paths = df['Categoria do produto'].dropna().unique()
    unique_paths = [str(x).strip() for x in unique_paths if str(x).strip() != '']
    unique_paths.sort()
    
    print(f"📂 {len(unique_paths)} rotas únicas para verificar.")
    
    # 2. Init Manager
    mgr = BlingCategoryManager()
    mgr.fetch_current_tree()
    
    # 3. Create missing
    path_to_id = {}
    
    for path in unique_paths:
        final_id = mgr.ensure_path(path)
        if final_id:
            path_to_id[path] = final_id
            
    print(f"✅ Estrutura sincronizada!")
    
    # 4. Save Map
    with open(r'c:\Users\caiof\NRAIZES\category_map.json', 'w', encoding='utf-8') as f:
        json.dump(path_to_id, f, ensure_ascii=False, indent=2)
        
    print(r"💾 Mapa salvo em category_map.json")
    
    # 5. Update Excel with IDs
    # (Optional, but good for next step)
    df['id_categoria_bling'] = df['Categoria do produto'].map(path_to_id)
    df.to_excel(file_path, index=False)
    print(r"💾 Excel atualizado com IDs de categoria.")

if __name__ == "__main__":
    main()
