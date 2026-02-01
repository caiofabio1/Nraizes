"""
Bling Optimizer - Strategic Dashboard Module
Coleta métricas do negócio e gera análises estratégicas com Gemini Pro.
"""

import os
import json
import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

from database import get_connection, VaultDB
from price_adjuster import PriceAdjuster

# Load API keys
cred_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), ".credentials", "bling_api_tokens.env"
)
load_dotenv(cred_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class MetricsCollector:
    """Coleta métricas de várias fontes para o dashboard."""

    def __init__(self):
        self.db = VaultDB()

    def collect_daily_metrics(self) -> Dict[str, Any]:
        """Coleta métricas do dia atual."""
        conn = get_connection()
        cursor = conn.cursor()

        metrics = {
            "data": date.today().isoformat(),
            "coletado_em": datetime.now().isoformat(),
        }

        # Produtos ativos
        cursor.execute('SELECT COUNT(*) as total FROM produtos WHERE situacao = "A"')
        metrics["produtos_ativos"] = cursor.fetchone()["total"]

        # Produtos sem estoque (preço = 0 ou NULL como proxy)
        cursor.execute(
            'SELECT COUNT(*) as total FROM produtos WHERE situacao = "A" AND (preco IS NULL OR preco = 0)'
        )
        metrics["produtos_sem_estoque"] = cursor.fetchone()["total"]

        # Propostas pendentes
        cursor.execute(
            'SELECT COUNT(*) as total FROM propostas_ia WHERE status = "pendente"'
        )
        metrics["propostas_pendentes"] = cursor.fetchone()["total"]

        # Produtos sem EAN (gtin NULL)
        cursor.execute(
            'SELECT COUNT(*) as total FROM produtos WHERE situacao = "A" AND (gtin IS NULL OR gtin = "")'
        )
        row = cursor.fetchone()
        metrics["produtos_sem_ean"] = row["total"] if row else 0

        # Alertas de preço pendentes
        cursor.execute(
            'SELECT COUNT(*) as total FROM alertas_preco WHERE status = "pendente"'
        )
        row = cursor.fetchone()
        metrics["alertas_preco_pendentes"] = row["total"] if row else 0

        # Preços coletados (últimos 7 dias)
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute(
            "SELECT COUNT(DISTINCT id_produto) as total FROM precos_concorrentes WHERE coletado_em > ?",
            (cutoff,),
        )
        row = cursor.fetchone()
        metrics["produtos_com_preco_mercado"] = row["total"] if row else 0

        # Margem média (se tiver preço de custo)
        cursor.execute("""
            SELECT AVG((preco - preco_custo) / preco * 100) as margem_media 
            FROM produtos 
            WHERE situacao = "A" AND preco > 0 AND preco_custo > 0
        """)
        row = cursor.fetchone()
        metrics["margem_media"] = (
            round(row["margem_media"], 1) if row and row["margem_media"] else None
        )

        conn.close()
        return metrics

    def save_snapshot(self, metrics: Dict[str, Any]) -> int:
        """Salva snapshot de métricas no banco."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO metricas_snapshot 
            (data, produtos_ativos, produtos_sem_estoque, propostas_pendentes, 
             produtos_sem_ean, alertas_margem, margem_media)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                metrics.get("data"),
                metrics.get("produtos_ativos"),
                metrics.get("produtos_sem_estoque"),
                metrics.get("propostas_pendentes"),
                metrics.get("produtos_sem_ean"),
                metrics.get("alertas_preco_pendentes"),
                metrics.get("margem_media"),
            ),
        )

        conn.commit()
        snapshot_id = cursor.lastrowid
        conn.close()

        return snapshot_id

    def get_history(self, days: int = 30) -> List[Dict]:
        """Retorna histórico de snapshots."""
        conn = get_connection()
        cursor = conn.cursor()

        cutoff = (date.today() - timedelta(days=days)).isoformat()

        cursor.execute(
            """
            SELECT * FROM metricas_snapshot 
            WHERE data > ? 
            ORDER BY data DESC
        """,
            (cutoff,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]


class GeminiAnalyzer:
    """Interface com Gemini para análises estratégicas."""

    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        self.model_name = model_name
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def analyze_metrics(self, snapshot: Dict, history: List[Dict] = None) -> Dict:
        """
        Analisa métricas atuais e históricas.

        Returns:
            Dict com insights e ações recomendadas
        """
        history_text = ""
        if history:
            history_text = f"\n\nHISTÓRICO (últimos {len(history)} dias):\n"
            for h in history[:7]:  # Últimos 7 dias
                history_text += f"- {h.get('data')}: {h.get('produtos_ativos')} produtos, margem {h.get('margem_media', 'N/A')}%\n"

        prompt = f"""Você é um consultor estratégico de e-commerce especializado em produtos naturais e MTC.

MÉTRICAS ATUAIS ({snapshot.get("data")}):
- Produtos ativos: {snapshot.get("produtos_ativos")}
- Produtos sem estoque: {snapshot.get("produtos_sem_estoque")}
- Margem média: {snapshot.get("margem_media", "N/D")}%
- Propostas IA pendentes: {snapshot.get("propostas_pendentes")}
- Produtos sem EAN: {snapshot.get("produtos_sem_ean")}
- Alertas de preço: {snapshot.get("alertas_preco_pendentes")}
- Produtos monitorados: {snapshot.get("produtos_com_preco_mercado")}
{history_text}

CONTEXTO DO NEGÓCIO:
- Loja especializada em MTC (Medicina Tradicional Chinesa) e produtos naturais
- Foco em SP Capital com entrega própria
- Diferencial: ecossistema de prescritores habilitados
- Concorrência: Kaizen (+48% preço), NaturalMed (-25% preço), Hérbora (regional)

TAREFA:
Analise as métricas e forneça:
1. 3 insights principais sobre o estado atual do negócio
2. 2 tendências (positivas ou negativas) identificadas
3. 3 ações prioritárias recomendadas
4. 1 risco que merece atenção

Responda APENAS em JSON válido:
{{
  "resumo": "Breve resumo em 2 linhas",
  "insights": [
    {{"tipo": "positivo/negativo/neutro", "titulo": "...", "descricao": "..."}},
    ...
  ],
  "tendencias": [
    {{"direcao": "up/down/stable", "metrica": "...", "descricao": "..."}}
  ],
  "acoes": [
    {{"prioridade": 1-3, "tipo": "preco/estoque/marketing/produto", "acao": "...", "impacto": "..."}}
  ],
  "risco": {{"nivel": "baixo/medio/alto", "descricao": "..."}}
}}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=2048,
                ),
            )
            text = response.text

            # Parse JSON
            import re

            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                return json.loads(json_match.group())

        except Exception as e:
            print(f"⚠️ Erro na análise Gemini: {e}")

        return {"error": "Não foi possível gerar análise"}

    def generate_report(self, analysis: Dict, snapshot: Dict) -> str:
        """Gera relatório em Markdown a partir da análise."""
        lines = [
            f"# 🎯 Análise Estratégica - {snapshot.get('data')}",
            "",
            f"## Resumo",
            f"> {analysis.get('resumo', 'Análise não disponível')}",
            "",
            "## 💡 Insights",
        ]

        for insight in analysis.get("insights", []):
            icon = (
                "✅"
                if insight.get("tipo") == "positivo"
                else "⚠️"
                if insight.get("tipo") == "negativo"
                else "ℹ️"
            )
            lines.append(
                f"- {icon} **{insight.get('titulo')}**: {insight.get('descricao')}"
            )

        lines.extend(["", "## 📈 Tendências"])
        for trend in analysis.get("tendencias", []):
            icon = (
                "🔺"
                if trend.get("direcao") == "up"
                else "🔻"
                if trend.get("direcao") == "down"
                else "➡️"
            )
            lines.append(
                f"- {icon} **{trend.get('metrica')}**: {trend.get('descricao')}"
            )

        lines.extend(["", "## ✅ Ações Prioritárias"])
        for acao in sorted(
            analysis.get("acoes", []), key=lambda x: x.get("prioridade", 3)
        ):
            lines.append(
                f"{acao.get('prioridade', '-')}. **[{acao.get('tipo', 'geral').upper()}]** {acao.get('acao')}"
            )
            lines.append(f"   - Impacto: {acao.get('impacto')}")

        risco = analysis.get("risco", {})
        if risco:
            nivel_icon = (
                "🔴"
                if risco.get("nivel") == "alto"
                else "🟡"
                if risco.get("nivel") == "medio"
                else "🟢"
            )
            lines.extend(
                [
                    "",
                    "## ⚠️ Risco Identificado",
                    f"{nivel_icon} **{risco.get('nivel', 'N/D').upper()}**: {risco.get('descricao')}",
                ]
            )

        lines.extend(
            [
                "",
                "---",
                f"*Gerado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M')}*",
            ]
        )

        return "\n".join(lines)


class StrategicDashboard:
    """Orquestra coleta de métricas e geração de análises."""

    def __init__(self):
        self.collector = MetricsCollector()
        self.analyzer = GeminiAnalyzer()

    def run_daily_analysis(self, save: bool = True) -> Dict:
        """Executa análise diária completa."""
        print("📊 Coletando métricas...")
        metrics = self.collector.collect_daily_metrics()
        print(f"   Produtos ativos: {metrics['produtos_ativos']}")
        print(f"   Margem média: {metrics.get('margem_media', 'N/D')}%")

        if save:
            self.collector.save_snapshot(metrics)
            print("   ✅ Snapshot salvo")

        print("\n🤖 Gerando análise com Gemini...")
        history = self.collector.get_history(7)
        analysis = self.analyzer.analyze_metrics(metrics, history)

        if "error" not in analysis:
            report = self.analyzer.generate_report(analysis, metrics)
            print("\n" + report)

            # Salvar relatório no banco
            if save:
                self._save_report(metrics["data"], "diario", report, analysis)
        else:
            print(f"   ⚠️ {analysis['error']}")

        return {"metrics": metrics, "analysis": analysis}

    def _save_report(self, data: str, tipo: str, conteudo: str, analysis: Dict):
        """Salva relatório no banco de dados."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO relatorios_estrategicos 
            (data, tipo, titulo, conteudo, insights_json, acoes_recomendadas)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                data,
                tipo,
                f"Análise {tipo.capitalize()} - {data}",
                conteudo,
                json.dumps(analysis.get("insights", []), ensure_ascii=False),
                json.dumps(analysis.get("acoes", []), ensure_ascii=False),
            ),
        )

        conn.commit()
        conn.close()

    def get_latest_report_data(self) -> Optional[Dict]:
        """Retorna dados estruturados do último relatório."""
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM relatorios_estrategicos 
            ORDER BY created_at DESC LIMIT 1
        """)
        report = cursor.fetchone()

        if not report:
            conn.close()
            return None

        cursor.execute(
            """
            SELECT * FROM metricas_snapshot 
            WHERE data = ?
        """,
            (report["data"],),
        )
        snapshot = cursor.fetchone()
        conn.close()

        return {
            "report": dict(report),
            "snapshot": dict(snapshot) if snapshot else {},
            "insights": json.loads(report["insights_json"])
            if report["insights_json"]
            else [],
            "actions": json.loads(report["acoes_recomendadas"])
            if report["acoes_recomendadas"]
            else [],
        }

    def _get_approval_candidates(self):
        """Busca candidatos para aprovação (Preços e EANs)."""
        adjuster = PriceAdjuster()
        suggestions = adjuster.analisar_todos()

        # Filtrar apenas sugestões com ação != MAINTAIN
        price_updates = [s for s in suggestions if s.acao.name != "MAINTAIN"]

        # Buscar EANs (Limitando aos últimos atualizados ou todos com GTIN)
        # Como não temos flag 'dirty', vamos listar todos com GTIN válido.
        # Em um cenário real, filtrariamos por 'updated_at' > 'last_sync'
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_bling, nome, gtin FROM produtos WHERE situacao='A' AND gtin IS NOT NULL AND gtin != ''"
        )
        ean_updates = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return price_updates, ean_updates

    def export_to_html(self, output_file: str = "dashboard.html"):
        """Gera um dashboard HTML moderno com área de aprovação interativa."""
        data = self.get_latest_report_data()
        if not data:
            print("⚠️ Nenhum relatório para exportar.")
            return

        report = data["report"]
        metrics = data["snapshot"]
        insights = data["insights"]
        actions = data["actions"]

        # Obter candidatos para aprovação
        price_recs, ean_recs = self._get_approval_candidates()

        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bling Optimizer Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Inter', sans-serif; }}</style>
    <script>
        function generateSyncCommand() {{
            const selectedPrices = Array.from(document.querySelectorAll('input[name="price_check"]:checked')).map(cb => cb.value);
            const selectedEans = Array.from(document.querySelectorAll('input[name="ean_check"]:checked')).map(cb => cb.value);
            
            if (selectedPrices.length === 0 && selectedEans.length === 0) {{
                alert("Selecione pelo menos um item para sincronizar.");
                return;
            }}
            
            // Construir JSONs safe para CLI
            const pricesJson = JSON.stringify(selectedPrices).replace(/"/g, '\\"');
            const eansJson = JSON.stringify(selectedEans).replace(/"/g, '\\"');
            
            const cmd = `python src/optimizer.py apply-changes --prices "${{pricesJson}}" --eans "${{eansJson}}"`;
            
            navigator.clipboard.writeText(cmd).then(() => {{
                alert("✅ Comando copiado para a área de transferência!\\n\\nCole no seu terminal para aplicar as mudanças.");
            }}, (err) => {{
                console.error('Erro ao copiar: ', err);
                prompt("Copie o comando abaixo:", cmd);
            }});
        }}
        
        function toggleAll(name, source) {{
            checkboxes = document.getElementsByName(name);
            for(var i=0, n=checkboxes.length;i<n;i++) {{
                checkboxes[i].checked = source.checked;
            }}
        }}
    </script>
</head>
<body class="bg-gray-50 text-gray-800">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Header -->
        <div class="md:flex md:items-center md:justify-between mb-8">
            <div class="flex-1 min-w-0">
                <h2 class="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate">
                    🎯 Dashboard Estratégico
                </h2>
                <p class="mt-1 text-sm text-gray-500">
                    Gerado em {
            datetime.strptime(report["created_at"], "%Y-%m-%d %H:%M:%S").strftime(
                "%d/%m/%Y às %H:%M"
            )
        }
                </p>
            </div>
            <div class="mt-4 flex md:mt-0 md:ml-4">
                <span class="inline-flex items-center px-3 py-0.5 rounded-full text-sm font-medium bg-green-100 text-green-800">
                    {report["tipo"].upper()}
                </span>
            </div>
        </div>

        <!-- KPI Cards -->
        <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            <div class="bg-white overflow-hidden shadow rounded-lg px-4 py-5 sm:p-6">
                <dt class="text-sm font-medium text-gray-500 truncate">Produtos Ativos</dt>
                <dd class="mt-1 text-3xl font-semibold text-gray-900">{
            metrics.get("produtos_ativos", 0)
        }</dd>
            </div>
             <div class="bg-white overflow-hidden shadow rounded-lg px-4 py-5 sm:p-6">
                <dt class="text-sm font-medium text-gray-500 truncate">Margem Média</dt>
                <dd class="mt-1 text-3xl font-semibold {
            "text-red-600" if metrics.get("margem_media", 0) < 0 else "text-green-600"
        }">
                    {metrics.get("margem_media", 0)}%
                </dd>
            </div>
            <div class="bg-white overflow-hidden shadow rounded-lg px-4 py-5 sm:p-6">
                <dt class="text-sm font-medium text-gray-500 truncate">Sem Estoque</dt>
                <dd class="mt-1 text-3xl font-semibold text-gray-900">{
            metrics.get("produtos_sem_estoque", 0)
        }</dd>
            </div>
            <div class="bg-white overflow-hidden shadow rounded-lg px-4 py-5 sm:p-6">
                <dt class="text-sm font-medium text-gray-500 truncate">Sem EAN</dt>
                <dd class="mt-1 text-3xl font-semibold text-gray-900">{
            metrics.get("produtos_sem_ean", 0)
        }</dd>
            </div>
        </div>

        <!-- Approval Section -->
        <div class="mb-8 bg-white shadow sm:rounded-lg border-l-4 border-blue-500">
            <div class="px-4 py-5 sm:px-6 border-b border-gray-200 flex justify-between items-center">
                <div>
                     <h3 class="text-xl leading-6 font-bold text-gray-900">✍️ Aprovação de Mudanças</h3>
                     <p class="mt-1 text-sm text-gray-500">Revise e selecione as alterações para sincronizar com o Bling.</p>
                </div>
                <button onclick="generateSyncCommand()" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    📋 Copiar Comando de Sincronização
                </button>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-0 divide-x divide-gray-200">
                <!-- Price Approval -->
                <div class="p-4">
                    <h4 class="font-bold text-gray-700 mb-4 flex items-center">
                        <input type="checkbox" onclick="toggleAll('price_check', this)" class="mr-2 h-4 w-4 text-blue-600 rounded">
                        💰 Sugestões de Preço ({len(price_recs)})
                    </h4>
                    <div class="overflow-y-auto max-h-96">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Produto</th>
                                    <th scope="col" class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">De -> Para</th>
                                    <th scope="col" class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Ação</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                {
            "".join(
                [
                    f'''
                                <tr>
                                    <td class="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900 flex items-center">
                                        <input type="checkbox" name="price_check" value="{r.id_produto}:{r.preco_sugerido}" class="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded">
                                        <span class="truncate w-40" title="{r.nome_produto}">{r.nome_produto[:25]}...</span>
                                    </td>
                                    <td class="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-500">
                                        R${r.preco_atual:.0f} -> <strong>R${r.preco_sugerido:.0f}</strong>
                                    </td>
                                    <td class="px-3 py-2 whitespace-nowrap text-center text-sm">
                                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {"bg-green-100 text-green-800" if "INCREASE" in str(r.acao) else "bg-red-100 text-red-800"}">
                                            {r.acao.name}
                                        </span>
                                    </td>
                                </tr>'''
                    for r in price_recs
                ]
            )
        }
                            </tbody>
                        </table>
                        {
            '<p class="text-sm text-gray-500 mt-2 text-center">Nenhuma sugestão de preço pendente.</p>'
            if not price_recs
            else ""
        }
                    </div>
                </div>

                <!-- EAN Approval -->
                <div class="p-4">
                    <h4 class="font-bold text-gray-700 mb-4 flex items-center">
                        <input type="checkbox" onclick="toggleAll('ean_check', this)" class="mr-2 h-4 w-4 text-blue-600 rounded">
                        🏷️ EANs/GTINs Encontrados ({len(ean_recs)})
                    </h4>
                    <div class="overflow-y-auto max-h-96">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Produto</th>
                                    <th scope="col" class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">GTIN</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                {
            "".join(
                [
                    f'''
                                <tr>
                                    <td class="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900 flex items-center">
                                        <input type="checkbox" name="ean_check" value="{e["id_bling"]}:{e["gtin"]}" class="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded" checked>
                                        <span class="truncate w-40" title="{e["nome"]}">{e["nome"][:25]}...</span>
                                    </td>
                                    <td class="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-500 font-mono">
                                        {e["gtin"]}
                                    </td>
                                </tr>'''
                    for e in ean_recs[:100]
                ]
            )
        } 
                                <!-- Limit to 100 to avoid huge DOM -->
                            </tbody>
                        </table>
                         {
            f'<p class="text-xs text-gray-400 mt-2 text-center">Mostrando 100 de {len(ean_recs)} itens.</p>'
            if len(ean_recs) > 100
            else ""
        }
                    </div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Insights -->
            <div class="bg-white shadow sm:rounded-lg">
                <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                    <h3 class="text-lg leading-6 font-medium text-gray-900">💡 Insights de IA</h3>
                </div>
                <ul class="divide-y divide-gray-200">
                    {
            "".join(
                [
                    f'''
                    <li class="px-4 py-4">
                        <div class="flex space-x-3">
                            <div class="flex-shrink-0 text-xl">
                                {"✅" if i.get("tipo") == "positivo" else "⚠️" if i.get("tipo") == "negativo" else "ℹ️"}
                            </div>
                            <div>
                                <h4 class="text-sm font-bold text-gray-900">{i.get("titulo")}</h4>
                                <p class="text-sm text-gray-600">{i.get("descricao")}</p>
                            </div>
                        </div>
                    </li>'''
                    for i in insights
                ]
            )
        }
                </ul>
            </div>

            <!-- Ações -->
            <div class="bg-white shadow sm:rounded-lg">
                <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                    <h3 class="text-lg leading-6 font-medium text-gray-900">🚀 Plano de Ação</h3>
                </div>
                <ul class="divide-y divide-gray-200">
                    {
            "".join(
                [
                    f'''
                    <li class="px-4 py-4">
                        <div class="flex space-x-3">
                            <div class="flex-shrink-0">
                                <span class="inline-flex items-center justify-center h-8 w-8 rounded-full bg-blue-100 text-blue-800 font-bold">
                                    {a.get("prioridade", "-")}
                                </span>
                            </div>
                            <div>
                                <h4 class="text-sm font-bold text-gray-900">[{a.get("tipo", "").upper()}] {a.get("acao")}</h4>
                                <p class="text-sm text-gray-500 mt-1">Impacto: {a.get("impacto")}</p>
                            </div>
                        </div>
                    </li>'''
                    for a in sorted(actions, key=lambda x: x.get("prioridade", 9))
                ]
            )
        }
                </ul>
            </div>
        </div>
        
        <!-- Relatório Completo -->
        <div class="mt-8 bg-white shadow sm:rounded-lg">
            <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
                 <h3 class="text-lg leading-6 font-medium text-gray-900">📝 Relatório Detalhado</h3>
            </div>
            <div class="px-4 py-5 sm:p-6 prose max-w-none text-gray-700">
                <pre class="whitespace-pre-wrap font-sans text-sm">{
            report["conteudo"]
        }</pre>
            </div>
        </div>
    </div>
</body>
</html>
"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"✅ Dashboard HTML exportado para: {os.path.abspath(output_file)}")
        return os.path.abspath(output_file)


if __name__ == "__main__":
    dashboard = StrategicDashboard()
    dashboard.run_daily_analysis()
