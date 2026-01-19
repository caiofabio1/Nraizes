import os
import sys
import time
import json
sys.path.append(os.path.join(os.path.dirname(__file__)))
from gestao_client import GestaoClient
from bling_client import BlingClient

def normalize_doc(doc):
    if not doc: return ""
    return str(doc).replace('.', '').replace('-', '').replace('/', '').strip()

TARGET_DOCS = [
    "39257016000209",
    "53676798000152",
    "40544709000172",
    "37831582000168",
    "04247792000154"
]

def fix_suppliers():
    gc = GestaoClient()
    bc = BlingClient()
    
    print("📥 Fetching Target Suppliers from Gestão Click...")
    
    # We have to fetch all to find them because GC API doesn't search by doc easily
    target_suppliers = []
    page = 1
    found_count = 0
    
    while found_count < len(TARGET_DOCS):
        resp = gc.get_fornecedores(limit=100, page=page)
        data = resp.get('data', []) if resp else []
        if not data: break
        
        for supp in data:
            doc = normalize_doc(supp.get('cnpj') or supp.get('cpf'))
            if doc in TARGET_DOCS:
                target_suppliers.append(supp)
                found_count += 1
                
        page += 1
        time.sleep(0.1)

    print(f"Found {len(target_suppliers)}/{len(TARGET_DOCS)} targets.")

    def format_cnpj(d):
        if len(d) == 14:
            return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
        return d

    for supp in target_suppliers:
        nome = supp.get('nome') or supp.get('razao_social')
        doc = normalize_doc(supp.get('cnpj') or supp.get('cpf'))
        fantasia = supp.get('nome_fantasia')
        
        doc_fmt = format_cnpj(doc)
        print(f"\n🔧 Processing: {nome} ({doc_fmt})")

        # 1. Direct Check
        print(f"   🔎 Checking existence in Bling...")
        exist_resp = bc.get_contatos(numeroDocumento=doc) # Try unformatted
        if not (exist_resp and 'data' in exist_resp):
             exist_resp = bc.get_contatos(numeroDocumento=doc_fmt) # Try formatted
        
        if exist_resp and exist_resp.get('data'):
            print(f"   ⚠️ Already exists! ID: {exist_resp['data'][0]['id']}")
            continue

        # Prepare Payload
        payload = {
            "nome": nome[:60], 
            "fantasia": fantasia,
            "tipo": "F",
            "situacao": "A",
            "numeroDocumento": doc_fmt, # Send Formatted
            "tipoPessoa": "J" if len(doc) > 11 else "F"
        }
        
        # Address
        if 'endereco' in supp:
             end = supp['endereco']
             payload['endereco'] = {
                 "geral": {
                     "endereco": end.get('logradouro'),
                     "numero": end.get('numero') or "S/N",
                     "bairro": end.get('bairro') or "Geral",
                     "cep": normalize_doc(end.get('cep')),
                     "municipio": end.get('cidade'),
                     "uf": end.get('estado')
                 }
             }
             
        # Contact
        if 'email' in supp: payload['email'] = supp['email']
        if 'telefone' in supp: payload['fones'] = [supp['telefone']]

        try:
             url = f"{bc.base_url}/contatos"
             print(f"   Sending Payload...")
             
             resp = bc._request('POST', url, json=payload)
             if resp and 'data' in resp:
                 print(f"✅ SUCCESS! Created ID: {resp['data']['id']}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 try:
                     print(f"   API Response: {json.dumps(e.response.json(), indent=2, ensure_ascii=False)}")
                 except:
                     print(f"   API Response (Text): {e.response.text}")
            time.sleep(1)

if __name__ == "__main__":
    fix_suppliers()
