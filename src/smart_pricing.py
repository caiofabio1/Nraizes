"""
NRAIZES - Smart Pricing Module
Pipeline completo de ajuste inteligente de preços:
  1. Coleta dados de vendas (WooCommerce) + analytics (GA4) + concorrentes
  2. Analisa com Gemini AI (flash para triagem, pro para decisões)
  3. Gera propostas de preço para aprovação
  4. Aplica propostas aprovadas em Bling + WooCommerce (multi-loja)
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from database import VaultDB, get_connection
from bling_client import BlingClient
from woo_client import WooClient
from price_adjuster import PriceAdjuster, PriceRecommendation, PriceAction
from logger import get_logger

_logger = get_logger(__name__)

# Constants
BLING_WOO_STORE_ID = 205326820
BLING_GOOGLE_SHOPPING_STORE_ID = 205282664
GA4_PROPERTY_ID = "448522931"

# =========================================================================
# DATA COLLECTORS
# =========================================================================


class SalesDataCollector:
    """Coleta dados de vendas do WooCommerce."""

    def __init__(self):
        try:
            self.woo = WooClient()
            self._available = True
        except Exception as e:
            _logger.warning(f"WooCommerce not available: {e}")
            self._available = False

    def get_sales_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Busca resumo de vendas dos últimos N dias.
        Returns dict com: total_pedidos, receita_total, ticket_medio, produtos_vendidos (top 20)
        """
        if not self._available:
            return {"error": "WooCommerce not configured", "pedidos": [], "resumo": {}}

        after_date = (datetime.now() - timedelta(days=days)).strftime(
            "%Y-%m-%dT00:00:00"
        )
        all_orders = []
        page = 1

        try:
            while page <= 10:  # Max 1000 orders
                orders = self.woo.get_orders(
                    per_page=100,
                    page=page,
                    after=after_date,
                    status="completed,processing",
                )
                if not orders:
                    break
                all_orders.extend(orders)
                if len(orders) < 100:
                    break
                page += 1
                time.sleep(0.3)
        except Exception as e:
            _logger.error(f"Error fetching WooCommerce orders: {e}")
            return {"error": str(e), "pedidos": [], "resumo": {}}

        # Processar vendas por produto (SKU)
        produto_vendas = {}
        receita_total = 0
        for order in all_orders:
            order_total = float(order.get("total", 0))
            receita_total += order_total
            for item in order.get("line_items", []):
                sku = item.get("sku", "")
                if not sku:
                    continue
                if sku not in produto_vendas:
                    produto_vendas[sku] = {
                        "sku": sku,
                        "nome": item.get("name", ""),
                        "qtd_vendida": 0,
                        "receita": 0,
                        "pedidos": 0,
                    }
                produto_vendas[sku]["qtd_vendida"] += item.get("quantity", 0)
                produto_vendas[sku]["receita"] += float(item.get("total", 0))
                produto_vendas[sku]["pedidos"] += 1

        # Top 20 por receita
        top_produtos = sorted(
            produto_vendas.values(), key=lambda x: x["receita"], reverse=True
        )[:20]

        resumo = {
            "periodo_dias": days,
            "total_pedidos": len(all_orders),
            "receita_total": round(receita_total, 2),
            "ticket_medio": round(receita_total / len(all_orders), 2)
            if all_orders
            else 0,
        }

        _logger.info(
            f"WooCommerce: {resumo['total_pedidos']} pedidos, "
            f"R${resumo['receita_total']:.2f} receita, "
            f"ticket médio R${resumo['ticket_medio']:.2f}"
        )

        return {
            "resumo": resumo,
            "top_produtos": top_produtos,
            "vendas_por_sku": produto_vendas,
        }


class AnalyticsCollector:
    """Coleta dados do Google Analytics 4."""

    def __init__(self):
        self._available = False
        self._client = None
        try:
            cred_path = os.environ.get(
                "GOOGLE_APPLICATION_CREDENTIALS",
                r"C:\Users\caiof\AppData\Roaming\gcloud\application_default_credentials.json",
            )
            if os.path.exists(cred_path):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
                from google.analytics.data_v1beta import BetaAnalyticsDataClient
                from google.analytics.data_v1beta.types import (
                    RunReportRequest,
                    DateRange,
                    Metric,
                    Dimension,
                )
                import google.auth

                self._types = type(
                    "GA4Types",
                    (),
                    {
                        "RunReportRequest": RunReportRequest,
                        "DateRange": DateRange,
                        "Metric": Metric,
                        "Dimension": Dimension,
                    },
                )
                scopes = ["https://www.googleapis.com/auth/analytics.readonly"]
                credentials, project = google.auth.default(
                    scopes=scopes, quota_project_id="novas-raizes"
                )
                self._client = BetaAnalyticsDataClient(credentials=credentials)
                self._available = True
                _logger.info("GA4 Analytics client initialized")
        except Exception as e:
            _logger.warning(f"GA4 Analytics not available: {e}")

    def get_traffic_summary(self, days: int = 30) -> Dict[str, Any]:
        """Busca resumo de tráfego e conversão dos últimos N dias."""
        if not self._available:
            return {"error": "GA4 not configured"}

        try:
            t = self._types
            # Main traffic metrics
            request = t.RunReportRequest(
                property=f"properties/{GA4_PROPERTY_ID}",
                dimensions=[t.Dimension(name="date")],
                metrics=[
                    t.Metric(name="activeUsers"),
                    t.Metric(name="sessions"),
                    t.Metric(name="transactions"),
                    t.Metric(name="purchaseRevenue"),
                    t.Metric(name="ecommercePurchases"),
                ],
                date_ranges=[
                    t.DateRange(start_date=f"{days}daysAgo", end_date="today")
                ],
            )
            response = self._client.run_report(request=request)

            total_users = 0
            total_sessions = 0
            total_transactions = 0
            total_revenue = 0

            for row in response.rows:
                total_users += int(float(row.metric_values[0].value))
                total_sessions += int(float(row.metric_values[1].value))
                total_transactions += int(float(row.metric_values[2].value))
                total_revenue += float(row.metric_values[3].value)

            conversion_rate = (
                (total_transactions / total_sessions * 100) if total_sessions > 0 else 0
            )

            # Top pages by pageviews
            pages_request = t.RunReportRequest(
                property=f"properties/{GA4_PROPERTY_ID}",
                dimensions=[t.Dimension(name="pagePath")],
                metrics=[
                    t.Metric(name="screenPageViews"),
                    t.Metric(name="activeUsers"),
                ],
                date_ranges=[
                    t.DateRange(start_date=f"{days}daysAgo", end_date="today")
                ],
            )
            pages_response = self._client.run_report(request=pages_request)

            top_pages = []
            for row in pages_response.rows[:20]:
                path = row.dimension_values[0].value
                if "/produto/" in path or "/product/" in path:
                    top_pages.append(
                        {
                            "path": path,
                            "views": int(float(row.metric_values[0].value)),
                            "users": int(float(row.metric_values[1].value)),
                        }
                    )

            result = {
                "periodo_dias": days,
                "usuarios": total_users,
                "sessoes": total_sessions,
                "transacoes": total_transactions,
                "receita_ga4": round(total_revenue, 2),
                "taxa_conversao": round(conversion_rate, 2),
                "top_paginas_produto": top_pages[:10],
            }

            _logger.info(
                f"GA4: {total_users} users, {total_sessions} sessions, "
                f"{conversion_rate:.2f}% conversion, R${total_revenue:.2f} revenue"
            )
            return result

        except Exception as e:
            _logger.error(f"GA4 error: {e}")
            return {"error": str(e)}


# =========================================================================
# GEMINI PRICE ANALYZER
# =========================================================================


class GeminiPriceAnalyzer:
    """Usa Gemini AI para análise de preços e geração de recomendações."""

    def __init__(self):
        from google import genai
        from google.genai import types as genai_types
        from dotenv import load_dotenv

        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cred_path = os.path.join(PROJECT_ROOT, ".credentials", "bling_api_tokens.env")
        load_dotenv(cred_path)

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")

        self.client = genai.Client(api_key=api_key)
        self._types = genai_types
        # Flash for quick batch analysis, Pro for strategic decisions
        self.flash_model = "gemini-3-flash-preview"
        self.pro_model = "gemini-3-pro-preview"

    def analyze_product_prices(
        self,
        produtos: List[Dict],
        vendas: Dict,
        analytics: Dict,
        concorrentes: Dict,
    ) -> List[Dict]:
        """
        Analisa preços de múltiplos produtos usando Gemini Flash.

        Returns:
            List of dicts with: id_produto, preco_sugerido, acao, motivo, confianca
        """
        if not produtos:
            return []

        # Build compact product summary for the prompt
        product_lines = []
        for p in produtos[:50]:  # Limit to 50 per batch
            sku = p.get("codigo", "?")
            nome = p.get("nome", "?")[:40]
            preco = p.get("preco", 0)
            custo = p.get("preco_custo", 0) or 0
            margem = (
                ((preco - custo) / preco * 100) if preco > 0 and custo > 0 else None
            )

            # Sales data for this product
            venda_info = vendas.get("vendas_por_sku", {}).get(sku, {})
            qtd_vendida = venda_info.get("qtd_vendida", 0)
            receita_sku = venda_info.get("receita", 0)

            # Competitor data
            conc_info = concorrentes.get(str(p.get("id_bling")), {})
            preco_mercado = conc_info.get("media") if conc_info else None

            line = f"SKU:{sku} | {nome} | R${preco:.2f}"
            if custo > 0:
                line += f" (custo R${custo:.2f}, margem {margem:.0f}%)"
            if qtd_vendida > 0:
                line += f" | {qtd_vendida}un vendidas (R${receita_sku:.2f})"
            else:
                line += " | sem vendas recentes"
            if preco_mercado:
                diff = (preco - preco_mercado) / preco_mercado * 100
                line += f" | mercado R${preco_mercado:.2f} ({diff:+.0f}%)"

            product_lines.append(line)

        # Analytics summary
        analytics_text = ""
        if analytics and "error" not in analytics:
            analytics_text = f"""
TRÁFEGO (últimos {analytics.get("periodo_dias", 30)} dias):
- {analytics.get("usuarios", "N/D")} usuários, {analytics.get("sessoes", "N/D")} sessões
- Taxa de conversão: {analytics.get("taxa_conversao", "N/D")}%
- Receita GA4: R${analytics.get("receita_ga4", 0):.2f}
"""

        vendas_text = ""
        if vendas.get("resumo"):
            r = vendas["resumo"]
            vendas_text = f"""
VENDAS ({r.get("periodo_dias", 30)} dias):
- {r.get("total_pedidos", 0)} pedidos, receita R${r.get("receita_total", 0):.2f}
- Ticket médio: R${r.get("ticket_medio", 0):.2f}
"""

        prompt = f"""Você é um especialista em pricing para e-commerce de produtos naturais/MTC no Brasil.

{vendas_text}
{analytics_text}

REGRAS DE PRECIFICAÇÃO:
- Margem mínima: 20% sobre custo
- Ajuste máximo por vez: 15% do preço atual
- Cooldown: produtos ajustados nos últimos 3 dias não devem ser reajustados
- Se sem dados de custo, NÃO sugerir redução abaixo de 70% do preço atual
- Priorizar aumento de preços em produtos com vendas fortes e preço abaixo do mercado
- Reduzir preços apenas quando SIGNIFICATIVAMENTE acima do mercado (>15%)

PRODUTOS:
{chr(10).join(product_lines)}

TAREFA:
Analise cada produto e retorne APENAS os que precisam de ajuste (ignore os que estão ok).
Para cada produto que precisa ajuste, retorne:

Responda SOMENTE em JSON válido (array):
[
  {{
    "sku": "...",
    "preco_sugerido": 99.90,
    "acao": "increase" ou "decrease",
    "motivo": "Explicação curta em português",
    "confianca": 0.0 a 1.0
  }}
]

Se nenhum produto precisa ajuste, retorne: []
"""

        try:
            response = self.client.models.generate_content(
                model=self.flash_model,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=16384,
                    response_mime_type="application/json",
                ),
            )
            text = response.text or ""

            import re

            # Extract JSON from code fences first (```json ... ```)
            fence_match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
            if fence_match:
                try:
                    results = json.loads(fence_match.group(1))
                    _logger.info(
                        f"Gemini suggested {len(results)} price changes (from code fence)"
                    )
                    return results
                except json.JSONDecodeError:
                    pass

            # Try to find any JSON array in the response (greedy last match)
            # Use findall to get the last/largest array match
            all_arrays = re.findall(r"\[[\s\S]*?\]", text)
            for arr_text in reversed(all_arrays):
                try:
                    results = json.loads(arr_text)
                    if isinstance(results, list):
                        _logger.info(f"Gemini suggested {len(results)} price changes")
                        return results
                except json.JSONDecodeError:
                    continue

            # Empty response means no adjustments needed
            if "[]" in text or not text.strip():
                _logger.info("Gemini says no adjustments needed for this batch")
                return []

            _logger.warning(
                f"Gemini returned no parseable JSON array. Response tail: {text[-500:]}"
            )
            return []

            _logger.warning(f"Gemini returned no JSON array. Response: {text[:300]}")
            return []

            _logger.warning(f"Gemini returned no JSON array. Response: {text[:300]}")
            return []

        except Exception as e:
            _logger.error(f"Gemini analysis error: {e}")
            return []

    def strategic_summary(
        self, proposals: List[Dict], vendas: Dict, analytics: Dict
    ) -> str:
        """
        Gera resumo estratégico das propostas usando Gemini Pro.
        Returns markdown string.
        """
        if not proposals:
            return "Nenhuma proposta de preço pendente."

        aumentos = [p for p in proposals if p.get("acao") == "increase"]
        reducoes = [p for p in proposals if p.get("acao") == "decrease"]

        prompt = f"""Você é consultor de pricing para loja de produtos naturais.

PROPOSTAS GERADAS:
- {len(aumentos)} aumentos de preço
- {len(reducoes)} reduções de preço

Top 5 aumentos: {json.dumps(aumentos[:5], ensure_ascii=False)}
Top 5 reduções: {json.dumps(reducoes[:5], ensure_ascii=False)}

VENDAS: {json.dumps(vendas.get("resumo", {}), ensure_ascii=False)}

Gere um resumo executivo de 3-5 linhas em português sobre o impacto esperado dessas mudanças.
Inclua estimativa de impacto na margem e receita.
"""

        try:
            response = self.client.models.generate_content(
                model=self.pro_model,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=1024,
                ),
            )
            return response.text
        except Exception as e:
            _logger.error(f"Gemini strategic summary error: {e}")
            return f"Erro ao gerar resumo: {e}"


# =========================================================================
# SMART PRICING PIPELINE
# =========================================================================


class SmartPricingPipeline:
    """
    Pipeline completo:
      collect -> analyze -> propose -> [approve] -> apply
    """

    def __init__(self):
        self.db = VaultDB()
        self.adjuster = PriceAdjuster()

    def collect_all_data(self, days: int = 30) -> Dict[str, Any]:
        """Step 1: Collect data from all sources."""
        _logger.info("=== COLLECTING DATA ===")

        # 1. Sales from WooCommerce
        _logger.info("Collecting WooCommerce sales...")
        sales_collector = SalesDataCollector()
        vendas = sales_collector.get_sales_summary(days=days)

        # 2. Analytics from GA4
        _logger.info("Collecting GA4 analytics...")
        analytics_collector = AnalyticsCollector()
        analytics = analytics_collector.get_traffic_summary(days=days)

        # 3. Competitor prices from DB (already collected by price_monitor)
        _logger.info("Loading competitor prices from DB...")
        conn = get_connection()
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute(
            """
            SELECT id_produto, AVG(preco) as media, MIN(preco) as min, MAX(preco) as max, 
                   COUNT(*) as num_fontes
            FROM precos_concorrentes 
            WHERE coletado_em > ? AND disponivel = 1
            GROUP BY id_produto
        """,
            (cutoff,),
        )
        concorrentes = {}
        for row in cursor.fetchall():
            concorrentes[str(row["id_produto"])] = {
                "media": row["media"],
                "min": row["min"],
                "max": row["max"],
                "num_fontes": row["num_fontes"],
            }

        _logger.info(f"Competitor data for {len(concorrentes)} products")

        return {
            "vendas": vendas,
            "analytics": analytics,
            "concorrentes": concorrentes,
            "collected_at": datetime.now().isoformat(),
        }

    def generate_proposals(
        self, data: Dict = None, use_gemini: bool = True
    ) -> List[Dict]:
        """
        Step 2: Generate price change proposals.
        Combines rule-based analysis (PriceAdjuster) with Gemini AI.
        """
        _logger.info("=== GENERATING PROPOSALS ===")

        if data is None:
            data = self.collect_all_data()

        # Clear old pending proposals
        cleared = self.db.limpar_propostas_pendentes()
        if cleared:
            _logger.info(f"Cleared {cleared} old pending proposals")

        # Get all active products
        produtos = self.db.get_all_produtos_ativos()
        _logger.info(f"Analyzing {len(produtos)} active products")

        proposals = []

        # === Method 1: Rule-based (PriceAdjuster) ===
        _logger.info("Running rule-based analysis...")
        rule_recs = self.adjuster.analisar_todos(apenas_com_dados=True)
        rule_changes = [r for r in rule_recs if r.acao != PriceAction.MAINTAIN]

        for rec in rule_changes:
            produto = self.db.get_produto_by_bling_id(rec.id_produto)
            preco_custo = produto.get("preco_custo", 0) if produto else 0

            proposta = {
                "id_produto": rec.id_produto,
                "preco_atual": rec.preco_atual,
                "preco_sugerido": rec.preco_sugerido,
                "preco_custo": preco_custo,
                "margem_atual": self._calc_margem(rec.preco_atual, preco_custo),
                "margem_nova": self._calc_margem(rec.preco_sugerido, preco_custo),
                "acao": rec.acao.value,
                "motivo": rec.motivo,
                "fonte_dados": f"regra ({rec.fonte_dados})",
                "dados_analise": json.dumps(
                    {"confianca_regra": rec.confianca}, ensure_ascii=False
                ),
                "confianca": rec.confianca,
            }
            proposals.append(proposta)

        _logger.info(f"Rule-based: {len(proposals)} proposals")

        # === Method 2: Gemini AI ===
        if use_gemini:
            _logger.info("Running Gemini AI analysis...")
            try:
                gemini = GeminiPriceAnalyzer()
                # Only send products NOT already covered by rule-based
                rule_ids = {r.id_produto for r in rule_changes}
                remaining = [p for p in produtos if p.get("id_bling") not in rule_ids]

                # Batch in groups of 50
                for i in range(0, len(remaining), 50):
                    batch = remaining[i : i + 50]
                    ai_results = gemini.analyze_product_prices(
                        batch,
                        data.get("vendas", {}),
                        data.get("analytics", {}),
                        data.get("concorrentes", {}),
                    )

                    # Match AI results back to products
                    sku_map = {p.get("codigo"): p for p in batch}
                    for ai_rec in ai_results:
                        sku = ai_rec.get("sku")
                        produto = sku_map.get(sku)
                        if not produto:
                            continue

                        preco_custo = produto.get("preco_custo", 0) or 0
                        preco_atual = produto.get("preco", 0)
                        preco_sugerido = ai_rec.get("preco_sugerido", preco_atual)

                        # Safety check: respect max swing
                        max_swing = preco_atual * 0.15
                        if abs(preco_sugerido - preco_atual) > max_swing:
                            if preco_sugerido > preco_atual:
                                preco_sugerido = round(preco_atual + max_swing, 2)
                            else:
                                preco_sugerido = round(preco_atual - max_swing, 2)

                        # Safety check: respect min margin
                        if preco_custo > 0:
                            preco_minimo = preco_custo * 1.2  # 20% min margin
                            preco_sugerido = max(preco_sugerido, preco_minimo)

                        proposta = {
                            "id_produto": produto["id_bling"],
                            "preco_atual": preco_atual,
                            "preco_sugerido": round(preco_sugerido, 2),
                            "preco_custo": preco_custo,
                            "margem_atual": self._calc_margem(preco_atual, preco_custo),
                            "margem_nova": self._calc_margem(
                                preco_sugerido, preco_custo
                            ),
                            "acao": ai_rec.get("acao", "maintain"),
                            "motivo": ai_rec.get("motivo", "Sugestão IA"),
                            "fonte_dados": "gemini_flash",
                            "dados_analise": json.dumps(ai_rec, ensure_ascii=False),
                            "confianca": ai_rec.get("confianca", 0.5),
                        }

                        # Skip if no real change
                        if abs(preco_sugerido - preco_atual) < 0.50:
                            continue

                        proposals.append(proposta)

                    if i + 50 < len(remaining):
                        time.sleep(1)  # Rate limit between batches

            except Exception as e:
                _logger.error(
                    f"Gemini analysis failed (continuing with rule-based only): {e}"
                )

        # === Save proposals to DB ===
        _logger.info(f"Saving {len(proposals)} proposals to database...")
        saved = 0
        for p in proposals:
            try:
                self.db.criar_proposta_preco(p)
                saved += 1
            except Exception as e:
                _logger.error(
                    f"Failed to save proposal for product {p.get('id_produto')}: {e}"
                )

        _logger.info(f"Saved {saved}/{len(proposals)} proposals")
        return proposals

    def apply_approved(self, sync_bling: bool = True, sync_woo: bool = True) -> Dict:
        """
        Step 3: Apply approved proposals to Bling and WooCommerce.

        Returns:
            Dict with success_count, error_count, details
        """
        _logger.info("=== APPLYING APPROVED PROPOSALS ===")

        approved = self.db.listar_propostas_preco(status="aprovado")
        if not approved:
            _logger.info("No approved proposals to apply")
            return {"success_count": 0, "error_count": 0, "details": []}

        _logger.info(f"Applying {len(approved)} approved proposals")

        bling = None
        woo = None

        if sync_bling:
            try:
                bling = BlingClient()
            except Exception as e:
                _logger.error(f"Failed to init BlingClient: {e}")

        if sync_woo:
            try:
                woo = WooClient()
            except Exception as e:
                _logger.error(f"Failed to init WooClient: {e}")

        success_count = 0
        error_count = 0
        details = []

        for proposta in approved:
            id_produto = proposta["id_produto"]
            preco_novo = proposta["preco_sugerido"]
            preco_anterior = proposta["preco_atual"]
            lojas_aplicadas = {}

            try:
                # 1. Update base price in Bling
                if bling:
                    bling.patch_produtos_id_produto(
                        str(id_produto), {"preco": preco_novo}
                    )
                    lojas_aplicadas["bling_base"] = True
                    _logger.info(
                        f"Bling base: {proposta.get('produto_nome', id_produto)[:30]} "
                        f"R${preco_anterior:.2f} -> R${preco_novo:.2f}"
                    )
                    time.sleep(0.35)  # Rate limit (3 req/s)

                # 2. Update WooCommerce store link price in Bling
                if bling:
                    try:
                        links = bling.get_all_produtos_lojas(
                            idProduto=id_produto, idLoja=BLING_WOO_STORE_ID
                        )
                        if links:
                            link_id = links[0].get("id")
                            bling.put_produtos_lojas_id(
                                str(link_id),
                                {"idProdutoLoja": link_id, "preco": preco_novo},
                            )
                            lojas_aplicadas["woocommerce_bling"] = True
                            time.sleep(0.35)
                    except Exception as e:
                        _logger.warning(
                            f"Failed to update WooCommerce link in Bling for {id_produto}: {e}"
                        )

                # 2b. Update Google Shopping store link price in Bling
                if bling:
                    try:
                        links_gs = bling.get_all_produtos_lojas(
                            idProduto=id_produto, idLoja=BLING_GOOGLE_SHOPPING_STORE_ID
                        )
                        if links_gs:
                            link_id_gs = links_gs[0].get("id")
                            bling.put_produtos_lojas_id(
                                str(link_id_gs),
                                {"idProdutoLoja": link_id_gs, "preco": preco_novo},
                            )
                            lojas_aplicadas["google_shopping_bling"] = True
                            time.sleep(0.35)
                    except Exception as e:
                        _logger.warning(
                            f"Failed to update Google Shopping link in Bling for {id_produto}: {e}"
                        )

                # 3. Update WooCommerce directly (via WC API) if product has WC ID
                if woo:
                    try:
                        # Find WC product by SKU
                        produto = self.db.get_produto_by_bling_id(id_produto)
                        sku = produto.get("codigo") if produto else None
                        if sku:
                            wc_products = woo.get_products(per_page=1, sku=sku)
                            if wc_products:
                                wc_id = wc_products[0]["id"]
                                woo.update_product(
                                    wc_id,
                                    {
                                        "regular_price": str(preco_novo),
                                    },
                                )
                                lojas_aplicadas["woocommerce_direct"] = True
                                time.sleep(0.3)
                    except Exception as e:
                        _logger.warning(
                            f"Failed to update WooCommerce directly for {id_produto}: {e}"
                        )

                # 4. Record in history
                self.db.registrar_alteracao_preco(
                    id_produto=id_produto,
                    preco_anterior=preco_anterior,
                    preco_novo=preco_novo,
                    motivo=f"smart_pricing: {proposta.get('motivo', '')}",
                )

                # 5. Mark as applied
                self.db.marcar_proposta_aplicada(
                    proposta["id"], json.dumps(lojas_aplicadas)
                )

                success_count += 1
                details.append(
                    {
                        "id_produto": id_produto,
                        "nome": proposta.get("produto_nome", ""),
                        "preco_anterior": preco_anterior,
                        "preco_novo": preco_novo,
                        "lojas": lojas_aplicadas,
                        "status": "ok",
                    }
                )

            except Exception as e:
                error_count += 1
                _logger.error(
                    f"Failed to apply proposal {proposta['id']} for product {id_produto}: {e}"
                )
                details.append(
                    {
                        "id_produto": id_produto,
                        "nome": proposta.get("produto_nome", ""),
                        "status": "error",
                        "error": str(e),
                    }
                )

        result = {
            "success_count": success_count,
            "error_count": error_count,
            "total": len(approved),
            "details": details,
        }

        _logger.info(
            f"Applied: {success_count} ok, {error_count} errors out of {len(approved)}"
        )
        return result

    def run_full_pipeline(
        self, days: int = 30, use_gemini: bool = True, auto_apply: bool = False
    ) -> Dict:
        """
        Run the complete pipeline:
        1. Collect data
        2. Generate proposals
        3. (Optional) Auto-apply high-confidence proposals

        Returns summary dict.
        """
        _logger.info("========================================")
        _logger.info("  SMART PRICING PIPELINE - START")
        _logger.info("========================================")

        # Step 1: Collect
        data = self.collect_all_data(days=days)

        # Step 2: Generate proposals
        proposals = self.generate_proposals(data=data, use_gemini=use_gemini)

        # Step 3: Auto-apply if requested (only high confidence)
        applied = None
        if auto_apply and proposals:
            # Auto-approve high confidence ones
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE propostas_preco 
                SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
                WHERE status = 'pendente' AND confianca >= 0.8
            """
            )
            auto_approved = cursor.rowcount
            conn.commit()
            _logger.info(f"Auto-approved {auto_approved} high-confidence proposals")

            if auto_approved > 0:
                applied = self.apply_approved()

        # Summary
        aumentos = [p for p in proposals if p.get("acao") == "increase"]
        reducoes = [p for p in proposals if p.get("acao") == "decrease"]

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_proposals": len(proposals),
            "aumentos": len(aumentos),
            "reducoes": len(reducoes),
            "vendas": data.get("vendas", {}).get("resumo", {}),
            "analytics": {
                k: v
                for k, v in data.get("analytics", {}).items()
                if k != "top_paginas_produto"
            },
            "applied": applied,
        }

        _logger.info("========================================")
        _logger.info(f"  PIPELINE COMPLETE: {len(proposals)} proposals generated")
        _logger.info("========================================")

        return summary

    @staticmethod
    def _calc_margem(preco: float, custo: float) -> Optional[float]:
        """Calculate margin percentage."""
        if not preco or not custo or preco <= 0 or custo <= 0:
            return None
        return round((preco - custo) / preco * 100, 1)


# =========================================================================
# CLI INTERFACE
# =========================================================================


def main():
    """CLI for smart pricing pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description="NRAIZES Smart Pricing")
    subparsers = parser.add_subparsers(dest="command")

    # collect
    sub = subparsers.add_parser("collect", help="Collect data from all sources")
    sub.add_argument("--days", type=int, default=30)

    # analyze
    sub = subparsers.add_parser("analyze", help="Generate price proposals")
    sub.add_argument("--days", type=int, default=30)
    sub.add_argument("--no-gemini", action="store_true")

    # apply
    sub = subparsers.add_parser("apply", help="Apply approved proposals")
    sub.add_argument("--no-bling", action="store_true")
    sub.add_argument("--no-woo", action="store_true")

    # full
    sub = subparsers.add_parser("full", help="Run full pipeline")
    sub.add_argument("--days", type=int, default=30)
    sub.add_argument("--no-gemini", action="store_true")
    sub.add_argument("--auto-apply", action="store_true")

    # status
    subparsers.add_parser("status", help="Show current proposals status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    pipeline = SmartPricingPipeline()

    if args.command == "collect":
        data = pipeline.collect_all_data(days=args.days)
        print(
            json.dumps(
                data.get("vendas", {}).get("resumo", {}), indent=2, ensure_ascii=False
            )
        )
        print(
            json.dumps(
                {
                    k: v
                    for k, v in data.get("analytics", {}).items()
                    if k != "top_paginas_produto"
                },
                indent=2,
                ensure_ascii=False,
            )
        )

    elif args.command == "analyze":
        proposals = pipeline.generate_proposals(use_gemini=not args.no_gemini)
        aumentos = [p for p in proposals if p.get("acao") == "increase"]
        reducoes = [p for p in proposals if p.get("acao") == "decrease"]
        print(f"\nPropostas geradas: {len(proposals)}")
        print(f"  Aumentos: {len(aumentos)}")
        print(f"  Reduções: {len(reducoes)}")
        print(f"\nAcesse o dashboard em http://localhost:5000 para revisar e aprovar.")

    elif args.command == "apply":
        result = pipeline.apply_approved(
            sync_bling=not args.no_bling,
            sync_woo=not args.no_woo,
        )
        print(
            f"\nResultado: {result['success_count']} aplicados, {result['error_count']} erros"
        )

    elif args.command == "full":
        summary = pipeline.run_full_pipeline(
            days=args.days,
            use_gemini=not args.no_gemini,
            auto_apply=args.auto_apply,
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

    elif args.command == "status":
        db = VaultDB()
        pendentes = db.listar_propostas_preco("pendente")
        aprovados = db.listar_propostas_preco("aprovado")
        aplicados = db.listar_propostas_preco("aplicado")
        rejeitados = db.listar_propostas_preco("rejeitado")

        print(f"Propostas de Preço:")
        print(f"  Pendentes:  {len(pendentes)}")
        print(f"  Aprovados:  {len(aprovados)}")
        print(f"  Aplicados:  {len(aplicados)}")
        print(f"  Rejeitados: {len(rejeitados)}")

        if pendentes:
            print(f"\nTop 10 pendentes:")
            for p in pendentes[:10]:
                nome = p.get("produto_nome", "?")[:30]
                print(
                    f"  {p['acao'].upper():8s} {nome:32s} "
                    f"R${p['preco_atual']:.2f} -> R${p['preco_sugerido']:.2f} "
                    f"({p.get('confianca', 0):.0%} confiança)"
                )


if __name__ == "__main__":
    main()
