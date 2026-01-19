
import requests
import os
import json
import pandas as pd
from dotenv import load_dotenv

load_dotenv(r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

def get_bling_categories():
    print("📥 Buscando categorias do Bling...")
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    categories = []
    page = 1
    
    while True:
        url = f'https://api.bling.com.br/Api/v3/categorias/produtos?pagina={page}&limite=100'
        # Note: check endpoint correctness. v3 is /categorias/produtos? 
        # Or /categorias?
        # Standard v3 is /categorias/produtos.
        
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"  ❌ Erro API ({r.status_code}): {r.text}")
            break
            
        data = r.json().get('data', [])
        if not data:
            break
            
        categories.extend(data)
        print(f"  Página {page}: {len(data)} categorias")
        page += 1
        
    print(f"✅ Total categorias no Bling: {len(categories)}")
    return categories

def map_categories():
    # 1. Fetch Bling Cats
    bling_cats = get_bling_categories()
    
    # Build Map path -> id
    # Bling returns id, descricao, categoriaPai.
    # We need to build full path "Pai > Filho".
    
    cat_map = {c['id']: c for c in bling_cats}
    
    # Helper to get full name
    def get_full_name(cid):
        parts = []
        curr = cat_map.get(cid)
        while curr:
            parts.insert(0, curr['descricao'])
            pid = curr.get('categoriaPai', {}).get('id')
            if pid and pid != 0:
                curr = cat_map.get(pid)
            else:
                curr = None
        return " > ".join(parts)

    name_to_id = {}
    print("\n📂 Estrutura de Categorias Bling:")
    for c in bling_cats:
        full_name = get_full_name(c['id'])
        name_to_id[full_name.lower()] = c['id']
        # print(f"  - {full_name} (ID: {c['id']})")
    
    print(f"  (Mapeadas {len(name_to_id)} rotas de categorias)")

    # 2. Load Excel
    file_path = r'c:\Users\caiof\NRAIZES\produtos_refinados_v2.xlsx'
    df = pd.read_excel(file_path)
    
    if 'Categoria do produto' not in df.columns:
        print("❌ Coluna 'Categoria do produto' não encontrada no Excel.")
        return

    print("\n🔗 Mapeando Excel -> Bling...")
    
    matched = 0
    missing = 0
    missing_names = set()
    
    for idx, row in df.iterrows():
        cat_name = str(row.get('Categoria do produto', '')).strip()
        if not cat_name or cat_name == 'nan' or cat_name == 'None':
            continue
            
        # Try match
        # AI generated "Cat > Sub". Bling separator might be different or fuzzy.
        # Simple lowercase match
        key = cat_name.lower()
        if key in name_to_id:
            matched += 1
            # We found a match!
        else:
            missing += 1
            missing_names.add(cat_name)
    
    print(f"✅ Mapeados: {matched}")
    print(f"⚠️ Sem correspondência exata: {missing}")
    
    # Suggest creation
    print("\n📝 Gerando plano de criação...")
    
    unique_missing = sorted(list(missing_names))
    
    md_content = "# Plano de Estruturação de Categorias\n\n"
    md_content += f"## Status Atual\n- Categorias no Bling: {len(bling_cats)}\n"
    md_content += f"- Produtos Mapeados: {matched}\n"
    md_content += f"- Produtos Sem Categoria Correspondente: {missing}\n\n"
    
    md_content += "## Novas Categorias Sugeridas (Criação Hierárquica)\n"
    md_content += "Estas categorias foram identificadas pela IA e não existem no Bling. Sugiro criá-las:\n\n"
    
    for name in unique_missing:
        md_content += f"- [ ] {name}\n"
        
    # Check Tags API status
    print("\n🏷️ Verificando endpoint de Tags...")
    tags_url = 'https://api.bling.com.br/Api/v3/tags' # Hypothetical v3 endpoint
    # Actually v3 'tags' endpoint exists? 
    # Let's try.
    try:
        r_tags = requests.get(tags_url, headers={'Authorization': f'Bearer {ACCESS_TOKEN}'})
        if r_tags.status_code == 200:
            tags_data = r_tags.json().get('data', [])
            md_content += f"\n## Tags no Sistema\n- Encontradas: {len(tags_data)}\n"
            if tags_data:
                md_content += f"- Exemplo: {tags_data[0].get('nome')}\n"
        else:
             md_content += f"\n## Tags\n- Endpoint /tags retornou: {r_tags.status_code}\n"
    except:
        pass

    with open(r'c:\Users\caiof\.gemini\antigravity\brain\fe8138f0-a67a-47f2-a687-2eca4fb3db4f\category_structure_plan.md', 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    print("✅ Plano gerado em: category_structure_plan.md")


if __name__ == "__main__":
    map_categories()
