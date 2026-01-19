"""
WooCommerce REST API Client for Novas Raízes
"""
import os
import time
from typing import Optional, Dict, Any, List
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

from logger import get_api_logger

# Load credentials using relative path from project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cred_path = os.path.join(PROJECT_ROOT, '.credentials', 'woo_api_tokens.env')
load_dotenv(cred_path)

# Initialize logger
_api_logger = get_api_logger('woocommerce')

class WooClient:
    def __init__(self):
        self.base_url = os.getenv('WOO_STORE_URL', 'https://nraizes.com.br')
        self.consumer_key = os.getenv('WOO_CONSUMER_KEY')
        self.consumer_secret = os.getenv('WOO_CONSUMER_SECRET')
        
        if not self.consumer_key or not self.consumer_secret:
            raise ValueError("WooCommerce credentials not found. Check .credentials/woo_api_tokens.env")
        
        self.api_url = f"{self.base_url}/wp-json/wc/v3"
        self.auth = HTTPBasicAuth(self.consumer_key, self.consumer_secret)
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Execute an HTTP request to the WooCommerce API.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments passed to requests

        Returns:
            JSON response data

        Raises:
            requests.exceptions.HTTPError: On HTTP errors
            requests.exceptions.RequestException: On other request errors
        """
        url = f"{self.api_url}/{endpoint}"
        start_time = time.time()
        _api_logger.log_request(method, url, kwargs.get('params'))

        try:
            response = requests.request(method, url, auth=self.auth, **kwargs)
            response_time_ms = (time.time() - start_time) * 1000
            _api_logger.log_response(response.status_code, url, response_time_ms)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout as e:
            _api_logger.log_error(e, f"Timeout on {method} {endpoint}")
            raise
        except requests.exceptions.ConnectionError as e:
            _api_logger.log_error(e, f"Connection error on {method} {endpoint}")
            raise
        except requests.exceptions.HTTPError as e:
            _api_logger.log_error(e, f"HTTP error on {method} {endpoint}")
            raise
        except requests.exceptions.RequestException as e:
            _api_logger.log_error(e, f"Request failed: {method} {endpoint}")
            raise
    
    def get_products(self, per_page=100, page=1, **params):
        """Fetch products from WooCommerce"""
        params.update({"per_page": per_page, "page": page})
        return self._request("GET", "products", params=params)
    
    def get_product(self, product_id):
        """Fetch single product by ID"""
        return self._request("GET", f"products/{product_id}")
    
    def get_orders(self, per_page=100, page=1, **params):
        """Fetch orders from WooCommerce"""
        params.update({"per_page": per_page, "page": page})
        return self._request("GET", "orders", params=params)
    
    def get_order(self, order_id):
        """Fetch single order by ID"""
        return self._request("GET", f"orders/{order_id}")
    
    def update_product(self, product_id, data):
        """Update product data"""
        return self._request("PUT", f"products/{product_id}", json=data)
    
    def get_system_status(self):
        """Check WooCommerce system status (API health check)"""
        return self._request("GET", "system_status")


if __name__ == "__main__":
    _api_logger.logger.info("Testing WooCommerce API connection...")
    try:
        client = WooClient()
        products = client.get_products(per_page=1)
        if products:
            _api_logger.logger.info(f"Connection OK! First product: {products[0]['name']}")
            print(f"Connection OK! First product: {products[0]['name']}")
        else:
            _api_logger.logger.warning("Connection OK but no products found")
            print("Connection OK but no products found")
    except ValueError as e:
        _api_logger.logger.error(f"Configuration error: {e}")
        print(f"Configuration error: {e}")
    except requests.exceptions.RequestException as e:
        _api_logger.logger.error(f"Connection failed: {e}")
        print(f"Connection failed: {e}")
