
import os
import sys
import io
import pandas as pd
from datetime import datetime, timedelta
from tabulate import tabulate

# Force UTF-8 for Windows output
sys.stdout = open('diagnostic_results.txt', 'w', encoding='utf-8')

# Configuração de Credenciais
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'C:\Users\caiof\AppData\Roaming\gcloud\application_default_credentials.json'

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension
import google.auth

# ID da Propriedade (Padrão descoberto anteriormente)
PROPERTY_ID = '448522931'

def get_client():
    SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
    credentials, project = google.auth.default(scopes=SCOPES, quota_project_id='novas-raizes')
    return BetaAnalyticsDataClient(credentials=credentials)

def fetch_report(client, dimensions, metrics, date_range='30daysAgo', filter_ghost=False):
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=date_range, end_date="today")],
    )
    # Note: GA4 API filtering is complex to build dynamically in python without helper.
    # We will fetch raw data and filter in Pandas for flexibility, as the dataset is small (<10k rows usually).
    
    response = client.run_report(request=request)
    
    data = []
    for row in response.rows:
        item = {}
        for i, d in enumerate(dimensions):
            item[d] = row.dimension_values[i].value
        for i, m in enumerate(metrics):
            item[m] = float(row.metric_values[i].value)
        data.append(item)
    
    df = pd.DataFrame(data)
    
    if filter_ghost and not df.empty and 'deviceCategory' in dimensions and 'sessionSourceMedium' in dimensions:
        # Ghost Definition: Desktop AND Direct AND Transactions = 0
        # But here we might not have all dims in all queries.
        # Filter Logic:
        # If overview query (date), we can't filter easily unless we breakdown by device/source.
        pass
        
    return df

def diagnose_store():
    # Force UTF-8 for Windows output
    sys.stdout = open('diagnostic_results.txt', 'w', encoding='utf-8')
    
    print(f"📊 Diagnóstico Estratégico da Loja (Propriedade: {PROPERTY_ID})")
    print("="*60)
    
    client = get_client()

    # 1. TRAFEGO REAL vs FANTASMA
    print("\n🔍 1. Qualidade do Tráfego (Últimos 30 dias)")
    
    # Fetch content with dimensions needed for filtering
    df_quality = fetch_report(client, ['deviceCategory', 'sessionSourceMedium'], ['activeUsers', 'sessions', 'transactions', 'purchaseRevenue'])
    
    if not df_quality.empty:
        # Define Ghost Traffic: Desktop AND (Direct OR (not set))
        # Note: 'sessionSourceMedium' for Direct is usually '(direct) / (none)'
        
        is_desktop = df_quality['deviceCategory'] == 'desktop'
        is_direct = df_quality['sessionSourceMedium'].str.contains(r'\(direct\)|\(not set\)', regex=True)
        
        ghost_mask = is_desktop & is_direct & (df_quality['transactions'] == 0)
        
        df_ghost = df_quality[ghost_mask]
        df_real = df_quality[~ghost_mask]
        
        total_users = df_quality['activeUsers'].sum()
        ghost_users = df_ghost['activeUsers'].sum()
        real_users = df_real['activeUsers'].sum()
        
        real_revenue = df_real['purchaseRevenue'].sum()
        ghost_revenue = df_ghost['purchaseRevenue'].sum() # Should be 0 based on filter, but let's see
        
        print(f"   📉 Tráfego Total: {int(total_users):,} usuários")
        print(f"   👻 Tráfego Fantasma (Bots/Atribuição Errada): {int(ghost_users):,} ({ghost_users/total_users:.1%})")
        print(f"   ✅ Tráfego REAL (Clientes): {int(real_users):,} ({real_users/total_users:.1%})")
        
        print(f"\n   💰 Receita Real: R$ {real_revenue:,.2f}")
        if real_users > 0:
            # We use sessions for conversion rate as it's more accurate for e-commerce benchmarks
            total_real_sessions = df_real['sessions'].sum()
            total_real_transactions = df_real['transactions'].sum()
            real_conversion = (total_real_transactions / total_real_sessions) * 100 if total_real_sessions > 0 else 0
            print(f"   🛒 Taxa de Conversão REAL: {real_conversion:.2f}% (Média e-commerce: 1.5% - 3.0%)")
            print(f"   📦 Pedidos Reais: {int(total_real_transactions)}")
        
        print("-" * 60)
        
        # ⚠️ ALERTA DE ESTRATÉGIA
        if ghost_users > total_users * 0.5:
            print("\n⚠️ ALERTA: Mais de 50% do seu tráfego é 'Fantasma' ou 'Direto sem conversão'.")
            print("   Isso geralmente indica:")
            print("   1. Erro de configuração no GTM4WP (o evento de página dispara antes do consentimento).")
            print("   2. Tráfego de bots massivos no servidor.")
            print("   3. Falta de filtros de IP interno.")
        
        # 2. ORIGEM DO DINHEIRO (Real Only)
        print("\n💎 2. De onde vem o dinheiro? (Top Fontes Reais)")
        df_sources_real = df_real.groupby('sessionSourceMedium')[['activeUsers', 'purchaseRevenue', 'transactions']].sum().reset_index()
        df_sources_real = df_sources_real.sort_values('purchaseRevenue', ascending=False).head(8)
        
        # Add Value per User
        df_sources_real['R$/User'] = df_sources_real['purchaseRevenue'] / df_sources_real['activeUsers']
        
        print(tabulate(df_sources_real, headers=['Fonte', 'Usuários', 'Receita (R$)', 'Pedidos', 'Ticket/User'], tablefmt='pretty', floatfmt=".2f", showindex=False))

    print("\n✅ Relatório Gerado com Sucesso em: diagnostic_results.txt")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        PROPERTY_ID = sys.argv[1]
    diagnose_store()
