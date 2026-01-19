
import os
import sys
import pandas as pd
from tabulate import tabulate
import google.auth
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension

# Configs
PROPERTY_ID = '448522931'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'C:\Users\caiof\AppData\Roaming\gcloud\application_default_credentials.json'

def get_client():
    SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
    credentials, project = google.auth.default(scopes=SCOPES, quota_project_id='novas-raizes')
    return BetaAnalyticsDataClient(credentials=credentials)

def fetch_data(client, dimensions, metrics, date_range='30daysAgo'):
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=date_range, end_date="today")],
    )
    response = client.run_report(request=request)
    
    data = []
    for row in response.rows:
        item = {}
        for i, d in enumerate(dimensions):
            item[d] = row.dimension_values[i].value
        for i, m in enumerate(metrics):
            item[m] = float(row.metric_values[i].value)
        data.append(item)
    return pd.DataFrame(data)

def analyze_ads():
    # Force UTF-8
    sys.stdout = open('ads_analysis_report.txt', 'w', encoding='utf-8')
    
    print(f"🚀 Análise Profunda: Google Ads (30 Dias)")
    print("="*60)
    
    client = get_client()
    
    # 1. Performance Geral do Canal (Source Medium = google / cpc)
    print("\n📊 1. Performance Geral (Google CPC)")
    df_traffic = fetch_data(client, ['sessionSourceMedium'], ['activeUsers', 'sessions', 'transactions', 'purchaseRevenue'])
    
    if not df_traffic.empty:
        df_ads = df_traffic[df_traffic['sessionSourceMedium'] == 'google / cpc']
        if not df_ads.empty:
            users = df_ads['activeUsers'].sum()
            revenue = df_ads['purchaseRevenue'].sum()
            tx = df_ads['transactions'].sum()
            conv = (tx / df_ads['sessions'].sum()) * 100 if df_ads['sessions'].sum() else 0
            roas_proxies = revenue / users # Simplificado, não temos custo aqui
            
            print(f"   👥 Usuários Pagos: {int(users)}")
            print(f"   💰 Receita Gerada: R$ {revenue:,.2f}")
            print(f"   🛒 Pedidos: {int(tx)}")
            print(f"   📈 Conversão: {conv:.2f}%")
            print(f"   💎 Receita por Usuário: R$ {roas_proxies:.2f}")
        else:
            print("   ❌ Nenhum tráfego 'google / cpc' encontrado.")
    
    print("-" * 60)
    
    # 2. Produtos Mais Vendidos (Global - já que item + sessionSource é arriscado)
    # Tentaremos filtrar por origem se possivel, se der erro capturamos.
    print("\n📦 2. Produtos Campeões (Receita)")
    try:
        # Tentar cruzar Item com Source
        df_items = fetch_data(client, ['itemName', 'sessionSourceMedium'], ['itemRevenue', 'itemsPurchased'])
        df_items_ads = df_items[df_items['sessionSourceMedium'] == 'google / cpc'].copy()
        
        if not df_items_ads.empty:
            df_items_ads = df_items_ads.groupby('itemName')[['itemRevenue', 'itemsPurchased']].sum().reset_index()
            df_items_ads = df_items_ads.sort_values('itemRevenue', ascending=False).head(10)
            print(tabulate(df_items_ads, headers=['Produto', 'Receita (R$)', 'Qtd'], tablefmt='simple', floatfmt=".2f", showindex=False))
        else:
            print("   ⚠️ Não foi possível isolar produtos por origem (zero dados). Mostrando Top Global:")
            # Fallback global
            df_global = fetch_data(client, ['itemName'], ['itemRevenue', 'itemsPurchased'])
            df_global = df_global.sort_values('itemRevenue', ascending=False).head(10)
            print(tabulate(df_global, headers=['Produto', 'Receita (R$)', 'Qtd'], tablefmt='simple', floatfmt=".2f", showindex=False))
            
    except Exception as e:
        print(f"   ❌ Erro ao buscar produtos: {e}")

    print("-" * 60)

    # 3. Campanhas (Se houver parametro UTM campaign ou gclid auto-tagueamento)
    print("\n📢 3. Campanhas (Top 5)")
    try:
        df_camp = fetch_data(client, ['sessionCampaignName', 'sessionSourceMedium'], ['purchaseRevenue', 'sessions', 'activeUsers'])
        df_camp_ads = df_camp[df_camp['sessionSourceMedium'] == 'google / cpc'].copy()
        
        if not df_camp_ads.empty:
            df_camp_ads = df_camp_ads.sort_values('purchaseRevenue', ascending=False).head(5)
            # Calcular ROI simplificado
            df_camp_ads['R$/Sessão'] = df_camp_ads['purchaseRevenue'] / df_camp_ads['sessions']
            print(tabulate(df_camp_ads[['sessionCampaignName', 'purchaseRevenue', 'R$/Sessão']], headers=['Campanha', 'Receita', 'R$/Sessão'], tablefmt='simple', floatfmt=".2f", showindex=False))
        else:
            print("   ⚠️ Nenhuma campanha identificada (provavelmente (not set) ou Performance Max 'cross-network').")
            # Listar o que tem google
            df_google = df_camp[df_camp['sessionSourceMedium'].str.contains('google', na=False)]
            if not df_google.empty:
                print("   Campanhas Google detectadas:")
                print(tabulate(df_google.head(5), headers='keys', tablefmt='simple'))
                
    except Exception as e:
        print(f"   ❌ Erro campanhas: {e}")
        
    print("\n✅ Deep Dive Concluído.")

if __name__ == "__main__":
    analyze_ads()
