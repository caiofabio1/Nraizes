import os
import sys
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from gestao_client import GestaoClient
from bling_client import BlingClient

def normalize_doc(doc):
    if not doc: return ""
    return str(doc).replace('.', '').replace('-', '').replace('/', '').strip()

def diagnose():
    gc = GestaoClient()
    bc = BlingClient()
    
    print("📥 Fetching Gestão Click Suppliers...")
    suppliers = []
    page = 1
    while True:
        resp = gc.get_fornecedores(limit=100, page=page)
        data = resp.get('data', []) if resp else []
        if not data: break
        suppliers.extend(data)
        page += 1
        time.sleep(0.2)
        
    print(f"Total Source: {len(suppliers)}")

    print("📥 Indexing Bling Contacts...")
    bling_map = {}
    page_b = 1
    while True:
        resp_b = bc.get_contatos(pagina=page_b, limite=100, criterio=5)
        data_b = resp_b.get('data', []) if resp_b else []
        if not data_b: break
        for c in data_b:
            d = normalize_doc(c.get('numeroDocumento'))
            if d: bling_map[d] = True
        page_b += 1
        time.sleep(0.5)

    print(f"Total Bling: {len(bling_map)}")
    
    print("\n--- Diagnosis ---")
    missing_doc = []
    failed_candidates = []
    
    for supp in suppliers:
        nome = supp.get('nome') or supp.get('razao_social')
        doc = normalize_doc(supp.get('cnpj') or supp.get('cpf'))
        
        if not doc:
            missing_doc.append(nome)
            continue
            
        if doc in bling_map:
            continue # Exists
            
        # These are the ones that presumably failed creation
        failed_candidates.append(f"{nome} (Doc: {doc})")

    print(f"Missing Doc (Should be 0 based on prev check): {len(missing_doc)}")
    for n in missing_doc: print(f" - {n}")

    print(f"\nCandidates for Failure (Not in Bling, Has Doc): {len(failed_candidates)}")
    for n in failed_candidates: print(f" - {n}")

if __name__ == "__main__":
    diagnose()
