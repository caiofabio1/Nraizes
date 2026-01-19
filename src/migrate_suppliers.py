import os
import sys
import time
import pandas as pd
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__)))
from gestao_client import GestaoClient
from bling_client import BlingClient

def normalize_doc(doc):
    if not doc: return ""
    return str(doc).replace('.', '').replace('-', '').replace('/', '').strip()

def migrate_suppliers():
    print("🚀 Starting Supplier Migration (API)...")
    
    gc = GestaoClient()
    bc = BlingClient()
    
    # 1. Fetch all suppliers from Gestão Click
    print("📥 Fetching suppliers from Gestão Click...")
    suppliers = []
    page = 1
    while True:
        resp = gc.get_fornecedores(limit=100, page=page)
        data = resp.get('data', []) if resp else []
        
        if not data:
            break
            
        suppliers.extend(data)
        print(f"   Page {page}: Retrieved {len(data)} suppliers...")
        page += 1
        time.sleep(0.2)
    
    print(f"✅ Total Gestão Click Suppliers: {len(suppliers)}")
    
    if not suppliers:
        print("⚠️ No suppliers found to migrate.")
        return

    # 2. Check existing suppliers in Bling (Dedup by CNPJ/CPF)
    # Since Bling API doesn't support bulk check easily without iterating, 
    # we will check one by one or fetch all if count is low. 
    # Strategy: Fetch all active contacts from Bling to build a local lookup map.
    
    print("📥 Fetching existing contacts from Bling for deduplication...")
    bling_contacts_map = {} # Key: Normalized CNPJ/CPF
    
    page_b = 1
    while True:
        resp_b = bc.get_contatos(pagina=page_b, limite=100, criterio=5) # 5=Todos
        data_b = resp_b.get('data', []) if resp_b else []
        
        if not data_b:
            break
            
        for contact in data_b:
            doc = normalize_doc(contact.get('numeroDocumento'))
            if doc:
                bling_contacts_map[doc] = contact.get('id')
                
        print(f"   Page {page_b}: Indexed {len(data_b)} existing contacts...")
        page_b += 1
        time.sleep(0.5)

    print(f"✅ Total Bling Contacts Indexed: {len(bling_contacts_map)}")

    # 3. Migrate
    created_count = 0
    skipped_count = 0
    errors_count = 0
    
    print("\n🔄 Processing Migration...")
    
    for supp in suppliers:
        # Extract fields
        nome = supp.get('nome') or supp.get('razao_social')
        fantasia = supp.get('nome_fantasia')
        doc = normalize_doc(supp.get('cnpj') or supp.get('cpf'))
        
        if not doc:
            print(f"⚠️ Skipping supplier '{nome}' - No CNPJ/CPF")
            errors_count += 1
            continue
            
        if doc in bling_contacts_map:
            print(f"⏭️ Skipping '{nome}' ({doc}) - Already exists in Bling.")
            skipped_count += 1
            continue
            
        # Map to Bling Body
        # types: F (Fisica), J (Juridica), E (Estrangeiro)
        tipo_pessoa = 'J' if len(doc) > 11 else 'F'
        
        payload = {
            "nome": nome,
            "fantasia": fantasia,
            "tipo": "F", # F=Fornecedor (Validation required usually, Bling might default to T)
            "situacao": "A", # Ativo
            "numeroDocumento": doc,
            "tipoPessoa": tipo_pessoa,
            # Address mapping if available
        }
        
        # Add Address if present
        if 'endereco' in supp:
             end = supp['endereco']
             payload['endereco'] = {
                 "geral": {
                     "endereco": end.get('logradouro'),
                     "numero": end.get('numero'),
                     "bairro": end.get('bairro'),
                     "cep": normalize_doc(end.get('cep')),
                     "municipio": end.get('cidade'),
                     "uf": end.get('estado')
                 }
             }
        
        # Add Contact Info
        if 'email' in supp:
            payload['email'] = supp['email']
        if 'telefone' in supp:
             payload['fones'] = [supp['telefone']]

        try:
            # Post to Bling
            resp_post = bc.post_contatos(payload)
            if resp_post and 'data' in resp_post:
                new_id = resp_post['data']['id']
                print(f"✅ Created: {nome} (ID: {new_id})")
                bling_contacts_map[doc] = new_id # Add to map to prevent duplicates in this run
                created_count += 1
            else:
                print(f"❌ Failed to create '{nome}': {resp_post}")
                errors_count += 1
        except Exception as e:
            print(f"❌ Error creating '{nome}': {e}")
            errors_count += 1
            
        time.sleep(0.34) # Rate limit safety (3 req/s limit usually)

    print("\n--- Migration Summary ---")
    print(f"Total Gestão Click Suppliers: {len(suppliers)}")
    print(f"✅ Created in Bling: {created_count}")
    print(f"⏭️ Skipped (Existing): {skipped_count}")
    print(f"⚠️ Errors/Skipped (No ID): {errors_count}")

if __name__ == "__main__":
    migrate_suppliers()
