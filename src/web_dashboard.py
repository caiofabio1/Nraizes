"""
NRAIZES - Unified Web Dashboard
Flask server for integrated management with direct Bling API sync.
"""

import os
import sys
import json
import sqlite3
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
from functools import wraps

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from database import get_connection, VaultDB, init_database
from bling_client import BlingClient
from price_adjuster import PriceAdjuster
from logger import get_logger

# Initialize logger
_logger = get_logger(__name__)

app = Flask(__name__)

# CORS Configuration for security
ALLOWED_ORIGINS = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]


def add_cors_headers(response):
    """Add CORS headers to response."""
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS or not origin:
        response.headers["Access-Control-Allow-Origin"] = origin or "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@app.after_request
def after_request(response):
    """Apply CORS headers to all responses."""
    return add_cors_headers(response)


@app.before_request
def handle_preflight():
    """Handle CORS preflight requests."""
    if request.method == "OPTIONS":
        response = app.make_response("")
        return add_cors_headers(response)


# Initialize
init_database()


def get_dashboard_data():
    """Collect all data for the unified dashboard."""
    db = VaultDB()
    conn = get_connection()
    cursor = conn.cursor()

    # Metrics
    cursor.execute('SELECT COUNT(*) FROM produtos WHERE situacao = "A"')
    total_produtos = cursor.fetchone()[0]

    cursor.execute(
        'SELECT COUNT(*) FROM produtos WHERE situacao = "A" AND (gtin IS NULL OR gtin = "")'
    )
    sem_ean = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM propostas_ia WHERE status = "pendente"')
    propostas_pendentes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT id_produto) FROM precos_concorrentes")
    com_preco_mercado = cursor.fetchone()[0]

    # Enrichment proposals
    cursor.execute("""
        SELECT p.id, p.id_produto, p.tipo, p.conteudo_proposto, pr.nome, pr.codigo
        FROM propostas_ia p
        JOIN produtos pr ON p.id_produto = pr.id_bling
        WHERE p.status = 'pendente'
        ORDER BY pr.nome, p.tipo
        LIMIT 100
    """)
    propostas = [dict(row) for row in cursor.fetchall()]

    # Products with EAN (for sync)
    cursor.execute("""
        SELECT id_bling, nome, gtin, codigo FROM produtos 
        WHERE situacao = 'A' AND gtin IS NOT NULL AND gtin != ''
        LIMIT 100
    """)
    eans = [dict(row) for row in cursor.fetchall()]

    # Price recommendations (legacy rule-based)
    try:
        adjuster = PriceAdjuster()
        price_recs = adjuster.analisar_todos()
        price_recs = [r for r in price_recs if r.acao.name != "MAINTAIN"][:50]
    except Exception as e:
        _logger.error(f"Failed to load price recommendations: {e}")
        price_recs = []

    # Smart Pricing proposals (new approval workflow)
    try:
        price_proposals = db.listar_propostas_preco("pendente")
    except Exception as e:
        _logger.error(f"Failed to load price proposals: {e}")
        price_proposals = []

    # Count approved waiting to be applied
    try:
        approved_proposals = db.listar_propostas_preco("aprovado")
    except Exception:
        approved_proposals = []

    conn.close()

    return {
        "metrics": {
            "total_produtos": total_produtos,
            "sem_ean": sem_ean,
            "propostas_pendentes": propostas_pendentes,
            "com_preco_mercado": com_preco_mercado,
            "price_proposals_pending": len(price_proposals),
            "price_proposals_approved": len(approved_proposals),
        },
        "propostas": propostas,
        "eans": eans,
        "price_recs": price_recs,
        "price_proposals": price_proposals,
        "approved_proposals": approved_proposals,
    }


UNIFIED_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bling Optimizer - Dashboard Unificado</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .tab-btn.active { border-bottom: 3px solid #3b82f6; color: #3b82f6; }
    </style>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
    <!-- Header -->
    <header class="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div class="max-w-7xl mx-auto flex justify-between items-center">
            <h1 class="text-2xl font-bold text-blue-400">🚀 Bling Optimizer</h1>
            <span class="text-gray-400 text-sm">{{ now }}</span>
        </div>
    </header>

    <!-- KPI Cards -->
    <div class="max-w-7xl mx-auto px-6 py-6">
        <div class="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-3xl font-bold text-blue-400">{{ data.metrics.total_produtos }}</div>
                <div class="text-sm text-gray-400">Produtos Ativos</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-3xl font-bold text-yellow-400">{{ data.metrics.sem_ean }}</div>
                <div class="text-sm text-gray-400">Sem EAN</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-3xl font-bold text-purple-400">{{ data.metrics.propostas_pendentes }}</div>
                <div class="text-sm text-gray-400">Propostas IA</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-3xl font-bold text-green-400">{{ data.metrics.com_preco_mercado }}</div>
                <div class="text-sm text-gray-400">Com Preço Mercado</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-orange-500/30">
                <div class="text-3xl font-bold text-orange-400">{{ data.metrics.price_proposals_pending }}</div>
                <div class="text-sm text-gray-400">Preços Pendentes</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-green-500/30">
                <div class="text-3xl font-bold text-green-400">{{ data.metrics.price_proposals_approved }}</div>
                <div class="text-sm text-gray-400">Preços Aprovados</div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="border-b border-gray-700 mb-6">
            <nav class="flex gap-8">
                <button class="tab-btn active pb-3 text-lg font-medium" onclick="showTab('smart-pricing')">
                    🧠 Smart Pricing
                </button>
                <button class="tab-btn pb-3 text-lg font-medium text-gray-400" onclick="showTab('enrichment')">
                    📝 Enriquecimento
                </button>
                <button class="tab-btn pb-3 text-lg font-medium text-gray-400" onclick="showTab('prices')">
                    💰 Preços (Regras)
                </button>
                <button class="tab-btn pb-3 text-lg font-medium text-gray-400" onclick="showTab('eans')">
                    🏷️ EANs
                </button>
                <button class="tab-btn pb-3 text-lg font-medium text-gray-400" onclick="showTab('sync')">
                    🔄 Sincronização
                </button>
            </nav>
        </div>

        <!-- Tab: Smart Pricing (NEW) -->
        <div id="tab-smart-pricing" class="tab-content active">
            <div class="flex justify-between items-center mb-4">
                <div>
                    <h2 class="text-xl font-bold">Propostas de Preço Inteligente ({{ data.price_proposals|length }} pendentes)</h2>
                    <p class="text-sm text-gray-400 mt-1">Geradas por IA + regras de mercado. Revise e aprove para sincronizar.</p>
                </div>
                <div class="flex gap-2">
                    <button onclick="generatePriceProposals()" class="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg font-medium text-sm">
                        🧠 Gerar Novas Propostas
                    </button>
                    <button onclick="approveAllPriceProposals()" class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-medium text-sm">
                        ✅ Aprovar Todas
                    </button>
                    <button onclick="applyApprovedPrices()" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium text-sm">
                        🚀 Aplicar Aprovadas ({{ data.approved_proposals|length }})
                    </button>
                </div>
            </div>

            {% if data.price_proposals %}
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead class="bg-gray-800">
                        <tr>
                            <th class="px-3 py-3 text-left">Produto</th>
                            <th class="px-3 py-3 text-right">Atual</th>
                            <th class="px-3 py-3 text-right">Sugerido</th>
                            <th class="px-3 py-3 text-center">Margem</th>
                            <th class="px-3 py-3 text-center">Acao</th>
                            <th class="px-3 py-3 text-center">Conf.</th>
                            <th class="px-3 py-3 text-left">Motivo</th>
                            <th class="px-3 py-3 text-center">Fonte</th>
                            <th class="px-3 py-3 text-center">Acoes</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-700">
                        {% for p in data.price_proposals %}
                        <tr class="hover:bg-gray-800/50" id="pp-{{ p.id }}">
                            <td class="px-3 py-3">
                                <div class="font-medium text-blue-300">{{ p.produto_nome[:35] }}{% if p.produto_nome|length > 35 %}...{% endif %}</div>
                                <div class="text-xs text-gray-500">{{ p.produto_codigo }}</div>
                            </td>
                            <td class="px-3 py-3 text-right font-mono">R$ {{ "%.2f"|format(p.preco_atual) }}</td>
                            <td class="px-3 py-3 text-right font-mono font-bold {% if p.acao == 'increase' %}text-green-400{% else %}text-red-400{% endif %}">
                                R$ {{ "%.2f"|format(p.preco_sugerido) }}
                            </td>
                            <td class="px-3 py-3 text-center text-xs">
                                {% if p.margem_atual is not none %}
                                <span class="text-gray-400">{{ "%.0f"|format(p.margem_atual) }}%</span>
                                <span class="text-gray-600">→</span>
                                <span class="{% if p.margem_nova and p.margem_nova >= 20 %}text-green-400{% else %}text-yellow-400{% endif %}">{{ "%.0f"|format(p.margem_nova) if p.margem_nova else '?' }}%</span>
                                {% else %}<span class="text-gray-600">-</span>{% endif %}
                            </td>
                            <td class="px-3 py-3 text-center">
                                <span class="px-2 py-1 rounded text-xs {% if p.acao == 'increase' %}bg-green-900 text-green-300{% else %}bg-red-900 text-red-300{% endif %}">
                                    {{ p.acao|upper }}
                                </span>
                            </td>
                            <td class="px-3 py-3 text-center">
                                <div class="w-full bg-gray-700 rounded-full h-2">
                                    <div class="h-2 rounded-full {% if p.confianca >= 0.8 %}bg-green-500{% elif p.confianca >= 0.6 %}bg-yellow-500{% else %}bg-red-500{% endif %}" style="width: {{ (p.confianca * 100)|int }}%"></div>
                                </div>
                                <span class="text-xs text-gray-400">{{ "%.0f"|format(p.confianca * 100) }}%</span>
                            </td>
                            <td class="px-3 py-3 text-xs text-gray-300 max-w-xs truncate" title="{{ p.motivo }}">{{ p.motivo[:60] }}{% if p.motivo|length > 60 %}...{% endif %}</td>
                            <td class="px-3 py-3 text-center">
                                <span class="text-xs px-2 py-1 rounded bg-gray-700 text-gray-300">{{ p.fonte_dados[:15] }}</span>
                            </td>
                            <td class="px-3 py-3 text-center">
                                <div class="flex gap-1">
                                    <button onclick="approvePriceProposal({{ p.id }})" class="bg-green-600 hover:bg-green-700 px-2 py-1 rounded text-xs" title="Aprovar">✅</button>
                                    <button onclick="rejectPriceProposal({{ p.id }})" class="bg-red-600 hover:bg-red-700 px-2 py-1 rounded text-xs" title="Rejeitar">❌</button>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="bg-gray-800 rounded-lg p-8 text-center">
                <div class="text-gray-500 text-lg mb-2">Nenhuma proposta de preco pendente</div>
                <p class="text-gray-600 text-sm">Clique em "Gerar Novas Propostas" para analisar precos com IA</p>
            </div>
            {% endif %}
        </div>

        <!-- Tab: Enrichment -->
        <div id="tab-enrichment" class="tab-content">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-bold">Propostas de Enriquecimento ({{ data.propostas|length }})</h2>
                <div class="flex gap-2">
                    <button onclick="approveAllEnrichment()" class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-medium">
                        ✅ Aprovar Todas
                    </button>
                </div>
            </div>
            <div class="space-y-3 max-h-96 overflow-y-auto">
                {% for p in data.propostas %}
                <div class="bg-gray-800 rounded-lg p-4" id="proposta-{{ p.id }}">
                    <div class="flex justify-between items-start">
                        <div class="flex-1">
                            <div class="font-medium text-blue-300">{{ p.nome[:50] }}...</div>
                            <div class="text-xs text-gray-500 mb-2">{{ p.tipo | upper }}</div>
                            <div class="text-sm text-gray-300 bg-gray-900 p-3 rounded max-h-32 overflow-y-auto whitespace-pre-wrap">{{ p.conteudo_proposto[:300] }}{% if p.conteudo_proposto|length > 300 %}...{% endif %}</div>
                        </div>
                        <div class="flex gap-2 ml-4">
                            <button onclick="approveProposal({{ p.id }})" class="bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-sm">✅</button>
                            <button onclick="rejectProposal({{ p.id }})" class="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm">❌</button>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- Tab: Prices -->
        <div id="tab-prices" class="tab-content">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-bold">Sugestões de Preço ({{ data.price_recs|length }})</h2>
                <button onclick="syncAllPrices()" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium">
                    🔄 Sincronizar Todos no Bling
                </button>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead class="bg-gray-800">
                        <tr>
                            <th class="px-4 py-3 text-left">Produto</th>
                            <th class="px-4 py-3 text-right">Atual</th>
                            <th class="px-4 py-3 text-right">Sugerido</th>
                            <th class="px-4 py-3 text-center">Ação</th>
                            <th class="px-4 py-3 text-center">Sync</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-700">
                        {% for r in data.price_recs %}
                        <tr class="hover:bg-gray-800" id="price-{{ r.id_produto }}">
                            <td class="px-4 py-3">{{ r.nome_produto[:40] }}...</td>
                            <td class="px-4 py-3 text-right">R$ {{ "%.2f"|format(r.preco_atual) }}</td>
                            <td class="px-4 py-3 text-right font-bold {% if r.acao.name == 'INCREASE' %}text-green-400{% else %}text-red-400{% endif %}">
                                R$ {{ "%.2f"|format(r.preco_sugerido) }}
                            </td>
                            <td class="px-4 py-3 text-center">
                                <span class="px-2 py-1 rounded text-xs {% if r.acao.name == 'INCREASE' %}bg-green-900 text-green-300{% else %}bg-red-900 text-red-300{% endif %}">
                                    {{ r.acao.name }}
                                </span>
                            </td>
                            <td class="px-4 py-3 text-center">
                                <button onclick="syncPrice({{ r.id_produto }}, {{ r.preco_sugerido }})" class="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-xs">
                                    Aplicar
                                </button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Tab: EANs -->
        <div id="tab-eans" class="tab-content">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-bold">EANs Encontrados ({{ data.eans|length }})</h2>
                <button onclick="syncAllEans()" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium">
                    🔄 Sincronizar Todos no Bling
                </button>
            </div>
            <div class="overflow-x-auto max-h-96 overflow-y-auto">
                <table class="w-full text-sm">
                    <thead class="bg-gray-800 sticky top-0">
                        <tr>
                            <th class="px-4 py-3 text-left">Produto</th>
                            <th class="px-4 py-3 text-left">Código</th>
                            <th class="px-4 py-3 text-left font-mono">GTIN/EAN</th>
                            <th class="px-4 py-3 text-center">Sync</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-700">
                        {% for e in data.eans %}
                        <tr class="hover:bg-gray-800" id="ean-{{ e.id_bling }}">
                            <td class="px-4 py-3">{{ e.nome[:40] }}...</td>
                            <td class="px-4 py-3 text-gray-400">{{ e.codigo }}</td>
                            <td class="px-4 py-3 font-mono text-green-400">{{ e.gtin }}</td>
                            <td class="px-4 py-3 text-center">
                                <button onclick="syncEan({{ e.id_bling }}, '{{ e.gtin }}')" class="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-xs">
                                    Aplicar
                                </button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Tab: Sync Log -->
        <div id="tab-sync" class="tab-content">
            <h2 class="text-xl font-bold mb-4">📋 Log de Sincronização</h2>
            <div id="sync-log" class="bg-gray-800 rounded-lg p-4 font-mono text-sm h-96 overflow-y-auto">
                <div class="text-gray-500">Aguardando operações de sincronização...</div>
            </div>
        </div>
    </div>

    <script>
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => {
                el.classList.remove('active');
                el.classList.add('text-gray-400');
            });
            // Show selected
            document.getElementById('tab-' + tabName).classList.add('active');
            event.target.classList.add('active');
            event.target.classList.remove('text-gray-400');
        }

        function log(message, type = 'info') {
            const logDiv = document.getElementById('sync-log');
            const colors = { success: 'text-green-400', error: 'text-red-400', info: 'text-blue-400' };
            const time = new Date().toLocaleTimeString();
            logDiv.innerHTML = `<div class="${colors[type]}">[${time}] ${message}</div>` + logDiv.innerHTML;
        }

        async function approveProposal(id) {
            log(`Aprovando proposta #${id}...`);
            try {
                const res = await fetch('/api/approve-proposal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                });
                const data = await res.json();
                if (data.success) {
                    log(`✅ Proposta #${id} aprovada!`, 'success');
                    document.getElementById('proposta-' + id).remove();
                } else {
                    log(`❌ Erro: ${data.error}`, 'error');
                }
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }

        async function rejectProposal(id) {
            log(`Rejeitando proposta #${id}...`);
            try {
                const res = await fetch('/api/reject-proposal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                });
                const data = await res.json();
                if (data.success) {
                    log(`🚫 Proposta #${id} rejeitada`, 'info');
                    document.getElementById('proposta-' + id).remove();
                }
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }

        async function approveAllEnrichment() {
            if (!confirm('Aprovar TODAS as propostas de enriquecimento?')) return;
            log('Aprovando todas as propostas...');
            try {
                const res = await fetch('/api/approve-all-proposals', { method: 'POST' });
                const data = await res.json();
                log(`✅ ${data.count} propostas aprovadas!`, 'success');
                setTimeout(() => location.reload(), 1000);
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }

        async function syncPrice(id, price) {
            log(`Sincronizando preço do produto #${id} para R$${price}...`);
            try {
                const res = await fetch('/api/sync-price', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id, price })
                });
                const data = await res.json();
                if (data.success) {
                    log(`✅ Preço do produto #${id} atualizado no Bling!`, 'success');
                    document.getElementById('price-' + id).classList.add('opacity-50');
                } else {
                    log(`❌ Erro: ${data.error}`, 'error');
                }
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }

        async function syncEan(id, ean) {
            log(`Sincronizando EAN do produto #${id}: ${ean}...`);
            try {
                const res = await fetch('/api/sync-ean', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id, ean })
                });
                const data = await res.json();
                if (data.success) {
                    log(`✅ EAN do produto #${id} atualizado no Bling!`, 'success');
                    document.getElementById('ean-' + id).classList.add('opacity-50');
                } else {
                    log(`❌ Erro: ${data.error}`, 'error');
                }
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }

        async function syncAllPrices() {
            if (!confirm('Sincronizar TODOS os preços sugeridos no Bling?')) return;
            log('Iniciando sincronização em lote de preços...');
            try {
                const res = await fetch('/api/sync-all-prices', { method: 'POST' });
                const data = await res.json();
                log(`✅ ${data.success_count} preços sincronizados, ${data.error_count} erros`, 'success');
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }

        async function syncAllEans() {
            if (!confirm('Sincronizar TODOS os EANs no Bling?')) return;
            log('Iniciando sincronização em lote de EANs...');
            try {
                const res = await fetch('/api/sync-all-eans', { method: 'POST' });
                const data = await res.json();
                log(`✅ ${data.success_count} EANs sincronizados, ${data.error_count} erros`, 'success');
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }

        // ============ Smart Pricing Functions ============

        async function approvePriceProposal(id) {
            log(`Aprovando proposta de preco #${id}...`);
            try {
                const res = await fetch('/api/smart-pricing/approve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                });
                const data = await res.json();
                if (data.success) {
                    log(`✅ Proposta #${id} aprovada!`, 'success');
                    const row = document.getElementById('pp-' + id);
                    if (row) row.classList.add('opacity-30');
                } else {
                    log(`❌ Erro: ${data.error}`, 'error');
                }
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }

        async function rejectPriceProposal(id) {
            log(`Rejeitando proposta de preco #${id}...`);
            try {
                const res = await fetch('/api/smart-pricing/reject', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                });
                const data = await res.json();
                if (data.success) {
                    log(`🚫 Proposta #${id} rejeitada`, 'info');
                    const row = document.getElementById('pp-' + id);
                    if (row) row.remove();
                }
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }

        async function approveAllPriceProposals() {
            if (!confirm('Aprovar TODAS as propostas de preco pendentes?')) return;
            log('Aprovando todas as propostas de preco...');
            try {
                const res = await fetch('/api/smart-pricing/approve-all', { method: 'POST' });
                const data = await res.json();
                log(`✅ ${data.count} propostas aprovadas!`, 'success');
                setTimeout(() => location.reload(), 1000);
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }

        async function applyApprovedPrices() {
            if (!confirm('Aplicar todas as propostas APROVADAS no Bling + WooCommerce?')) return;
            log('Aplicando propostas aprovadas... (pode demorar)');
            try {
                const res = await fetch('/api/smart-pricing/apply', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    log(`✅ ${data.success_count} precos aplicados, ${data.error_count} erros`, 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    log(`❌ Erro: ${data.error}`, 'error');
                }
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }

        async function generatePriceProposals() {
            if (!confirm('Gerar novas propostas de preco? (vai limpar pendentes anteriores)')) return;
            log('🧠 Gerando propostas com IA + regras... (pode demorar 1-2 min)');
            try {
                const res = await fetch('/api/smart-pricing/generate', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    log(`✅ ${data.total} propostas geradas (${data.aumentos} aumentos, ${data.reducoes} reducoes)`, 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    log(`❌ Erro: ${data.error}`, 'error');
                }
            } catch (e) {
                log(`❌ Erro: ${e}`, 'error');
            }
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    data = get_dashboard_data()
    return render_template_string(
        UNIFIED_TEMPLATE, data=data, now=datetime.now().strftime("%d/%m/%Y %H:%M")
    )


# ============ API Endpoints ============


@app.route("/api/approve-proposal", methods=["POST"])
def approve_proposal():
    try:
        data = request.json
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE propostas_ia 
            SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (data["id"],),
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/reject-proposal", methods=["POST"])
def reject_proposal():
    try:
        data = request.json
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE propostas_ia 
            SET status = 'rejeitado', reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (data["id"],),
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/approve-all-proposals", methods=["POST"])
def approve_all_proposals():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE propostas_ia 
            SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
            WHERE status = 'pendente'
        """)
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/sync-price", methods=["POST"])
def sync_price():
    try:
        data = request.json
        client = BlingClient()
        client.put_produtos_id_produto(str(data["id"]), {"preco": float(data["price"])})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/sync-ean", methods=["POST"])
def sync_ean():
    try:
        data = request.json
        client = BlingClient()
        client.put_produtos_id_produto(str(data["id"]), {"gtin": data["ean"]})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/sync-all-prices", methods=["POST"])
def sync_all_prices():
    try:
        adjuster = PriceAdjuster()
        recs = adjuster.analisar_todos()
        recs = [r for r in recs if r.acao.name != "MAINTAIN"]

        client = BlingClient()
        success = 0
        errors = 0

        for r in recs:
            try:
                client.put_produtos_id_produto(
                    str(r.id_produto), {"preco": float(r.preco_sugerido)}
                )
                success += 1
            except Exception as e:
                _logger.error(f"Failed to sync price for product {r.id_produto}: {e}")
                errors += 1

        return jsonify(
            {"success": True, "success_count": success, "error_count": errors}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/sync-all-eans", methods=["POST"])
def sync_all_eans():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_bling, gtin FROM produtos 
            WHERE situacao = 'A' AND gtin IS NOT NULL AND gtin != ''
        """)
        eans = cursor.fetchall()
        conn.close()

        client = BlingClient()
        success = 0
        errors = 0

        for e in eans:
            try:
                client.put_produtos_id_produto(str(e[0]), {"gtin": e[1]})
                success += 1
            except Exception as err:
                _logger.error(f"Failed to sync EAN for product {e[0]}: {err}")
                errors += 1

        return jsonify(
            {"success": True, "success_count": success, "error_count": errors}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ============ Smart Pricing API Endpoints ============


@app.route("/api/smart-pricing/approve", methods=["POST"])
def smart_pricing_approve():
    try:
        data = request.json
        db = VaultDB()
        db.aprovar_proposta_preco(data["id"])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/smart-pricing/reject", methods=["POST"])
def smart_pricing_reject():
    try:
        data = request.json
        db = VaultDB()
        db.rejeitar_proposta_preco(data["id"])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/smart-pricing/approve-all", methods=["POST"])
def smart_pricing_approve_all():
    try:
        db = VaultDB()
        count = db.aprovar_todas_propostas_preco()
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/smart-pricing/apply", methods=["POST"])
def smart_pricing_apply():
    try:
        from smart_pricing import SmartPricingPipeline

        pipeline = SmartPricingPipeline()
        result = pipeline.apply_approved(sync_bling=True, sync_woo=True)
        return jsonify(
            {
                "success": True,
                "success_count": result["success_count"],
                "error_count": result["error_count"],
                "total": result["total"],
            }
        )
    except Exception as e:
        _logger.error(f"Smart pricing apply error: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/smart-pricing/generate", methods=["POST"])
def smart_pricing_generate():
    try:
        from smart_pricing import SmartPricingPipeline

        pipeline = SmartPricingPipeline()
        proposals = pipeline.generate_proposals(use_gemini=True)
        aumentos = len([p for p in proposals if p.get("acao") == "increase"])
        reducoes = len([p for p in proposals if p.get("acao") == "decrease"])
        return jsonify(
            {
                "success": True,
                "total": len(proposals),
                "aumentos": aumentos,
                "reducoes": reducoes,
            }
        )
    except Exception as e:
        _logger.error(f"Smart pricing generate error: {e}")
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    _logger.logger.info("Starting NRAIZES Dashboard on http://localhost:5000")
    print("Starting NRAIZES Dashboard...")
    print("Access: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
