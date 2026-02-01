#!/usr/bin/env python3
"""
Dashboard Web de Gestao de Precos - Novas Raizes
=================================================
Dashboard completo para visualizar, analisar e ajustar precos de todos os produtos.

Funcionalidades:
- Tabela de todos os produtos com preco, custo, margem
- Filtros por marca, faixa de margem, situacao de estoque
- Propostas de ajuste de preco (pendentes, aprovadas, rejeitadas, aplicadas)
- Ajuste manual de preco individual
- Geracao de propostas via Gemini AI
- Aplicacao em lote (Bling + WooCommerce + Google Shopping)
- Historico de alteracoes

Porta: 5001
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, render_template_string
from database import VaultDB, get_connection
from logger import get_logger

_logger = get_logger("pricing_dashboard")

app = Flask(__name__)


# CORS
@app.after_request
def add_cors(response):
    origin = request.headers.get("Origin", "")
    allowed = ["http://localhost:5001", "http://127.0.0.1:5001"]
    if origin in allowed:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# =========================================================================
# API ENDPOINTS
# =========================================================================


@app.route("/api/products")
def api_products():
    """Lista todos os produtos ativos com dados de preco e margem."""
    db = VaultDB()
    conn = db._get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id_bling, p.codigo, p.nome, p.preco, p.preco_custo,
               p.situacao, p.tipo, p.imagem_url,
               (SELECT COUNT(*) FROM produtos_lojas pl WHERE pl.id_produto = p.id_bling) as num_lojas
        FROM produtos p
        WHERE p.situacao = 'A'
        ORDER BY p.nome
    """)
    rows = cursor.fetchall()

    # Get market average prices
    cursor.execute("""
        SELECT id_produto, ROUND(AVG(preco), 2) as preco_medio,
               MIN(preco) as preco_min, MAX(preco) as preco_max, COUNT(*) as qtd_fontes
        FROM precos_concorrentes
        WHERE disponivel = 1
        GROUP BY id_produto
    """)
    market_prices = {r["id_produto"]: dict(r) for r in cursor.fetchall()}

    products = []
    for r in rows:
        preco = r["preco"] or 0
        custo = r["preco_custo"] or 0
        margem = (
            round((preco - custo) / preco * 100, 1) if preco > 0 and custo > 0 else None
        )
        # Extrair marca do SKU (3 primeiras letras)
        sku = r["codigo"] or ""
        marca = sku.split("-")[0] if "-" in sku else ""
        mp = market_prices.get(r["id_bling"], {})

        products.append(
            {
                "id_bling": r["id_bling"],
                "sku": sku,
                "nome": r["nome"],
                "preco": preco,
                "custo": custo,
                "margem": margem,
                "marca": marca,
                "tipo": r["tipo"],
                "imagem_url": r["imagem_url"],
                "num_lojas": r["num_lojas"],
                "preco_mercado_medio": mp.get("preco_medio"),
                "preco_mercado_min": mp.get("preco_min"),
                "preco_mercado_max": mp.get("preco_max"),
                "mercado_fontes": mp.get("qtd_fontes", 0),
            }
        )

    return jsonify({"products": products, "total": len(products)})


@app.route("/api/proposals")
def api_proposals():
    """Lista propostas de preco com filtro por status."""
    db = VaultDB()
    status = request.args.get("status", "all")

    if status == "all":
        pendentes = db.listar_propostas_preco(status="pendente", limit=500)
        aprovados = db.listar_propostas_preco(status="aprovado", limit=500)
        aplicados = db.listar_propostas_preco(status="aplicado", limit=500)
        rejeitados = db.listar_propostas_preco(status="rejeitado", limit=500)
        proposals = pendentes + aprovados + aplicados + rejeitados
    else:
        proposals = db.listar_propostas_preco(status=status, limit=500)

    # Get market average prices from precos_concorrentes
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id_produto, ROUND(AVG(preco), 2) as preco_medio, 
               MIN(preco) as preco_min, MAX(preco) as preco_max, COUNT(*) as qtd_fontes
        FROM precos_concorrentes 
        WHERE disponivel = 1
        GROUP BY id_produto
    """)
    market_prices = {r["id_produto"]: dict(r) for r in cursor.fetchall()}

    result = []
    for p in proposals:
        mp = market_prices.get(p["id_produto"], {})
        result.append(
            {
                "id": p["id"],
                "id_produto": p["id_produto"],
                "nome": p.get("produto_nome", ""),
                "sku": p.get("produto_codigo", ""),
                "preco_atual": p["preco_atual"],
                "preco_sugerido": p["preco_sugerido"],
                "preco_custo": p.get("preco_custo"),
                "margem_atual": p["margem_atual"],
                "margem_nova": p["margem_nova"],
                "acao": p["acao"],
                "motivo": p["motivo"],
                "fonte_dados": p["fonte_dados"],
                "confianca": p["confianca"],
                "status": p["status"],
                "created_at": p.get("created_at", ""),
                "reviewed_at": p.get("reviewed_at", ""),
                "applied_at": p.get("applied_at", ""),
                "preco_mercado_medio": mp.get("preco_medio"),
                "preco_mercado_min": mp.get("preco_min"),
                "preco_mercado_max": mp.get("preco_max"),
                "mercado_fontes": mp.get("qtd_fontes", 0),
            }
        )

    counts = {
        "pendente": len([p for p in result if p["status"] == "pendente"]),
        "aprovado": len([p for p in result if p["status"] == "aprovado"]),
        "aplicado": len([p for p in result if p["status"] == "aplicado"]),
        "rejeitado": len([p for p in result if p["status"] == "rejeitado"]),
    }

    return jsonify({"proposals": result, "counts": counts})


@app.route("/api/proposals/approve", methods=["POST"])
def api_approve_proposal():
    """Aprova uma proposta de preco."""
    db = VaultDB()
    data = request.json
    prop_id = data.get("id")
    if not prop_id:
        return jsonify({"error": "id obrigatorio"}), 400
    db.aprovar_proposta_preco(prop_id)
    return jsonify({"ok": True, "message": f"Proposta {prop_id} aprovada"})


@app.route("/api/proposals/reject", methods=["POST"])
def api_reject_proposal():
    """Rejeita uma proposta de preco."""
    db = VaultDB()
    data = request.json
    prop_id = data.get("id")
    if not prop_id:
        return jsonify({"error": "id obrigatorio"}), 400
    db.rejeitar_proposta_preco(prop_id)
    return jsonify({"ok": True, "message": f"Proposta {prop_id} rejeitada"})


@app.route("/api/proposals/update-price", methods=["POST"])
def api_update_proposal_price():
    """Atualiza o preco sugerido de uma proposta (ajuste manual pelo usuario)."""
    db = VaultDB()
    conn = db._get_conn()
    data = request.json
    prop_id = data.get("id")
    novo_preco = data.get("preco_sugerido")
    if not prop_id or not novo_preco:
        return jsonify({"error": "id e preco_sugerido obrigatorios"}), 400

    novo_preco = round(float(novo_preco), 2)
    cursor = conn.cursor()

    # Get current proposal
    cursor.execute("SELECT * FROM propostas_preco WHERE id = ?", (prop_id,))
    prop = cursor.fetchone()
    if not prop:
        return jsonify({"error": "proposta nao encontrada"}), 404

    # Recalculate margin
    custo = prop["preco_custo"] or 0
    margem_nova = (
        round((novo_preco - custo) / novo_preco * 100, 1)
        if novo_preco > 0 and custo > 0
        else None
    )
    acao = (
        "increase"
        if novo_preco > prop["preco_atual"]
        else "decrease"
        if novo_preco < prop["preco_atual"]
        else "maintain"
    )

    cursor.execute(
        """
        UPDATE propostas_preco 
        SET preco_sugerido = ?, margem_nova = ?, acao = ?,
            motivo = motivo || ' [Ajustado manualmente para R$' || ? || ']'
        WHERE id = ?
    """,
        (novo_preco, margem_nova, acao, str(novo_preco), prop_id),
    )
    conn.commit()

    return jsonify(
        {
            "ok": True,
            "preco_sugerido": novo_preco,
            "margem_nova": margem_nova,
            "acao": acao,
        }
    )


@app.route("/api/proposals/approve-all", methods=["POST"])
def api_approve_all():
    """Aprova todas as propostas pendentes."""
    db = VaultDB()
    count = db.aprovar_todas_propostas_preco()
    return jsonify({"ok": True, "count": count})


@app.route("/api/proposals/generate", methods=["POST"])
def api_generate_proposals():
    """Gera novas propostas de preco via Gemini AI."""
    try:
        from smart_pricing import SmartPricingPipeline

        pipeline = SmartPricingPipeline()
        proposals = pipeline.generate_proposals(use_gemini=True)
        return jsonify(
            {
                "ok": True,
                "count": len(proposals),
                "aumentos": len([p for p in proposals if p.get("acao") == "increase"]),
                "reducoes": len([p for p in proposals if p.get("acao") == "decrease"]),
            }
        )
    except Exception as e:
        _logger.error(f"Erro ao gerar propostas: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/proposals/apply", methods=["POST"])
def api_apply_proposals():
    """Aplica propostas aprovadas no Bling + WooCommerce + Google Shopping."""
    try:
        from smart_pricing import SmartPricingPipeline

        pipeline = SmartPricingPipeline()
        result = pipeline.apply_approved(sync_bling=True, sync_woo=True)
        return jsonify({"ok": True, **result})
    except Exception as e:
        _logger.error(f"Erro ao aplicar propostas: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/product/<int:id_bling>/update-price", methods=["POST"])
def api_update_price(id_bling):
    """Atualiza preco de um produto manualmente."""
    db = VaultDB()
    data = request.json
    novo_preco = data.get("preco")
    if not novo_preco or float(novo_preco) <= 0:
        return jsonify({"error": "preco invalido"}), 400

    novo_preco = round(float(novo_preco), 2)
    produto = db.get_produto_by_bling_id(id_bling)
    if not produto:
        return jsonify({"error": "produto nao encontrado"}), 404

    preco_anterior = produto["preco"]
    errors = []
    applied = {}

    # 1. Bling base
    bling = None
    try:
        from bling_client import BlingClient

        bling = BlingClient()
        bling.patch_produtos_id_produto(str(id_bling), {"preco": novo_preco})
        applied["bling_base"] = True
        time.sleep(0.35)
    except Exception as e:
        errors.append(f"Bling base: {e}")

    # 2. WooCommerce link in Bling
    try:
        if not bling:
            raise Exception("Bling client nao inicializado")
        links = bling.get_all_produtos_lojas(idProduto=id_bling, idLoja=205326820)
        if links:
            lid = links[0].get("id")
            bling.put_produtos_lojas_id(
                str(lid), {"idProdutoLoja": lid, "preco": novo_preco}
            )
            applied["woocommerce_bling"] = True
            time.sleep(0.35)
    except Exception as e:
        errors.append(f"WooCommerce link: {e}")

    # 3. Google Shopping link in Bling
    try:
        if not bling:
            raise Exception("Bling client nao inicializado")
        links_gs = bling.get_all_produtos_lojas(idProduto=id_bling, idLoja=205282664)
        if links_gs:
            lid_gs = links_gs[0].get("id")
            bling.put_produtos_lojas_id(
                str(lid_gs), {"idProdutoLoja": lid_gs, "preco": novo_preco}
            )
            applied["google_shopping_bling"] = True
            time.sleep(0.35)
    except Exception as e:
        errors.append(f"Google Shopping link: {e}")

    # 4. WooCommerce direto
    try:
        from woo_client import WooClient

        woo = WooClient()
        sku = produto.get("codigo")
        if sku:
            wc_products = woo.get_products(per_page=1, sku=sku)
            if wc_products:
                wc_id = wc_products[0]["id"]
                woo.update_product(wc_id, {"regular_price": str(novo_preco)})
                applied["woocommerce_direct"] = True
    except Exception as e:
        errors.append(f"WooCommerce direto: {e}")

    # 5. Historico
    try:
        db.registrar_alteracao_preco(
            id_produto=id_bling,
            preco_anterior=preco_anterior,
            preco_novo=novo_preco,
            motivo="ajuste_manual_dashboard",
        )
    except Exception as e:
        errors.append(f"Historico: {e}")

    # 6. Update local DB
    conn = db._get_conn()
    conn.cursor().execute(
        "UPDATE produtos SET preco = ? WHERE id_bling = ?", (novo_preco, id_bling)
    )
    conn.commit()

    return jsonify(
        {
            "ok": len(errors) == 0,
            "preco_anterior": preco_anterior,
            "preco_novo": novo_preco,
            "applied": applied,
            "errors": errors,
        }
    )


@app.route("/api/product/<int:id_bling>/history")
def api_product_history(id_bling):
    """Historico de alteracoes de preco de um produto."""
    db = VaultDB()
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM historico_precos
        WHERE id_produto = ?
        ORDER BY alterado_em DESC
        LIMIT 50
    """,
        (id_bling,),
    )
    rows = cursor.fetchall()
    return jsonify({"history": [dict(r) for r in rows]})


@app.route("/api/metrics")
def api_metrics():
    """Metricas gerais de preco."""
    db = VaultDB()
    conn = db._get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM produtos WHERE situacao = 'A'")
    total = cursor.fetchone()["total"]

    cursor.execute(
        "SELECT COUNT(*) as c FROM produtos WHERE situacao = 'A' AND preco_custo > 0"
    )
    com_custo = cursor.fetchone()["c"]

    cursor.execute("""
        SELECT COUNT(*) as c FROM produtos
        WHERE situacao = 'A' AND preco_custo > 0
        AND preco > 0 AND (preco - preco_custo) / preco * 100 < 20
    """)
    margem_baixa = cursor.fetchone()["c"]

    cursor.execute("""
        SELECT COUNT(*) as c FROM produtos
        WHERE situacao = 'A' AND preco_custo > preco AND preco_custo > 0 AND preco > 0
    """)
    margem_negativa = cursor.fetchone()["c"]

    cursor.execute(
        "SELECT COUNT(*) as c FROM propostas_preco WHERE status = 'pendente'"
    )
    prop_pendentes = cursor.fetchone()["c"]

    cursor.execute(
        "SELECT COUNT(*) as c FROM propostas_preco WHERE status = 'aprovado'"
    )
    prop_aprovadas = cursor.fetchone()["c"]

    cursor.execute("""
        SELECT AVG((preco - preco_custo) / preco * 100) as avg_margin
        FROM produtos
        WHERE situacao = 'A' AND preco_custo > 0 AND preco > preco_custo
    """)
    row = cursor.fetchone()
    avg_margin = round(row["avg_margin"], 1) if row["avg_margin"] else 0

    return jsonify(
        {
            "total_produtos": total,
            "com_custo": com_custo,
            "sem_custo": total - com_custo,
            "margem_baixa": margem_baixa,
            "margem_negativa": margem_negativa,
            "propostas_pendentes": prop_pendentes,
            "propostas_aprovadas": prop_aprovadas,
            "margem_media": avg_margin,
        }
    )


# =========================================================================
# FRONTEND
# =========================================================================

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Novas Raizes - Gestao de Precos</title>
<style>
:root {
  --bg: #0f1117;
  --surface: #1a1d27;
  --surface2: #242836;
  --border: #2e3345;
  --text: #e4e6ef;
  --text2: #8b8fa3;
  --accent: #6366f1;
  --accent2: #818cf8;
  --green: #22c55e;
  --green-bg: rgba(34,197,94,0.12);
  --red: #ef4444;
  --red-bg: rgba(239,68,68,0.12);
  --orange: #f59e0b;
  --orange-bg: rgba(245,158,11,0.12);
  --blue: #3b82f6;
  --blue-bg: rgba(59,130,246,0.12);
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: 'Inter', -apple-system, sans-serif; background:var(--bg); color:var(--text); }
a { color:var(--accent2); text-decoration:none; }

/* Layout */
.header { background:var(--surface); border-bottom:1px solid var(--border); padding:16px 24px; display:flex; align-items:center; justify-content:space-between; }
.header h1 { font-size:20px; font-weight:600; }
.header .subtitle { color:var(--text2); font-size:13px; }
.main { padding:20px 24px; max-width:1600px; margin:0 auto; }

/* KPI Cards */
.kpi-row { display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-bottom:20px; }
.kpi { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px; }
.kpi .label { color:var(--text2); font-size:12px; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px; }
.kpi .value { font-size:28px; font-weight:700; }
.kpi .sub { color:var(--text2); font-size:12px; margin-top:2px; }
.kpi.green .value { color:var(--green); }
.kpi.red .value { color:var(--red); }
.kpi.orange .value { color:var(--orange); }
.kpi.blue .value { color:var(--accent2); }

/* Tabs */
.tabs { display:flex; gap:4px; margin-bottom:16px; background:var(--surface); border-radius:10px; padding:4px; border:1px solid var(--border); }
.tab { padding:10px 20px; border-radius:8px; cursor:pointer; font-size:13px; font-weight:500; color:var(--text2); transition:all 0.2s; border:none; background:none; }
.tab:hover { color:var(--text); background:var(--surface2); }
.tab.active { color:var(--text); background:var(--accent); }
.tab .badge { background:var(--red); color:white; font-size:10px; padding:2px 6px; border-radius:10px; margin-left:6px; }

/* Toolbar */
.toolbar { display:flex; gap:10px; margin-bottom:16px; flex-wrap:wrap; align-items:center; }
.toolbar input, .toolbar select {
  background:var(--surface); border:1px solid var(--border); color:var(--text);
  padding:8px 14px; border-radius:8px; font-size:13px; outline:none;
}
.toolbar input:focus, .toolbar select:focus { border-color:var(--accent); }
.toolbar input { width:280px; }
.btn { padding:8px 16px; border-radius:8px; font-size:13px; font-weight:500; cursor:pointer; border:none; transition:all 0.15s; display:inline-flex; align-items:center; gap:6px; }
.btn-primary { background:var(--accent); color:white; }
.btn-primary:hover { background:var(--accent2); }
.btn-green { background:var(--green); color:white; }
.btn-green:hover { opacity:0.9; }
.btn-red { background:var(--red); color:white; }
.btn-red:hover { opacity:0.9; }
.btn-orange { background:var(--orange); color:#111; }
.btn-orange:hover { opacity:0.9; }
.btn-ghost { background:transparent; color:var(--text2); border:1px solid var(--border); }
.btn-ghost:hover { background:var(--surface2); color:var(--text); }
.btn-sm { padding:5px 10px; font-size:12px; }
.btn:disabled { opacity:0.4; cursor:not-allowed; }
.spacer { flex:1; }

/* Table */
.table-wrap { background:var(--surface); border:1px solid var(--border); border-radius:10px; overflow:hidden; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { background:var(--surface2); color:var(--text2); font-weight:600; text-transform:uppercase; font-size:11px; letter-spacing:0.5px; padding:10px 14px; text-align:left; position:sticky; top:0; cursor:pointer; user-select:none; white-space:nowrap; }
th:hover { color:var(--text); }
th.sorted-asc::after { content:' \\25B2'; font-size:9px; }
th.sorted-desc::after { content:' \\25BC'; font-size:9px; }
td { padding:10px 14px; border-top:1px solid var(--border); white-space:nowrap; }
tr:hover { background:var(--surface2); }
.product-name { max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-weight:500; }
.sku { color:var(--text2); font-family:monospace; font-size:12px; }
.price { font-weight:600; font-family:monospace; }
.margin { font-weight:600; }
.margin.good { color:var(--green); }
.margin.warn { color:var(--orange); }
.margin.bad { color:var(--red); }
.margin.none { color:var(--text2); }
.status-badge { padding:3px 8px; border-radius:6px; font-size:11px; font-weight:600; text-transform:uppercase; }
.status-pendente { background:var(--orange-bg); color:var(--orange); }
.status-aprovado { background:var(--green-bg); color:var(--green); }
.status-aplicado { background:var(--blue-bg); color:var(--blue); }
.status-rejeitado { background:var(--red-bg); color:var(--red); }
.action-increase { color:var(--green); font-weight:600; }
.action-decrease { color:var(--red); font-weight:600; }
.confidence-bar { width:60px; height:6px; background:var(--surface2); border-radius:3px; overflow:hidden; display:inline-block; vertical-align:middle; }
.confidence-fill { height:100%; border-radius:3px; }
.arrow { color:var(--text2); margin:0 4px; }

/* Scroll container */
.table-scroll { max-height:calc(100vh - 300px); overflow-y:auto; }

/* Modal */
.modal-overlay { position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:1000; display:none; align-items:center; justify-content:center; }
.modal-overlay.active { display:flex; }
.modal { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:24px; min-width:420px; max-width:560px; }
.modal h2 { font-size:18px; margin-bottom:16px; }
.modal .field { margin-bottom:14px; }
.modal .field label { display:block; color:var(--text2); font-size:12px; margin-bottom:4px; }
.modal .field input { width:100%; background:var(--surface2); border:1px solid var(--border); color:var(--text); padding:10px; border-radius:8px; font-size:14px; }
.modal .field .info { color:var(--text2); font-size:12px; margin-top:4px; }
.modal .actions { display:flex; gap:10px; justify-content:flex-end; margin-top:20px; }
.modal .history-list { max-height:200px; overflow-y:auto; font-size:12px; margin-top:10px; }
.modal .history-list .entry { padding:6px 0; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; }

/* Toast */
.toast-container { position:fixed; top:20px; right:20px; z-index:2000; display:flex; flex-direction:column; gap:8px; }
.toast { padding:12px 20px; border-radius:8px; font-size:13px; font-weight:500; animation:slideIn 0.3s ease; min-width:280px; }
.toast.success { background:var(--green); color:white; }
.toast.error { background:var(--red); color:white; }
.toast.info { background:var(--accent); color:white; }
@keyframes slideIn { from { transform:translateX(100%); opacity:0; } to { transform:translateX(0); opacity:1; } }

/* Loading */
.loading { text-align:center; padding:40px; color:var(--text2); }
.spinner { display:inline-block; width:24px; height:24px; border:3px solid var(--border); border-top-color:var(--accent); border-radius:50%; animation:spin 0.8s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }

/* Responsive */
@media (max-width:900px) {
  .kpi-row { grid-template-columns:repeat(2, 1fr); }
  .toolbar input { width:180px; }
}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>Gestao de Precos</h1>
    <div class="subtitle">Novas Raizes - Dashboard de Pricing</div>
  </div>
  <div style="display:flex;gap:10px;">
    <button class="btn btn-primary" onclick="generateProposals()" id="btnGenerate">Gerar Propostas IA</button>
    <button class="btn btn-green" onclick="applyApproved()" id="btnApply">Aplicar Aprovadas</button>
  </div>
</div>

<div class="main">
  <!-- KPIs -->
  <div class="kpi-row" id="kpis">
    <div class="kpi"><div class="label">Carregando...</div><div class="value">-</div></div>
  </div>

  <!-- Tabs -->
  <div class="tabs">
    <button class="tab active" data-tab="products" onclick="switchTab('products', this)">Todos os Produtos</button>
    <button class="tab" data-tab="proposals" onclick="switchTab('proposals', this)">
      Propostas <span class="badge" id="proposalBadge" style="display:none">0</span>
    </button>
    <button class="tab" data-tab="history" onclick="switchTab('history', this)">Historico</button>
  </div>

  <!-- Tab: Products -->
  <div id="tab-products" class="tab-content">
    <div class="toolbar">
      <input type="text" id="searchProducts" placeholder="Buscar por nome, SKU ou marca..." oninput="filterProducts()">
      <select id="filterMargin" onchange="filterProducts()">
        <option value="all">Todas as margens</option>
        <option value="negative">Margem negativa</option>
        <option value="low">Margem < 20%</option>
        <option value="ok">Margem 20-40%</option>
        <option value="high">Margem > 40%</option>
        <option value="nocost">Sem custo</option>
      </select>
      <select id="filterBrand" onchange="filterProducts()">
        <option value="all">Todas as marcas</option>
      </select>
      <div class="spacer"></div>
      <span id="productCount" style="color:var(--text2);font-size:13px;"></span>
    </div>
    <div class="table-wrap">
      <div class="table-scroll">
        <table id="productsTable">
          <thead>
            <tr>
              <th data-sort="nome" onclick="sortProducts('nome')">Produto</th>
              <th data-sort="sku" onclick="sortProducts('sku')">SKU</th>
              <th data-sort="marca" onclick="sortProducts('marca')">Marca</th>
              <th data-sort="preco" onclick="sortProducts('preco')" style="text-align:right">Preco</th>
              <th data-sort="preco_mercado_medio" onclick="sortProducts('preco_mercado_medio')" style="text-align:right">Mercado</th>
              <th data-sort="custo" onclick="sortProducts('custo')" style="text-align:right">Custo</th>
              <th data-sort="margem" onclick="sortProducts('margem')" style="text-align:right">Margem</th>
              <th data-sort="num_lojas" onclick="sortProducts('num_lojas')" style="text-align:center">Lojas</th>
              <th style="text-align:center">Acoes</th>
            </tr>
          </thead>
          <tbody id="productsBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Tab: Proposals -->
  <div id="tab-proposals" class="tab-content" style="display:none">
    <div class="toolbar">
      <select id="filterProposalStatus" onchange="loadProposals()">
        <option value="all">Todos os status</option>
        <option value="pendente">Pendentes</option>
        <option value="aprovado">Aprovadas</option>
        <option value="aplicado">Aplicadas</option>
        <option value="rejeitado">Rejeitadas</option>
      </select>
      <div class="spacer"></div>
      <button class="btn btn-green btn-sm" onclick="approveAll()">Aprovar Todas Pendentes</button>
    </div>
    <div class="table-wrap">
      <div class="table-scroll">
        <table id="proposalsTable">
          <thead>
            <tr>
              <th>Produto</th>
              <th>SKU</th>
              <th style="text-align:right">Preco Atual</th>
              <th style="text-align:center">-></th>
              <th style="text-align:right">Preco Sugerido</th>
              <th style="text-align:right">Preco Mercado</th>
              <th style="text-align:right">Margem</th>
              <th>Acao</th>
              <th>Motivo</th>
              <th style="text-align:center">Confianca</th>
              <th>Status</th>
              <th style="text-align:center">Acoes</th>
            </tr>
          </thead>
          <tbody id="proposalsBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Tab: History -->
  <div id="tab-history" class="tab-content" style="display:none">
    <div class="table-wrap">
      <div class="table-scroll">
        <table id="historyTable">
          <thead>
            <tr>
              <th>Data</th>
              <th>Produto</th>
              <th style="text-align:right">Preco Anterior</th>
              <th style="text-align:center">-></th>
              <th style="text-align:right">Preco Novo</th>
              <th style="text-align:right">Variacao</th>
              <th>Motivo</th>
            </tr>
          </thead>
          <tbody id="historyBody"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- Modal: Edit Price -->
<div class="modal-overlay" id="editModal">
  <div class="modal">
    <h2 id="modalTitle">Ajustar Preco</h2>
    <div class="field">
      <label>Produto</label>
      <div id="modalProductName" style="font-weight:600;"></div>
      <div id="modalSku" class="sku" style="margin-top:2px;"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
      <div class="field">
        <label>Preco Atual</label>
        <input type="text" id="modalCurrentPrice" disabled>
      </div>
      <div class="field">
        <label>Custo</label>
        <input type="text" id="modalCost" disabled>
      </div>
    </div>
    <div class="field">
      <label>Novo Preco (R$)</label>
      <input type="number" id="modalNewPrice" step="0.01" min="0.01" oninput="updateModalMargin()">
      <div class="info" id="modalMarginInfo"></div>
    </div>
    <div class="field" id="modalHistorySection">
      <label>Historico recente</label>
      <div class="history-list" id="modalHistory"></div>
    </div>
    <div class="actions">
      <button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="savePrice()" id="btnSave">Salvar e Aplicar</button>
    </div>
  </div>
</div>

<!-- Modal: Edit Proposal Price -->
<div class="modal-overlay" id="proposalEditModal">
  <div class="modal">
    <h2>Ajustar Preco da Proposta</h2>
    <div class="field">
      <label>Produto</label>
      <div id="propModalName" style="font-weight:600;"></div>
      <div id="propModalSku" class="sku" style="margin-top:2px;"></div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;">
      <div class="field">
        <label>Preco Atual</label>
        <input type="text" id="propModalCurrentPrice" disabled>
      </div>
      <div class="field">
        <label>Custo</label>
        <input type="text" id="propModalCost" disabled>
      </div>
      <div class="field">
        <label>Preco Mercado</label>
        <input type="text" id="propModalMarket" disabled>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
      <div class="field">
        <label>Preco Sugerido IA</label>
        <input type="text" id="propModalOriginal" disabled>
      </div>
      <div class="field">
        <label>Novo Preco (R$)</label>
        <input type="number" id="propModalNewPrice" step="0.01" min="0.01" oninput="updatePropModalMargin()">
      </div>
    </div>
    <div class="field">
      <div class="info" id="propModalMarginInfo"></div>
    </div>
    <div class="field" style="margin-top:8px;">
      <label>Motivo da IA</label>
      <div id="propModalMotivo" style="color:var(--text2);font-size:12px;max-height:60px;overflow-y:auto;"></div>
    </div>
    <div class="actions">
      <button class="btn btn-ghost" onclick="closePropModal()">Cancelar</button>
      <button class="btn btn-primary" onclick="savePropPrice()" id="btnSaveProp">Salvar Ajuste</button>
      <button class="btn btn-green" onclick="savePropPriceAndApprove()" id="btnSavePropApprove">Salvar e Aprovar</button>
    </div>
  </div>
</div>

<!-- Toast container -->
<div class="toast-container" id="toasts"></div>

<script>
// =========================================================================
// STATE
// =========================================================================
let allProducts = [];
let allProposals = [];
let currentSort = { key: 'nome', dir: 'asc' };
let editingProduct = null;

// =========================================================================
// INIT
// =========================================================================
document.addEventListener('DOMContentLoaded', () => {
  loadMetrics();
  loadProducts();
  loadProposals();
  loadHistory();
});

// =========================================================================
// TOAST
// =========================================================================
function toast(msg, type='info') {
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  document.getElementById('toasts').appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// =========================================================================
// TABS
// =========================================================================
function switchTab(tab, btn) {
  document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + tab).style.display = 'block';
  btn.classList.add('active');
  if (tab === 'proposals') loadProposals();
  if (tab === 'history') loadHistory();
}

// =========================================================================
// METRICS
// =========================================================================
async function loadMetrics() {
  try {
    const res = await fetch('/api/metrics');
    const data = await res.json();
    document.getElementById('kpis').innerHTML = `
      <div class="kpi blue">
        <div class="label">Total Produtos</div>
        <div class="value">${data.total_produtos}</div>
        <div class="sub">${data.com_custo} com custo | ${data.sem_custo} sem</div>
      </div>
      <div class="kpi ${data.margem_media >= 25 ? 'green' : 'orange'}">
        <div class="label">Margem Media</div>
        <div class="value">${data.margem_media}%</div>
        <div class="sub">Produtos com custo cadastrado</div>
      </div>
      <div class="kpi ${data.margem_baixa > 0 ? 'orange' : 'green'}">
        <div class="label">Margem Baixa (<20%)</div>
        <div class="value">${data.margem_baixa}</div>
        <div class="sub">${data.margem_negativa} com margem negativa</div>
      </div>
      <div class="kpi ${data.propostas_pendentes > 0 ? 'orange' : ''}">
        <div class="label">Propostas Pendentes</div>
        <div class="value">${data.propostas_pendentes}</div>
        <div class="sub">${data.propostas_aprovadas} aprovadas para aplicar</div>
      </div>
    `;
    const badge = document.getElementById('proposalBadge');
    if (data.propostas_pendentes > 0) {
      badge.textContent = data.propostas_pendentes;
      badge.style.display = 'inline';
    }
    // Update apply button
    document.getElementById('btnApply').textContent = `Aplicar Aprovadas (${data.propostas_aprovadas})`;
    if (data.propostas_aprovadas === 0) document.getElementById('btnApply').disabled = true;
    else document.getElementById('btnApply').disabled = false;
  } catch(e) { console.error('loadMetrics', e); }
}

// =========================================================================
// PRODUCTS TABLE
// =========================================================================
async function loadProducts() {
  try {
    document.getElementById('productsBody').innerHTML = '<tr><td colspan="9" class="loading"><div class="spinner"></div></td></tr>';
    const res = await fetch('/api/products');
    const data = await res.json();
    allProducts = data.products;
    populateBrandFilter();
    renderProducts();
  } catch(e) {
    document.getElementById('productsBody').innerHTML = '<tr><td colspan="9" class="loading">Erro ao carregar produtos</td></tr>';
  }
}

function populateBrandFilter() {
  const brands = [...new Set(allProducts.map(p => p.marca).filter(Boolean))].sort();
  const sel = document.getElementById('filterBrand');
  sel.innerHTML = '<option value="all">Todas as marcas</option>';
  brands.forEach(b => {
    const count = allProducts.filter(p => p.marca === b).length;
    sel.innerHTML += `<option value="${b}">${b} (${count})</option>`;
  });
}

function getFilteredProducts() {
  const search = document.getElementById('searchProducts').value.toLowerCase();
  const margin = document.getElementById('filterMargin').value;
  const brand = document.getElementById('filterBrand').value;

  return allProducts.filter(p => {
    if (search && !p.nome.toLowerCase().includes(search) && !p.sku.toLowerCase().includes(search) && !p.marca.toLowerCase().includes(search)) return false;
    if (brand !== 'all' && p.marca !== brand) return false;
    if (margin === 'negative' && !(p.margem !== null && p.margem < 0)) return false;
    if (margin === 'low' && !(p.margem !== null && p.margem >= 0 && p.margem < 20)) return false;
    if (margin === 'ok' && !(p.margem !== null && p.margem >= 20 && p.margem <= 40)) return false;
    if (margin === 'high' && !(p.margem !== null && p.margem > 40)) return false;
    if (margin === 'nocost' && p.custo > 0) return false;
    return true;
  });
}

function sortProducts(key) {
  if (currentSort.key === key) {
    currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
  } else {
    currentSort.key = key;
    currentSort.dir = 'asc';
  }
  renderProducts();
  // Update th classes
  document.querySelectorAll('#productsTable th').forEach(th => {
    th.classList.remove('sorted-asc', 'sorted-desc');
    if (th.dataset.sort === key) th.classList.add('sorted-' + currentSort.dir);
  });
}

function renderProducts() {
  let filtered = getFilteredProducts();

  // Sort
  filtered.sort((a, b) => {
    let va = a[currentSort.key], vb = b[currentSort.key];
    if (va === null || va === undefined) va = currentSort.dir === 'asc' ? Infinity : -Infinity;
    if (vb === null || vb === undefined) vb = currentSort.dir === 'asc' ? Infinity : -Infinity;
    if (typeof va === 'string') { va = va.toLowerCase(); vb = (vb||'').toLowerCase(); }
    if (va < vb) return currentSort.dir === 'asc' ? -1 : 1;
    if (va > vb) return currentSort.dir === 'asc' ? 1 : -1;
    return 0;
  });

  document.getElementById('productCount').textContent = `${filtered.length} de ${allProducts.length} produtos`;

  const tbody = document.getElementById('productsBody');
  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="loading">Nenhum produto encontrado</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(p => {
    const marginClass = p.margem === null ? 'none' : p.margem < 0 ? 'bad' : p.margem < 20 ? 'warn' : 'good';
    const marginText = p.margem !== null ? p.margem.toFixed(1) + '%' : 'S/C';
    // Market price comparison
    let marketHtml = '<span style="color:var(--text2)">-</span>';
    if (p.preco_mercado_medio) {
      const mktDiff = p.preco > 0 ? ((p.preco - p.preco_mercado_medio) / p.preco_mercado_medio * 100).toFixed(0) : 0;
      const mktColor = mktDiff > 10 ? 'var(--red)' : mktDiff < -10 ? 'var(--green)' : 'var(--text)';
      marketHtml = `<span style="color:${mktColor};font-family:monospace;">R$ ${p.preco_mercado_medio.toFixed(2)}</span>
        <span style="color:var(--text2);font-size:10px;"> (${p.mercado_fontes})</span>`;
    }
    return `<tr>
      <td class="product-name" title="${esc(p.nome)}">${esc(p.nome)}</td>
      <td class="sku">${esc(p.sku)}</td>
      <td>${esc(p.marca)}</td>
      <td style="text-align:right" class="price">R$ ${p.preco.toFixed(2)}</td>
      <td style="text-align:right">${marketHtml}</td>
      <td style="text-align:right" class="price">${p.custo > 0 ? 'R$ ' + p.custo.toFixed(2) : '<span style="color:var(--text2)">-</span>'}</td>
      <td style="text-align:right"><span class="margin ${marginClass}">${marginText}</span></td>
      <td style="text-align:center">${p.num_lojas}</td>
      <td style="text-align:center">
        <button class="btn btn-ghost btn-sm" onclick="openEditModal(${p.id_bling})">Editar</button>
      </td>
    </tr>`;
  }).join('');
}

function filterProducts() { renderProducts(); }

// =========================================================================
// PROPOSALS TABLE
// =========================================================================
async function loadProposals() {
  try {
    const status = document.getElementById('filterProposalStatus')?.value || 'all';
    const res = await fetch('/api/proposals?status=' + status);
    const data = await res.json();
    allProposals = data.proposals;
    renderProposals();
    // Update badge
    const badge = document.getElementById('proposalBadge');
    const pendCount = data.counts.pendente || 0;
    if (pendCount > 0) { badge.textContent = pendCount; badge.style.display = 'inline'; }
    else { badge.style.display = 'none'; }
  } catch(e) { console.error('loadProposals', e); }
}

function renderProposals() {
  const tbody = document.getElementById('proposalsBody');
  if (allProposals.length === 0) {
    tbody.innerHTML = '<tr><td colspan="12" class="loading">Nenhuma proposta encontrada</td></tr>';
    return;
  }

  tbody.innerHTML = allProposals.map(p => {
    const diff = p.preco_atual > 0 ? ((p.preco_sugerido - p.preco_atual) / p.preco_atual * 100).toFixed(1) : '0';
    const marginFrom = p.margem_atual !== null ? p.margem_atual.toFixed(0) + '%' : '-';
    const marginTo = p.margem_nova !== null ? p.margem_nova.toFixed(0) + '%' : '-';
    const marginToClass = p.margem_nova !== null ? (p.margem_nova < 0 ? 'bad' : p.margem_nova < 20 ? 'warn' : 'good') : 'none';
    const confPct = Math.round((p.confianca || 0) * 100);
    const confColor = confPct >= 70 ? 'var(--green)' : confPct >= 40 ? 'var(--orange)' : 'var(--red)';
    const isPending = p.status === 'pendente';
    const isEditable = p.status === 'pendente' || p.status === 'aprovado';

    // Market price display
    let marketHtml = '<span style="color:var(--text2)">-</span>';
    if (p.preco_mercado_medio) {
      const mktDiff = p.preco_atual > 0 ? ((p.preco_atual - p.preco_mercado_medio) / p.preco_mercado_medio * 100).toFixed(0) : 0;
      const mktColor = mktDiff > 10 ? 'var(--red)' : mktDiff < -10 ? 'var(--green)' : 'var(--text)';
      marketHtml = `<span style="color:${mktColor};font-weight:600;font-family:monospace;">R$ ${p.preco_mercado_medio.toFixed(2)}</span>
        <span style="color:var(--text2);font-size:10px;display:block">${p.mercado_fontes} fonte${p.mercado_fontes > 1 ? 's' : ''}</span>`;
    }

    return `<tr>
      <td class="product-name" title="${esc(p.nome)}">${esc(p.nome || '')}</td>
      <td class="sku">${esc(p.sku || '')}</td>
      <td style="text-align:right" class="price">R$ ${p.preco_atual.toFixed(2)}</td>
      <td style="text-align:center" class="arrow">&rarr;</td>
      <td style="text-align:right">
        <span class="price ${p.acao === 'increase' ? 'action-increase' : 'action-decrease'}">R$ ${p.preco_sugerido.toFixed(2)}</span>
        <span style="color:var(--text2);font-size:11px;margin-left:4px">(${diff > 0 ? '+' : ''}${diff}%)</span>
      </td>
      <td style="text-align:right">${marketHtml}</td>
      <td style="text-align:right">
        <span style="color:var(--text2)">${marginFrom}</span>
        <span class="arrow">&rarr;</span>
        <span class="margin ${marginToClass}">${marginTo}</span>
      </td>
      <td><span class="action-${p.acao}">${p.acao === 'increase' ? 'AUMENTO' : 'REDUCAO'}</span></td>
      <td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(p.motivo || '')}">${esc(p.motivo || '')}</td>
      <td style="text-align:center">
        <div class="confidence-bar">
          <div class="confidence-fill" style="width:${confPct}%;background:${confColor}"></div>
        </div>
        <span style="font-size:11px;color:var(--text2);margin-left:4px">${confPct}%</span>
      </td>
      <td><span class="status-badge status-${p.status}">${p.status}</span></td>
      <td style="text-align:center;white-space:nowrap;">
        ${isEditable ? `<button class="btn btn-ghost btn-sm" onclick="openProposalEdit(${p.id})" title="Ajustar preco">Editar</button>` : ''}
        ${isPending ? `
          <button class="btn btn-green btn-sm" onclick="approveOne(${p.id})">Aprovar</button>
          <button class="btn btn-red btn-sm" onclick="rejectOne(${p.id})">Rejeitar</button>
        ` : ''}
      </td>
    </tr>`;
  }).join('');
}

// =========================================================================
// HISTORY TABLE
// =========================================================================
async function loadHistory() {
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    const tbody = document.getElementById('historyBody');
    if (!data.history || data.history.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="loading">Nenhuma alteracao registrada</td></tr>';
      return;
    }
    tbody.innerHTML = data.history.map(h => {
      const diff = h.preco_anterior > 0 ? ((h.preco_novo - h.preco_anterior) / h.preco_anterior * 100).toFixed(1) : '0';
      const diffClass = diff > 0 ? 'action-increase' : diff < 0 ? 'action-decrease' : '';
      return `<tr>
        <td>${h.alterado_em || ''}</td>
        <td class="product-name">${esc(h.produto_nome || 'ID ' + h.id_produto)}</td>
        <td style="text-align:right" class="price">R$ ${(h.preco_anterior||0).toFixed(2)}</td>
        <td style="text-align:center" class="arrow">→</td>
        <td style="text-align:right" class="price">R$ ${(h.preco_novo||0).toFixed(2)}</td>
        <td style="text-align:right" class="${diffClass}">${diff > 0 ? '+' : ''}${diff}%</td>
        <td>${esc(h.motivo || '')}</td>
      </tr>`;
    }).join('');
  } catch(e) { console.error('loadHistory', e); }
}

// =========================================================================
// PROPOSAL ACTIONS
// =========================================================================
async function approveOne(id) {
  await fetch('/api/proposals/approve', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({id}) });
  toast('Proposta aprovada', 'success');
  loadProposals();
  loadMetrics();
}

async function rejectOne(id) {
  await fetch('/api/proposals/reject', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({id}) });
  toast('Proposta rejeitada', 'info');
  loadProposals();
  loadMetrics();
}

async function approveAll() {
  if (!confirm('Aprovar TODAS as propostas pendentes?')) return;
  const res = await fetch('/api/proposals/approve-all', { method: 'POST' });
  const data = await res.json();
  toast(`${data.count} propostas aprovadas`, 'success');
  loadProposals();
  loadMetrics();
}

async function generateProposals() {
  const btn = document.getElementById('btnGenerate');
  btn.disabled = true;
  btn.textContent = 'Gerando...';
  toast('Gerando propostas com Gemini AI... (pode levar alguns minutos)', 'info');
  try {
    const res = await fetch('/api/proposals/generate', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      toast(`${data.count} propostas geradas (${data.aumentos} aumentos, ${data.reducoes} reducoes)`, 'success');
    } else {
      toast('Erro: ' + (data.error || 'desconhecido'), 'error');
    }
  } catch(e) {
    toast('Erro ao gerar propostas', 'error');
  }
  btn.disabled = false;
  btn.textContent = 'Gerar Propostas IA';
  loadProposals();
  loadMetrics();
}

async function applyApproved() {
  if (!confirm('Aplicar todas as propostas aprovadas no Bling + WooCommerce + Google Shopping?')) return;
  const btn = document.getElementById('btnApply');
  btn.disabled = true;
  btn.textContent = 'Aplicando...';
  try {
    const res = await fetch('/api/proposals/apply', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      toast(`${data.success_count} precos aplicados com sucesso!`, 'success');
      if (data.error_count > 0) toast(`${data.error_count} erros`, 'error');
    } else {
      toast('Erro: ' + (data.error || 'desconhecido'), 'error');
    }
  } catch(e) {
    toast('Erro ao aplicar', 'error');
  }
  btn.disabled = false;
  btn.textContent = 'Aplicar Aprovadas';
  loadProposals();
  loadMetrics();
  loadProducts();
  loadHistory();
}

// =========================================================================
// EDIT MODAL
// =========================================================================
function openEditModal(idBling) {
  editingProduct = allProducts.find(p => p.id_bling === idBling);
  if (!editingProduct) return;

  document.getElementById('modalTitle').textContent = 'Ajustar Preco';
  document.getElementById('modalProductName').textContent = editingProduct.nome;
  document.getElementById('modalSku').textContent = editingProduct.sku;
  document.getElementById('modalCurrentPrice').value = 'R$ ' + editingProduct.preco.toFixed(2);
  document.getElementById('modalCost').value = editingProduct.custo > 0 ? 'R$ ' + editingProduct.custo.toFixed(2) : 'Sem custo';
  document.getElementById('modalNewPrice').value = editingProduct.preco.toFixed(2);
  updateModalMargin();

  // Load history
  fetch('/api/product/' + idBling + '/history')
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('modalHistory');
      if (!data.history || data.history.length === 0) {
        el.innerHTML = '<div style="color:var(--text2)">Sem historico</div>';
      } else {
        el.innerHTML = data.history.slice(0, 10).map(h => `
          <div class="entry">
            <span>${h.alterado_em || ''}</span>
            <span>R$ ${(h.preco_anterior||0).toFixed(2)} → R$ ${(h.preco_novo||0).toFixed(2)}</span>
            <span style="color:var(--text2)">${h.motivo || ''}</span>
          </div>
        `).join('');
      }
    });

  document.getElementById('editModal').classList.add('active');
}

function closeModal() {
  document.getElementById('editModal').classList.remove('active');
  editingProduct = null;
}

function updateModalMargin() {
  if (!editingProduct) return;
  const newPrice = parseFloat(document.getElementById('modalNewPrice').value) || 0;
  const cost = editingProduct.custo;
  const el = document.getElementById('modalMarginInfo');

  if (cost > 0 && newPrice > 0) {
    const margin = ((newPrice - cost) / newPrice * 100).toFixed(1);
    const diff = ((newPrice - editingProduct.preco) / editingProduct.preco * 100).toFixed(1);
    const color = margin < 0 ? 'var(--red)' : margin < 20 ? 'var(--orange)' : 'var(--green)';
    el.innerHTML = `Margem: <strong style="color:${color}">${margin}%</strong> | Variacao: <strong>${diff > 0 ? '+' : ''}${diff}%</strong>`;
  } else {
    el.innerHTML = 'Sem custo cadastrado para calcular margem';
  }
}

async function savePrice() {
  if (!editingProduct) return;
  const newPrice = parseFloat(document.getElementById('modalNewPrice').value);
  if (!newPrice || newPrice <= 0) { toast('Preco invalido', 'error'); return; }
  if (newPrice === editingProduct.preco) { toast('Preco nao alterado', 'info'); closeModal(); return; }

  const btn = document.getElementById('btnSave');
  btn.disabled = true;
  btn.textContent = 'Salvando...';

  try {
    const res = await fetch(`/api/product/${editingProduct.id_bling}/update-price`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ preco: newPrice })
    });
    const data = await res.json();
    if (data.ok) {
      toast(`Preco atualizado: R$ ${data.preco_anterior.toFixed(2)} → R$ ${data.preco_novo.toFixed(2)}`, 'success');
      // Update local
      editingProduct.preco = newPrice;
      if (editingProduct.custo > 0) {
        editingProduct.margem = round((newPrice - editingProduct.custo) / newPrice * 100, 1);
      }
      renderProducts();
      loadMetrics();
      loadHistory();
    } else {
      toast('Erros: ' + (data.errors || []).join(', '), 'error');
    }
  } catch(e) {
    toast('Erro ao salvar', 'error');
  }

  btn.disabled = false;
  btn.textContent = 'Salvar e Aplicar';
  closeModal();
}

// =========================================================================
// PROPOSAL EDIT MODAL
// =========================================================================
let editingProposal = null;

function openProposalEdit(propId) {
  editingProposal = allProposals.find(p => p.id === propId);
  if (!editingProposal) return;

  document.getElementById('propModalName').textContent = editingProposal.nome || 'Produto ID ' + editingProposal.id_produto;
  document.getElementById('propModalSku').textContent = editingProposal.sku || '';
  document.getElementById('propModalCurrentPrice').value = 'R$ ' + editingProposal.preco_atual.toFixed(2);
  document.getElementById('propModalCost').value = editingProposal.preco_custo > 0 ? 'R$ ' + editingProposal.preco_custo.toFixed(2) : 'S/C';
  document.getElementById('propModalMarket').value = editingProposal.preco_mercado_medio ? 'R$ ' + editingProposal.preco_mercado_medio.toFixed(2) + ' (' + editingProposal.mercado_fontes + ' fontes)' : 'Sem dados';
  document.getElementById('propModalOriginal').value = 'R$ ' + editingProposal.preco_sugerido.toFixed(2);
  document.getElementById('propModalNewPrice').value = editingProposal.preco_sugerido.toFixed(2);
  document.getElementById('propModalMotivo').textContent = editingProposal.motivo || '';
  updatePropModalMargin();

  // Show/hide approve button based on status
  document.getElementById('btnSavePropApprove').style.display = editingProposal.status === 'pendente' ? 'inline-flex' : 'none';

  document.getElementById('proposalEditModal').classList.add('active');
}

function closePropModal() {
  document.getElementById('proposalEditModal').classList.remove('active');
  editingProposal = null;
}

function updatePropModalMargin() {
  if (!editingProposal) return;
  const newPrice = parseFloat(document.getElementById('propModalNewPrice').value) || 0;
  const cost = editingProposal.preco_custo || 0;
  const el = document.getElementById('propModalMarginInfo');
  let parts = [];

  if (cost > 0 && newPrice > 0) {
    const margin = ((newPrice - cost) / newPrice * 100).toFixed(1);
    const color = margin < 0 ? 'var(--red)' : margin < 20 ? 'var(--orange)' : 'var(--green)';
    parts.push(`Margem: <strong style="color:${color}">${margin}%</strong>`);
  }
  const diffAtual = editingProposal.preco_atual > 0 ? ((newPrice - editingProposal.preco_atual) / editingProposal.preco_atual * 100).toFixed(1) : 0;
  parts.push(`vs Atual: <strong>${diffAtual > 0 ? '+' : ''}${diffAtual}%</strong>`);

  if (editingProposal.preco_mercado_medio) {
    const diffMkt = ((newPrice - editingProposal.preco_mercado_medio) / editingProposal.preco_mercado_medio * 100).toFixed(1);
    const mktColor = diffMkt > 10 ? 'var(--red)' : diffMkt < -10 ? 'var(--green)' : 'var(--text)';
    parts.push(`vs Mercado: <strong style="color:${mktColor}">${diffMkt > 0 ? '+' : ''}${diffMkt}%</strong>`);
  }
  el.innerHTML = parts.join(' | ');
}

async function savePropPrice() {
  if (!editingProposal) return;
  const newPrice = parseFloat(document.getElementById('propModalNewPrice').value);
  if (!newPrice || newPrice <= 0) { toast('Preco invalido', 'error'); return; }

  const btn = document.getElementById('btnSaveProp');
  btn.disabled = true; btn.textContent = 'Salvando...';
  try {
    const res = await fetch('/api/proposals/update-price', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ id: editingProposal.id, preco_sugerido: newPrice })
    });
    const data = await res.json();
    if (data.ok) {
      toast(`Preco ajustado para R$ ${newPrice.toFixed(2)}`, 'success');
      loadProposals();
    } else {
      toast('Erro: ' + (data.error || 'desconhecido'), 'error');
    }
  } catch(e) { toast('Erro ao salvar', 'error'); }
  btn.disabled = false; btn.textContent = 'Salvar Ajuste';
  closePropModal();
}

async function savePropPriceAndApprove() {
  if (!editingProposal) return;
  const newPrice = parseFloat(document.getElementById('propModalNewPrice').value);
  if (!newPrice || newPrice <= 0) { toast('Preco invalido', 'error'); return; }

  const btn = document.getElementById('btnSavePropApprove');
  btn.disabled = true; btn.textContent = 'Salvando...';
  try {
    // Update price first
    await fetch('/api/proposals/update-price', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ id: editingProposal.id, preco_sugerido: newPrice })
    });
    // Then approve
    await fetch('/api/proposals/approve', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ id: editingProposal.id })
    });
    toast(`Proposta ajustada para R$ ${newPrice.toFixed(2)} e aprovada`, 'success');
    loadProposals();
    loadMetrics();
  } catch(e) { toast('Erro ao salvar/aprovar', 'error'); }
  btn.disabled = false; btn.textContent = 'Salvar e Aprovar';
  closePropModal();
}

// =========================================================================
// HELPERS
// =========================================================================
function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
function round(n, d) { return Math.round(n * Math.pow(10,d)) / Math.pow(10,d); }

// Close modal on overlay click
document.getElementById('editModal').addEventListener('click', e => {
  if (e.target === document.getElementById('editModal')) closeModal();
});
document.getElementById('proposalEditModal').addEventListener('click', e => {
  if (e.target === document.getElementById('proposalEditModal')) closePropModal();
});

// Close modal on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closeModal(); closePropModal(); }
});
</script>

</body>
</html>"""


@app.route("/api/history")
def api_history():
    """Historico global de alteracoes de preco."""
    db = VaultDB()
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.*, p.nome as produto_nome, p.codigo
        FROM historico_precos h
        LEFT JOIN produtos p ON h.id_produto = p.id_bling
        ORDER BY h.alterado_em DESC
        LIMIT 200
    """)
    rows = cursor.fetchall()
    return jsonify({"history": [dict(r) for r in rows]})


@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


# =========================================================================
# MAIN
# =========================================================================

if __name__ == "__main__":
    print("\n  Pricing Dashboard: http://localhost:5001\n")
    app.run(host="0.0.0.0", port=5001, debug=False)
