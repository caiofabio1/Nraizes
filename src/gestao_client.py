import requests
import os
from dotenv import load_dotenv

# Load credentials
cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.credentials', 'gestao_api_tokens.env')
load_dotenv(cred_path)

class GestaoClient:
    def __init__(self):
        self.base_url = "https://api.gestaoclick.com"
        self.access_token = os.getenv("ACCESS_TOKEN")
        self.secret_token = os.getenv("SECRET_TOKEN")
        self.headers = {
            "Access-Token": self.access_token,
            "Secret-Access-Token": self.secret_token,
            "Content-Type": "application/json"
        }

    def _request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Gestão Click API Error: {e}")
            if e.response is not None:
                print(f"Response: {e.response.text}")
            return None

    def get_produtos(self, limit=10, page=1):
        """Fetch products from Gestão Click"""
        return self._request("GET", "/api/produtos/", params={"limit": limit, "page": page})

    def get_produto(self, produto_id):
        """Fetch a single product by ID"""
        return self._request("GET", f"/api/produtos/{produto_id}")

    def test_connection(self):
        """Simple test to verify credentials"""
        print("🔌 Testing Gestão Click Connection...")
        result = self.get_produtos(limit=1)
        if result and 'code' in result and result['code'] == 200:
            print("✅ Gestão Click Connection OK!")
            return True
        else:
            print("❌ Gestão Click Connection Failed!")
            return False

if __name__ == "__main__":
    client = GestaoClient()
    client.test_connection()
