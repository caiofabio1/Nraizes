import requests
import os
import time
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from logger import get_api_logger

# Load credentials
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cred_path = os.path.join(PROJECT_ROOT, '.credentials', 'gestao_api_tokens.env')
load_dotenv(cred_path)

# Initialize logger
_api_logger = get_api_logger('gestao')

class GestaoClient:
    def __init__(self):
        self.base_url = "https://api.gestaoclick.com"
        self.access_token = os.getenv("GESTAO_ACCESS_TOKEN")
        self.secret_token = os.getenv("GESTAO_SECRET_TOKEN")
        self.headers = {
            "Access-Token": self.access_token,
            "Secret-Access-Token": self.secret_token,
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Execute an HTTP request to the Gestao Click API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments passed to requests

        Returns:
            JSON response as dict, or None on error
        """
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        _api_logger.log_request(method, url, kwargs.get('params'))

        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response_time_ms = (time.time() - start_time) * 1000
            _api_logger.log_response(response.status_code, url, response_time_ms)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout as e:
            _api_logger.log_error(e, f"Timeout on {method} {endpoint}")
            return None
        except requests.exceptions.ConnectionError as e:
            _api_logger.log_error(e, f"Connection error on {method} {endpoint}")
            return None
        except requests.exceptions.HTTPError as e:
            _api_logger.log_error(e, f"HTTP error on {method} {endpoint}")
            if e.response is not None:
                _api_logger.logger.error(f"Response body: {e.response.text[:500]}")
            return None
        except requests.exceptions.RequestException as e:
            _api_logger.log_error(e, f"Request failed: {method} {endpoint}")
            return None

    def get_produtos(self, limit=10, page=1):
        """Fetch products from Gestão Click"""
        return self._request("GET", "/api/produtos/", params={"limit": limit, "page": page})

    def get_produto(self, produto_id):
        """Fetch a single product by ID"""
        return self._request("GET", f"/api/produtos/{produto_id}")

    def get_fornecedores(self, limit=10, page=1):
        """Fetch suppliers from Gestão Click"""
        return self._request("GET", "/api/fornecedores/", params={"limit": limit, "page": page})

    def get_vendas(self, limit=10, page=1, **kwargs):
        """Fetch sales (vendas) from Gestão Click"""
        params = {"limit": limit, "page": page}
        params.update(kwargs)
        return self._request("GET", "/api/vendas/", params=params)

    def get_venda(self, venda_id):
        """Fetch single sale (venda) detail"""
        return self._request("GET", f"/api/vendas/{venda_id}")

    def get_pedidos(self, limit=10, page=1, **kwargs):
        """Fetch orders (pedidos) from Gestão Click"""
        params = {"limit": limit, "page": page}
        params.update(kwargs)
        return self._request("GET", "/api/pedidos/", params=params)

    def get_notas_fiscais(self, limit=10, page=1, **kwargs):
        """Fetch NF-e from Gestão Click"""
        params = {"limit": limit, "page": page}
        params.update(kwargs)
        return self._request("GET", "/api/notas-fiscais/", params=params)

    def test_connection(self) -> bool:
        """
        Test API credentials by fetching a single product.

        Returns:
            True if connection is successful, False otherwise
        """
        _api_logger.logger.info("Testing Gestao Click connection...")
        result = self.get_produtos(limit=1)

        if result and 'code' in result and result['code'] == 200:
            _api_logger.logger.info("Gestao Click connection OK")
            return True
        else:
            _api_logger.logger.error("Gestao Click connection failed")
            return False


if __name__ == "__main__":
    client = GestaoClient()
    success = client.test_connection()
    print("Connection OK" if success else "Connection FAILED")
