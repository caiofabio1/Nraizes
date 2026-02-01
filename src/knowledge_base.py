"""
Bling Optimizer - Product Knowledge Base
Comprehensive product research including usage, contraindications, scientific studies, etc.
"""

import os
import json
import sqlite3
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime

# Load API key
cred_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), ".credentials", "bling_api_tokens.env"
)
load_dotenv(cred_path)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vault.db")


def init_knowledge_tables():
    """Initialize knowledge base tables in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Product Knowledge table - detailed product information
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produto_conhecimento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_produto INTEGER UNIQUE NOT NULL,
            
            -- Informações básicas
            categoria_produto TEXT,  -- 'suplemento', 'cosmetico', 'alimento', 'planta', 'oleo_essencial'
            
            -- Composição
            ingredientes TEXT,  -- JSON array
            principios_ativos TEXT,  -- JSON array
            
            -- Uso
            modo_uso TEXT,
            dosagem_recomendada TEXT,
            frequencia_uso TEXT,
            melhor_horario TEXT,
            
            -- Segurança
            contraindicacoes TEXT,  -- JSON array
            interacoes TEXT,  -- JSON array (medicamentos, outros suplementos)
            efeitos_colaterais TEXT,  -- JSON array
            alertas TEXT,  -- JSON array (gravidez, lactação, crianças, etc.)
            
            -- Benefícios
            beneficios TEXT,  -- JSON array
            indicacoes TEXT,  -- JSON array
            
            -- Informações técnicas
            armazenamento TEXT,
            validade_media TEXT,
            origem TEXT,
            certificacoes TEXT,  -- JSON array (orgânico, vegano, etc.)
            
            -- Pesquisas
            referencias_cientificas TEXT,  -- JSON array with links/citations
            estudos_resumo TEXT,
            
            -- FAQ
            faq TEXT,  -- JSON array of {pergunta, resposta}
            
            -- Metadados
            confianca_score REAL,  -- 0-1, how confident AI is about the data
            pesquisado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (id_produto) REFERENCES produtos(id_bling)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Knowledge base tables initialized")


class ProductResearcher:
    """AI-powered product research for comprehensive knowledge base."""

    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        self.model_name = model_name
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        init_knowledge_tables()

    def categorize_product(self, nome: str) -> str:
        """Determine product category based on name."""
        nome_lower = nome.lower()

        if any(x in nome_lower for x in ["oleo essencial", "oleorresina", "hidrolato"]):
            return "oleo_essencial"
        elif any(
            x in nome_lower for x in ["cha ", "chá ", "folha", "raiz", "casca", "erva"]
        ):
            return "planta"
        elif any(
            x in nome_lower
            for x in [
                "capsulas",
                "cápsulas",
                "vitamina",
                "proteina",
                "colageno",
                "omega",
                "aminnu",
                "guardian",
                "magnesio",
                "suplemento",
            ]
        ):
            return "suplemento"
        elif any(
            x in nome_lower
            for x in [
                "sabonete",
                "shampoo",
                "creme",
                "serum",
                "base",
                "batom",
                "mascara",
                "oleo facial",
            ]
        ):
            return "cosmetico"
        elif any(
            x in nome_lower
            for x in [
                "mel",
                "cafe",
                "cha",
                "shake",
                "polpa",
                "pao de queijo",
                "torta",
                "wafel",
            ]
        ):
            return "alimento"
        else:
            return "outro"

    def research_product(self, produto: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Research a product and generate comprehensive knowledge.

        Returns dict with all knowledge base fields.
        """
        nome = produto.get("nome", "")
        codigo = produto.get("codigo", "")
        categoria = self.categorize_product(nome)

        prompt = f"""Você é um especialista em produtos naturais, suplementos e cosméticos. 
Pesquise e forneça informações detalhadas sobre o seguinte produto:

PRODUTO: {nome}
CÓDIGO: {codigo}
CATEGORIA: {categoria}

FORNEÇA AS SEGUINTES INFORMAÇÕES (em português brasileiro):

1. **ingredientes**: Lista dos ingredientes principais (como array JSON)
2. **principios_ativos**: Princípios ativos ou componentes funcionais (como array JSON)
3. **modo_uso**: Como usar o produto corretamente
4. **dosagem_recomendada**: Quantidade/frequência recomendada (se aplicável)
5. **contraindicacoes**: Situações em que NÃO deve ser usado (como array JSON)
6. **interacoes**: Possíveis interações com medicamentos ou outros produtos (como array JSON)
7. **efeitos_colaterais**: Possíveis efeitos adversos (como array JSON)
8. **alertas**: Avisos importantes como gravidez, lactação, crianças, alergias (como array JSON)
9. **beneficios**: Principais benefícios do produto (como array JSON)
10. **indicacoes**: Para quem/que situações é indicado (como array JSON)
11. **armazenamento**: Como conservar o produto
12. **origem**: Origem dos ingredientes principais (se conhecida)
13. **certificacoes**: Certificações prováveis (orgânico, vegano, etc.) (como array JSON)
14. **referencias_cientificas**: 2-3 referências de estudos relevantes se for suplemento/planta (como array JSON de strings)
15. **estudos_resumo**: Resumo breve do que estudos dizem sobre os principais ingredientes
16. **faq**: 3 perguntas frequentes com respostas (como array JSON de objetos {{"pergunta": "...", "resposta": "..."}})
17. **confianca_score**: De 0 a 1, quão confiante você está sobre essas informações

IMPORTANTE:
- Se não souber algo com certeza, coloque array vazio [] ou string vazia ""
- Seja preciso e factual
- Para suplementos e plantas, priorize informações baseadas em evidências
- NÃO invente estudos científicos

RESPONDA APENAS EM JSON VÁLIDO com estas chaves exatas.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            result = self._parse_response(response.text)
            result["categoria_produto"] = categoria
            return result

        except Exception as e:
            print(f"❌ Error researching {nome}: {e}")
            return None

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from Gemini response."""
        import re

        # Clean markdown code blocks
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)

        # Try to find JSON
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"Could not parse response as JSON")

    def save_knowledge(self, id_produto: int, knowledge: Dict[str, Any]):
        """Save product knowledge to database."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Convert lists/dicts to JSON strings
        def to_json(val):
            if isinstance(val, (list, dict)):
                return json.dumps(val, ensure_ascii=False)
            return val

        cursor.execute(
            """
            INSERT INTO produto_conhecimento (
                id_produto, categoria_produto, ingredientes, principios_ativos,
                modo_uso, dosagem_recomendada, contraindicacoes, interacoes,
                efeitos_colaterais, alertas, beneficios, indicacoes,
                armazenamento, origem, certificacoes, referencias_cientificas,
                estudos_resumo, faq, confianca_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id_produto) DO UPDATE SET
                categoria_produto = excluded.categoria_produto,
                ingredientes = excluded.ingredientes,
                principios_ativos = excluded.principios_ativos,
                modo_uso = excluded.modo_uso,
                dosagem_recomendada = excluded.dosagem_recomendada,
                contraindicacoes = excluded.contraindicacoes,
                interacoes = excluded.interacoes,
                efeitos_colaterais = excluded.efeitos_colaterais,
                alertas = excluded.alertas,
                beneficios = excluded.beneficios,
                indicacoes = excluded.indicacoes,
                armazenamento = excluded.armazenamento,
                origem = excluded.origem,
                certificacoes = excluded.certificacoes,
                referencias_cientificas = excluded.referencias_cientificas,
                estudos_resumo = excluded.estudos_resumo,
                faq = excluded.faq,
                confianca_score = excluded.confianca_score,
                atualizado_em = CURRENT_TIMESTAMP
        """,
            (
                id_produto,
                knowledge.get("categoria_produto", ""),
                to_json(knowledge.get("ingredientes", [])),
                to_json(knowledge.get("principios_ativos", [])),
                knowledge.get("modo_uso", ""),
                knowledge.get("dosagem_recomendada", ""),
                to_json(knowledge.get("contraindicacoes", [])),
                to_json(knowledge.get("interacoes", [])),
                to_json(knowledge.get("efeitos_colaterais", [])),
                to_json(knowledge.get("alertas", [])),
                to_json(knowledge.get("beneficios", [])),
                to_json(knowledge.get("indicacoes", [])),
                knowledge.get("armazenamento", ""),
                knowledge.get("origem", ""),
                to_json(knowledge.get("certificacoes", [])),
                to_json(knowledge.get("referencias_cientificas", [])),
                knowledge.get("estudos_resumo", ""),
                to_json(knowledge.get("faq", [])),
                knowledge.get("confianca_score", 0.5),
            ),
        )

        conn.commit()
        conn.close()

    def research_all_products(self, limit: int = None) -> int:
        """Research all products and save to knowledge base."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get products not yet researched
        if limit:
            cursor.execute(
                """
                SELECT p.* FROM produtos p
                LEFT JOIN produto_conhecimento pk ON p.id_bling = pk.id_produto
                WHERE pk.id_produto IS NULL AND p.situacao = 'A'
                LIMIT ?
            """,
                (limit,),
            )
        else:
            cursor.execute("""
                SELECT p.* FROM produtos p
                LEFT JOIN produto_conhecimento pk ON p.id_bling = pk.id_produto
                WHERE pk.id_produto IS NULL AND p.situacao = 'A'
            """)

        products = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not products:
            print("✅ All products already researched!")
            return 0

        print(f"🔬 Researching {len(products)} products...")

        count = 0
        for product in products:
            print(f"📚 Researching: {product['nome'][:50]}...")

            knowledge = self.research_product(product)

            if knowledge:
                self.save_knowledge(product["id_bling"], knowledge)
                count += 1

        print(f"✅ Researched {count} products")
        return count

    def get_product_knowledge(self, id_produto: int) -> Optional[Dict[str, Any]]:
        """Get knowledge for a specific product."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM produto_conhecimento WHERE id_produto = ?", (id_produto,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        result = dict(row)

        # Parse JSON fields
        json_fields = [
            "ingredientes",
            "principios_ativos",
            "contraindicacoes",
            "interacoes",
            "efeitos_colaterais",
            "alertas",
            "beneficios",
            "indicacoes",
            "certificacoes",
            "referencias_cientificas",
            "faq",
        ]

        for field in json_fields:
            if result.get(field):
                try:
                    result[field] = json.loads(result[field])
                except:
                    pass

        return result


def cmd_research(args):
    """CLI command to research products."""
    researcher = ProductResearcher()

    if args.product_id:
        # Research specific product
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM produtos WHERE id_bling = ?", (args.product_id,))
        product = cursor.fetchone()
        conn.close()

        if not product:
            print(f"❌ Product {args.product_id} not found")
            return

        product = dict(product)

        if args.dry_run:
            print(f"🔍 Would research: {product['nome']}")
            print(f"   Category: {researcher.categorize_product(product['nome'])}")
            return

        knowledge = researcher.research_product(product)

        if knowledge:
            researcher.save_knowledge(args.product_id, knowledge)
            print(f"✅ Researched: {product['nome']}")
            print(json.dumps(knowledge, indent=2, ensure_ascii=False))
    else:
        # Research all
        count = researcher.research_all_products(limit=args.limit)
        print(f"\n📊 Total researched: {count}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Product Knowledge Base Research")
    parser.add_argument("--product-id", type=int, help="Research specific product")
    parser.add_argument("--limit", type=int, help="Limit number of products")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")

    args = parser.parse_args()
    cmd_research(args)
