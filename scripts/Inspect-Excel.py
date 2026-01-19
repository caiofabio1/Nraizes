
import pandas as pd

file_path = "c:\\Users\\caiof\\NRAIZES\\relatorio_produtos (4).xlsx"

try:
    # Read without header to see raw rows
    df = pd.read_excel(file_path, header=None, nrows=10)
    
    print("Row Inspection:")
    for index, row in df.iterrows():
        print(f"Row {index}: {row.tolist()}")
        
except Exception as e:
    print(f"Error: {e}")
