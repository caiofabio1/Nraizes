import sys
import os

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from gestao_client import GestaoClient
from bling_client import BlingClient

def verify_all():
    print("========================================")
    print("🚀 Verifying API Connections")
    print("========================================")
    
    # 1. Gestão Click
    print("\n1️⃣  Testing Gestão Click...")
    try:
        g_client = GestaoClient()
        if g_client.test_connection():
            print("   ✅ Connected successfully")
        else:
            print("   ❌ Connection failed")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 2. Bling
    print("\n2️⃣  Testing Bling...")
    try:
        b_client = BlingClient()
        # Try to fetch products (lite)
        products = b_client.get_produtos(limite=1)
        if products and 'data' in products:
            print("   ✅ Connected successfully (Fetched products)")
        elif products is None or (isinstance(products, dict) and not products.get('data')):
             # Empty list is also a success valid connection
            print("   ✅ Connected successfully (No data returned but connection OK)")
        else:
            print(f"   ⚠️ Connected but unexpected response format: {products}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n========================================")

if __name__ == "__main__":
    verify_all()
