import os
import sys
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from gestao_client import GestaoClient

def debug_vendas():
    print("🔍 Debugging Sales API...")
    gc = GestaoClient()
    
    # Fetch just 1 record to see structure
    resp = gc.get_vendas(limit=1)
    
    if resp:
        print("✅ Response Received.")
        if 'data' in resp:
            print(f"Items in data: {len(resp['data'])}")
            if len(resp['data']) > 0:
                item = resp['data'][0]
                print(f"FOUND: ID={item.get('id')} | Date={item.get('data_emissao')} | Val={item.get('valor_total')}")
            else:
                print("⚠️ 'data' list is empty.")
        else:
             print(f"⚠️ 'data' key missing. Keys: {list(resp.keys())}")
             print(json.dumps(resp, indent=2))
    else:
        print("❌ No response received.")

if __name__ == "__main__":
    debug_vendas()
