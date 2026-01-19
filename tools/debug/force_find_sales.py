import os
import sys
import json
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from gestao_client import GestaoClient

def force_find():
    print("search with limit=1 strategy...")
    gc = GestaoClient()
    
    for page in range(1, 21):
        try:
            resp = gc.get_vendas(limit=1, page=page)
            if resp and 'data' in resp and resp['data']:
                item = resp['data'][0]
                did = item.get('id')
                date = item.get('data_emissao')
                total = item.get('valor_total')
                print(f"Page {page}: ID={did} | Date={date} | Val={total}")
            else:
                print(f"Page {page}: No data.")
        except Exception as e:
            print(f"Page {page}: Error {e}")
        
        time.sleep(0.2)

if __name__ == "__main__":
    force_find()
