"""
Bling Optimizer - Price Adjuster Module
Motor de regras para ajuste automático de preços baseado em dados de mercado.
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from database import get_connection, VaultDB


class PriceAction(Enum):
    """Tipos de ação de preço."""
    INCREASE = "increase"
    DECREASE = "decrease"
    MAINTAIN = "maintain"


@dataclass
class PriceRecommendation:
    """Recomendação de ajuste de preço."""
    id_produto: int
    nome_produto: str
    preco_atual: float
    preco_sugerido: float
    acao: PriceAction
    motivo: str
    diferenca_percent: float
    fonte_dados: str
    confianca: float  # 0-1
    pode_auto_aplicar: bool = False


class PriceAdjuster:
    """
    Motor de regras para ajuste de preços.
    
    Analisa preços de mercado vs preços internos e sugere/aplica ajustes
    respeitando margens mínimas e regras de negócio.
    """
    
    # Configurações padrão
    DEFAULT_MIN_MARGIN = 20  # %
    DEFAULT_MAX_SWING = 15  # % máximo ajuste por vez
    DEFAULT_COOLDOWN_DAYS = 3  # dias entre ajustes
    
    def __init__(self):
        self.db = VaultDB()
        self._load_config()
    
    def _load_config(self):
        """Carrega configurações do banco."""
        self.min_margin = float(self.db.get_config('MIN_MARGIN_PERCENT') or self.DEFAULT_MIN_MARGIN)
        self.max_swing = float(self.db.get_config('MAX_PRICE_SWING_PERCENT') or self.DEFAULT_MAX_SWING)
    
    def _get_regra_produto(self, id_produto: int, marca: str = None, categoria: str = None) -> Dict:
        """Busca regra de precificação específica para o produto."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Prioridade: produto > marca > categoria > default
        regra = None
        
        # Busca por produto específico
        cursor.execute('''
            SELECT * FROM regras_preco WHERE tipo = 'produto' AND referencia = ?
        ''', (str(id_produto),))
        row = cursor.fetchone()
        if row:
            regra = dict(row)
        
        # Busca por marca
        elif marca:
            cursor.execute('''
                SELECT * FROM regras_preco WHERE tipo = 'marca' AND referencia = ?
            ''', (marca,))
            row = cursor.fetchone()
            if row:
                regra = dict(row)
        
        # Busca por categoria
        elif categoria:
            cursor.execute('''
                SELECT * FROM regras_preco WHERE tipo = 'categoria' AND referencia = ?
            ''', (categoria,))
            row = cursor.fetchone()
            if row:
                regra = dict(row)
        
        conn.close()
        
        # Default se não encontrou
        if not regra:
            regra = {
                'margem_minima': self.min_margin,
                'margem_alvo': 35,
                'permite_auto_ajuste': True,
                'premium_permitido': 15
            }
        
        return regra
    
    def _get_ultimo_ajuste(self, id_produto: int) -> Optional[datetime]:
        """Retorna data do último ajuste do produto."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT MAX(aplicado_em) as ultimo FROM historico_ajustes
            WHERE id_produto = ?
        ''', (id_produto,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row['ultimo']:
            return datetime.fromisoformat(row['ultimo'])
        return None
    
    def _pode_ajustar(self, id_produto: int) -> bool:
        """Verifica se o produto pode ser ajustado (cooldown)."""
        ultimo = self._get_ultimo_ajuste(id_produto)
        if not ultimo:
            return True
        
        cooldown = timedelta(days=self.DEFAULT_COOLDOWN_DAYS)
        return datetime.now() - ultimo > cooldown
    
    def _get_precos_mercado(self, id_produto: int, dias: int = 7) -> Dict:
        """Busca preços de mercado coletados recentemente."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=dias)).isoformat()
        
        cursor.execute('''
            SELECT fonte, preco, vendedor, disponivel, coletado_em
            FROM precos_concorrentes
            WHERE id_produto = ? AND coletado_em > ?
            ORDER BY coletado_em DESC
        ''', (id_produto, cutoff))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {'precos': [], 'media': None, 'min': None, 'max': None}
        
        precos = [dict(row) for row in rows]
        valores = [p['preco'] for p in precos if p['disponivel']]
        
        return {
            'precos': precos,
            'media': sum(valores) / len(valores) if valores else None,
            'min': min(valores) if valores else None,
            'max': max(valores) if valores else None,
            'num_fontes': len(set(p['fonte'] for p in precos))
        }
    
    def analisar_produto(self, id_produto: int) -> Optional[PriceRecommendation]:
        """
        Analisa um produto e retorna recomendação de preço.
        
        Returns:
            PriceRecommendation ou None se não há dados suficientes
        """
        # Buscar produto
        produto = self.db.get_produto_by_bling_id(id_produto)
        if not produto:
            return None
        
        preco_atual = produto['preco']
        preco_custo = produto.get('preco_custo', 0) or 0
        nome = produto['nome']
        
        # Buscar preços de mercado
        mercado = self._get_precos_mercado(id_produto)
        if not mercado['media']:
            return None  # Sem dados de mercado
        
        preco_mercado = mercado['media']
        
        # Buscar regra aplicável
        regra = self._get_regra_produto(id_produto)
        margem_minima = regra['margem_minima']
        premium_permitido = regra['premium_permitido']
        permite_auto = regra['permite_auto_ajuste']
        
        # Calcular diferença
        diferenca_percent = ((preco_atual - preco_mercado) / preco_mercado) * 100
        
        # Calcular preço mínimo (respeitando margem)
        if preco_custo > 0:
            preco_minimo = preco_custo * (1 + margem_minima / 100)
        else:
            preco_minimo = preco_atual * 0.7  # Fallback: não reduzir mais que 30%
        
        # Decidir ação
        acao = PriceAction.MAINTAIN
        preco_sugerido = preco_atual
        motivo = ""
        confianca = 0.5
        
        if diferenca_percent > premium_permitido:
            # Preço muito acima do mercado
            acao = PriceAction.DECREASE
            # Reduzir até o máximo permitido, respeitando margem
            reducao_max = preco_atual * (self.max_swing / 100)
            preco_sugerido = max(preco_mercado * (1 + premium_permitido/100), preco_minimo)
            preco_sugerido = max(preco_sugerido, preco_atual - reducao_max)
            motivo = f"Preço {diferenca_percent:.0f}% acima do mercado (média R${preco_mercado:.2f})"
            confianca = 0.8 if mercado['num_fontes'] >= 2 else 0.6
            
        elif diferenca_percent < -10:
            # Preço abaixo do mercado - oportunidade de aumento
            acao = PriceAction.INCREASE
            aumento_max = preco_atual * (self.max_swing / 100)
            preco_sugerido = min(preco_mercado * 0.95, preco_atual + aumento_max)
            motivo = f"Preço {abs(diferenca_percent):.0f}% abaixo do mercado - oportunidade de aumento"
            confianca = 0.7 if mercado['num_fontes'] >= 2 else 0.5
        
        else:
            # Preço competitivo
            motivo = f"Preço competitivo ({diferenca_percent:+.0f}% vs mercado)"
            confianca = 0.9
        
        # Verificar cooldown
        pode_auto = permite_auto and self._pode_ajustar(id_produto) and acao != PriceAction.MAINTAIN
        
        return PriceRecommendation(
            id_produto=id_produto,
            nome_produto=nome,
            preco_atual=preco_atual,
            preco_sugerido=round(preco_sugerido, 2),
            acao=acao,
            motivo=motivo,
            diferenca_percent=diferenca_percent,
            fonte_dados=f"{mercado['num_fontes']} fontes",
            confianca=confianca,
            pode_auto_aplicar=pode_auto
        )
    
    def analisar_todos(self, apenas_com_dados: bool = True) -> List[PriceRecommendation]:
        """Analisa todos os produtos e retorna recomendações."""
        conn = get_connection()
        cursor = conn.cursor()
        
        if apenas_com_dados:
            # Apenas produtos com dados de mercado
            cursor.execute('''
                SELECT DISTINCT p.id_bling
                FROM produtos p
                INNER JOIN precos_concorrentes pc ON p.id_bling = pc.id_produto
                WHERE p.situacao = 'A'
            ''')
        else:
            cursor.execute('SELECT id_bling FROM produtos WHERE situacao = "A"')
        
        produtos = cursor.fetchall()
        conn.close()
        
        recomendacoes = []
        for row in produtos:
            rec = self.analisar_produto(row['id_bling'])
            if rec:
                recomendacoes.append(rec)
        
        # Ordenar por potencial de impacto
        recomendacoes.sort(key=lambda r: abs(r.diferenca_percent), reverse=True)
        
        return recomendacoes
    
    def aplicar_ajuste(self, id_produto: int, preco_novo: float, motivo: str = "auto",
                       bling_client=None) -> bool:
        """
        Aplica ajuste de preço no banco local e opcionalmente no Bling.
        
        Args:
            id_produto: ID do produto no Bling
            preco_novo: Novo preço a aplicar
            motivo: Motivo do ajuste
            bling_client: Cliente Bling para aplicar remotamente
            
        Returns:
            True se aplicado com sucesso
        """
        produto = self.db.get_produto_by_bling_id(id_produto)
        if not produto:
            return False
        
        preco_anterior = produto['preco']
        
        # Registrar no histórico
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO historico_ajustes 
            (id_produto, preco_anterior, preco_novo, motivo, fonte_referencia)
            VALUES (?, ?, ?, ?, ?)
        ''', (id_produto, preco_anterior, preco_novo, motivo, 'price_adjuster'))
        
        conn.commit()
        conn.close()
        
        # Aplicar no Bling se cliente fornecido
        if bling_client:
            try:
                bling_client.atualizar_produto(id_produto, {'preco': preco_novo})
                print(f"✅ Preço atualizado no Bling: {produto['nome'][:30]} R${preco_anterior:.2f} → R${preco_novo:.2f}")
                return True
            except Exception as e:
                print(f"❌ Erro ao atualizar Bling: {e}")
                return False
        
        print(f"📝 Ajuste registrado localmente: {produto['nome'][:30]} R${preco_anterior:.2f} → R${preco_novo:.2f}")
        return True
    
    def criar_alerta(self, rec: PriceRecommendation):
        """Cria alerta de preço no banco."""
        conn = get_connection()
        cursor = conn.cursor()
        
        tipo = 'acima_mercado' if rec.acao == PriceAction.DECREASE else 'abaixo_mercado'
        
        cursor.execute('''
            INSERT INTO alertas_preco 
            (id_produto, tipo, mensagem, preco_atual, preco_mercado, diferenca_percent, acao_sugerida)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            rec.id_produto,
            tipo,
            rec.motivo,
            rec.preco_atual,
            rec.preco_sugerido,
            rec.diferenca_percent,
            f"Ajustar para R${rec.preco_sugerido:.2f}"
        ))
        
        conn.commit()
        conn.close()
    
    def gerar_relatorio(self) -> str:
        """Gera relatório de análise de preços."""
        recomendacoes = self.analisar_todos()
        
        aumentos = [r for r in recomendacoes if r.acao == PriceAction.INCREASE]
        reducoes = [r for r in recomendacoes if r.acao == PriceAction.DECREASE]
        ok = [r for r in recomendacoes if r.acao == PriceAction.MAINTAIN]
        
        linhas = [
            "# 📊 Relatório de Análise de Preços",
            f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "",
            f"## Resumo",
            f"- Total analisados: {len(recomendacoes)}",
            f"- 🔺 Oportunidades de aumento: {len(aumentos)}",
            f"- 🔻 Necessitam redução: {len(reducoes)}",
            f"- ✅ Competitivos: {len(ok)}",
            ""
        ]
        
        if reducoes:
            linhas.append("## 🔻 Produtos Acima do Mercado")
            for r in reducoes[:10]:
                linhas.append(f"- **{r.nome_produto[:40]}**: R${r.preco_atual:.2f} → R${r.preco_sugerido:.2f} ({r.diferenca_percent:+.0f}%)")
            linhas.append("")
        
        if aumentos:
            linhas.append("## 🔺 Oportunidades de Aumento")
            for r in aumentos[:10]:
                linhas.append(f"- **{r.nome_produto[:40]}**: R${r.preco_atual:.2f} → R${r.preco_sugerido:.2f} ({r.diferenca_percent:+.0f}%)")
            linhas.append("")
        
        return "\n".join(linhas)


if __name__ == "__main__":
    adjuster = PriceAdjuster()
    
    # Gerar relatório
    print(adjuster.gerar_relatorio())
