import pandas as pd
import unicodedata

SOURCE = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\gestão click.xlsx'
TARGET = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos.xlsx'

def normalize_str(s):
    return unicodedata.normalize('NFKD', str(s)).encode('ASCII', 'ignore').decode('ASCII').lower()

def debug_matches():
    # Read Source (Positional Fallback)
    try:
        df_source = pd.read_excel(SOURCE, header=None, skiprows=2)
        df_source.rename(columns={0: 'Código', 1: 'Descrição'}, inplace=True)
    except Exception as e:
        print(f"Error reading source: {e}")
        return

    # Read Target
    try:
        df_target = pd.read_excel(TARGET)
    except Exception as e:
        print(f"Error reading target: {e}")
        return

    # Normalize
    df_source['Code_Clean'] = df_source['Código'].astype(str).str.strip()
    df_source['Name_Clean'] = df_source['Descrição'].astype(str).str.strip()
    
    df_target['Code_Clean'] = df_target['Código'].astype(str).str.strip().replace('nan', '')
    df_target['Name_Clean'] = df_target['Descrição'].astype(str).str.strip()

    source_codes = set(df_source['Code_Clean'])
    
    print(f"Total Source Products: {len(df_source)}")
    print(f"Total Target Products: {len(df_target)}")

    # Check non-matches
    unmatched = []
    for i, row in df_target.iterrows():
        if row['Code_Clean'] not in source_codes:
            unmatched.append((row['Code_Clean'], row['Name_Clean']))
    
    print(f"\nUnmatched Products: {len(unmatched)}")
    print("\n--- SAMPLE UNMATCHED (Target) ---")
    for code, name in unmatched[:15]:
        print(f"Target: [{code}] {name}")
        
    print("\n--- SAMPLE SOURCE OPTIONS ---")
    print(df_source[['Code_Clean', 'Name_Clean']].head(20).to_string(index=False))

    # Check for simple subsets
    print("\n--- Potential Partial Matches? ---")
    count = 0
    for code, name in unmatched[:5]:
        # Search in source names
        matches = df_source[df_source['Name_Clean'].str.contains(name[:10], case=False, na=False)]
        if not matches.empty:
            print(f"\nFor Target '{name}':")
            print(matches[['Code_Clean', 'Name_Clean']].head(3).to_string(index=False))
            count += 1
    
    if count == 0:
        print("No immediate substring matches found in first 5 unmatched.")

if __name__ == "__main__":
    debug_matches()
