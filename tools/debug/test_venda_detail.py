import os
import sys
import json

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from gestao_client import GestaoClient

def test_detail():
    gc = GestaoClient()
    # ID found in previous step
    vid = 126276506 
    print(f"Fetching detail for Venda {vid}...")
    
    resp = gc.get_venda(vid)
    if resp and 'data' in resp:
        # Usually detail returns { "code": 200, "data": { ... } } or { "data": [ ... ] }?
        # get_produto returned { "data": { ... } }
        data = resp['data']
        print(f"Data Type: {type(data)}")
        if isinstance(data, dict):
            print(f"Keys: {list(data.keys())}")
            print(f"Data Emissao: {data.get('data_emissao')}")
        elif isinstance(data, list) and len(data) > 0:
             print(f"Keys: {list(data[0].keys())}")
             print(f"Data Emissao: {data[0].get('data_emissao')}")
        else:
            print("Data is empty or weird.")
            print(json.dumps(data, indent=2))
    else:
        print(f"Failed. Resp: {resp}")

if __name__ == "__main__":
    test_detail()
