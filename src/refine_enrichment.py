
import pandas as pd
import requests
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load Env
load_dotenv(r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env')

GENAI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configurable URL (using user requested model)
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GENAI_API_KEY}"
FALLBACK_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GENAI_API_KEY}"

def clean_json_response(text):
    text = text.strip()
    if text.startswith('```json'):
        text = text[7:]
    if text.endswith('```'):
        text = text[:-3]
    return text

def generate_content(prompt):
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }
    
    # Try user URL
    try:
        resp = requests.post(API_URL, headers=headers, json=data, timeout=30)
    except:
        resp = None

    if not resp or resp.status_code != 200:
        # Fallback
        try:
             resp = requests.post(FALLBACK_URL, headers=headers, json=data, timeout=30)
        except:
             return None

    if resp and resp.status_code == 200:
        try:
            return resp.json()['candidates'][0]['content']['parts'][0]['text']
        except:
            return None
    return None

def refine_product(row):
    name = row['Descrição']
    current_brand = str(row.get('Marca', '')).strip()
    current_obs = str(row.get('Observações', '')).strip()
    

    # Logic: Production Type (Default T, override if NR)
    prod_type = 'T'
    if 'novas raízes' in current_brand.lower() or 'novas raizes' in current_brand.lower():
        prod_type = 'P'
        
    prompt = f"""
    Analise este produto: "{name}" (Preço: {row.get('Preço')}).
    Marca atual no cadastro: "{current_brand}".
    
    TAREFAS:
    1. Identifique a MARCA correta. Se for 'Novas Raízes', confirme.
    2. Determine a CATEGORIA ideal para o Mercado Livre.
    3. Identifique atributos: 'eVegano' (Sim/Não), 'eLivreDeGluten' (Sim/Não).
    4. Gere uma DESCRIÇÃO COMERCIAL (HTML) para 'Descrição Complementar'. 
       - Use <b> para destaques.
       - Liste benefícios em <ul><li>.
       - Seja persuasivo mas fiel ao produto.
    5. Defina 'Tipo Produção': 'P' (Se marca for Novas Raízes) ou 'T' (Outras marcas).

    Retorne APENAS JSON:
    {{
        "marca": "Nome da Marca",
        "categoria": "Categoria > Subcategoria",
        "vegano": "Sim/Não",
        "gluten_free": "Sim/Não",
        "descricao_html": "<p>...</p>",
        "tipo_producao": "P" ou "T"
    }}
    """
    
    ai_data = None
    try:
        text = generate_content(prompt)
        if text:
            ai_data = json.loads(clean_json_response(text))
    except Exception as e:
        # print(f"Erro AI em {name}: {e}")
        pass

    return {'ai_data': ai_data, 'fallback_type': prod_type}

def main():
    # Always start from Original to avoid mixed state from partial runs
    input_path = r'c:\Users\caiof\NRAIZES\produtos_2026-01-12-15-23-54.xls'
    output_path = r'c:\Users\caiof\NRAIZES\produtos_refinados_v2.xlsx'
    
    input_path = r'c:\Users\caiof\NRAIZES\produtos_2026-01-12-15-23-54.xls'
    output_path = r'c:\Users\caiof\NRAIZES\produtos_refinados_v2.xlsx'
    
    # FORCE Start from original to fix bad descriptions
    print(f"📂 Iniciando do original (FORÇADO): {input_path}")
    df = pd.read_excel(input_path)
    
    print(f"🚀 Iniciando Re-Enriquecimento COMPLETO de {len(df)} produtos (Paralelo 25 threads)...")
    
    updates = {}
    tasks = []
    
    # Ensure columns
    cols = ['Marca', 'Categoria do produto', 'eVegano', 'eLivreDeGluten', 'Descrição Complementar', 'Tipo Produção']
    for c in cols:
        if c not in df.columns:
            df[c] = None

    for idx, row in df.iterrows():
        # Process ALL
        tasks.append((idx, row))
        
    print(f"📋 {len(tasks)} produtos para processar.")
    
    completed = 0
    total = len(tasks)
    
    if total == 0:
        print("✅ Tudo pronto!")
        return
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        future_to_idx = {executor.submit(refine_product, row): idx for idx, row in tasks}
        
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                res = future.result()
                updates[idx] = res
            except:
                pass
            
            completed += 1
            if completed % 20 == 0:
                print(f"  ✅ {completed}/{total} processados...")
                apply_updates_to_df(df, updates)
                df.to_excel(output_path, index=False)
                updates = {}

    apply_updates_to_df(df, updates)
    df.to_excel(output_path, index=False)
    print("="*60)
    print(f"✅ Re-Enriquecimento concluído! Salvo em: {output_path}")

def apply_updates_to_df(df, updates):
    if not updates: return
    for idx, res in updates.items():
        data = res.get('ai_data')
        
        if data:
            df.at[idx, 'Marca'] = data.get('marca')
            df.at[idx, 'Categoria do produto'] = data.get('categoria')
            df.at[idx, 'eVegano'] = data.get('vegano')
            df.at[idx, 'eLivreDeGluten'] = data.get('gluten_free')
            df.at[idx, 'Descrição Complementar'] = data.get('descricao_html')
            df.at[idx, 'Tipo Produção'] = data.get('tipo_producao')
        else:
            # Fallback logic if AI failed?
            # At least set Type based on existing brand if possible
            # But we generated nothing.
            pass
            
if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
