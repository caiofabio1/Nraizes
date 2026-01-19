import os
import sys
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from gestao_client import GestaoClient

def normalize_doc(doc):
    if not doc: return ""
    return str(doc).replace('.', '').replace('-', '').replace('/', '').strip()

def check_skipped():
    gc = GestaoClient()
    print("📥 Fetching suppliers from Gestão Click...")
    
    skipped = []
    page = 1
    while True:
        resp = gc.get_fornecedores(limit=100, page=page)
        data = resp.get('data', []) if resp else []
        if not data: break
            
        for supp in data:
            nome = supp.get('nome') or supp.get('razao_social')
            doc = normalize_doc(supp.get('cnpj') or supp.get('cpf'))
            
            if not doc:
                skipped.append(nome)
        
        page += 1
        time.sleep(0.2)
        
    print(f"\n⚠️ Total Skipped (No CNPJ/CPF): {len(skipped)}")
    for name in skipped:
        print(f"   - {name}")

if __name__ == "__main__":
    check_skipped()
