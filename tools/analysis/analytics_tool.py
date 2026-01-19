
import os
import sys

# Force credentials path to ensure auth works
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'C:\Users\caiof\AppData\Roaming\gcloud\application_default_credentials.json'
# os.environ['GOOGLE_CLOUD_PROJECT'] = 'novas-raizes'

from google.analytics.admin import AnalyticsAdminServiceClient
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension
import google.auth

def list_properties():
    try:
        SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
        credentials, project = google.auth.default(scopes=SCOPES, quota_project_id='novas-raizes')
        
        client = AnalyticsAdminServiceClient(credentials=credentials)
        
        print(f"🔍 Autenticado: {project}")
        print("🔍 Buscando contas...")
        
        accounts = list(client.list_accounts())
        
        if not accounts:
            print("❌ Nenhuma conta acessível. (Tente fornecer o Property ID diretamente)")
            return

        print(f"✅ {len(accounts)} contas encontradas.\n")

        for account in accounts:
            print(f"👤 Conta: {account.display_name} ({account.name})")
            try:
                # properties = client.list_properties(filter=f"parent:{account.name}")
                # V1Alpha/Beta often takes request object or named args. 
                # Trying dict request
                req = {"filter": f"parent:{account.name}", "show_deleted": False}
                properties = client.list_properties(request=req)
                count = 0
                for prop in properties:
                    count += 1
                    pid = prop.name.split('/')[-1]
                    print(f"   🏠 {prop.display_name}")
                    print(f"      ID: {pid}")
                if count == 0:
                    print("   ⚠️ Nenhuma propriedade.")
            except Exception as e:
                print(f"   ❌ Erro ao listar props: {e}")
            print("-" * 40)
            
    except Exception as e:
        print(f"❌ Erro fatal na listagem: {e}")

def get_report(property_id):
    try:
        SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
        credentials, project = google.auth.default(scopes=SCOPES, quota_project_id='novas-raizes')
        client = BetaAnalyticsDataClient(credentials=credentials)

        print(f"📊 Gerando relatório para Propriedade ID: {property_id} (Últimos 30 dias)")
        
        # Request Total Active Users
        req_total = RunReportRequest(
            property=f"properties/{property_id}",
            metrics=[Metric(name="activeUsers")],
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        )
        res_total = client.run_report(request=req_total)
        total_users = res_total.rows[0].metric_values[0].value if res_total.rows else "0"

        # Request Daily breakdown
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="date")],
            metrics=[Metric(name="activeUsers")],
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        )
        response = client.run_report(request=request)

        print(f"\n👥 Usuários Ativos Totais: {total_users}")
        print("-" * 40)
        print(f"{'Data':<15} | {'Usuários':<15}")
        print("-" * 40)
        
        sorted_rows = sorted(response.rows, key=lambda x: x.dimension_values[0].value)

        for row in sorted_rows:
            date = row.dimension_values[0].value # YYYYMMDD
            users = row.metric_values[0].value
            formatted_date = f"{date[6:8]}/{date[4:6]}/{date[0:4]}"
            print(f"{formatted_date:<15} | {users:<15}")
            
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {e}")

def get_investment_metrics(property_id):
    try:
        SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
        credentials, project = google.auth.default(scopes=SCOPES, quota_project_id='novas-raizes')
        client = BetaAnalyticsDataClient(credentials=credentials)

        print(f"💰 Buscando métricas de investimento ID: {property_id} (90 dias)...")
        
        # Metrics: Sessions, Transactions, Revenue, Ad Cost, Clicks
        # Dimensions: Session Source/Medium to isolate Paid
        
        req = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="sessionSourceMedium")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="transactions"),
                Metric(name="purchaseRevenue"),
                Metric(name="advertiserAdCost"),
                Metric(name="advertiserAdClicks") 
            ],
            date_ranges=[DateRange(start_date="90daysAgo", end_date="today")],
        )
        
        response = client.run_report(request=req)
        
        print("-" * 60)
        print(f"{'Source/Medium':<30} | {'Sess':<8} | {'Trans':<6} | {'Cost':<10} | {'Rev':<10} | {'ROAS':<6}")
        print("-" * 60)
        
        total_sessions = 0
        total_trans = 0
        total_rev = 0.0
        total_cost = 0.0
        
        paid_data = [] # To store paid channels for projection
        
        for row in response.rows:
            source = row.dimension_values[0].value
            sess = int(row.metric_values[0].value)
            trans = int(row.metric_values[1].value)
            rev = float(row.metric_values[2].value)
            cost = float(row.metric_values[3].value)
            clicks = int(row.metric_values[4].value)
            
            roas = (rev / cost) if cost > 0 else 0
            
            print(f"{source[:30]:<30} | {sess:<8} | {trans:<6} | {cost:<10.2f} | {rev:<10.2f} | {roas:<6.2f}")
            
            total_sessions += sess
            total_trans += trans
            total_rev += rev
            total_cost += cost
            
            if 'cpc' in source or 'cpm' in source or 'ads' in source or cost > 0:
                paid_data.append({
                    "source": source,
                    "cost": cost,
                    "revenue": rev,
                    "transactions": trans,
                    "sessions": sess,
                    "clicks": clicks
                })

        print("-" * 60)
        print(f"{'TOTAL':<30} | {total_sessions:<8} | {total_trans:<6} | {total_cost:<10.2f} | {total_rev:<10.2f} | {(total_rev/total_cost if total_cost>0 else 0):<6.2f}")
        
        # Calculate Base Metrics for Projection
        # 1. Conversion Rate (Global vs Paid)
        global_cr = (total_trans / total_sessions * 100) if total_sessions > 0 else 0
        global_aov = (total_rev / total_trans) if total_trans > 0 else 0
        
        paid_sessions = sum(p['sessions'] for p in paid_data)
        paid_trans = sum(p['transactions'] for p in paid_data)
        paid_rev = sum(p['revenue'] for p in paid_data)
        paid_cost = sum(p['cost'] for p in paid_data)
        
        paid_cr = (paid_trans / paid_sessions * 100) if paid_sessions > 0 else 0
        paid_aov = (paid_rev / paid_trans) if paid_trans > 0 else 0
        paid_roas = (paid_rev / paid_cost) if paid_cost > 0 else 0
        paid_cpc = (paid_cost / sum(p['clicks'] for p in paid_data)) if paid_data and sum(p['clicks'] for p in paid_data) > 0 else 0
        
        print("\n📈 METRICS FOR PROJECTION")
        print(f"Global CR: {global_cr:.2f}% | AOV: R$ {global_aov:.2f}")
        print(f"Paid CR:   {paid_cr:.2f}% | Paid AOV: R$ {paid_aov:.2f} | ROAS: {paid_roas:.2f} | CPC: R$ {paid_cpc:.2f}")
        
        if paid_roas < 1 and paid_cost > 0:
            print("⚠️ Paid Traffic is currently running at a LOSS (ROAS < 1). Scale with caution!")
        
        return {
            "paid_cr": paid_cr,
            "paid_aov": paid_aov,
            "paid_roas": paid_roas,
            "paid_cpc": paid_cpc,
            "total_rev": total_rev
        }

    except Exception as e:
        print(f"❌ Erro na análise de investimento: {e}")
        return None

def get_product_performance(property_id):
    try:
        SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
        credentials, project = google.auth.default(scopes=SCOPES, quota_project_id='novas-raizes')
        client = BetaAnalyticsDataClient(credentials=credentials)

        print(f"📦 Buscando performance de produtos ID: {property_id} (90 dias)...")
        
        req = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="itemName")],
            metrics=[
                Metric(name="itemsPurchased"),
                Metric(name="itemRevenue")
            ],
            date_ranges=[DateRange(start_date="90daysAgo", end_date="today")],
            limit=500 # Top 500 products
        )
        
        response = client.run_report(request=req)
        
        products = []
        for row in response.rows:
            name = row.dimension_values[0].value
            qty = int(row.metric_values[0].value)
            rev = float(row.metric_values[1].value)
            
            if qty > 0:
                products.append({
                    "name": name,
                    "qty": qty,
                    "revenue": rev
                })
                
        print(f"✅ Encontrados {len(products)} produtos com vendas no GA4.")
        return products

    except Exception as e:
        print(f"❌ Erro na análise de produtos: {e}")
        return []

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'list':
            list_properties()
        elif sys.argv[1] == 'invest':
            # Default ID or arg 2
            pid = sys.argv[2] if len(sys.argv) > 2 else "448522931"
            get_investment_metrics(pid)
        else:
            get_report(sys.argv[1])
    else:
        print("Uso: python analytics_tool.py [list|invest <ID>|PROPERTY_ID]")
