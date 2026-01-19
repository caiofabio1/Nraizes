
import os
import requests
from dotenv import load_dotenv

# Load credentials
env_path = r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env'
load_dotenv(env_path)

ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
REFRESH_TOKEN = os.getenv('REFRESH_TOKEN')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')

BASE_URL = "https://api.bling.com.br/Api/v3"

def test_connection():
    """Test API connection and list stores"""
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    
    print("🔌 Testando conexão com Bling API...")
    print(f"   Token: {ACCESS_TOKEN[:10]}...{ACCESS_TOKEN[-5:]}")
    
    # Test with /situacoes/modulos endpoint (lightweight)
    response = requests.get(f"{BASE_URL}/situacoes/modulos", headers=headers)
    
    if response.status_code == 200:
        print("✅ Conexão OK!\n")
    elif response.status_code == 401:
        print("❌ Token expirado! Tentando renovar...\n")
        if refresh_token():
            return test_connection()  # Retry after refresh
        return False
    else:
        print(f"❌ Erro: {response.status_code} - {response.text}")
        return False
    
    # List stores (lojas virtuais)
    print("📦 Buscando lojas virtuais configuradas...")
    response = requests.get(f"{BASE_URL}/lojas", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        stores = data.get('data', [])
        print(f"\n🏪 {len(stores)} loja(s) encontrada(s):\n")
        for store in stores:
            print(f"   ID: {store.get('id')}")
            print(f"   Nome: {store.get('descricao')}")
            print(f"   Tipo: {store.get('tipo')}")
            print(f"   Situação: {'Ativa' if store.get('situacao') == 'A' else 'Inativa'}")
            print("-" * 40)
        return stores
    else:
        print(f"❌ Erro ao buscar lojas: {response.status_code}")
        print(response.text)
        return []

def refresh_token():
    """Refresh the access token"""
    print("🔄 Renovando token...")
    
    url = "https://www.bling.com.br/Api/v3/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }
    
    response = requests.post(url, data=payload, auth=(CLIENT_ID, CLIENT_SECRET))
    
    if response.status_code == 200:
        tokens = response.json()
        new_access = tokens.get('access_token')
        new_refresh = tokens.get('refresh_token')
        
        # Update env file
        with open(env_path, 'r') as f:
            content = f.read()
        
        content = content.replace(f"ACCESS_TOKEN={ACCESS_TOKEN}", f"ACCESS_TOKEN={new_access}")
        content = content.replace(f"REFRESH_TOKEN={REFRESH_TOKEN}", f"REFRESH_TOKEN={new_refresh}")
        
        with open(env_path, 'w') as f:
            f.write(content)
        
        print("✅ Token renovado com sucesso!\n")
        # Reload env
        load_dotenv(env_path, override=True)
        return True
    else:
        print(f"❌ Falha ao renovar: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    test_connection()
