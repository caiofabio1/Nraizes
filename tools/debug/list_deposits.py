import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from bling_client import BlingClient

bc = BlingClient()
resp = bc.get_depositos()
if resp and 'data' in resp:
    print("Deposits:")
    for d in resp['data']:
        print(f"ID: {d['id']} - Name: {d['descricao']} (Default: {d.get('padrao', False)})")
else:
    print("No deposits found or error:", resp)
