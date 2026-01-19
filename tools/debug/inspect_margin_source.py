import pandas as pd
import os

path = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx'
if os.path.exists(path):
    df = pd.read_excel(path)
    print(f"Columns: {df.columns.tolist()}")
    print("First 3 rows:")
    # Print specific columns if they likely exist, else print all
    cols_to_show = [c for c in df.columns if 'Preço' in c or 'Descrição' in c or 'Nome' in c]
    if cols_to_show:
        print(df[cols_to_show].head(3).to_string())
    else:
        print(df.head(3).to_string())
else:
    print("File not found.")
