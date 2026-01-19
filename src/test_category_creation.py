
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv(r'c:\Users\caiof\NRAIZES\.credentials\bling_api_tokens.env')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

def test_create():
    print("🧪 Testando criação de categoria via API v3...")
    url = 'https://api.bling.com.br/Api/v3/categorias/produtos'
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Payload
    payload = {
        "descricao": "_Teste Antigravity API_",
        "categoriaPai": { "id": 0 } # Root
    }
    
    print(f"  POST {url}")
    print(f"  Payload: {json.dumps(payload)}")
    
    r = requests.post(url, headers=headers, json=payload)
    
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.text}")

if __name__ == "__main__":
    test_create()
