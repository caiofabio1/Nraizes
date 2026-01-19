import pandas as pd

BEFORE = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos.xlsx'
AFTER = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx'

def inspect_changes():
    print(f"Loading Before: {BEFORE}")
    df_before = pd.read_excel(BEFORE)
    print(f"Loading After: {AFTER}")
    df_after = pd.read_excel(AFTER)

    # Align columns
    cols = [c for c in df_before.columns if c in df_after.columns]
    
    changes = {}
    
    for col in cols:
        # Convert to string for comparison to handle type changes
        b_vals = df_before[col].fillna('').astype(str).str.strip()
        a_vals = df_after[col].fillna('').astype(str).str.strip()
        
        # Count differences where Before was empty but After is not
        filled_count = 0
        diff_indices = []
        for i in range(len(b_vals)):
            if i >= len(a_vals): break
            
            b = b_vals[i]
            a = a_vals[i]
            
            # Check if it changed
            if b != a:
                # Just report it
                filled_count += 1
                if len(diff_indices) < 5:
                    diff_indices.append((i, b, a))
        
        if filled_count > 0:
            changes[col] = {
                'count': filled_count,
                'examples': diff_indices
            }

    print("\n--- Summary of Fields Filled ---")
    if not changes:
        print("No fields appeared to be filled.")
    else:
        for col, data in changes.items():
            print(f"Field: '{col}' -> {data['count']} rows filled.")
            for (idx, old, new) in data['examples']:
                product_name = df_after.iloc[idx]['Descrição'] if 'Descrição' in df_after.columns else f"Row {idx}"
                print(f"   Row {idx} ({product_name}): '{old}' -> '{new}'")

if __name__ == "__main__":
    inspect_changes()
