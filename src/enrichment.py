"""
Bling Optimizer - AI Enrichment Module
Uses Gemini API to generate product descriptions and SEO metadata.
"""

import os
import json
import re
from typing import Dict, Any, Optional, Tuple
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load API key from credentials file
cred_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), ".credentials", "bling_api_tokens.env"
)
load_dotenv(cred_path)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class ProductEnricher:
    """AI-powered product description and SEO generator."""

    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        self.model_name = model_name
        self.client = genai.Client(api_key=GEMINI_API_KEY)

        # SEO constraints based on Yoast SEO best practices
        self.SEO_TITLE_MAX = 60
        self.SEO_META_MAX = 160
        self.SHORT_DESC_MAX = 150

    def enrich_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate enriched content for a product.

        Returns dict with:
        - descricao_curta: Short selling description (< 150 chars)
        - descricao_complementar: Rich HTML description
        - seo_title: SEO-optimized title (< 60 chars)
        - seo_meta: Meta description (< 160 chars)
        - keywords: List of relevant keywords
        """
        nome = product.get("nome", "")
        codigo = product.get("codigo", "")
        preco = product.get("preco", 0)
        categoria = product.get("categoria", {}).get("nome", "Produto")
        descricao_atual = product.get("descricaoCurta", "") or product.get(
            "descricaoComplementar", ""
        )

        prompt = f"""Você é um especialista em copywriting para e-commerce de produtos naturais, suplementos e cosméticos orgânicos.
Trabalha para a loja "Novas Raízes", referência em produtos naturais e bem-estar.

PRODUTO PARA ENRIQUECER:
- Nome: {nome}
- Código: {codigo}  
- Preço: R$ {preco:.2f}
- Categoria: {categoria}
- Descrição atual: {descricao_atual or "Nenhuma"}

GERE O SEGUINTE CONTEÚDO (em português brasileiro):

1. **descricao_curta** (máx {self.SHORT_DESC_MAX} caracteres): 
   Frase de impacto vendedora que destaca o benefício principal.
   Use linguagem persuasiva e emocional. Não inclua preço.

2. **descricao_complementar** (400-600 palavras, texto corrido SEM HTML):
   Crie uma descrição COMPLETA e DETALHADA seguindo esta estrutura:

   INTRODUÇÃO (1-2 parágrafos):
   - Apresente o produto de forma envolvente
   - Conecte com o estilo de vida saudável do cliente
   - Mencione a origem/procedência se relevante

   BENEFÍCIOS PRINCIPAIS (3-5 benefícios):
   - Liste os benefícios mais importantes
   - Explique COMO cada benefício impacta a vida do cliente
   - Use linguagem sensorial e emocional
   
   INGREDIENTES/COMPOSIÇÃO (se aplicável):
   - Destaque ingredientes naturais e suas propriedades
   - Mencione se é orgânico, vegano, sem glúten, etc.
   - Explique o que torna a fórmula especial

   MODO DE USO:
   - Instruções claras e práticas
   - Frequência recomendada
   - Dicas para melhores resultados

   DIFERENCIAIS:
   - Por que escolher este produto
   - Qualidade e procedência
   - Compromisso com sustentabilidade
   
   FECHAMENTO:
   - Call-to-action sutil
   - Reforce o valor e benefícios
   - Mencione a marca Novas Raízes

3. **seo_title** (máx {self.SEO_TITLE_MAX} caracteres):
   Título otimizado para Google com palavra-chave principal.

4. **seo_meta** (máx {self.SEO_META_MAX} caracteres):
   Meta description atrativa com call-to-action.

5. **keywords** (5-8 palavras-chave separadas por vírgula)

REGRAS IMPORTANTES:
- NÃO use tags HTML (sem <p>, <h3>, <strong>, etc.)
- Texto deve ser corrido e fluido
- Descrição complementar deve ter MÍNIMO 400 palavras
- Complete TODAS as frases, não corte no meio
- Use parágrafos separados por quebra de linha dupla

RESPONDA APENAS EM JSON VÁLIDO:
{{"descricao_curta": "...", "descricao_complementar": "...", "seo_title": "...", "seo_meta": "...", "keywords": "..."}}
"""

        try:
            # Use generation config with higher token limit to prevent truncation
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=8192,
                    temperature=0.7,
                ),
            )
            result = self._parse_response(response.text)

            # Validate lengths
            result = self._validate_and_trim(result)

            return result

        except Exception as e:
            print(f"❌ Error enriching product {nome}: {e}")
            return None

    def _parse_response(self, text: str) -> Dict[str, str]:
        """Extract JSON from Gemini response."""
        # Try to find JSON in the response
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: try parsing the entire response
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"Could not parse response as JSON: {text[:200]}...")

    def _validate_and_trim(self, result: Dict[str, str]) -> Dict[str, str]:
        """Ensure all fields respect length constraints."""
        if "descricao_curta" in result:
            result["descricao_curta"] = result["descricao_curta"][: self.SHORT_DESC_MAX]

        if "seo_title" in result:
            result["seo_title"] = result["seo_title"][: self.SEO_TITLE_MAX]

        if "seo_meta" in result:
            result["seo_meta"] = result["seo_meta"][: self.SEO_META_MAX]

        return result

    def generate_batch_proposals(self, products: list, db) -> int:
        """
        Generate AI proposals for multiple products and save to database.

        Args:
            products: List of product dicts from database
            db: VaultDB instance

        Returns:
            Number of proposals created
        """
        count = 0

        for product in products:
            print(f"🤖 Enriching: {product.get('nome', 'Unknown')[:50]}...")

            enrichment = self.enrich_product(product)

            if enrichment:
                # Create proposal for short description
                if enrichment.get("descricao_curta"):
                    db.create_proposta(
                        id_produto=product["id_bling"],
                        tipo="descricao_curta",
                        conteudo_original=product.get("descricao_curta", ""),
                        conteudo_proposto=enrichment["descricao_curta"],
                    )
                    count += 1

                # Create proposal for complementary description
                if enrichment.get("descricao_complementar"):
                    db.create_proposta(
                        id_produto=product["id_bling"],
                        tipo="descricao_complementar",
                        conteudo_original=product.get("descricao_complementar", ""),
                        conteudo_proposto=enrichment["descricao_complementar"],
                    )
                    count += 1

                # Store SEO metadata as combined proposal
                if enrichment.get("seo_title") or enrichment.get("seo_meta"):
                    seo_data = json.dumps(
                        {
                            "title": enrichment.get("seo_title", ""),
                            "meta": enrichment.get("seo_meta", ""),
                            "keywords": enrichment.get("keywords", ""),
                        },
                        ensure_ascii=False,
                    )

                    db.create_proposta(
                        id_produto=product["id_bling"],
                        tipo="seo",
                        conteudo_original="",
                        conteudo_proposto=seo_data,
                    )
                    count += 1

        print(f"✅ Created {count} AI proposals")
        return count


class SEOValidator:
    """Validates SEO content against best practices."""

    TITLE_MAX = 60
    META_MAX = 160

    @staticmethod
    def validate_title(title: str) -> Tuple[bool, str]:
        """Check if title meets SEO requirements."""
        if not title:
            return False, "Title is empty"
        if len(title) > SEOValidator.TITLE_MAX:
            return False, f"Title too long ({len(title)}/{SEOValidator.TITLE_MAX})"
        if len(title) < 30:
            return False, f"Title too short ({len(title)} chars, recommend 30-60)"
        return True, "OK"

    @staticmethod
    def validate_meta(meta: str) -> Tuple[bool, str]:
        """Check if meta description meets SEO requirements."""
        if not meta:
            return False, "Meta description is empty"
        if len(meta) > SEOValidator.META_MAX:
            return False, f"Meta too long ({len(meta)}/{SEOValidator.META_MAX})"
        if len(meta) < 70:
            return False, f"Meta too short ({len(meta)} chars, recommend 70-160)"
        return True, "OK"

    @staticmethod
    def has_call_to_action(text: str) -> bool:
        """Check if text contains a call to action."""
        cta_patterns = [
            r"compre",
            r"confira",
            r"descubra",
            r"experimente",
            r"aproveite",
            r"garanta",
            r"adquira",
            r"saiba mais",
            r"clique",
            r"veja",
            r"conheça",
        ]
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in cta_patterns)


if __name__ == "__main__":
    # Quick test
    enricher = ProductEnricher()

    test_product = {
        "id": 123,
        "nome": "Mel Orgânico Silvestre 500g",
        "codigo": "MEL-ORG-500",
        "preco": 45.90,
        "descricaoCurta": "",
    }

    print("Testing product enrichment...")
    result = enricher.enrich_product(test_product)

    if result:
        print("\n✅ Enrichment successful!")
        for key, value in result.items():
            print(f"\n{key}:")
            print(f"  {value[:100]}..." if len(str(value)) > 100 else f"  {value}")
    else:
        print("❌ Enrichment failed")
