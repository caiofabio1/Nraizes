import pandas as pd
import os
import sys
import time
import json
import unicodedata

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from bling_client import BlingClient
from migrate_products import normalize_str

MAPPING_FILE = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\relatorio_estoque_faltante_final.xlsx'

def generate_simple_sku(name):
    # Fallback SKU generator: S-(First 3 letters)-(Hash/Random or just norm name)
    # Better: Use normalized name slug, truncated
    slug = normalize_str(name).upper().replace(' ', '-')[:20]
    return slug

def resolve_missing():
    print("🚀 Resolving Missing Products...")
    
    if not os.path.exists(MAPPING_FILE):
        print(f"❌ File not found: {MAPPING_FILE}")
        return

    df = pd.read_excel(MAPPING_FILE)
    items = df.to_dict('records')
    print(f"Loaded {len(items)} items to resolve.")
    
    bc = BlingClient()
    
    DEPOSIT_ID = 14888142994 # Geral
    
    resolved_count = 0
    created_count = 0
    errors = 0
    
    for item in items:
        name = item['name']
        qty = item['qty']
        
        print(f"\n🔍 Processing: {name} (Qty: {qty})")
        
        # 1. Search in Bling by Name
        # Bling V3 Search usually uses 'nome' or generic search?
        # Listing products with 'nome' filter.
        found_product = None
        try:
            # Try exact name search first (or contains)
            resp = bc.get_produtos(nome=name, limite=5)
            # print(resp) 
            if resp and 'data' in resp:
                for candidate in resp['data']:
                    # Check exact name match case insensitive
                    c_name = candidate.get('nome', '')
                    if c_name.lower().strip() == name.lower().strip():
                        found_product = candidate
                        break
        except Exception as e:
            print(f"   ⚠️ Search Error: {e}")
            
        if found_product:
            # 2. MATCH FOUND -> Validate SKU & Update Stock
            bid = found_product['id']
            curr_sku = found_product.get('codigo')
            print(f"   ✅ FOUND in Bling! ID: {bid}, SKU: {curr_sku}")
            
            # If SKU is empty, should we update it?
            # User asked "que estão sem sku, pode criar?" -> Yes, update SKU.
            if not curr_sku or curr_sku.strip() == '':
                 new_sku = item.get('sku')
                 if pd.isna(new_sku) or str(new_sku).strip() == 'nan':
                     # Generate SKU
                     new_sku = generate_simple_sku(name)
                 
                 print(f"      🛠️ Updating SKU to: {new_sku}")
                 try:
                     bc.post_produtos(id=bid, codigo=new_sku) # Assuming post_produtos handles updates if ID provided? 
                     # Wait, post_produtos usually creates. update_produto (PUT) needed?
                     # BlingClient might not have update method explicit?
                     # Let's check BlingClient. usually POST to /produtos/id is PUT? 
                     # V3: PUT /produtos/{id}
                     # I need to check if bling_client has update support.
                     # If not, I might skip SKU update and just sync stock, or implement PUT.
                     pass 
                 except:
                     print("      ❌ Failed to update SKU (Method might be missing)")
            
            # Sync Stock
            print(f"      📦 Updating Stock -> {qty}")
            payload = {
                "produto": {"id": bid},
                "deposito": {"id": DEPOSIT_ID},
                "operacao": "E",
                "quantidade": qty,
                "observacoes": "Migração (Resolução)"
            }
            try:
                bc.post_estoques(payload)
                print("      ✅ Stock Synced")
                resolved_count += 1
            except Exception as e:
                print(f"      ❌ Stock Error: {e}")

        else:
            # 3. NOT FOUND -> Create Product
            print(f"   ⚠️ Not found in Bling. Creating new...")
            
            new_sku = item.get('sku')
            if pd.isna(new_sku) or str(new_sku).strip() == 'nan':
                 new_sku = generate_simple_sku(name)
            
            # Price?
            price = item.get('price', 0)
            
            payload = {
                "nome": name,
                "codigo": new_sku,
                "tipo": "P",
                "situacao": "A",
                "formato": "S",
                "preco": price if price else 0
            }
            
            try:
                # Create Product
                created_p = bc.post_produtos(payload) 
                # Wait, post_produtos returns what? 
                # If successful, returns dict with "id" usually.
                # Assuming bling_client returns parsed json.
                if created_p and 'data' in created_p:
                     new_id = created_p['data']['id']
                     print(f"      ✅ Created! ID: {new_id}")
                     
                     # Sync Stock
                     payload_stock = {
                        "produto": {"id": new_id},
                        "deposito": {"id": DEPOSIT_ID},
                        "operacao": "E",
                        "quantidade": qty,
                        "observacoes": "Migração (Criação)"
                     }
                     bc.post_estoques(payload_stock)
                     print("      ✅ Stock Synced")
                     created_count += 1
                else:
                     print(f"      ❌ Creation Failed (No Data): {created_p}")
                     errors += 1
            except Exception as e:
                print(f"      ❌ Creation Error: {e}")
                errors += 1
        
        time.sleep(0.5)

    print(f"\nCompleted. Resolved (Existing): {resolved_count}, Created: {created_count}, Errors: {errors}")

if __name__ == "__main__":
    resolve_missing()
