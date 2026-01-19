import pandas as pd

FILE_PATH = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx'

def check_cols():
    df = pd.read_excel(FILE_PATH)
    print("Columns:", list(df.columns))
    if 'id' in df.columns or 'ID' in df.columns:
        print("✅ ID Column Found!")
        print(df[['id', 'Código', 'Descrição']].head() if 'id' in df.columns else df[['ID', 'Código', 'Descrição']].head())
    else:
        print("❌ No ID column found.")

if __name__ == "__main__":
    check_cols()
