import pandas as pd
import os

path = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\relatorio_estoque_faltante_final.xlsx'
if os.path.exists(path):
    df = pd.read_excel(path)
    print(f"Columns: {df.columns.tolist()}")
    print("First 5 rows:")
    print(df.head().to_string())
else:
    print("File not found.")
