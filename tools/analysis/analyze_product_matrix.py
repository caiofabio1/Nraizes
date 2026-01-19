import pandas as pd
import os
import sys
import unicodedata

# sys.path.append(os.path.dirname(__file__))
from analytics_tool import get_product_performance

def normalize_str(s):
    if not isinstance(s, str):
        return ""
    return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII').lower().strip()

def analyze_matrix():
    print("🚀 Iniciando Análise Estratégica de Matriz (BCG Adaptada)...")
    
    # 1. Fetch Sales Data from GA4
    ga_products = get_product_performance("448522931")
    if not ga_products:
        print("❌ Sem dados do GA4.")
        return

    # 2. Load Cost/Margin Data
    margin_file = r'c:\Users\caiof\NRAIZES\MIGRAÇÃO\produtos_importacao_bling.xlsx'
    if not os.path.exists(margin_file):
        print("❌ Arquivo de margens não encontrado.")
        return
        
    df_margin = pd.read_excel(margin_file)
    
    # Pre-process Margin Data into a Lookup Dict (Norm Name -> Data)
    margin_map = {}
    
    def parse_float(val):
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        if isinstance(val, str):
            val = val.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
            try:
                return float(val)
            except:
                return 0.0
        return 0.0

    for _, row in df_margin.iterrows():
        # Columns: 'Descrição', 'Preço', 'Preço de custo off' (or 'Preço de custo')
        name = str(row.get('Descrição', ''))
        # Try both cost columns 
        cost_val = row.get('Preço de custo')
        if pd.isna(cost_val) or cost_val == 0 or str(cost_val).strip() == '0':
            cost_val = row.get('Preço de custo off')
        
        cost = parse_float(cost_val)
        price = parse_float(row.get('Preço'))
        
        if pd.notna(cost) and pd.notna(price):
            norm_name = normalize_str(name)
            margin_map[norm_name] = {
                'cost': float(cost),
                'price': float(price),
                'original_name': name
            }

    # 3. Merge Data
    # List of all analyzed products
    # We will prioritize GA4 products (those that sell)
    
    analysis_data = []
    matched_count = 0
    
    # Optimize: Pre-tokenize Bling names
    bling_tokens = []
    for k, v in margin_map.items():
        tokens = set(k.split())
        bling_tokens.append((tokens, v))
        
    for p in ga_products:
        ga_name = p['name']
        norm_ga = normalize_str(ga_name)
        ga_tokens = set(norm_ga.split())
        
        match = None
        best_score = 0.0
        
        # 1. Exact Match
        if norm_ga in margin_map:
            match = margin_map[norm_ga]
        else:
            # 2. Token Overlap Match
            # We want to find the Bling product that shares the most words
            for b_tokens, v in bling_tokens:
                if not b_tokens: continue
                
                intersection = ga_tokens.intersection(b_tokens)
                if not intersection: continue
                
                # Score = Intersection / Union (Jaccard) or just Intersection / GA_Len
                # Let's use Intersection / Min_Len to be generous
                # score = len(intersection) / len(ga_tokens)
                
                # Higher threshold, e.g. 70% match
                score = len(intersection) / len(ga_tokens.union(b_tokens))
                
                if score > best_score and score > 0.25: # 25% overlap threshold
                    best_score = score
                    match = v
        
        if match:
            matched_count += 1
            price = match['price']
            cost = match['cost']
            qty = p['qty']
            rev = p['revenue']
            
            margin_pct = 0
            if price > 0:
                margin_pct = ((price - cost) / price) * 100
                
            analysis_data.append({
                'name': ga_name,
                'qty': qty,
                'revenue': rev,
                'margin_pct': margin_pct,
                'price': price,
                'cost': cost,
                'category': 'Unknown'
            })
            # print(f"MATCH: {ga_name} <-> {match['original_name']} ({best_score:.2f})") # Debug match
            
    print(f"📊 Cruzamento: {len(ga_products)} do GA4 -> {matched_count} com margem encontrada.")
    
    if matched_count == 0 and len(ga_products) > 0:
         print("\n⚠️ DEBUG: Names Comparison")
         print("--- GA4 Names (First 5) ---")
         for p in ga_products[:5]:
             print(f"   '{p['name']}' -> Norm: '{normalize_str(p['name'])}'")
             
         print("\n--- Bling Names Sample (First 5) ---")
         for k in list(margin_map.keys())[:5]:
             print(f"   Original: '{margin_map[k]['original_name']}' -> Norm: '{k}'")
    
    if not analysis_data:
        print("⚠️ Nenhum produto cruzado com sucesso. Verifique os nomes.")
        return
        
    df = pd.DataFrame(analysis_data)
    
    # 4. Strategic Quadrants
    # Thresholds:
    # High Volume: Top 30% of sales qty? Or mean?
    # High Margin: > 40% (as defined before)
    
    vol_median = df['qty'].median()
    vol_mean = df['qty'].mean()
    # Use average or a fixed number (e.g. > 10 sales in 90 days?)
    # Let's use a robust threshold: > 10 sales is "Selling".
    VOL_THRESHOLD = max(10, vol_median) 
    
    MARGIN_THRESHOLD = 40.0
    
    stars = df[(df['qty'] >= VOL_THRESHOLD) & (df['margin_pct'] >= MARGIN_THRESHOLD)]
    cows = df[(df['qty'] >= VOL_THRESHOLD) & (df['margin_pct'] < MARGIN_THRESHOLD)]
    opps = df[(df['qty'] < VOL_THRESHOLD) & (df['margin_pct'] >= MARGIN_THRESHOLD)]
    dogs = df[(df['qty'] < VOL_THRESHOLD) & (df['margin_pct'] < MARGIN_THRESHOLD)]
    
    # 5. Generate Intelligent Report
    report_file = r'c:\Users\caiof\NRAIZES\analise_estrategica_produtos.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("ANÁLISE ESTRATÉGICA DE MATRIZ (VOLUME x MARGEM)\n")
        f.write("Base de Dados: Google Analytics (90d) + Bling (Custos)\n")
        f.write("="*80 + "\n\n")
        
        f.write("1. ESTRELAS (⭐⭐⭐⭐⭐): Alto Volume + Alta Margem\n")
        f.write("ESTRATÉGIA: ESCALAR ADS AGRESSIVAMENTE. Estes são seus vencedores.\n")
        f.write(f"Volume > {VOL_THRESHOLD} | Margem > {MARGIN_THRESHOLD}%\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Produto':<40} | {'Vendas':<6} | {'Margem':<8} | {' Ação Sugerida'}\n")
        for _, p in stars.sort_values(by='revenue', ascending=False).iterrows():
            f.write(f"{p['name'][:40]:<40} | {p['qty']:<6} | {p['margin_pct']:<7.1f}% | 🚀 Aumentar Budget\n")
        f.write("\n")
        
        f.write("2. OPORTUNIDADES (💎): Baixo Volume + Alta Margem\n")
        f.write("ESTRATÉGIA: TESTAR CRIATIVOS. Eles dão lucro, mas ninguém vê. Precisam de tráfego.\n")
        f.write("-" * 80 + "\n")
        for _, p in opps.sort_values(by='margin_pct', ascending=False).head(20).iterrows():
             f.write(f"{p['name'][:40]:<40} | {p['qty']:<6} | {p['margin_pct']:<7.1f}% | 📢 Criar Anúncio\n")
        f.write("\n")
        
        f.write("3. VACAS LEITEIRAS (🐮): Alto Volume + Baixa Margem\n")
        f.write("ESTRATÉGIA: OTIMIZAR/BUNDLE. Vendem sozinhos, mas lucro baixo. Criar Kits com 'Estrelas' ou 'Oportunidades'.\n")
        f.write("-" * 80 + "\n")
        for _, p in cows.sort_values(by='qty', ascending=False).head(20).iterrows():
             f.write(f"{p['name'][:40]:<40} | {p['qty']:<6} | {p['margin_pct']:<7.1f}% | 📦 Montar Kit\n")
        f.write("\n")

        f.write("4. ABACAXIS (🍍): Baixo Volume + Baixa Margem\n")
        f.write("ESTRATÉGIA: LIMPEZA. Não gaste energia ou ads aqui.\n")
        f.write("-" * 80 + "\n")
        for _, p in dogs.sort_values(by='qty', ascending=False).head(10).iterrows():
             f.write(f"{p['name'][:40]:<40} | {p['qty']:<6} | {p['margin_pct']:<7.1f}% | 🛑 Pausar\n")

    print(f"✅ Relatório Estratégico Salvo: {report_file}")
    
    # Preview
    print("\n[Preview] Top Estrelas:")
    print(stars[['name', 'qty', 'margin_pct']].head().to_string())

if __name__ == "__main__":
    analyze_matrix()
