import pandas as pd
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv(r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env')
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

FILE_PATH = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx'

def get_gemini_sku(products):
    prompt = """
    You are a SKU naming expert. Create SEMANTIC SKUs for these products.
    
    Structure: [BRAND_3_CHARS]-[CATEGORY_3_CHARS]-[KEYWORD_TERM_MAX_6_CHARS]
    All Uppercase. Max 15 chars.
    
    Example: 
    "Central Nutrition Omega 3 120 Caps" -> "CEN-SUP-OMEGA3"
    "Mushin Lions Mane Po" -> "MUS-COG-LIONS"
    
    Products:
    """ + "\n".join(products) + """
    
    Output JSON: {"Product Name": "SKU"}
    """
    
    models = ["gemini-3.0-flash-preview", "gemini-2.0-flash-exp", "gemini-1.5-flash"]
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    last_error = ""
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            resp = requests.post(url, headers=headers, json=data)
            if resp.status_code == 200:
                return resp.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                last_error = f"Model {model} Error {resp.status_code}: {resp.text}"
        except Exception as e:
            last_error = f"Model {model} Exception: {e}"
            
    return f"Error: All models failed. Last error: {last_error}"

def preview():
    df = pd.read_excel(FILE_PATH)
    sample = df['Descrição'].dropna().sample(10).tolist()
    
    print("🤖 Generating Semantic SKUs for Sample...")
    result_text = get_gemini_sku(sample)
    
    # Clean JSON
    if result_text.startswith('```json'): result_text = result_text[7:]
    if result_text.endswith('```'): result_text = result_text[:-3]
    
    try:
        data = json.loads(result_text)
        print("\n--- Proposed SKUs ---")
        for k, v in data.items():
            print(f"{k[:40].ljust(40)} -> {v}")
    except:
        print("Raw Output:", result_text)

if __name__ == "__main__":
    preview()
