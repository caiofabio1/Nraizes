import pandas as pd

SOURCE = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\gestão click.xlsx'
TARGET = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos.xlsx'

def inspect(path, name):
    print(f"\n--- {name} ---")
    try:
        # Read raw first 20 rows
        df = pd.read_excel(path, header=None, nrows=20)
        print("First 10 rows preview:")
        print(df.head(10))
        
        # Try to find 'Código'
        found = False
        for i, row in df.iterrows():
            row_str = " ".join([str(x) for x in row.values])
            if "Código" in row_str or "Codigo" in row_str:
                print(f"Potential header at row {i}: {row.values}")
                found = True
        
        if not found:
            print("❌ 'Código' column not visually found in first 20 rows.")
            
    except Exception as e:
        print(f"Error: {e}")

inspect(SOURCE, "Gestão Click (Source)")
inspect(TARGET, "Bling (Target)")
