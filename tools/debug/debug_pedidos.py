import os
import sys
import json

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from gestao_client import GestaoClient

def debug_pedidos():
    print("🔍 Debugging Orders (Pedidos) API...")
    gc = GestaoClient()
    
    resp = gc.get_pedidos(limit=5)
    
    if resp and 'data' in resp:
        print(f"Items in data: {len(resp['data'])}")
        if len(resp['data']) > 0:
            print("First item sample:")
            print(json.dumps(resp['data'][0], indent=2))
        else:
            print("Empty data list.")
    else:
        print(f"Response: {resp}")

if __name__ == "__main__":
    debug_pedidos()
