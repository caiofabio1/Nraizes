import pandas as pd
import time
import os
import sys
import requests
import json
import unicodedata

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__)))
from bling_client import BlingClient
from gestao_client import GestaoClient
from migrate_products import normalize_str
from dotenv import load_dotenv

# Load Environment Mechanism for Gemini
load_dotenv(r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env')
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
MODELS = ["gemini-3.0-flash-preview", "gemini-2.0-flash-exp", "gemini-1.5-flash"]

def get_gemini_response(prompt, model_index=0):
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY not found. Skipping AI.")
        return None

    model = MODELS[model_index]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        resp = requests.post(url, headers=headers, json=data)
        if resp.status_code != 200:
            if model_index + 1 < len(MODELS):
                return get_gemini_response(prompt, model_index + 1)
            else:
                return None
        return resp.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return None

MAPPING_FILE = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx'

def clean_price(val):
    try:
        if pd.isna(val) or val == '': return 0.0
        if isinstance(val, (int, float)): return float(val)
        s = str(val).replace('R$', '').replace('.', '').replace(',', '.').strip()
        if not s: return 0.0
        return float(s)
    except:
        return 0.0

def migrate_stock():
    print("🚀 Starting Stock Migration (Gestão Click -> Bling)...")
    
    gc = GestaoClient()
    bc = BlingClient()
    
    print(f"   [DEBUG] GC Token loaded: {gc.access_token[:5]}...{gc.access_token[-5:] if gc.access_token else ''}")
    # Verify via test method first
    if not gc.test_connection():
         print("   ❌ GC Connection failed inside migration script.")
         return

    # 1. Load Bling ID Mapping
    print(f"📂 Loading Bling ID Map from {MAPPING_FILE}...")
    try:
        df_map = pd.read_excel(MAPPING_FILE)
        if 'ID' not in df_map.columns:
            print("❌ 'ID' column missing in mapping file.")
            return
        
        # Create lookup: Name -> Bling ID
        # Also Code -> Bling ID (Old or New?)
        # Let's rely on Name normalization as the primary link since SKUs changed
        df_map['Name_Norm'] = df_map['Descrição'].apply(normalize_str)
        bling_map = df_map.set_index('Name_Norm')['ID'].to_dict()
        print(f"   Loaded {len(bling_map)} mapped products.")
        
    except Exception as e:
        print(f"❌ Failed to load mapping file: {e}")
        return

    # 2. Fetch Gestão Click Stock
    print("📥 Fetching Stock from Gestão Click...")
    gc_products = []
    page = 1
    while True:
        print(f"   Page {page}...", end='\r')
        resp = gc.get_produtos(limit=100, page=page)
        
        if not resp:
            print(f"\n   ❌ Page {page}: No response or Request Failed.")
            break
            
        if 'data' not in resp:
             print(f"\n   ⚠️ Page {page}: 'data' not in response. Keys: {list(resp.keys())}")
             # print(f"Response Dump: {json.dumps(resp, indent=2)}")
             break
             
        if not resp['data']:
             print(f"\n   ℹ️ Page {page}: Empty data list. End of pages.")
             break
        
        print(f"   Page {page}: Fetched {len(resp['data'])} items.") # Debug line
        
        print(f"   Page {page}: Fetched {len(resp['data'])} items.") 
        
        for item in resp['data']:
            pid = item.get('id')
            sku = item.get('codigo')
            name = item.get('nome')
            
            # Fetch Detail for Stock
            qty = 0
            price = 0.0
            brand = ''
            
            # Try to get price from list item 'valores' first
            if isinstance(item.get('valores'), list) and len(item.get('valores')) > 0:
                 v = item['valores'][0]
                 price = clean_price(v.get('preco_venda'))
            
            if pid:
                 try:
                     detail = gc.get_produto(pid)
                     if detail and 'data' in detail:
                         d = detail['data']
                         qty = float(d.get('estoque', 0))
                         # Also check brand here? or category?
                         # Usually brand is a field or within 'geral'
                         # Let's just use what we have.
                 except Exception as e:
                     print(f"      ⚠️ Failed to fetch detail for {name}: {e}")
            
            gc_products.append({
                'name': name,
                'sku': sku,
                'qty': qty,
                'price': price,
                'brand': brand # Placeholder if not found
            })
            
            # Rate limit for detail fetch (don't hammer API)
            time.sleep(0.1)
        
        page += 1
        
        page += 1
    print(f"   Fetched {len(gc_products)} products from Gestão Click.")
    
    # 3. Match and Update
    print(f"\n🔄 Syncing Stock...")
    updated_count = 0
    skipped_count = 0
    
    DEPOSIT_ID = 14888142994 # Geral
    DRY_RUN = False # Perform actual update
    
    skipped_items = []

    for p in gc_products:
        name_norm = normalize_str(p['name'])
        qty = p['qty']
        
        if qty <= 0:
            continue
            
        bling_id = bling_map.get(name_norm)
        
        if not bling_id:
            skipped_count += 1
            skipped_items.append(p)
            print(f"   ⚠️ Skipped (No Match): {p['name']} (Qty: {qty})")
            continue
            
        print(f"   📦 Match found for {p['name']} (ID: {bling_id}) -> Qty: {qty}")
        
        if DRY_RUN:
            print("      [DRY RUN] Would post stock.")
            continue

        # Post Stock Movement
        payload = {
            "produto": {"id": int(bling_id)},
            "deposito": {"id": DEPOSIT_ID}, 
            "operacao": "E", # Entrada (Entry) to set initial stock
            "quantidade": qty,
            "observacoes": "Migração Gestão Click"
        }
        
        try:
            bc.post_estoques(payload)
            updated_count += 1
            print("      ✅ OK")
        except Exception as e:
            print(f"      ❌ Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 print(f"      Resp: {e.response.text}")
        
        time.sleep(0.2) # Rate limit

    print(f"\n✅ Completed Name Match. Updated/Matched {updated_count}. Skipped {len(skipped_items)}.")
    
    # ---------------------------------------------------------
    # AI MATCHING PHASE for SKIPPED ITEMS
    # ---------------------------------------------------------
    if skipped_items and GEMINI_API_KEY:
        print(f"\n🧠 Starting AI Matching for {len(skipped_items)} skipped items...")
        
        # Prepare Bling Context (All possible targets)
        # We need ID, Name, Brand, Price from the mapping file
        # Check mapping file columns first
        # df_map has 'Descrição', 'ID', 'Preço'
        
        bling_candidates = []
        for _, row in df_map.iterrows():
            bid = row.get('ID')
            bname = row.get('Descrição')
            bprice = row.get('Preço')
            # Extract brand if possible or assume contained in description
            # If we have 'Marca' column, use it
            bbrand = row.get('Marca') if 'Marca' in row else ''
            
            if pd.notna(bid):
                bling_candidates.append(f"ID: {bid} | Name: {bname} | Brand: {bbrand} | Price: {bprice}")
        
        full_bling_context = "\n".join(bling_candidates)
        
        # Process in Batches
        BATCH_SIZE = 10
        ai_matches = 0
        
        for i in range(0, len(skipped_items), BATCH_SIZE):
            batch = skipped_items[i:i+BATCH_SIZE]
            print(f"   AI Batch {i//BATCH_SIZE + 1} ({len(batch)} items)...")
            
            # Construct Prompt
            target_list_str = ""
            for j, p in enumerate(batch):
                 # p keys: name, sku, qty, (we need more detais? we fetched detail in loop!)
                 # but 'p' is just the dict we built.
                 # Let's see what we put in 'p'.
                 # We put: name, sku, qty.
                 # We don't have price in 'p'.
                 # We need to fetch price/brand from detail or we missed it?
                 # Wait, in the loop we fetched detail but only extracted 'estoque'.
                 # We SHOULD have extracted price/brand too if we wanted to match by them.
                 # Okay, I need to fix the loop to extract price/brand too.
                 # Assuming i fixed it below (I will need another edit to extract these fields).
                 
                 p_price = p.get('price', 'N/A')
                 p_brand = p.get('brand', 'N/A')
                 target_list_str += f"GC_Item_{j}: Name: {p['name']} | SKU: {p['sku']} | Price: {p_price} | Brand: {p_brand}\n"
            
            prompt = f"""
            You are a rigorous product matching expert.
            Map each "GC_Item" to the CORRECT "ID" from the Bling List.
            
            CRITERIA:
            1. Price must be similar (allow small variance).
            2. Brand must match (if present).
            3. Name must be semantically properly.
            
            Bling List:
            {full_bling_context}
            
            Items to Match:
            {target_list_str}
            
            Return ONLY JSON: {{ "GC_Item_0": "Bling_ID", "GC_Item_1": null }}
            """
            
            try:
                resp_text = get_gemini_response(prompt)
                if resp_text:
                    cleaned_json = resp_text.strip()
                    if cleaned_json.startswith('```json'): cleaned_json = cleaned_json[7:]
                    if cleaned_json.endswith('```'): cleaned_json = cleaned_json[:-3]
                    
                    matches = json.loads(cleaned_json)
                    
                    for key, bling_id_found in matches.items():
                        if bling_id_found and str(bling_id_found).lower() != 'null':
                            # Extract index from key
                            idx = int(key.split('_')[-1])
                            if idx < len(batch):
                                product = batch[idx]
                                matched_id = int(str(bling_id_found).strip())
                                
                                print(f"      ✨ AI Match: {product['name']} -> Bling ID: {matched_id}")
                                
                                # Post Stock
                                if not DRY_RUN:
                                    payload = {
                                        "produto": {"id": matched_id},
                                        "deposito": {"id": DEPOSIT_ID},
                                        "operacao": "E",
                                        "quantidade": product['qty'],
                                        "observacoes": "Migração Gestão Click (AI Match)"
                                    }
                                    try:
                                        bc.post_estoques(payload)
                                        updated_count += 1
                                        ai_matches += 1
                                        print("         ✅ Stock Updated")
                                    except Exception as e:
                                        print(f"         ❌ API Error: {e}")
                                else:
                                    print("         [DRY RUN] Would update stock.")
                                    ai_matches += 1
                                    
                                # Remove from skipped list for reporting? 
                                # Actually simpler to just mark it.
                                product['match_status'] = 'AI_MATCHED'
                                product['bling_id'] = matched_id
                                
            except Exception as e:
                print(f"   ⚠️ AI Process Error: {e}")
                time.sleep(1)

    print(f"\nFinal Stats:")
    print(f"Updated (Exact): {updated_count - ai_matches}")
    print(f"Updated (AI): {ai_matches}")
    
    # Save Full Mapping (Requested by User)
    if not DRY_RUN or ai_matches > 0:
        mapping_dump_file = os.path.join(os.path.dirname(MAPPING_FILE), 'id_mapping_final.xlsx')
        print(f"📄 Saving Full Match Mapping to {mapping_dump_file}...")
        
        all_matches = []
        # Add Exact Matches
        for p in gc_products:
             name_norm = normalize_str(p['name'])
             bid = bling_map.get(name_norm)
             if bid:
                 all_matches.append({
                     'gestao_click_name': p['name'],
                     'gestao_click_sku': p['sku'],
                     'bling_id': bid,
                     'match_type': 'EXACT'
                 })
                 
        # Add AI Matches
        for p in skipped_items:
            if p.get('match_status') == 'AI_MATCHED':
                all_matches.append({
                     'gestao_click_name': p['name'],
                     'gestao_click_sku': p['sku'],
                     'bling_id': p.get('bling_id'),
                     'match_type': 'AI'
                })
        
        if all_matches:
            pd.DataFrame(all_matches).to_excel(mapping_dump_file, index=False)
            print("   ✅ Mapping saved.")
    
    if skipped_items:
        # Filter out those we just matched
        still_missing = [p for p in skipped_items if p.get('match_status') != 'AI_MATCHED']
        if still_missing:
            report_file = os.path.join(os.path.dirname(MAPPING_FILE), 'relatorio_estoque_faltante_final.xlsx')
            print(f"📄 Saving {len(still_missing)} truly missing items to {report_file}...")
            df_missing = pd.DataFrame(still_missing)
            df_missing.to_excel(report_file, index=False)
            print("   ✅ Report saved.")
        else:
            print("🎉 All items matched!")

if __name__ == "__main__":
    migrate_stock()
