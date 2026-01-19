import os
import sys
import json

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from gestao_client import GestaoClient

def debug_nfe():
    print("🔍 Debugging NF-e API (Multiple Endpoints)...")
    gc = GestaoClient()
    
    endpoints = ["/api/nfe/", "/api/notas_fiscais/", "/api/notas-fiscais/"]
    
    for ep in endpoints:
        print(f"Testing {ep}...")
        try:
             # Manually request since client method is fixed
             resp = gc._request("GET", ep, params={"limit": 5})
             if resp:
                 print(f"✅ SUCCESS at {ep}")
                 print(json.dumps(resp, indent=2)[:500])
                 return
             else:
                 print(f"❌ Failed at {ep} (Response None)")
        except Exception as e:
             print(f"❌ Error at {ep}: {e}")

if __name__ == "__main__":
    debug_nfe()
