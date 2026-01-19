import pandas as pd
import os

def find_star_products():
    path = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx'
    
    if not os.path.exists(path):
        print("❌ File not found.")
        return
        
    print(f"Loading {path}...")
    df = pd.read_excel(path)
    
    # Columns check
    # We need 'Preço' (Sale) and 'Preço de custo off' (Cost)
    # The debug output showed columns like 'Preço de custo off', 'Preço'
    
    products = []
    
    for _, row in df.iterrows():
        try:
            name = row.get('Descrição', 'Unknown')
            price = float(row.get('Preço', 0))
            # Column name might be tricky, debug output showed 'Preço de custo off' maybe?
            # Wait, debug output showed:
            # Columns: ['ID', 'Código', 'Descrição', ... 'Preço', 'Valor IPI fixo', 'Preço de custo', 'Preço de custo off', ...]
            # Let's try 'Preço de custo' first, then 'Preço de custo off'
            
            cost = row.get('Preço de custo')
            if pd.isna(cost) or cost == 0:
                cost = row.get('Preço de custo off')
            
            cost = float(cost) if pd.notna(cost) else 0.0
            
            if price > 0:
                gross_margin_val = price - cost
                margin_pct = (gross_margin_val / price) * 100
            else:
                gross_margin_val = 0
                margin_pct = 0
            
            products.append({
                'name': name,
                'price': price,
                'cost': cost,
                'margin_pct': margin_pct,
                'margin_brl': gross_margin_val
            })
            
        except Exception as e:
            continue
            
    # Convert to DF for sorting
    df_res = pd.DataFrame(products)
    
    # Filter: Margin > 40%
    star_products = df_res[df_res['margin_pct'] >= 40].sort_values(by='margin_pct', ascending=False)
    
    # Also good to check high ticket items with reasonable margin (>30%)
    high_ticket = df_res[(df_res['price'] >= 150) & (df_res['margin_pct'] >= 30)].sort_values(by='price', ascending=False)
    
    # Generate Report
    report_file = r'c:\Users\caiof\NRAIZES\produtos_margem_alta.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("RELATÓRIO DE PRODUTOS ESTRELA (FOCO EM ADS)\n")
        f.write("="*60 + "\n")
        f.write("Critério: Margem Bruta > 40% ou Ticket > R$ 150 (com margem > 30%)\n\n")
        
        f.write(f"PRODUTOS COM MAIOR MARGEM (> 40%) - Top 30\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Produto':<40} | {'Preço':<10} | {'Custo':<10} | {'Margem %':<8} | {'Lucro R$':<10}\n")
        f.write("-" * 80 + "\n")
        
        for _, p in star_products.head(30).iterrows():
            f.write(f"{p['name'][:40]:<40} | R$ {p['price']:<7.2f} | R$ {p['cost']:<7.2f} | {p['margin_pct']:<6.2f}% | R$ {p['margin_brl']:<7.2f}\n")
            
        f.write("\n" + "="*60 + "\n")
        f.write(f"PRODUTOS HIGH TICKET (> R$ 150) - Top 20\n")
        f.write("(Ideais para subir ROAS com poucas vendas)\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Produto':<40} | {'Preço':<10} | {'Custo':<10} | {'Margem %':<8} | {'Lucro R$':<10}\n")
        f.write("-" * 80 + "\n")
        
        for _, p in high_ticket.head(20).iterrows():
             f.write(f"{p['name'][:40]:<40} | R$ {p['price']:<7.2f} | R$ {p['cost']:<7.2f} | {p['margin_pct']:<6.2f}% | R$ {p['margin_brl']:<7.2f}\n")

    print(f"✅ Report saved to {report_file}")
    
    # Print preview
    print("\nTop 5 Margins:")
    print(star_products[['name', 'margin_pct']].head().to_string())

if __name__ == "__main__":
    find_star_products()
