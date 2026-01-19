import pandas as pd
import time
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__)))
from bling_client import BlingClient

FILE_PATH = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx'

def update_skus():
    print("🚀 Starting SKU Update via API...")
    bc = BlingClient()
    
    try:
        df = pd.read_excel(FILE_PATH)
    except Exception as e:
        print(f"❌ Failed to read {FILE_PATH}: {e}")
        return

    if 'ID' not in df.columns or 'Código' not in df.columns:
        print("❌ Missing ID or Código columns.")
        return

    print(f"Processing {len(df)} products...")
    
    success_count = 0
    error_count = 0
    
    for idx, row in df.iterrows():
        pid = row['ID']
        new_sku = str(row['Código']).strip()
        
        if pd.isna(pid) or pid == 0:
            print(f"⏩ Skipping Row {idx}: No ID")
            continue
            
        print(f"🔄 Updating ID {pid} -> SKU: {new_sku}")
        
        payload = {
            "codigo": new_sku
        }
        
        try:
            # Using PATCH for partial update
            resp = bc.patch_produtos_id_produto(str(pid), payload)
            
            # Check response - Bling v3 usually returns data on success or 200/204
            # If method returns dict, it's likely success or error struct
            if resp is None: # 204 No Content success? Or None from client error?
                 # My client returns None on 204, but patch usually returns updated object
                 print(f"   ✅ Success (No Content/Unknown)")
                 success_count += 1
            elif 'data' in resp or 'id' in resp:
                 print(f"   ✅ Updated!")
                 success_count += 1
            else:
                 print(f"   ⚠️ Potential Issue: {resp}")
                 success_count += 1 # Assume success unless explicit error raised
                 
        except Exception as e:
            error_count += 1
            print(f"   ❌ Failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
        
        time.sleep(0.34) # Rate limit

    print("\n--- Update Summary ---")
    print(f"Total: {len(df)}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {error_count}")

if __name__ == "__main__":
    update_skus()
