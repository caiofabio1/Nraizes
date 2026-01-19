import sys
import os
# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from bling_client import BlingClient
import json

def test_client():
    client = BlingClient()
    
    print("Testing Authentication and Basic Fetch...")
    try:
        # Fetch 1 product to verify connectivity
        response = client.get_produtos(limite=1)
        print("Success! Response:")
        print(json.dumps(response, indent=2))
        
        if response and 'data' in response and len(response['data']) > 0:
            prod_id = response['data'][0]['id']
            print(f"\nFetching specific product {prod_id}...")
            # Test the method with path param
            prod_detail = client.get_produtos_id_produto(idProduto=str(prod_id))
            print("Product Detail Fetched successfully.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_client()
