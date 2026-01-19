"""
Bling Optimizer - Unified Web Dashboard (Standalone - No Flask Required)
Uses Python's built-in http.server for zero-dependency operation.
"""
import os
import sys
import json
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime
import webbrowser
import threading

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from database import get_connection, VaultDB, init_database
from bling_client import BlingClient
from price_adjuster import PriceAdjuster

PORT = 5000

def get_dashboard_data():
    """Collect all data for the unified dashboard."""
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Metrics
    cursor.execute('SELECT COUNT(*) FROM produtos WHERE situacao = "A"')
    total_produtos = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM produtos WHERE situacao = "A" AND (gtin IS NULL OR gtin = "")')
    sem_ean = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM propostas_ia WHERE status = "pendente"')
    propostas_pendentes = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT id_produto) FROM precos_concorrentes')
    com_preco_mercado = cursor.fetchone()[0]
    
    # Enrichment proposals
    cursor.execute('''
        SELECT p.id, p.id_produto, p.tipo, p.conteudo_proposto, pr.nome, pr.codigo
        FROM propostas_ia p
        JOIN produtos pr ON p.id_produto = pr.id_bling
        WHERE p.status = 'pendente'
        ORDER BY pr.nome, p.tipo
        LIMIT 100
    ''')
    propostas = [dict(row) for row in cursor.fetchall()]
    
    # Products with EAN (for sync)
    cursor.execute('''
        SELECT id_bling, nome, gtin, codigo FROM produtos 
        WHERE situacao = 'A' AND gtin IS NOT NULL AND gtin != ''
        LIMIT 100
    ''')
    eans = [dict(row) for row in cursor.fetchall()]
    
    # Price recommendations
    price_recs = []
    try:
        adjuster = PriceAdjuster()
        all_recs = adjuster.analisar_todos()
        price_recs = [
            {
                'id_produto': r.id_produto,
                'nome_produto': r.nome_produto,
                'preco_atual': r.preco_atual,
                'preco_sugerido': r.preco_sugerido,
                'acao': r.acao.name
            }
            for r in all_recs if r.acao.name != 'MAINTAIN'
        ][:50]
    except Exception as e:
        print(f"Price recs error: {e}")
    
    conn.close()
    
    return {
        'metrics': {
            'total_produtos': total_produtos,
            'sem_ean': sem_ean,
            'propostas_pendentes': propostas_pendentes,
            'com_preco_mercado': com_preco_mercado
        },
        'propostas': propostas,
        'eans': eans,
        'price_recs': price_recs
    }


def generate_html(data):
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    # Generate proposal rows
    propostas_html = ""
    for p in data['propostas']:
        content = p['conteudo_proposto'][:300].replace('<', '&lt;').replace('>', '&gt;')
        if len(p['conteudo_proposto']) > 300:
            content += "..."
        propostas_html += f'''
        <div class="bg-gray-800 rounded-lg p-4 mb-3" id="proposta-{p['id']}">
            <div class="flex justify-between items-start">
                <div class="flex-1">
                    <div class="font-medium text-blue-300">{p['nome'][:50]}...</div>
                    <div class="text-xs text-gray-500 mb-2">{p['tipo'].upper()}</div>
                    <div class="text-sm text-gray-300 bg-gray-900 p-3 rounded whitespace-pre-wrap">{content}</div>
                </div>
                <div class="flex gap-2 ml-4">
                    <button onclick="approveProposal({p['id']})" class="bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-sm">✅</button>
                    <button onclick="rejectProposal({p['id']})" class="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm">❌</button>
                </div>
            </div>
        </div>'''
    
    # Generate price rows
    prices_html = ""
    for r in data['price_recs']:
        color = 'text-green-400' if r['acao'] == 'INCREASE' else 'text-red-400'
        badge_color = 'bg-green-900 text-green-300' if r['acao'] == 'INCREASE' else 'bg-red-900 text-red-300'
        prices_html += f'''
        <tr class="hover:bg-gray-800" id="price-{r['id_produto']}">
            <td class="px-4 py-3">{r['nome_produto'][:40]}...</td>
            <td class="px-4 py-3 text-right">R$ {r['preco_atual']:.2f}</td>
            <td class="px-4 py-3 text-right font-bold {color}">R$ {r['preco_sugerido']:.2f}</td>
            <td class="px-4 py-3 text-center"><span class="px-2 py-1 rounded text-xs {badge_color}">{r['acao']}</span></td>
            <td class="px-4 py-3 text-center">
                <button onclick="syncPrice({r['id_produto']}, {r['preco_sugerido']})" class="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-xs">Aplicar</button>
            </td>
        </tr>'''
    
    # Generate EAN rows
    eans_html = ""
    for e in data['eans']:
        eans_html += f'''
        <tr class="hover:bg-gray-800" id="ean-{e['id_bling']}">
            <td class="px-4 py-3">{e['nome'][:40]}...</td>
            <td class="px-4 py-3 text-gray-400">{e['codigo']}</td>
            <td class="px-4 py-3 font-mono text-green-400">{e['gtin']}</td>
            <td class="px-4 py-3 text-center">
                <button onclick="syncEan({e['id_bling']}, '{e['gtin']}')" class="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-xs">Aplicar</button>
            </td>
        </tr>'''

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bling Optimizer - Dashboard Unificado</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .tab-btn.active {{ border-bottom: 3px solid #3b82f6; color: #3b82f6; }}
    </style>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
    <header class="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div class="max-w-7xl mx-auto flex justify-between items-center">
            <h1 class="text-2xl font-bold text-blue-400">🚀 Bling Optimizer</h1>
            <span class="text-gray-400 text-sm">{now}</span>
        </div>
    </header>

    <div class="max-w-7xl mx-auto px-6 py-6">
        <!-- KPI Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-3xl font-bold text-blue-400">{data['metrics']['total_produtos']}</div>
                <div class="text-sm text-gray-400">Produtos Ativos</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-3xl font-bold text-yellow-400">{data['metrics']['sem_ean']}</div>
                <div class="text-sm text-gray-400">Sem EAN</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-3xl font-bold text-purple-400">{data['metrics']['propostas_pendentes']}</div>
                <div class="text-sm text-gray-400">Propostas IA</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-3xl font-bold text-green-400">{data['metrics']['com_preco_mercado']}</div>
                <div class="text-sm text-gray-400">Com Preço Mercado</div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="border-b border-gray-700 mb-6">
            <nav class="flex gap-8">
                <button class="tab-btn active pb-3 text-lg font-medium" onclick="showTab('enrichment')">📝 Enriquecimento</button>
                <button class="tab-btn pb-3 text-lg font-medium text-gray-400" onclick="showTab('prices')">💰 Preços</button>
                <button class="tab-btn pb-3 text-lg font-medium text-gray-400" onclick="showTab('eans')">🏷️ EANs</button>
                <button class="tab-btn pb-3 text-lg font-medium text-gray-400" onclick="showTab('sync')">🔄 Log</button>
            </nav>
        </div>

        <!-- Tab: Enrichment -->
        <div id="tab-enrichment" class="tab-content active">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-bold">Propostas de Enriquecimento ({len(data['propostas'])})</h2>
                <button onclick="approveAllEnrichment()" class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-medium">✅ Aprovar Todas</button>
            </div>
            <div class="space-y-3 max-h-96 overflow-y-auto">{propostas_html}</div>
        </div>

        <!-- Tab: Prices -->
        <div id="tab-prices" class="tab-content">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-bold">Sugestões de Preço ({len(data['price_recs'])})</h2>
                <button onclick="syncAllPrices()" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium">🔄 Sincronizar Todos</button>
            </div>
            <table class="w-full text-sm">
                <thead class="bg-gray-800"><tr>
                    <th class="px-4 py-3 text-left">Produto</th>
                    <th class="px-4 py-3 text-right">Atual</th>
                    <th class="px-4 py-3 text-right">Sugerido</th>
                    <th class="px-4 py-3 text-center">Ação</th>
                    <th class="px-4 py-3 text-center">Sync</th>
                </tr></thead>
                <tbody class="divide-y divide-gray-700">{prices_html}</tbody>
            </table>
        </div>

        <!-- Tab: EANs -->
        <div id="tab-eans" class="tab-content">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-bold">EANs Encontrados ({len(data['eans'])})</h2>
                <button onclick="syncAllEans()" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium">🔄 Sincronizar Todos</button>
            </div>
            <div class="overflow-x-auto max-h-96 overflow-y-auto">
                <table class="w-full text-sm">
                    <thead class="bg-gray-800 sticky top-0"><tr>
                        <th class="px-4 py-3 text-left">Produto</th>
                        <th class="px-4 py-3 text-left">Código</th>
                        <th class="px-4 py-3 text-left font-mono">GTIN/EAN</th>
                        <th class="px-4 py-3 text-center">Sync</th>
                    </tr></thead>
                    <tbody class="divide-y divide-gray-700">{eans_html}</tbody>
                </table>
            </div>
        </div>

        <!-- Tab: Sync Log -->
        <div id="tab-sync" class="tab-content">
            <h2 class="text-xl font-bold mb-4">📋 Log de Sincronização</h2>
            <div id="sync-log" class="bg-gray-800 rounded-lg p-4 font-mono text-sm h-96 overflow-y-auto">
                <div class="text-gray-500">Aguardando operações...</div>
            </div>
        </div>
    </div>

    <script>
        function showTab(tabName) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => {{ el.classList.remove('active'); el.classList.add('text-gray-400'); }});
            document.getElementById('tab-' + tabName).classList.add('active');
            event.target.classList.add('active');
            event.target.classList.remove('text-gray-400');
        }}

        function log(msg, type = 'info') {{
            const logDiv = document.getElementById('sync-log');
            const colors = {{ success: 'text-green-400', error: 'text-red-400', info: 'text-blue-400' }};
            const time = new Date().toLocaleTimeString();
            logDiv.innerHTML = `<div class="${{colors[type]}}">[$${{time}}] $${{msg}}</div>` + logDiv.innerHTML;
        }}

        async function api(endpoint, data) {{
            const res = await fetch('/api/' + endpoint, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(data)
            }});
            return await res.json();
        }}

        async function approveProposal(id) {{
            log(`Aprovando proposta #$${{id}}...`);
            const r = await api('approve-proposal', {{ id }});
            if (r.success) {{ log(`✅ Aprovada!`, 'success'); document.getElementById('proposta-'+id)?.remove(); }}
            else log(`❌ $${{r.error}}`, 'error');
        }}

        async function rejectProposal(id) {{
            log(`Rejeitando #$${{id}}...`);
            const r = await api('reject-proposal', {{ id }});
            if (r.success) {{ log(`🚫 Rejeitada`, 'info'); document.getElementById('proposta-'+id)?.remove(); }}
        }}

        async function approveAllEnrichment() {{
            if (!confirm('Aprovar TODAS?')) return;
            log('Aprovando todas...');
            const r = await api('approve-all', {{}});
            log(`✅ $${{r.count}} aprovadas!`, 'success');
            setTimeout(() => location.reload(), 1000);
        }}

        async function syncPrice(id, price) {{
            log(`Sync preço #$${{id}} → R$$${{price}}...`);
            const r = await api('sync-price', {{ id, price }});
            if (r.success) {{ log(`✅ Atualizado no Bling!`, 'success'); document.getElementById('price-'+id)?.classList.add('opacity-50'); }}
            else log(`❌ $${{r.error}}`, 'error');
        }}

        async function syncEan(id, ean) {{
            log(`Sync EAN #$${{id}} → $${{ean}}...`);
            const r = await api('sync-ean', {{ id, ean }});
            if (r.success) {{ log(`✅ Atualizado no Bling!`, 'success'); document.getElementById('ean-'+id)?.classList.add('opacity-50'); }}
            else log(`❌ $${{r.error}}`, 'error');
        }}

        async function syncAllPrices() {{
            if (!confirm('Sincronizar TODOS os preços?')) return;
            log('Sincronizando preços em lote...');
            const r = await api('sync-all-prices', {{}});
            log(`✅ $${{r.success_count}} OK, $${{r.error_count}} erros`, 'success');
        }}

        async function syncAllEans() {{
            if (!confirm('Sincronizar TODOS os EANs?')) return;
            log('Sincronizando EANs em lote...');
            const r = await api('sync-all-eans', {{}});
            log(`✅ $${{r.success_count}} OK, $${{r.error_count}} erros`, 'success');
        }}
    </script>
</body>
</html>'''


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress logs
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            data = get_dashboard_data()
            html = generate_html(data)
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body) if body else {}
        
        result = {'success': False, 'error': 'Unknown endpoint'}
        
        try:
            if '/api/approve-proposal' in self.path:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE propostas_ia SET status = "aprovado", reviewed_at = CURRENT_TIMESTAMP WHERE id = ?', (data['id'],))
                conn.commit()
                conn.close()
                result = {'success': True}
                
            elif '/api/reject-proposal' in self.path:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE propostas_ia SET status = "rejeitado", reviewed_at = CURRENT_TIMESTAMP WHERE id = ?', (data['id'],))
                conn.commit()
                conn.close()
                result = {'success': True}
                
            elif '/api/approve-all' in self.path:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE propostas_ia SET status = "aprovado", reviewed_at = CURRENT_TIMESTAMP WHERE status = "pendente"')
                count = cursor.rowcount
                conn.commit()
                conn.close()
                result = {'success': True, 'count': count}
                
            elif '/api/sync-price' in self.path:
                client = BlingClient()
                client.patch_produtos_id_produto(str(data['id']), {'preco': float(data['price'])})
                result = {'success': True}
                
            elif '/api/sync-ean' in self.path:
                client = BlingClient()
                client.patch_produtos_id_produto(str(data['id']), {'gtin': data['ean']})
                result = {'success': True}
                
            elif '/api/sync-all-prices' in self.path:
                adjuster = PriceAdjuster()
                recs = [r for r in adjuster.analisar_todos() if r.acao.name != 'MAINTAIN']
                client = BlingClient()
                success, errors = 0, 0
                for r in recs:
                    try:
                        client.patch_produtos_id_produto(str(r.id_produto), {'preco': float(r.preco_sugerido)})
                        success += 1
                    except:
                        errors += 1
                result = {'success': True, 'success_count': success, 'error_count': errors}
                
            elif '/api/sync-all-eans' in self.path:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT id_bling, gtin FROM produtos WHERE situacao = "A" AND gtin IS NOT NULL AND gtin != ""')
                eans = cursor.fetchall()
                conn.close()
                client = BlingClient()
                success, errors = 0, 0
                for e in eans:
                    try:
                        client.patch_produtos_id_produto(str(e[0]), {'gtin': e[1]})
                        success += 1
                    except:
                        errors += 1
                result = {'success': True, 'success_count': success, 'error_count': errors}
                
        except Exception as e:
            result = {'success': False, 'error': str(e)}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode('utf-8'))


def run_server():
    server = HTTPServer(('0.0.0.0', PORT), DashboardHandler)
    print(f"🚀 Dashboard Unificado rodando em http://localhost:{PORT}")
    print("   Pressione Ctrl+C para encerrar.\n")
    
    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(1)
        webbrowser.open(f'http://localhost:{PORT}')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⛔ Servidor encerrado.")


if __name__ == '__main__':
    run_server()
