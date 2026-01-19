
import pandas as pd
import requests
import os
import json
from dotenv import load_dotenv

# Load Env
load_dotenv(r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

def analyze():
    print("="*60)
    print("🔬 ANÁLISE DE ESTRUTURA: TAGS E CATEGORIAS")
    print("="*60)
    
    # 1. Check Excel
    file_path = r'c:\Users\caiof\NRAIZES\produtos_refinados_v2.xlsx'
    if os.path.exists(file_path):
        print(f"\n📂 Arquivo Excel: {file_path}")
        try:
            df = pd.read_excel(file_path, nrows=5)
            print("  Colunas encontradas:")
            print(df.columns.tolist())
            
            # Check for potential tag columns
            candidates = ['Tags', 'Palavras-chave', 'Keywords', 'Categoria', 'Categoria do produto']
            for c in candidates:
                if c in df.columns:
                    print(f"  ✅ Coluna explícita: {c}")
                    print(f"     Exemplo: {df[c].iloc[0]}")
        except Exception as e:
            print(f"  ❌ Erro ao ler Excel: {e}")
    else:
        print(f"  ❌ Arquivo não encontrado.")

    # 2. Check Bling API (Sample)
    print("\n🌐 Verificando API Bling (Amostra)...")
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    
    # Get 1 active product
    url_list = 'https://api.bling.com.br/Api/v3/produtos?limite=1&situacao=A'
    r = requests.get(url_list, headers=headers)
    
    if r.status_code == 200:
        data = r.json()
        items = data.get('data', [])
        if items:
            pid = items[0]['id']
            print(f"  Buscando detalhes do produto ID: {pid} ({items[0]['nome']})")
            
            # Get Details
            r_det = requests.get(f'https://api.bling.com.br/Api/v3/produtos/{pid}', headers=headers)
            if r_det.status_code == 200:
                prod = r_det.json().get('data', {})
                
                # Check Category
                cat = prod.get('categoria', {}) # Object?
                print(f"  📂 Categoria (API): {json.dumps(cat, indent=2, ensure_ascii=False)}")
                
                # Check Tags? (Is it a direct field?)
                print(f"  🏷️  Campos de topo no JSON: {list(prod.keys())}")
                
                # Often tags are not in main endpoint? Or named differently?
                # Check 'tags', 'palavrasChave'?
                for k in ['tags', 'tag', 'palavrasChave', 'keywords']:
                    if k in prod:
                        print(f"  ✅ Campo '{k}': {prod[k]}")
            else:
                print(f"  ❌ Erro detalhes: {r_det.status_code}")
        else:
            print("  ⚠️ Nenhum produto encontrado.")
    else:
        print(f"  ❌ Erro lista: {r.status_code}")

if __name__ == "__main__":
    analyze()
