import pandas as pd

FILE_PATH = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx'

def analyze_skus():
    try:
        df = pd.read_excel(FILE_PATH)
        print(f"Loaded {len(df)} products.")
        
        # Columns of interest
        cols = ['Código', 'Descrição', 'Marca', 'Categoria']
        available_cols = [c for c in cols if c in df.columns]
        
        sample = df[available_cols].dropna(subset=['Descrição']).sample(20)
        
        print("\n--- Current SKU Samples ---")
        print(sample.to_string(index=False))
        
        # Check for duplicates or patterns
        print("\n--- SKU Length Stats ---")
        df['Len'] = df['Código'].astype(str).str.len()
        print(df['Len'].value_counts().head())

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_skus()
