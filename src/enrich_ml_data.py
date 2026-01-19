
import pandas as pd
import requests
import os
import json
import time
from dotenv import load_dotenv

# Load Env
load_dotenv(r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env')

# Configure Gemini
GENAI_API_KEY = os.getenv('GEMINI_API_KEY')
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
# Note: User asked for gemini-3-flash-preview, but URL usually follows model name.
# Let's try to infer or use the exact one if known, but "gemini-3" is likely 2.0-flash-exp or similar in preview.
# Wait, user provided: https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent
# If that exact model exists, we use it. If 404, we fallback.
# Actually, I will trust the user and use the exact string "gemini-3.0-flash-preview" if that's what they mean, 
# but normally it's "gemini-1.5-flash" or "gemini-2.0-flash-exp". 
# "gemini-3" is highly likely a typo for "gemini-2.0-flash-exp" or future. 
# BUT, I will try to use the `gemini-1.5-flash` via SDK or `requests` to be safe if `3` fails?
# Let's stick to `requests` for flexibility.

# Let's assume the user really means "gemini-2.0-flash-exp" (often called Next Gen) or just blindly try what they pasted?
# They pasted: .../models/gemini-3-flash-preview...
# Use that EXACT URL.

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent" 
# REVERTING TO 1.5-flash because 3 doesn't exist publicly yet and might be a hallucination of the user or private.
# BUT, to respect the "execute" and "use this model", I will try to use a very robust one via requests.
# Actually, let's use `gemini-1.5-flash` via Requests to avoid SDK issues.

def clean_json_response(text):
    text = text.strip()
    if text.startswith('```json'):
        text = text[7:]
    if text.endswith('```'):
        text = text[:-3]
    return text

def generate_content(prompt):
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    # User requested specific URL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GENAI_API_KEY}"
    
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code != 200:
        # Fallback to 1.5 Flash if user URL fails (likely 404)
        print(f"⚠️ Erro no modelo solicitado ({resp.status_code}). Tentando fallback para gemini-1.5-flash...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GENAI_API_KEY}"
        resp = requests.post(url, headers=headers, json=data)
        
    if resp.status_code == 200:
        try:
            return resp.json()['candidates'][0]['content']['parts'][0]['text']
        except:
            return None
    return None

def enrich_product(row):
    retries = 3
    for attempt in range(retries):
        try:
            name = row['Descrição']
            desc = str(row['Observações']) if pd.notna(row['Observações']) else ""
            
            prompt = f"""
            Analise este produto para venda no Mercado Livre.
            Produto: {name}
            Descrição: {desc[:500]}
            
            Retorne JSON:
            {{ "Marca": "...", "Categoria": "...", "eVegano": "Sim/Não", "eLivreDeGluten": "Sim/Não", "formatoDoSuplemento": "...", "tipoDeSuplemento": "..." }}
            """
            
            text = generate_content(prompt)
            if text:
                return json.loads(clean_json_response(text))
            
        except Exception as e:
            time.sleep(1)
            if attempt == retries - 1:
                print(f"Erro: {e}")
                return None

from concurrent.futures import ThreadPoolExecutor, as_completed

def main():
    file_path = r'c:\Users\caiof\NRAIZES\produtos_2026-01-12-15-23-54.xls'
    print(f"📂 Carregando arquivo: {file_path}")
    
    try:
        df = pd.read_excel(file_path)
    except:
         df = pd.read_excel(file_path, engine='xlrd')

    total = len(df)
    print(f"🚀 Iniciando enriquecimento de {total} produtos (Paralelo)...")
    
    updates = {}
    
    # Process only rows that need enrichment
    # Create list of (index, row) tuples
    tasks = []
    for index, row in df.iterrows():
        if pd.notna(row.get('Marca')) and str(row.get('Marca')).strip() != '':
           continue
        tasks.append((index, row))
        
    print(f"📋 {len(tasks)} produtos precisam de enriquecimento.")

    enriched_count = 0
    
    # Use ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_index = {
            executor.submit(enrich_product, row): index 
            for index, row in tasks
        }
        
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            data = future.result()
            
            if data:
                updates[index] = data
                enriched_count += 1
                if enriched_count % 10 == 0:
                    print(f"  ✅ {enriched_count}/{len(tasks)} processados...")

    # Apply updates to dataframe
    print("💾 Aplicando alterações...")
    for index, data in updates.items():
        if not pd.notna(df.at[index, 'marca']) or str(df.at[index, 'marca']).strip() == 'nan':
             df.at[index, 'marca'] = data.get('Marca')
             # Also try standard capitalized column if exists or create it
             # df.at[index, 'Marca'] = data.get('Marca')

        if not pd.notna(df.at[index, 'Categoria do produto']):
            df.at[index, 'Categoria do produto'] = data.get('Categoria')

        df.at[index, 'eVegano'] = data.get('eVegano')
        df.at[index, 'eLivreDeGluten'] = data.get('eLivreDeGluten')
        
        if data.get('formatoDoSuplemento'):
            df.at[index, 'formatoDoSuplemento'] = data.get('formatoDoSuplemento')
        
        if data.get('tipoDeSuplemento'):
            df.at[index, 'tipoDeSuplemento'] = data.get('tipoDeSuplemento')

    output_file = r'c:\Users\caiof\NRAIZES\produtos_enriquecidos.xlsx'
    df.to_excel(output_file, index=False)
    print("=" * 60)
    print(f"✅ Concluído! Arquivo salvo em: {output_file}")
    print(f"📝 Produtos enriquecidos: {enriched_count}")

if __name__ == "__main__":
    main()
