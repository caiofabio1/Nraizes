import pandas as pd
import os

def search_excel():
    path = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx'
    df = pd.read_excel(path)
    
    keywords = ['liu', 'wei', 'curcuma', 'ocean', 'taimin', 'ba zhen']
    
    print(f"Searching for {keywords} in {len(df)} rows...")
    
    found_count = 0
    for i, row in df.iterrows():
        desc = str(row.get('Descrição', '')).lower()
        if any(k in desc for k in keywords):
            print(f"Found: {desc}")
            found_count += 1
            if found_count > 10: break

    if found_count == 0:
        print("❌ No keywords found.")

if __name__ == "__main__":
    search_excel()
