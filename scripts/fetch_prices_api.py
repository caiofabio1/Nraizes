
import requests
import json
import pandas as pd
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

# API Credentials
ACCESS_TOKEN = "a96fb92370c9efa05081a0c8ebb14052a21018e7"
SECRET_TOKEN = "859f974d5495aa6924d6cc5b7f6d17fc6432d80a"
BASE_URL = "https://api.gestaoclick.com"

headers = {
    "Access-Token": ACCESS_TOKEN,
    "Secret-Access-Token": SECRET_TOKEN,
    "Content-Type": "application/json"
}

def search_product(query):
    """Search for a product by name or code"""
    if not query or len(str(query)) < 2:
        return None
        
    url = f"{BASE_URL}/api/produtos/"
    params = {"nome": query, "limit": 10}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                return data['data']
    except Exception as e:
        print(f"Error searching for {query}: {e}")
    return None

def fetch_and_update_prices():
    # Load files
    df_main = pd.read_csv('produtos_bling_import.csv', encoding='utf-8')
    df_missing_sale = pd.read_csv('produtos_sem_preco_venda.csv', sep=';', encoding='utf-8')
    df_missing_cost = pd.read_csv('produtos_sem_preco_custo.csv', sep=';', encoding='utf-8')
    
    # Get unique products that need checking (union of missing sale and cost)
    ids_to_check = set(df_missing_sale['ID'].tolist()) | set(df_missing_cost['ID'].tolist())
    print(f"Total unique products to check: {len(ids_to_check)}")
    
    # Helper for converting price strings
    def clean_price(val):
        if pd.isna(val): return 0.0
        return float(str(val).replace(',', '.'))

    updates_sale = 0
    updates_cost = 0
    
    for idx, row in df_main.iterrows():
        if row['ID'] not in ids_to_check:
            continue
            
        name = str(row['Descrição']).strip()
        # Clean name for better search results (remove generic prefixes if needed)
        search_term = name
        
        print(f"Searching for: {search_term}...")
        results = search_product(search_term)
        
        found = False
        if results:
            # Try to find exact match or best match
            for prod in results:
                # Calculate similarity or just take the first good match
                # For now taking the first result as the API search is usually relevant
                api_price_sale = clean_price(prod.get('valor_venda', 0))
                api_price_cost = clean_price(prod.get('valor_custo', 0))
                
                # Update if we have valid values
                current_sale = clean_price(row['Preço'])
                if current_sale == 0.0 and api_price_sale > 0:
                    df_main.at[idx, 'Preço'] = str(api_price_sale).replace('.', ',')
                    updates_sale += 1
                    found = True
                    
                current_cost = clean_price(row['Preço de custo'])
                if current_cost == 0.0 and api_price_cost > 0:
                    df_main.at[idx, 'Preço de custo'] = str(api_price_cost).replace('.', ',')
                    updates_cost += 1
                    found = True
                
                if found:
                    print(f"  -> FOUND! Sale: {api_price_sale}, Cost: {api_price_cost}")
                    break
        
        if not found:
            print("  -> Not found")
        
        # Rate limiting
        time.sleep(0.4) # Max 3 req/s
        
    print(f"\nUpdate Summary:")
    print(f"Sale prices updated: {updates_sale}")
    print(f"Cost prices updated: {updates_cost}")
    
    # Save updated file
    df_main.to_csv('produtos_bling_import.csv', index=False, encoding='utf-8')
    print("Updated file saved: produtos_bling_import.csv")

if __name__ == "__main__":
    fetch_and_update_prices()
