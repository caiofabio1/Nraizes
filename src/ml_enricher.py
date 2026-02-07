"""
NRAIZES - Mercado Livre Product Enricher
=========================================
Generates ML-optimized content using Gemini AI:
- Titulo PMME (Produto + Marca + Modelo + Especificacao, max 60 chars)
- Descricao complementar (400-600 palavras, sem HTML, regras ML)
- Ficha tecnica (marca, formato, tipo, sabor, vegano, sem gluten)
- Descricao curta (max 150 chars)

Diferente do enrichment.py (foco WooCommerce/SEO), este modulo
segue estritamente as regras do Mercado Livre.
"""

import os
import json
import re
import time
from typing import Dict, Any, Optional, List, Tuple

from dotenv import load_dotenv

# Support both google-genai (new) and google-generativeai (old) SDKs
try:
    from google import genai
    from google.genai import types as genai_types

    GENAI_SDK = "new"
except ImportError:
    import google.generativeai as genai_legacy

    GENAI_SDK = "legacy"

from database import VaultDB
from logger import get_logger

# Load API key
cred_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), ".credentials", "bling_api_tokens.env"
)
load_dotenv(cred_path)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

logger = get_logger("ml_enricher")

# =========================================================================
# CONSTANTES ML
# =========================================================================

ML_TITLE_MAX = 60
ML_SHORT_DESC_MAX = 150
ML_DESC_MIN_WORDS = 300
ML_DESC_IDEAL_WORDS = 500

# Palavras proibidas em titulo ML
TITLE_BANNED_WORDS = [
    "compre",
    "frete gratis",
    "gratis",
    "desconto",
    "oferta",
    "melhor preco",
    "barato",
    "promocao",
    "12x",
    "sem juros",
    "novo",
    "original",
    "lacrado",
    "envio imediato",
]

# Termos proibidos em descricao ML
DESC_BANNED_PATTERNS = [
    r"nraizes\.com\.br",
    r"novasraizes\.com\.br",
    r"www\.\w+\.com",
    r"http[s]?://",
    r"whatsapp",
    r"instagram",
    r"facebook",
    r"woocommerce",
    r"nosso site",
    r"nossa loja online",
    r"clique aqui",
    r"acesse nosso",
    r"visite nossa",
    r"<[^>]+>",  # HTML tags
    r"&\w+;",  # HTML entities
]

# Categorias ML tipicas NRAIZES e seus atributos
ML_CATEGORY_ATTRIBUTES = {
    "suplemento": {
        "campos": [
            "marca",
            "formato_suplemento",
            "tipo_suplemento",
            "sabor",
            "peso_liquido",
            "e_vegano",
            "livre_de_gluten",
        ],
        "formatos": [
            "Capsulas",
            "Po",
            "Liquido",
            "Comprimidos",
            "Saches",
            "Gotas",
            "Softgel",
            "Gomas",
        ],
    },
    "cosmetico": {
        "campos": ["marca", "tipo_pele", "volume", "genero", "linha", "beneficio"],
        "formatos": [],
    },
    "cha": {
        "campos": ["marca", "tipo_cha", "peso", "sabor", "forma_cha"],
        "formatos": ["Sache", "Granel", "Soluvel", "Capsulas"],
    },
    "oleo_essencial": {
        "campos": ["marca", "volume", "tipo_oleo", "uso"],
        "formatos": [],
    },
    "alimento": {
        "campos": ["marca", "peso_liquido", "sabor", "e_vegano", "livre_de_gluten"],
        "formatos": [],
    },
}


class MLProductEnricher:
    """
    Enricher otimizado para Mercado Livre.
    Gera titulo PMME, descricao sem HTML, ficha tecnica com atributos.
    """

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        if GENAI_SDK == "new":
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        else:
            genai_legacy.configure(api_key=GEMINI_API_KEY)
            self.client = None  # legacy uses module-level calls

    def enrich_product(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Gera conteudo ML-otimizado para um produto.

        Returns dict com:
        - titulo_ml: Titulo formato PMME (max 60 chars)
        - descricao_curta: Frase de impacto (max 150 chars)
        - descricao_ml: Descricao longa sem HTML (400-600 palavras)
        - ficha_tecnica: Dict com atributos ML (marca, formato, vegano, etc.)
        """
        nome = product.get("nome", "")
        codigo = product.get("codigo", "")
        preco = product.get("preco", 0)
        categoria = product.get("categoria", {})
        cat_nome = (
            categoria.get("nome", "") if isinstance(categoria, dict) else str(categoria)
        )
        descricao_atual = (
            product.get("descricaoCurta", "")
            or product.get("descricao_curta", "")
            or ""
        )
        desc_complementar = (
            product.get("descricaoComplementar", "")
            or product.get("descricao_complementar", "")
            or ""
        )

        prompt = self._build_prompt(
            nome, codigo, preco, cat_nome, descricao_atual, desc_complementar
        )

        try:
            if GENAI_SDK == "new":
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        max_output_tokens=8192,
                        temperature=0.6,
                    ),
                )
                response_text = response.text
            else:
                # Legacy SDK (google-generativeai)
                model = genai_legacy.GenerativeModel(
                    self.model_name,
                    generation_config=genai_legacy.GenerationConfig(
                        max_output_tokens=8192,
                        temperature=0.6,
                    ),
                )
                response = model.generate_content(prompt)
                response_text = response.text

            result = self._parse_response(response_text)
            result = self._validate_and_fix(result, nome)
            return result

        except Exception as e:
            logger.error(f"Erro ao enriquecer produto ML '{nome}': {e}")
            return None

    def _build_prompt(
        self,
        nome: str,
        codigo: str,
        preco: float,
        categoria: str,
        descricao_curta: str,
        descricao_complementar: str,
    ) -> str:
        """Constroi prompt otimizado para regras do Mercado Livre."""

        return f"""Voce e um especialista em copywriting para o Mercado Livre, categoria de produtos naturais, suplementos e cosmeticos organicos.

PRODUTO:
- Nome atual: {nome}
- Codigo: {codigo}
- Preco: R$ {preco:.2f}
- Categoria: {categoria or "Nao informada"}
- Descricao curta existente: {descricao_curta[:200] if descricao_curta else "Nenhuma"}
- Descricao complementar existente: {descricao_complementar[:500] if descricao_complementar else "Nenhuma"}

GERE O SEGUINTE CONTEUDO EM JSON:

1. "titulo_ml" (MAXIMO {ML_TITLE_MAX} caracteres, OBRIGATORIO):
   FORMATO PMME: [Produto] [Marca] [Quantidade/Peso] [Variacao]
   REGRAS:
   - Title Case (primeira letra maiuscula)
   - SEM caracteres especiais: nada de ?, !, :, (, ), @, #
   - SEM palavras promocionais: nada de "compre", "frete gratis", "novo", "oferta", "original"
   - SEM condicao do produto (novo/usado)
   - Inclua a MARCA do produto
   - Inclua PESO ou QUANTIDADE (ex: 500g, 60 Capsulas)
   - Se tiver sabor/variacao, inclua no final
   EXEMPLOS CORRETOS:
   - "Omega 3 DHA Ocean Drop 60 Capsulas 1000mg"
   - "Creatina Collcreatine Central Nutrition 500g"
   - "Superfoods Amazonicos Mahta 840g Acai Cacau"
   - "Serum Facial Acido Hialuronico 30ml Vegano"
   - "Pre-Treino Nitrato Xtratus 300g Beterraba"

2. "descricao_curta" (MAXIMO {ML_SHORT_DESC_MAX} caracteres):
   Frase de impacto que destaca o beneficio principal do produto.
   Sem preco, sem HTML.

3. "descricao_ml" (MINIMO {ML_DESC_MIN_WORDS} palavras, ideal {ML_DESC_IDEAL_WORDS}):
   Descricao COMPLETA seguindo REGRAS DO MERCADO LIVRE:
   
   ESTRUTURA OBRIGATORIA:
   
   Paragrafo 1 - APRESENTACAO (2-3 linhas):
   O que e o produto, para que serve, beneficio principal.
   
   Paragrafo 2 - BENEFICIOS (3-5 itens com bullet "-"):
   - Beneficio 1 e como impacta a vida do cliente
   - Beneficio 2
   - Beneficio 3
   
   Paragrafo 3 - COMPOSICAO/INGREDIENTES:
   Ingredientes naturais, certificacoes (vegano, sem gluten, organico).
   Destaque o que torna a formula especial.
   
   Paragrafo 4 - MODO DE USO:
   Instrucoes claras, frequencia, dosagem recomendada.
   
   Paragrafo 5 - INFORMACOES DO PRODUTO:
   - Peso liquido / Conteudo
   - Fabricante / Marca
   - Conservacao (como armazenar)
   - Validade media
   
   REGRAS DA DESCRICAO (MERCADO LIVRE):
   - ZERO HTML (sem <p>, <br>, <strong>, <b>, nenhuma tag)
   - ZERO links ou URLs
   - ZERO informacoes de contato (telefone, email, site, redes sociais)
   - ZERO mencao a outros marketplaces ou lojas online
   - NAO mencionar "nraizes", "novas raizes", "nosso site"
   - NAO incluir preco ou informacoes de pagamento/parcelamento
   - NAO incluir informacoes de frete
   - Texto CORRIDO e fluido, paragrafos separados por quebra de linha dupla
   - Use bullets com "-" para listas (nao HTML)
   - Inclua palavras-chave de busca naturalmente no texto
   - TODAS as frases devem estar COMPLETAS (nao cortar no meio)
   
   PALAVRAS-CHAVE para incluir naturalmente:
   suplemento natural, capsulas, po, organico, vegano, sem gluten,
   alta concentracao, biodisponivel, importado, premium, saude,
   bem-estar, qualidade, natural

4. "ficha_tecnica" (objeto JSON com atributos do produto):
   {{
     "marca": "Nome da marca do produto (ex: Ocean Drop, Mahta, Central Nutrition)",
     "formato_suplemento": "Capsulas / Po / Liquido / Comprimidos / Saches / Gotas / Softgel / Gomas / N/A",
     "tipo_suplemento": "Tipo especifico (ex: Omega 3, Creatina, Proteina Vegetal, Multivitaminico, Colageno, Pre-Treino, N/A)",
     "sabor": "Sabor se aplicavel (ex: Chocolate, Baunilha, Limao, Neutro, N/A)",
     "peso_liquido": "Peso ou volume (ex: 500g, 60 capsulas, 30ml)",
     "e_vegano": "Sim / Nao / Nao informado",
     "livre_de_gluten": "Sim / Nao / Nao informado"
   }}
   Deduza os valores a partir do nome, codigo e descricoes existentes.
   Se nao for possivel determinar com certeza, use "Nao informado".

RESPONDA APENAS EM JSON VALIDO:
{{"titulo_ml": "...", "descricao_curta": "...", "descricao_ml": "...", "ficha_tecnica": {{...}}}}
"""

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Extrai JSON da resposta do Gemini, tratando newlines e encoding."""
        # Remove markdown code blocks
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Fix unescaped newlines inside JSON string values
        # Replace literal newlines inside strings with \\n
        fixed = self._fix_json_newlines(text)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in the response
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            raw = json_match.group()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                fixed = self._fix_json_newlines(raw)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        raise ValueError(f"Nao foi possivel parsear JSON da resposta: {text[:300]}...")

    @staticmethod
    def _fix_json_newlines(text: str) -> str:
        """
        Fix unescaped newlines inside JSON string values.
        Gemini often returns JSON with literal newlines in string fields
        (especially in long descriptions), which breaks json.loads().
        """
        result = []
        in_string = False
        escape_next = False
        i = 0
        while i < len(text):
            char = text[i]
            if escape_next:
                result.append(char)
                escape_next = False
            elif char == "\\":
                result.append(char)
                escape_next = True
            elif char == '"':
                result.append(char)
                in_string = not in_string
            elif in_string and char == "\n":
                result.append("\\n")
            elif in_string and char == "\r":
                result.append("")  # skip \r
            elif in_string and char == "\t":
                result.append("\\t")
            else:
                result.append(char)
            i += 1
        return "".join(result)

    def _validate_and_fix(
        self, result: Dict[str, Any], nome_original: str
    ) -> Dict[str, Any]:
        """Valida e corrige o resultado do enrichment conforme regras ML."""

        # === TITULO ===
        titulo = result.get("titulo_ml", "")
        if titulo:
            # Remove caracteres proibidos
            titulo = re.sub(r'[?!:()@#"\'&]', "", titulo)
            # Remove palavras proibidas
            titulo_lower = titulo.lower()
            for word in TITLE_BANNED_WORDS:
                if word in titulo_lower:
                    # Remove a palavra mantendo o resto
                    titulo = re.sub(
                        rf"\b{re.escape(word)}\b", "", titulo, flags=re.IGNORECASE
                    )
            # Limpa espacos duplos
            titulo = re.sub(r"\s+", " ", titulo).strip()
            # Trunca no limite
            if len(titulo) > ML_TITLE_MAX:
                # Tenta cortar em um espaco
                truncated = titulo[:ML_TITLE_MAX]
                last_space = truncated.rfind(" ")
                if last_space > ML_TITLE_MAX - 15:
                    titulo = truncated[:last_space]
                else:
                    titulo = truncated
            result["titulo_ml"] = titulo.strip()

        # === DESCRICAO CURTA ===
        desc_curta = result.get("descricao_curta", "")
        if desc_curta:
            desc_curta = self._clean_text(desc_curta)
            result["descricao_curta"] = desc_curta[:ML_SHORT_DESC_MAX]

        # === DESCRICAO ML ===
        desc_ml = result.get("descricao_ml", "")
        if desc_ml:
            desc_ml = self._clean_ml_description(desc_ml)
            result["descricao_ml"] = desc_ml

        # === FICHA TECNICA ===
        ficha = result.get("ficha_tecnica", {})
        if isinstance(ficha, str):
            try:
                ficha = json.loads(ficha)
            except json.JSONDecodeError:
                ficha = {}
        # Normaliza valores
        for key, val in ficha.items():
            if isinstance(val, str):
                ficha[key] = val.strip()
                if ficha[key].lower() in ("n/a", "na", "nenhum", "nenhuma", "-", ""):
                    ficha[key] = "Nao informado"
        result["ficha_tecnica"] = ficha

        return result

    def _clean_text(self, text: str) -> str:
        """Remove HTML e caracteres indesejados de texto."""
        # Remove tags HTML
        text = re.sub(r"<[^>]+>", "", text)
        # Remove HTML entities
        text = re.sub(r"&\w+;", "", text)
        # Remove URLs
        text = re.sub(r"https?://\S+", "", text)
        # Limpa espacos
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _clean_ml_description(self, text: str) -> str:
        """Limpa descricao conforme regras ML."""
        # Remove tags HTML
        text = re.sub(r"<[^>]+>", "", text)
        # Remove HTML entities
        text = re.sub(r"&\w+;", " ", text)
        # Remove URLs
        text = re.sub(r"https?://\S+", "", text)
        # Remove padroes proibidos
        for pattern in DESC_BANNED_PATTERNS:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        # Limpa espacos extras preservando paragrafos
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            line = re.sub(r"[ \t]+", " ", line).strip()
            cleaned_lines.append(line)
        text = "\n".join(cleaned_lines)
        # Remove mais de 2 quebras de linha consecutivas
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def generate_batch_proposals(
        self, products: List[Dict], db: VaultDB, delay: float = 3.0
    ) -> Dict[str, int]:
        """
        Enriquece multiplos produtos e salva como propostas no banco.

        Returns dict com contadores: {criados, erros, pulados}
        """
        stats = {"criados": 0, "erros": 0, "pulados": 0}

        for i, product in enumerate(products, 1):
            nome = product.get("nome", "Desconhecido")
            bling_id = product.get("id_bling") or product.get("id")

            if not bling_id:
                logger.warning(f"Produto sem id_bling: {nome}")
                stats["pulados"] += 1
                continue

            logger.info(f"[{i}/{len(products)}] Enriquecendo ML: {nome[:55]}")

            try:
                enrichment = self.enrich_product(product)
            except Exception as e:
                logger.error(f"Erro no enrichment de {nome}: {e}")
                stats["erros"] += 1
                if i < len(products):
                    time.sleep(2)
                continue

            if not enrichment:
                stats["erros"] += 1
                continue

            # Salva propostas por tipo
            count = 0

            if enrichment.get("titulo_ml"):
                db.create_proposta(
                    id_produto=bling_id,
                    tipo="titulo_ml",
                    conteudo_original=product.get("nome", ""),
                    conteudo_proposto=enrichment["titulo_ml"],
                )
                count += 1

            if enrichment.get("descricao_curta"):
                db.create_proposta(
                    id_produto=bling_id,
                    tipo="descricao_curta_ml",
                    conteudo_original=product.get("descricao_curta", "") or "",
                    conteudo_proposto=enrichment["descricao_curta"],
                )
                count += 1

            if enrichment.get("descricao_ml"):
                db.create_proposta(
                    id_produto=bling_id,
                    tipo="descricao_ml",
                    conteudo_original=product.get("descricao_complementar", "") or "",
                    conteudo_proposto=enrichment["descricao_ml"],
                )
                count += 1

            if enrichment.get("ficha_tecnica"):
                ficha_json = json.dumps(enrichment["ficha_tecnica"], ensure_ascii=False)
                db.create_proposta(
                    id_produto=bling_id,
                    tipo="ficha_tecnica_ml",
                    conteudo_original="",
                    conteudo_proposto=ficha_json,
                )
                count += 1

            stats["criados"] += count
            logger.info(f"  -> {count} propostas criadas para {nome[:40]}")

            # Rate limit
            if i < len(products):
                time.sleep(delay)

        return stats


# =========================================================================
# ML CONTENT VALIDATOR
# =========================================================================


class MLValidator:
    """Valida conteudo gerado contra regras do Mercado Livre."""

    @staticmethod
    def validate_title(titulo: str) -> Tuple[bool, List[str]]:
        """
        Valida titulo ML.
        Returns (is_valid, list_of_issues).
        """
        issues = []

        if not titulo:
            return False, ["Titulo vazio"]

        if len(titulo) > ML_TITLE_MAX:
            issues.append(f"Titulo muito longo: {len(titulo)}/{ML_TITLE_MAX} chars")

        if len(titulo) < 20:
            issues.append(
                f"Titulo muito curto: {len(titulo)} chars (min recomendado: 20)"
            )

        # Check CAPS
        if titulo == titulo.upper() and len(titulo) > 5:
            issues.append("Titulo todo em CAIXA ALTA")

        # Check banned words
        titulo_lower = titulo.lower()
        for word in TITLE_BANNED_WORDS:
            if word in titulo_lower:
                issues.append(f"Palavra proibida no titulo: '{word}'")

        # Check special chars
        special = re.findall(r"[?!:()@#]", titulo)
        if special:
            issues.append(f"Caracteres especiais proibidos: {', '.join(set(special))}")

        return len(issues) == 0, issues

    @staticmethod
    def validate_description(desc: str) -> Tuple[bool, List[str]]:
        """
        Valida descricao ML.
        Returns (is_valid, list_of_issues).
        """
        issues = []

        if not desc:
            return False, ["Descricao vazia"]

        # Word count
        words = desc.split()
        word_count = len(words)
        if word_count < ML_DESC_MIN_WORDS:
            issues.append(
                f"Descricao muito curta: {word_count}/{ML_DESC_MIN_WORDS} palavras"
            )

        # Check HTML
        html_tags = re.findall(r"<[^>]+>", desc)
        if html_tags:
            issues.append(f"Contem HTML: {', '.join(html_tags[:5])}")

        # Check HTML entities
        entities = re.findall(r"&\w+;", desc)
        if entities:
            issues.append(f"Contem HTML entities: {', '.join(entities[:5])}")

        # Check URLs
        urls = re.findall(r"https?://\S+", desc)
        if urls:
            issues.append(f"Contem URLs: {', '.join(urls[:3])}")

        # Check banned patterns
        for pattern in DESC_BANNED_PATTERNS:
            matches = re.findall(pattern, desc, re.IGNORECASE)
            if matches:
                issues.append(f"Contem termo proibido: '{matches[0]}'")

        # Check truncation (ends mid-sentence)
        desc_stripped = desc.rstrip()
        if desc_stripped and desc_stripped[-1] not in ".!?\n":
            last_line = desc_stripped.split("\n")[-1].strip()
            if len(last_line) > 20 and last_line[-1] not in ".!?":
                issues.append(
                    "Descricao pode estar truncada (nao termina com pontuacao)"
                )

        return len(issues) == 0, issues

    @staticmethod
    def validate_ficha_tecnica(ficha: Dict) -> Tuple[bool, List[str]]:
        """
        Valida ficha tecnica ML.
        Returns (is_valid, list_of_issues).
        """
        issues = []

        if not ficha:
            return False, ["Ficha tecnica vazia"]

        # Campos criticos
        if not ficha.get("marca") or ficha["marca"] == "Nao informado":
            issues.append("Marca nao identificada (obrigatorio para ML)")

        if not ficha.get("peso_liquido") or ficha["peso_liquido"] == "Nao informado":
            issues.append("Peso liquido nao informado (importante para ML)")

        return len(issues) == 0, issues

    @staticmethod
    def validate_all(enrichment: Dict) -> Dict[str, Any]:
        """
        Valida todo o enrichment de uma vez.
        Returns dict com resultado de cada campo.
        """
        results = {}

        titulo_ok, titulo_issues = MLValidator.validate_title(
            enrichment.get("titulo_ml", "")
        )
        results["titulo_ml"] = {"valid": titulo_ok, "issues": titulo_issues}

        desc_ok, desc_issues = MLValidator.validate_description(
            enrichment.get("descricao_ml", "")
        )
        results["descricao_ml"] = {"valid": desc_ok, "issues": desc_issues}

        ficha_ok, ficha_issues = MLValidator.validate_ficha_tecnica(
            enrichment.get("ficha_tecnica", {})
        )
        results["ficha_tecnica"] = {"valid": ficha_ok, "issues": ficha_issues}

        results["all_valid"] = titulo_ok and desc_ok and ficha_ok
        results["total_issues"] = (
            len(titulo_issues) + len(desc_issues) + len(ficha_issues)
        )

        return results
