import pandas as pd
import os

base_path = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO'
gestao_file = os.path.join(base_path, 'gestão click.xlsx')
bling_file = os.path.join(base_path, 'produtos.xls')

def inspect_file(path, name):
    print(f"\n--- Inspecting {name} ---")
    try:
        # Check extension to decide engine usually auto-detected but being safe
        if path.endswith('.xls'):
            df = pd.read_excel(path, engine='xlrd') # might need xlrd for xls
        else:
            df = pd.read_excel(path)
            
        print(f"Columns: {list(df.columns)}")
        print(f"Shape: {df.shape}")
        print("First row sample:")
        print(df.iloc[0].to_dict())
    except Exception as e:
        print(f"Error reading {name}: {e}")

if __name__ == "__main__":
    inspect_file(gestao_file, "Gestão Click")
    inspect_file(bling_file, "Bling (Template)")
