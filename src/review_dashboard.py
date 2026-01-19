"""
Bling Optimizer - Review Dashboard Generator
Generates HTML review page for AI proposals.
"""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vault.db')
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'review_dashboard.html')


def generate_review_dashboard():
    """Generate an HTML dashboard for reviewing AI proposals."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all pending proposals grouped by product
    cursor.execute('''
        SELECT 
            p.id as proposta_id,
            p.id_produto,
            p.tipo,
            p.conteudo_original,
            p.conteudo_proposto,
            p.status,
            pr.nome as produto_nome,
            pr.codigo as produto_codigo,
            pr.preco
        FROM propostas_ia p
        JOIN produtos pr ON p.id_produto = pr.id_bling
        WHERE p.status = 'pendente'
        ORDER BY pr.nome, p.tipo
    ''')
    
    proposals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Group by product
    products = {}
    for p in proposals:
        pid = p['id_produto']
        if pid not in products:
            products[pid] = {
                'nome': p['produto_nome'],
                'codigo': p['produto_codigo'],
                'preco': p['preco'],
                'proposals': []
            }
        products[pid]['proposals'].append(p)
    
    # Generate HTML
    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bling Optimizer - Revisão de Propostas</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
        h1 {{ color: #00d4ff; margin-bottom: 10px; }}
        .stats {{ background: #16213e; padding: 15px; border-radius: 10px; margin-bottom: 20px; display: flex; gap: 30px; }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #00d4ff; }}
        .stat-label {{ font-size: 0.9em; color: #888; }}
        .controls {{ background: #16213e; padding: 15px; border-radius: 10px; margin-bottom: 20px; display: flex; gap: 10px; }}
        button {{ padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
        .btn-approve {{ background: #00c853; color: white; }}
        .btn-reject {{ background: #ff5252; color: white; }}
        .btn-approve:hover {{ background: #00e676; }}
        .btn-reject:hover {{ background: #ff1744; }}
        .product {{ background: #16213e; margin-bottom: 15px; border-radius: 10px; overflow: hidden; }}
        .product-header {{ background: #0f3460; padding: 15px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
        .product-header:hover {{ background: #1a4a80; }}
        .product-name {{ font-weight: bold; color: #00d4ff; }}
        .product-code {{ color: #888; font-size: 0.9em; }}
        .product-body {{ padding: 15px; display: none; }}
        .product.expanded .product-body {{ display: block; }}
        .proposal {{ background: #1a1a2e; padding: 15px; margin-bottom: 10px; border-radius: 8px; border-left: 4px solid #00d4ff; }}
        .proposal-type {{ font-weight: bold; color: #ffc107; margin-bottom: 10px; text-transform: uppercase; font-size: 0.8em; }}
        .proposal-content {{ background: #0d1117; padding: 15px; border-radius: 5px; white-space: pre-wrap; font-size: 0.9em; }}
        .proposal-actions {{ margin-top: 10px; display: flex; gap: 10px; }}
        .proposal-actions button {{ padding: 5px 15px; font-size: 0.9em; }}
        .approved {{ border-left-color: #00c853; }}
        .rejected {{ border-left-color: #ff5252; opacity: 0.5; }}
        .filter-bar {{ margin-bottom: 20px; }}
        .filter-bar input {{ padding: 10px; width: 300px; border-radius: 5px; border: none; background: #16213e; color: #eee; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; margin-left: 10px; }}
        .badge-pending {{ background: #ffc107; color: #000; }}
        .badge-approved {{ background: #00c853; }}
        .badge-rejected {{ background: #ff5252; }}
    </style>
</head>
<body>
    <h1>🔍 Revisão de Propostas IA</h1>
    <p style="color: #888; margin-bottom: 20px;">Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value">{len(products)}</div>
            <div class="stat-label">Produtos</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len(proposals)}</div>
            <div class="stat-label">Propostas Pendentes</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len([p for p in proposals if p['tipo'] == 'descricao_curta'])}</div>
            <div class="stat-label">Descrições Curtas</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len([p for p in proposals if p['tipo'] == 'descricao_complementar'])}</div>
            <div class="stat-label">Descrições Longas</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len([p for p in proposals if p['tipo'] == 'seo'])}</div>
            <div class="stat-label">SEO</div>
        </div>
    </div>
    
    <div class="controls">
        <button class="btn-approve" onclick="approveAll()">✅ Aprovar Todas</button>
        <button class="btn-reject" onclick="rejectAll()">❌ Rejeitar Todas</button>
        <button onclick="expandAll()">📂 Expandir Todos</button>
        <button onclick="collapseAll()">📁 Recolher Todos</button>
        <button onclick="exportApproved()">📤 Exportar Aprovadas</button>
    </div>
    
    <div class="filter-bar">
        <input type="text" id="search" placeholder="🔍 Filtrar produtos..." onkeyup="filterProducts()">
    </div>
    
    <div id="products">
'''
    
    for pid, prod in products.items():
        proposals_html = ""
        for prop in prod['proposals']:
            # Escape HTML and format content
            content = prop['conteudo_proposto'].replace('<', '&lt;').replace('>', '&gt;')
            if prop['tipo'] == 'seo':
                try:
                    seo_data = json.loads(prop['conteudo_proposto'])
                    content = f"""📌 Title: {seo_data.get('title', 'N/A')}

📝 Meta Description: {seo_data.get('meta', 'N/A')}

🏷️ Keywords: {seo_data.get('keywords', 'N/A')}"""
                except:
                    pass
            
            proposals_html += f'''
        <div class="proposal" data-id="{prop['proposta_id']}" data-type="{prop['tipo']}">
            <div class="proposal-type">{prop['tipo'].replace('_', ' ')}</div>
            <div class="proposal-content">{content}</div>
            <div class="proposal-actions">
                <button class="btn-approve" onclick="approve({prop['proposta_id']}, this)">✅ Aprovar</button>
                <button class="btn-reject" onclick="reject({prop['proposta_id']}, this)">❌ Rejeitar</button>
            </div>
        </div>
'''
        
        html += f'''
    <div class="product" data-name="{prod['nome'].lower()}">
        <div class="product-header" onclick="toggleProduct(this)">
            <div>
                <span class="product-name">{prod['nome']}</span>
                <span class="product-code">({prod['codigo']})</span>
                <span class="badge badge-pending">{len(prod['proposals'])} propostas</span>
            </div>
            <span>R$ {prod['preco']:.2f}</span>
        </div>
        <div class="product-body">{proposals_html}</div>
    </div>
'''
    
    html += '''
    </div>
    
    <script>
        let approvedIds = [];
        let rejectedIds = [];
        
        function toggleProduct(header) {
            header.parentElement.classList.toggle('expanded');
        }
        
        function expandAll() {
            document.querySelectorAll('.product').forEach(p => p.classList.add('expanded'));
        }
        
        function collapseAll() {
            document.querySelectorAll('.product').forEach(p => p.classList.remove('expanded'));
        }
        
        function approve(id, btn) {
            const proposal = btn.closest('.proposal');
            proposal.classList.remove('rejected');
            proposal.classList.add('approved');
            approvedIds.push(id);
            rejectedIds = rejectedIds.filter(x => x !== id);
            updateExportButton();
        }
        
        function reject(id, btn) {
            const proposal = btn.closest('.proposal');
            proposal.classList.remove('approved');
            proposal.classList.add('rejected');
            rejectedIds.push(id);
            approvedIds = approvedIds.filter(x => x !== id);
            updateExportButton();
        }
        
        function approveAll() {
            document.querySelectorAll('.proposal:not(.rejected)').forEach(p => {
                const id = parseInt(p.dataset.id);
                p.classList.add('approved');
                if (!approvedIds.includes(id)) approvedIds.push(id);
            });
            updateExportButton();
        }
        
        function rejectAll() {
            document.querySelectorAll('.proposal').forEach(p => {
                const id = parseInt(p.dataset.id);
                p.classList.add('rejected');
                if (!rejectedIds.includes(id)) rejectedIds.push(id);
            });
            approvedIds = [];
            updateExportButton();
        }
        
        function updateExportButton() {
            console.log('Approved:', approvedIds.length, 'Rejected:', rejectedIds.length);
        }
        
        function exportApproved() {
            const data = JSON.stringify(approvedIds);
            const blob = new Blob([data], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'approved_proposals.json';
            a.click();
            alert('Exportado ' + approvedIds.length + ' propostas aprovadas.\\nExecute: python src/approve_batch.py approved_proposals.json');
        }
        
        function filterProducts() {
            const query = document.getElementById('search').value.toLowerCase();
            document.querySelectorAll('.product').forEach(p => {
                const name = p.dataset.name;
                p.style.display = name.includes(query) ? 'block' : 'none';
            });
        }
    </script>
</body>
</html>
'''
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Dashboard gerado: {OUTPUT_PATH}")
    print(f"   {len(products)} produtos | {len(proposals)} propostas")
    return OUTPUT_PATH


if __name__ == "__main__":
    generate_review_dashboard()
