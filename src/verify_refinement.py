
import pandas as pd
import sys

# output to stdout
file_path = r'c:\Users\caiof\NRAIZES\produtos_refinados.xlsx'

if len(sys.argv) > 1:
    file_path = sys.argv[1]

print("=" * 60)
print(f"🧐 VERIFICAÇÃO DE REFINAMENTO: {file_path}")
print("=" * 60)

try:
    df = pd.read_excel(file_path)
    
    total = len(df)
    print(f"\n✅ Total: {total}")
    
    # 1. Check Production Type
    print("\n🏭 TIPO DE PRODUÇÃO:")
    if 'Tipo Produção' in df.columns:
        counts = df['Tipo Produção'].value_counts(dropna=False)
        print(counts)
    else:
        print("  ❌ Coluna 'Tipo Produção' não encontrada.")
        
    # 2. Check Description
    print("\n📝 DESCRIÇÃO COMPLEMENTAR:")
    if 'Descrição Complementar' in df.columns:
        filled = df['Descrição Complementar'].notna() & (df['Descrição Complementar'].astype(str).str.strip() != '')
        print(f"  Preenchidos: {filled.sum()}/{total} ({filled.sum()/total:.1%})")
        
        # Sample length
        lens = df[filled]['Descrição Complementar'].astype(str).apply(len)
        print(f"  Tamanho médio: {lens.mean():.0f} caracteres")
    else:
         print("  ❌ Coluna 'Descrição Complementar' não encontrada.")
         
    # 3. Check Brand
    print("\n🏷️ MARCA:")
    if 'Marca' in df.columns:
        filled_brand = df['Marca'].notna() & (df['Marca'].astype(str).str.strip() != '')
        print(f"  Preenchidos: {filled_brand.sum()}/{total} ({filled_brand.sum()/total:.1%})")
    
    # Sample
    print("\n🔍 AMOSTRA (5):")
    cols = ['Descrição', 'Marca', 'Tipo Produção']
    if 'Descrição Complementar' in df.columns:
        # Show truncated desc
        df['Desc_Short'] = df['Descrição Complementar'].astype(str).str[:50] + '...'
        cols.append('Desc_Short')
        
    print(df[cols].head(5).to_string())

except Exception as e:
    print(f"Erro: {e}")
