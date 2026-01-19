
import requests
import os
import sys
import time
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load env from .credentials
cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.credentials', 'bling_api_tokens.env')
load_dotenv(cred_path)

ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

def check_products():
    print(f"🚀 Iniciando auditoria de produtos ativos no Bling (Paralelo)...")
    
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Accept': 'application/json'
    }
    
    # 1. Fetch all active products first (lightweight list)
    all_products_basic = []
    page = 1
    while True:
        url = f'https://api.bling.com.br/Api/v3/produtos?pagina={page}&limite=100&situacao=A'
        print(f"  📄 Buscando lista página {page}...")
        try:
            resp = requests.get(url, headers=headers)
        except Exception as e:
            print(f"Erro conexao: {e}")
            break

        if resp.status_code == 401:
            print("❌ Token expirado ou inválido.")
            return
        
        if resp.status_code != 200:
            print(f"❌ Erro na API: {resp.status_code} - {resp.text}")
            break
            
        data = resp.json()
        products = data.get('data', [])
        
        if not products:
            break
            
        all_products_basic.extend(products)
        page += 1
        
    total_active = len(all_products_basic)
    print(f"✅ Total ativos encontrados: {total_active}")
    
    if total_active == 0:
        return

    # 2. Parallel fetch details
    print(f"🚀 Verificando detalhes em paralelo (10 threads)...")
    
    products_with_issues = []
    completed = 0
    
    def check_detail(p_basic):
        pid = p_basic['id']
        try:
            r = requests.get(f'https://api.bling.com.br/Api/v3/produtos/{pid}', headers=headers, timeout=10)
            if r.status_code == 200:
                p_det = r.json().get('data', {})
                name = p_det.get('nome')
                code = p_det.get('codigo')
                brand = p_det.get('marca')
                
                issues = []
                if not code or str(code).strip() == '':
                    issues.append("Sem Código")
                if not brand or str(brand).strip() == '':
                     issues.append("Sem Marca")
                
                if issues:
                    return {'id': pid, 'nome': name, 'issues': issues}
        except:
            pass
        return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_detail, p): p for p in all_products_basic}
        
        for future in as_completed(futures):
            res = future.result()
            completed += 1
            if res:
                products_with_issues.append(res)
            
            if completed % 50 == 0:
                print(f"  ✅ {completed}/{total_active} verificados...")

    print(f"\n✅ Auditoria concluída.")
    if products_with_issues:
        print(f"⚠️ Encontrados {len(products_with_issues)} produtos com problemas:")
        for item in products_with_issues:
            print(f"  - [{', '.join(item['issues'])}] {item['nome']}")
    else:
        print("🎉 Nenhum produto ativo com problemas de Código ou Marca!")

if __name__ == '__main__':
    check_products()
