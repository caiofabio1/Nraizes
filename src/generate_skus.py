import pandas as pd
import requests
import os
import json
import time
import unicodedata
from dotenv import load_dotenv

load_dotenv(r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env')
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

FILE_PATH = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx'
OUTPUT_FILE = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx' # Overwrite

# Models with fallback
MODELS = ["gemini-3.0-flash-preview", "gemini-2.0-flash-exp", "gemini-1.5-flash"]

def get_gemini_response(prompt, model_index=0):
    if not GEMINI_API_KEY:
        return None

    model = MODELS[model_index]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        resp = requests.post(url, headers=headers, json=data)
        if resp.status_code != 200:
            if model_index + 1 < len(MODELS):
                time.sleep(1)
                return get_gemini_response(prompt, model_index + 1)
            else:
                print(f"Error {resp.status_code}: {resp.text}")
                return None
        return resp.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Exception: {e}")
        return None

def normalize_str(s):
    if pd.isna(s): return ""
    return unicodedata.normalize('NFKD', str(s)).encode('ASCII', 'ignore').decode('ASCII').upper().strip()

def generate_skus():
    print(f"📂 Loading {FILE_PATH}...")
    df = pd.read_excel(FILE_PATH)
    
    # Ensure columns exist
    if 'Descrição' not in df.columns:
        print("❌ Column 'Descrição' missing.")
        return
        
    products = []
    for idx, row in df.iterrows():
        desc = str(row['Descrição'])
        brand = str(row.get('Marca', ''))
        old_sku = str(row.get('Código', ''))
        if desc == 'nan': continue
        
        products.append({
            'id': idx,
            'desc': desc,
            'brand': brand,
            'old_sku': old_sku
        })
        
    print(f"🚀 Processing {len(products)} products for SKU Generation...")
    
    generated_skus_map = {} # idx -> new_sku
    seen_skus = set()
    
    BATCH_SIZE = 30
    for i in range(0, len(products), BATCH_SIZE):
        batch = products[i:i+BATCH_SIZE]
        print(f"   Batch {i//BATCH_SIZE + 1} ({len(batch)} items)...")
        
        # Construct Prompt
        batch_text = "\n".join([f"ID_{item['id']}: {item['desc']} (Marca: {item['brand']})" for item in batch])
        
        prompt = f"""
        You are a SKU Generator.
        Create a SEMANTIC SKU for each product using format: [BRAND_3]-[CAT_3]-[KEYWORD_6]
        
        Rules:
        1. All Uppercase. No spaces. Use hyphens.
        2. BRAND_3: First 3 letters of Brand. If Brand unknown, infer from Description. If 'Generic', use 'GEN'.
        3. CAT_3: 3 letter code for Category (e.g., SUP=Supplement, COS=Cosmetic, OIL=Oil, FOO=Food, VIT=Vitamin).
        4. KEYWORD_6: Main product identifier term, max 6 chars.
        
        Input List:
        {batch_text}
        
        Output JSON:
        {{ "ID_0": "BRA-CAT-KEYWOR", "ID_1": "..." }}
        """
        
        resp_text = get_gemini_response(prompt)
        if resp_text:
             try:
                clean_json = resp_text.strip()
                if clean_json.startswith('```json'): clean_json = clean_json[7:]
                if clean_json.endswith('```'): clean_json = clean_json[:-3]
                
                mapping = json.loads(clean_json)
                
                for item in batch:
                    key = f"ID_{item['id']}"
                    if key in mapping:
                        raw_sku = mapping[key].strip().upper()
                        
                        # Uniqueness Check
                        final_sku = raw_sku
                        counter = 2
                        while final_sku in seen_skus:
                            # Truncate to make room for suffix if needed, or just append
                            base = raw_sku[:13] # Leave 2 chars for suffix if max 15
                            final_sku = f"{base}{counter}"
                            counter += 1
                        
                        seen_skus.add(final_sku)
                        generated_skus_map[item['id']] = final_sku
             except Exception as e:
                 print(f"   ❌ Batch Parse Error: {e}")
        else:
            print("   ❌ AI Failed to respond.")
            
        time.sleep(1)

    # Apply to DataFrame
    print("\n💾 Applying Changes...")
    count = 0
    for idx, new_sku in generated_skus_map.items():
        df.at[idx, 'Código'] = new_sku
        count += 1
        
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"✅ Updated {count} SKUs. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_skus()
