import pandas as pd

SOURCE = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\gestão click.xlsx'

def check_row_3():
    print(f"Loading {SOURCE}...")
    try:
        df = pd.read_excel(SOURCE, header=None, nrows=10)
        row_3 = df.iloc[3].values
        print(f"Row 3 Raw: {row_3}")
        print(f"Row 3 String: {[str(x) for x in row_3]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_row_3()
