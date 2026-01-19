import pandas as pd

SOURCE = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\gestão click.xlsx'

def check_rows():
    print(f"Loading {SOURCE}...")
    try:
        df = pd.read_excel(SOURCE, header=None, nrows=10)
        for i, row in df.iterrows():
            print(f"Row {i}: {row.values}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_rows()
