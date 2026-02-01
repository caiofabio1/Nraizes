"""
Export Consultation Data for WordPress
Consolidates data from SQLite knowledge base + Excel scientific database
into a clean JSON file for the WordPress consultation tool.
"""

import sqlite3
import json
import pandas as pd
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "vault.db")
EXCEL_PATH = os.path.join(
    BASE_DIR, "tools", "Base de dados", "base_dados_cientifica_produtos.xlsx"
)
OUTPUT_PATH = os.path.join(
    BASE_DIR, "wp-content", "themes", "organium-child", "data", "consulta-produtos.json"
)


def safe_json_parse(value):
    """Parse JSON string safely."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return [value] if value else []


def clean_text(text):
    """Clean text encoding issues."""
    if not text:
        return ""
    # Fix common encoding artifacts
    replacements = {
        "ÃƒÂ£": "ã",
        "ÃƒÂ¡": "á",
        "ÃƒÂ©": "é",
        "ÃƒÂ­": "í",
        "ÃƒÂ³": "ó",
        "ÃƒÂº": "ú",
        "ÃƒÂ§": "ç",
        "ÃƒÂ": "à",
        "Ã£": "ã",
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã§": "ç",
        "Ã ": "à",
        "Ã¢": "â",
        "Ãª": "ê",
        "Ã´": "ô",
        "\\n": " ",
        "\\r": "",
        "\\t": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Remove multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_list(items):
    """Clean a list of strings."""
    if not items:
        return []
    return [clean_text(item) for item in items if item and clean_text(item)]


def normalize_product_name(name):
    """Normalize product name for deduplication."""
    name = name.lower().strip()
    # Remove volume/weight info
    name = re.sub(
        r"\d+\s*(ml|g|mg|kg|l|caps|cap|sachê|saches|sache|un|und)\b", "", name
    )
    # Remove brand suffixes
    name = re.sub(
        r"\s*-\s*(laszlo|ocean drop|central nutrition|avatim|brazo|taimin).*$",
        "",
        name,
        flags=re.IGNORECASE,
    )
    # Remove common suffixes
    name = re.sub(r"\s*(pct|cx|c/|kit|combo)\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def export_knowledge_base():
    """Export product knowledge from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT pk.*, p.nome, p.codigo
        FROM produto_conhecimento pk
        JOIN produtos p ON p.id_bling = pk.id_produto
        WHERE pk.confianca_score >= 0.7
        AND pk.categoria_produto IN ('suplemento', 'planta', 'oleo_essencial', 'cosmetico', 'alimento')
        ORDER BY p.nome
    """)

    products = {}
    for row in cursor.fetchall():
        row = dict(row)
        name = row["nome"]
        norm_name = normalize_product_name(name)

        # Keep best score version for duplicates
        if norm_name in products:
            if row["confianca_score"] <= products[norm_name]["_score"]:
                continue

        beneficios = safe_json_parse(row.get("beneficios"))
        indicacoes = safe_json_parse(row.get("indicacoes"))
        contraindicacoes = safe_json_parse(row.get("contraindicacoes"))
        interacoes = safe_json_parse(row.get("interacoes"))
        efeitos_colaterais = safe_json_parse(row.get("efeitos_colaterais"))
        alertas = safe_json_parse(row.get("alertas"))
        ingredientes = safe_json_parse(row.get("ingredientes"))
        principios_ativos = safe_json_parse(row.get("principios_ativos"))
        certificacoes = safe_json_parse(row.get("certificacoes"))
        referencias = safe_json_parse(row.get("referencias_cientificas"))
        faq = safe_json_parse(row.get("faq"))

        # Map category names to Portuguese display
        cat_map = {
            "suplemento": "Suplemento",
            "planta": "Planta / Chá",
            "oleo_essencial": "Óleo Essencial",
            "cosmetico": "Cosmético Natural",
            "alimento": "Alimento Natural",
        }

        products[norm_name] = {
            "_score": row["confianca_score"],
            "nome": clean_text(name),
            "categoria": cat_map.get(row["categoria_produto"], "Outro"),
            "categoria_slug": row["categoria_produto"],
            "ingredientes": clean_list(ingredientes),
            "principios_ativos": clean_list(principios_ativos),
            "modo_uso": clean_text(row.get("modo_uso", "")),
            "dosagem": clean_text(row.get("dosagem_recomendada", "")),
            "frequencia": clean_text(row.get("frequencia_uso", "")),
            "beneficios": clean_list(beneficios),
            "indicacoes": clean_list(indicacoes),
            "contraindicacoes": clean_list(contraindicacoes),
            "interacoes": clean_list(interacoes),
            "efeitos_colaterais": clean_list(efeitos_colaterais),
            "alertas": clean_list(alertas),
            "armazenamento": clean_text(row.get("armazenamento", "")),
            "origem": clean_text(row.get("origem", "")),
            "certificacoes": clean_list(certificacoes),
            "referencias": clean_list(referencias),
            "estudos_resumo": clean_text(row.get("estudos_resumo", "")),
            "faq": faq if isinstance(faq, list) else [],
            "fonte": "knowledge_base",
        }

    conn.close()

    # Remove internal score
    for p in products.values():
        del p["_score"]

    return list(products.values())


def export_scientific_database():
    """Export TCM formulas and supplements from Excel."""
    try:
        df = pd.read_excel(EXCEL_PATH)
    except Exception as e:
        print(f"Warning: Could not read Excel: {e}")
        return []

    products = []
    for _, row in df.iterrows():
        name = str(row.get("Fórmula (Pinyin)", "")).strip()
        if not name:
            continue

        # Parse DOI links
        doi_raw = str(row.get("DOI/Referência Principal", ""))
        referencias = []
        if doi_raw and doi_raw != "nan":
            for link in doi_raw.split(";"):
                link = link.strip()
                if link:
                    referencias.append(link)

        # Parse evidence level
        nivel = str(row.get("Nível de Evidência", "Baixa"))
        if nivel == "nan":
            nivel = "Baixa"

        # Determine category
        is_supplement = any(
            kw in name.lower()
            for kw in [
                "coenzyme",
                "coq10",
                "spirulina",
                "magnesium",
                "magnésio",
                "curcumin",
                "cúrcuma",
                "omega",
                "vitamina",
                "collagen",
            ]
        )

        chinese_name = str(row.get("Nome Chinês", ""))
        if chinese_name == "nan":
            chinese_name = ""

        indicacao = str(row.get("Indicação Principal (MTC)", ""))
        if indicacao == "nan":
            indicacao = ""

        aplicacoes = str(row.get("Aplicações Clínicas Baseadas em Evidências", ""))
        if aplicacoes == "nan":
            aplicacoes = ""

        dosagem = str(row.get("Dosagem Usual", ""))
        if dosagem == "nan":
            dosagem = ""

        evidencia = str(row.get("Evidência Científica (Resumo)", ""))
        if evidencia == "nan":
            evidencia = ""

        product = {
            "nome": name,
            "nome_chines": chinese_name,
            "categoria": "Suplemento Ocidental" if is_supplement else "Fórmula MTC",
            "categoria_slug": "suplemento" if is_supplement else "formula_mtc",
            "ingredientes": [],
            "principios_ativos": [],
            "modo_uso": "",
            "dosagem": dosagem,
            "frequencia": "",
            "indicacao_mtc": indicacao,
            "aplicacoes_clinicas": aplicacoes,
            "beneficios": [a.strip() for a in aplicacoes.split(";") if a.strip()]
            if aplicacoes
            else [],
            "indicacoes": [indicacao] if indicacao else [],
            "contraindicacoes": [],
            "interacoes": [],
            "efeitos_colaterais": [],
            "alertas": [],
            "armazenamento": "",
            "origem": "Medicina Tradicional Chinesa" if not is_supplement else "",
            "certificacoes": [],
            "referencias": referencias,
            "estudos_resumo": evidencia,
            "nivel_evidencia": nivel,
            "faq": [],
            "fonte": "base_cientifica",
        }
        products.append(product)

    return products


def expand_scientific_data():
    """Add more supplements and plants with scientific data."""
    expanded = [
        {
            "nome": "Vitamina D3 (Colecalciferol)",
            "categoria": "Suplemento Ocidental",
            "categoria_slug": "suplemento",
            "dosagem": "1.000-4.000 UI/dia (manutenção); até 10.000 UI sob orientação médica",
            "indicacao_mtc": "",
            "aplicacoes_clinicas": "Saúde óssea; Imunidade; Depressão sazonal; Prevenção de fraturas; Suporte em doenças autoimunes",
            "beneficios": [
                "Essencial para absorção de cálcio e saúde óssea",
                "Modulação do sistema imunológico",
                "Redução do risco de infecções respiratórias",
                "Melhora do humor e redução de sintomas depressivos",
                "Suporte na prevenção de doenças cardiovasculares",
            ],
            "indicacoes": [
                "Deficiência de vitamina D",
                "Osteoporose e osteopenia",
                "Imunidade baixa",
                "Depressão sazonal",
                "Idosos com pouca exposição solar",
            ],
            "contraindicacoes": ["Hipercalcemia", "Sarcoidose", "Hipervitaminose D"],
            "interacoes": [
                "Digoxina (risco de arritmia com hipercalcemia)",
                "Diuréticos tiazídicos (aumentam cálcio)",
                "Corticosteroides (reduzem absorção)",
            ],
            "efeitos_colaterais": [
                "Hipercalcemia em doses excessivas",
                "Náusea",
                "Constipação",
                "Calcificação renal em uso prolongado excessivo",
            ],
            "alertas": [
                "Monitorar níveis séricos de 25(OH)D",
                "Doses acima de 4.000 UI requerem acompanhamento médico",
                "Absorção melhorada com gordura na refeição",
            ],
            "referencias": [
                "https://pubmed.ncbi.nlm.nih.gov/28768407/",
                "https://pubmed.ncbi.nlm.nih.gov/31405892/",
                "https://pubmed.ncbi.nlm.nih.gov/33220155/",
            ],
            "estudos_resumo": "Meta-análises confirmam eficácia na prevenção de fraturas (com cálcio), redução de infecções respiratórias agudas (NNT=33) e associação com menor mortalidade por todas as causas. Evidência promissora para depressão e doenças autoimunes.",
            "nivel_evidencia": "Alta",
            "faq": [
                {
                    "pergunta": "Qual o melhor horário para tomar vitamina D?",
                    "resposta": "Preferencialmente com a refeição mais gordurosa do dia, pois é lipossolúvel e a absorção é melhor com gordura.",
                },
                {
                    "pergunta": "Preciso tomar vitamina D com vitamina K2?",
                    "resposta": "A K2 ajuda a direcionar o cálcio para os ossos em vez dos vasos sanguíneos. A combinação é recomendada, especialmente em doses altas de D3.",
                },
                {
                    "pergunta": "Como saber se tenho deficiência?",
                    "resposta": "Através do exame de sangue 25-hidroxivitamina D. Níveis abaixo de 20 ng/mL indicam deficiência; 30-60 ng/mL é considerado adequado.",
                },
            ],
            "fonte": "base_cientifica",
        },
        {
            "nome": "Vitamina B12 (Metilcobalamina)",
            "categoria": "Suplemento Ocidental",
            "categoria_slug": "suplemento",
            "dosagem": "500-1.000 mcg/dia (sublingual ou oral); 1.000-5.000 mcg para deficiência",
            "aplicacoes_clinicas": "Energia celular; Saúde neurológica; Anemia megaloblástica; Saúde cardiovascular (redução de homocisteína)",
            "beneficios": [
                "Essencial para formação de glóbulos vermelhos",
                "Suporte ao sistema nervoso e mielina",
                "Redução de fadiga e fraqueza",
                "Melhora da função cognitiva",
                "Redução de homocisteína (fator de risco cardiovascular)",
            ],
            "indicacoes": [
                "Vegetarianos e veganos",
                "Idosos (absorção reduzida)",
                "Anemia megaloblástica",
                "Neuropatia periférica",
                "Fadiga crônica",
            ],
            "contraindicacoes": [
                "Doença de Leber (neuropatia óptica hereditária)",
                "Alergia a cobalamina",
            ],
            "interacoes": [
                "Metformina (reduz absorção de B12)",
                "Inibidores de bomba de prótons (reduzem absorção)",
                "Colchicina (interfere na absorção)",
            ],
            "efeitos_colaterais": [
                "Muito raros em doses orais",
                "Acne em doses muito altas",
                "Reações alérgicas raras",
            ],
            "alertas": [
                "Forma metilcobalamina é preferível à cianocobalamina",
                "Veganos devem suplementar obrigatoriamente",
                "Deficiência pode causar danos neurológicos irreversíveis",
            ],
            "referencias": [
                "https://pubmed.ncbi.nlm.nih.gov/28660890/",
                "https://pubmed.ncbi.nlm.nih.gov/27572656/",
                "https://pubmed.ncbi.nlm.nih.gov/29076437/",
            ],
            "estudos_resumo": "Suplementação essencial para populações de risco (veganos, idosos, usuários de metformina). Estudos mostram que a deficiência afeta até 40% dos idosos e está associada a declínio cognitivo, depressão e neuropatia.",
            "nivel_evidencia": "Alta",
            "faq": [
                {
                    "pergunta": "Qual a diferença entre metilcobalamina e cianocobalamina?",
                    "resposta": "Metilcobalamina é a forma ativa, já pronta para uso pelo organismo. Cianocobalamina precisa ser convertida e contém um grupo ciano que deve ser eliminado.",
                },
                {
                    "pergunta": "Quem deve suplementar B12?",
                    "resposta": "Veganos, vegetarianos, idosos acima de 60 anos, usuários de metformina ou inibidores de bomba de prótons, e pessoas com doenças gastrointestinais.",
                },
                {
                    "pergunta": "B12 sublingual é melhor que comprimido?",
                    "resposta": "Para pessoas com problemas de absorção gástrica, a forma sublingual pode ser vantajosa pois é absorvida diretamente pela mucosa oral.",
                },
            ],
            "fonte": "base_cientifica",
        },
        {
            "nome": "Ashwagandha (Withania somnifera)",
            "categoria": "Suplemento Ocidental",
            "categoria_slug": "suplemento",
            "dosagem": "300-600mg/dia de extrato padronizado (KSM-66 ou Sensoril); dividir em 1-2 doses",
            "aplicacoes_clinicas": "Adaptógeno; Ansiedade; Estresse; Performance atlética; Saúde hormonal masculina",
            "beneficios": [
                "Redução significativa de cortisol e estresse",
                "Melhora da qualidade do sono",
                "Aumento da força e resistência muscular",
                "Melhora dos parâmetros de fertilidade masculina",
                "Efeito ansiolítico comparável a lorazepam em estudos animais",
            ],
            "indicacoes": [
                "Estresse crônico",
                "Ansiedade leve a moderada",
                "Insônia",
                "Fadiga adrenal",
                "Suporte à performance atlética",
                "Infertilidade masculina",
            ],
            "contraindicacoes": [
                "Hipertireoidismo (pode aumentar hormônios tireoidianos)",
                "Doenças autoimunes (pode estimular sistema imune)",
                "Gravidez",
            ],
            "interacoes": [
                "Sedativos e benzodiazepínicos (efeito aditivo)",
                "Medicamentos para tireoide",
                "Imunossupressores",
            ],
            "efeitos_colaterais": [
                "Sonolência",
                "Desconforto gastrointestinal",
                "Diarreia em doses altas",
            ],
            "alertas": [
                "Evitar na gravidez e lactação",
                "Pode alterar hormônios tireoidianos",
                "Suspender 2 semanas antes de cirurgias",
            ],
            "referencias": [
                "https://pubmed.ncbi.nlm.nih.gov/23439798/",
                "https://pubmed.ncbi.nlm.nih.gov/31517876/",
                "https://pubmed.ncbi.nlm.nih.gov/30854916/",
            ],
            "estudos_resumo": "Meta-análises mostram redução significativa de cortisol (até 30%), melhora em escalas de ansiedade (Hamilton e Beck) e aumento de testosterona e qualidade seminal. Extrato KSM-66 é o mais estudado clinicamente.",
            "nivel_evidencia": "Alta",
            "faq": [
                {
                    "pergunta": "Ashwagandha causa dependência?",
                    "resposta": "Não. Diferente de ansiolíticos farmacêuticos, a ashwagandha não causa dependência física ou tolerância significativa.",
                },
                {
                    "pergunta": "Posso tomar à noite?",
                    "resposta": "Sim, muitas pessoas preferem tomar à noite pois ajuda na qualidade do sono. Pode ser dividida em manhã e noite.",
                },
                {
                    "pergunta": "Quanto tempo leva para fazer efeito?",
                    "resposta": "Efeitos no estresse e sono podem ser percebidos em 2-4 semanas. Benefícios completos geralmente após 8-12 semanas de uso contínuo.",
                },
            ],
            "fonte": "base_cientifica",
        },
        {
            "nome": "Probióticos (Lactobacillus / Bifidobacterium)",
            "categoria": "Suplemento Ocidental",
            "categoria_slug": "suplemento",
            "dosagem": "1-50 bilhões de UFC/dia dependendo da indicação; manutenção: 5-10 bilhões UFC",
            "aplicacoes_clinicas": "Saúde intestinal; Imunidade; Diarreia associada a antibióticos; Síndrome do intestino irritável; Eczema atópica",
            "beneficios": [
                "Restauração da microbiota intestinal",
                "Fortalecimento da barreira intestinal",
                "Modulação do sistema imunológico",
                "Produção de vitaminas do complexo B e K",
                "Redução de inflamação sistêmica",
            ],
            "indicacoes": [
                "Após uso de antibióticos",
                "Síndrome do intestino irritável",
                "Constipação crônica",
                "Infecções urinárias recorrentes",
                "Prevenção de eczema em crianças de risco",
            ],
            "contraindicacoes": [
                "Imunossupressão grave",
                "Pancreatite aguda grave",
                "Cateter venoso central (risco teórico)",
            ],
            "interacoes": [
                "Antibióticos (tomar com 2h de intervalo)",
                "Antifúngicos (podem reduzir eficácia de probióticos à base de levedura)",
            ],
            "efeitos_colaterais": [
                "Gases e distensão nos primeiros dias",
                "Desconforto abdominal transitório",
            ],
            "alertas": [
                "Cada cepa tem indicações específicas",
                "Refrigeração pode ser necessária",
                "Não substituem tratamento médico para condições graves",
            ],
            "referencias": [
                "https://pubmed.ncbi.nlm.nih.gov/28639575/",
                "https://pubmed.ncbi.nlm.nih.gov/31584359/",
                "https://pubmed.ncbi.nlm.nih.gov/29536849/",
            ],
            "estudos_resumo": "Forte evidência para prevenção de diarreia associada a antibióticos (NNT=13), melhora de SII (especialmente Bifidobacterium infantis) e prevenção de eczema atópica em crianças. Eixo intestino-cérebro é área emergente de pesquisa.",
            "nivel_evidencia": "Alta",
            "faq": [
                {
                    "pergunta": "Preciso tomar em jejum?",
                    "resposta": "Preferencialmente 30 min antes da refeição ou com alimentos. Cápsulas gastrorresistentes podem ser tomadas a qualquer hora.",
                },
                {
                    "pergunta": "Posso tomar probiótico junto com antibiótico?",
                    "resposta": "Sim, mas com intervalo mínimo de 2 horas. Comece durante o antibiótico e continue por pelo menos 2 semanas após.",
                },
                {
                    "pergunta": "Todos os probióticos são iguais?",
                    "resposta": "Não. Cada cepa tem funções específicas. Lactobacillus rhamnosus GG é indicado para diarreia, Bifidobacterium infantis para SII, Lactobacillus reuteri para cólica infantil.",
                },
            ],
            "fonte": "base_cientifica",
        },
        {
            "nome": "Melatonina",
            "categoria": "Suplemento Ocidental",
            "categoria_slug": "suplemento",
            "dosagem": "0,3-5mg, 30-60 min antes de dormir. Iniciar com dose mais baixa.",
            "aplicacoes_clinicas": "Insônia; Jet lag; Distúrbios do ritmo circadiano; Ansiedade pré-operatória",
            "beneficios": [
                "Regulação do ritmo circadiano",
                "Redução da latência do sono",
                "Potente antioxidante",
                "Efeito ansiolítico pré-operatório",
                "Suporte ao sistema imunológico",
            ],
            "indicacoes": [
                "Insônia de início",
                "Jet lag",
                "Trabalho noturno",
                "Idosos com produção reduzida",
                "Crianças com TEA (sob orientação)",
            ],
            "contraindicacoes": [
                "Doenças autoimunes (uso cauteloso)",
                "Depressão grave",
                "Epilepsia não controlada",
            ],
            "interacoes": [
                "Anticoagulantes (pode aumentar efeito)",
                "Medicamentos para diabetes (altera glicemia)",
                "Imunossupressores",
                "Sedativos e álcool",
            ],
            "efeitos_colaterais": [
                "Sonolência matinal",
                "Cefaleia",
                "Tontura",
                "Náusea",
            ],
            "alertas": [
                "Não dirigir após ingestão",
                "Doses maiores não significam melhor efeito",
                "Liberação prolongada pode ser melhor para manutenção do sono",
            ],
            "referencias": [
                "https://pubmed.ncbi.nlm.nih.gov/28648359/",
                "https://pubmed.ncbi.nlm.nih.gov/30215696/",
                "https://pubmed.ncbi.nlm.nih.gov/31070246/",
            ],
            "estudos_resumo": "Meta-análises mostram redução da latência do sono em 7 min e aumento da duração em 8 min. Eficácia mais pronunciada em idosos e distúrbios de ritmo circadiano. Dose ótima: 0,5-1mg para insônia; 3-5mg para jet lag.",
            "nivel_evidencia": "Alta",
            "faq": [
                {
                    "pergunta": "Melatonina causa dependência?",
                    "resposta": "Não. Diferente de sedativos, a melatonina não causa dependência física, tolerância ou abstinência.",
                },
                {
                    "pergunta": "Qual a dose ideal?",
                    "resposta": "Doses entre 0,3-1mg são frequentemente tão eficazes quanto doses maiores. Comece com 0,5mg e ajuste conforme necessidade.",
                },
                {
                    "pergunta": "Crianças podem tomar?",
                    "resposta": "Apenas sob orientação médica. Há evidência para uso em crianças com TEA e TDAH, mas a segurança a longo prazo não está totalmente estabelecida.",
                },
            ],
            "fonte": "base_cientifica",
        },
        {
            "nome": "Zinco",
            "categoria": "Suplemento Ocidental",
            "categoria_slug": "suplemento",
            "dosagem": "15-30mg/dia (elementar). Picolinato ou bisglicinato: melhor absorção. Não exceder 40mg/dia.",
            "aplicacoes_clinicas": "Imunidade; Saúde da pele; Fertilidade masculina; Cicatrização; Resfriados",
            "beneficios": [
                "Fortalecimento do sistema imunológico",
                "Essencial para mais de 300 enzimas",
                "Melhora da saúde da pele e acne",
                "Suporte à fertilidade masculina",
                "Redução da duração de resfriados",
            ],
            "indicacoes": [
                "Deficiência de zinco",
                "Acne",
                "Resfriados frequentes",
                "Vegetarianos (maior necessidade)",
                "Cicatrização de feridas",
            ],
            "contraindicacoes": [
                "Insuficiência renal grave",
                "Doença de Wilson (metabolismo do cobre)",
            ],
            "interacoes": [
                "Antibióticos quinolonas e tetraciclinas (reduz absorção de ambos)",
                "Penicilamina",
                "Suplementos de cobre e ferro (competição na absorção)",
            ],
            "efeitos_colaterais": [
                "Náusea (especialmente em jejum)",
                "Gosto metálico",
                "Deficiência de cobre em uso prolongado",
            ],
            "alertas": [
                "Tomar com alimento para reduzir náusea",
                "Uso prolongado >40mg requer suplementação de cobre",
                "Forma quelada (bisglicinato) é mais gentil ao estômago",
            ],
            "referencias": [
                "https://pubmed.ncbi.nlm.nih.gov/28515951/",
                "https://pubmed.ncbi.nlm.nih.gov/31305906/",
                "https://pubmed.ncbi.nlm.nih.gov/28944596/",
            ],
            "estudos_resumo": "Meta-análise Cochrane: zinco oral reduz duração de resfriados em 33% se iniciado em 24h dos sintomas. Evidência forte para tratamento de acne (sulfato de zinco 30-45mg) e melhora de parâmetros seminais em homens inférteis.",
            "nivel_evidencia": "Alta",
            "faq": [
                {
                    "pergunta": "Qual a melhor forma de zinco?",
                    "resposta": "Picolinato e bisglicinato de zinco têm melhor absorção e menos efeitos gastrointestinais. Óxido de zinco tem a pior biodisponibilidade.",
                },
                {
                    "pergunta": "Zinco ajuda na imunidade contra gripes?",
                    "resposta": "Sim. Tomar zinco nas primeiras 24h dos sintomas reduz a duração em cerca de 1-2 dias. Pastilhas de acetato de zinco são as mais eficazes para resfriados.",
                },
                {
                    "pergunta": "Posso tomar zinco com ferro?",
                    "resposta": "Evite tomar juntos pois competem pela absorção. Separe por pelo menos 2 horas entre zinco e suplementos de ferro.",
                },
            ],
            "fonte": "base_cientifica",
        },
        {
            "nome": "Colágeno Hidrolisado (Tipo I e II)",
            "categoria": "Suplemento Ocidental",
            "categoria_slug": "suplemento",
            "dosagem": "Tipo I: 2,5-10g/dia; Tipo II: 40mg/dia (não desnaturado - UC-II)",
            "aplicacoes_clinicas": "Saúde articular; Pele; Unhas e cabelos; Osteoartrite; Sarcopenia",
            "beneficios": [
                "Melhora da elasticidade e hidratação da pele",
                "Redução de dor articular",
                "Fortalecimento de unhas e cabelos",
                "Suporte à saúde óssea",
                "Preservação de massa muscular em idosos",
            ],
            "indicacoes": [
                "Envelhecimento da pele",
                "Osteoartrite",
                "Osteopenia",
                "Unhas frágeis",
                "Atletas com desgaste articular",
            ],
            "contraindicacoes": [
                "Alergia a peixes ou frutos do mar (colágeno marinho)",
                "Fenilcetonúria (contém fenilalanina)",
            ],
            "interacoes": ["Sem interações medicamentosas significativas conhecidas"],
            "efeitos_colaterais": [
                "Plenitude gástrica",
                "Gosto residual desagradável",
                "Hipercalcemia (se fonte bovina com alto cálcio)",
            ],
            "alertas": [
                "Colágeno tipo II (UC-II) tem mecanismo diferente do hidrolisado",
                "Peptídeos de colágeno (2,5-5g) são tão eficazes quanto doses maiores para pele",
                "Vitamina C é cofator essencial para síntese",
            ],
            "referencias": [
                "https://pubmed.ncbi.nlm.nih.gov/30681787/",
                "https://pubmed.ncbi.nlm.nih.gov/26362110/",
                "https://pubmed.ncbi.nlm.nih.gov/28786550/",
            ],
            "estudos_resumo": "RCTs duplo-cegos mostram melhora significativa na elasticidade da pele após 8 semanas (2,5g/dia), redução de rugas e aumento de pró-colágeno tipo I. Para articulações, UC-II (40mg) foi superior a glucosamina+condroitina em estudo de 180 dias.",
            "nivel_evidencia": "Moderada-Alta",
            "faq": [
                {
                    "pergunta": "Colágeno em pó ou cápsulas?",
                    "resposta": "Pó permite maior dose por porção (5-10g) de forma prática. Cápsulas são mais convenientes mas requerem múltiplas unidades para atingir a dose eficaz.",
                },
                {
                    "pergunta": "Qual a diferença entre tipo I, II e III?",
                    "resposta": "Tipo I: pele, ossos e tendões (o mais abundante). Tipo II: cartilagem articular. Tipo III: pele e vasos sanguíneos. Para articulações, prefira tipo II; para pele, tipo I.",
                },
                {
                    "pergunta": "Preciso tomar vitamina C junto?",
                    "resposta": "Sim, idealmente. Vitamina C é essencial como cofator na síntese de colágeno. Tomar 100-200mg de vitamina C junto com o colágeno potencializa os resultados.",
                },
            ],
            "fonte": "base_cientifica",
        },
        {
            "nome": "Clorella (Chlorella vulgaris)",
            "categoria": "Suplemento Ocidental",
            "categoria_slug": "suplemento",
            "dosagem": "2-10g/dia em pó ou comprimidos. Iniciar com 1-2g e aumentar gradualmente.",
            "aplicacoes_clinicas": "Desintoxicação de metais pesados; Perfil lipídico; Imunidade; Nutrição",
            "beneficios": [
                "Rica em clorofila e nutrientes (proteína, ferro, B12)",
                "Auxilia na eliminação de metais pesados",
                "Melhora do perfil lipídico",
                "Suporte ao sistema imunológico",
                "Propriedades antioxidantes",
            ],
            "indicacoes": [
                "Desintoxicação",
                "Suplementação nutricional",
                "Colesterol elevado",
                "Anemia por deficiência de ferro",
                "Suporte imunológico",
            ],
            "contraindicacoes": [
                "Alergia a algas ou iodo",
                "Uso de warfarina (contém vitamina K)",
                "Doenças autoimunes (pode estimular imunidade)",
            ],
            "interacoes": ["Warfarina (vitamina K antagoniza)", "Imunossupressores"],
            "efeitos_colaterais": [
                "Gases e distensão inicial",
                "Fezes esverdeadas (normal)",
                "Fotossensibilidade em raros casos",
            ],
            "alertas": [
                "Escolher marcas com certificação de pureza (sem contaminantes)",
                "Parede celular deve ser quebrada para absorção",
                "Iniciar com dose baixa para adaptação",
            ],
            "referencias": [
                "https://pubmed.ncbi.nlm.nih.gov/25320462/",
                "https://pubmed.ncbi.nlm.nih.gov/24920270/",
                "https://pubmed.ncbi.nlm.nih.gov/29097438/",
            ],
            "estudos_resumo": "Estudos demonstram capacidade de quelação de metais pesados (dioxinas, cádmio), redução de triglicerídeos e LDL, e aumento de IgA. RCT com 12 semanas mostrou redução significativa de triglicerídeos em indivíduos com hiperlipidemia.",
            "nivel_evidencia": "Moderada",
            "faq": [
                {
                    "pergunta": "Chlorella e spirulina são a mesma coisa?",
                    "resposta": "Não. Chlorella é uma alga verde unicelular rica em clorofila e com capacidade de desintoxicação. Spirulina é uma cianobactéria azul-esverdeada mais rica em proteínas e ficocianina.",
                },
                {
                    "pergunta": "Para que serve a desintoxicação com clorella?",
                    "resposta": "A clorella se liga a metais pesados como mercúrio, chumbo e cádmio no trato digestivo, facilitando sua eliminação. É usada especialmente em protocolos de remoção de amálgama dental.",
                },
                {
                    "pergunta": "Quanto tempo leva para sentir benefícios?",
                    "resposta": "Efeitos na energia e digestão podem ser sentidos em 1-2 semanas. Benefícios no perfil lipídico e desintoxicação: 4-12 semanas.",
                },
            ],
            "fonte": "base_cientifica",
        },
    ]

    # Add common plant entries
    plants = [
        {
            "nome": "Alcachofra (Cynara scolymus)",
            "categoria": "Planta / Chá",
            "categoria_slug": "planta",
            "dosagem": "Chá: 1-2 colheres de sopa em 250ml de água quente, 2-3x/dia. Extrato: 300-600mg/dia",
            "aplicacoes_clinicas": "Digestão; Proteção hepática; Colesterol; Dispepsia funcional",
            "beneficios": [
                "Estimula a produção e secreção de bile",
                "Ação hepatoprotetora",
                "Redução do colesterol LDL",
                "Melhora da digestão de gorduras",
                "Propriedades antioxidantes (cinarina e luteolina)",
            ],
            "indicacoes": [
                "Dispepsia funcional",
                "Colesterol elevado",
                "Má digestão de gorduras",
                "Proteção hepática",
            ],
            "contraindicacoes": [
                "Obstrução biliar",
                "Cálculos biliares",
                "Alergia a plantas da família Asteraceae",
            ],
            "interacoes": [
                "Estatinas (efeito aditivo na redução de colesterol)",
                "Anticoagulantes (uso cauteloso)",
            ],
            "efeitos_colaterais": [
                "Gases",
                "Fezes amolecidas",
                "Reação alérgica em sensíveis a Asteraceae",
            ],
            "alertas": [
                "Não usar se houver obstrução do ducto biliar",
                "Consultar médico se houver cálculos biliares",
            ],
            "referencias": [
                "https://pubmed.ncbi.nlm.nih.gov/25776008/",
                "https://pubmed.ncbi.nlm.nih.gov/29520889/",
            ],
            "estudos_resumo": "Meta-análise de 9 RCTs mostra redução significativa de colesterol total e LDL. Cochrane: eficácia em dispepsia funcional com boa tolerabilidade. Cinarina é o principal princípio ativo hepatoprotetor.",
            "nivel_evidencia": "Moderada-Alta",
            "faq": [
                {
                    "pergunta": "Chá de alcachofra emagrece?",
                    "resposta": "Não diretamente. Auxilia na digestão e função hepática, o que pode indiretamente apoiar programas de perda de peso, mas não é um termogênico.",
                },
                {
                    "pergunta": "Pode tomar em jejum?",
                    "resposta": "Sim, pode ser tomado em jejum ou antes das refeições para estimular a função digestiva e biliar.",
                },
            ],
            "fonte": "base_cientifica",
        },
        {
            "nome": "Camomila (Matricaria chamomilla)",
            "categoria": "Planta / Chá",
            "categoria_slug": "planta",
            "dosagem": "Chá: 1-2 sachês ou 2-3g de flores secas em 250ml, até 4x/dia. Extrato: 220-1100mg/dia",
            "aplicacoes_clinicas": "Ansiedade; Insônia; Cólicas; Anti-inflamatório; Saúde digestiva",
            "beneficios": [
                "Efeito calmante e ansiolítico",
                "Anti-inflamatório suave",
                "Melhora da qualidade do sono",
                "Alívio de cólicas e espasmos",
                "Propriedades antimicrobianas",
            ],
            "indicacoes": [
                "Ansiedade leve",
                "Dificuldade para dormir",
                "Cólicas menstruais e intestinais",
                "Irritação da pele",
                "Inflamação da mucosa oral",
            ],
            "contraindicacoes": [
                "Alergia a plantas da família Asteraceae",
                "Primeiro trimestre da gravidez (doses altas)",
            ],
            "interacoes": [
                "Anticoagulantes (cumarinas naturais)",
                "Sedativos (efeito aditivo)",
                "Ciclosporina (pode alterar níveis)",
            ],
            "efeitos_colaterais": ["Dermatite de contato (raro)", "Sonolência"],
            "alertas": [
                "Segura para uso prolongado em doses de chá",
                "Pode ser usada em crianças (doses menores)",
                "Evitar uso tópico se alergia a Asteraceae",
            ],
            "referencias": [
                "https://pubmed.ncbi.nlm.nih.gov/27912875/",
                "https://pubmed.ncbi.nlm.nih.gov/28233153/",
            ],
            "estudos_resumo": "RCT demonstrou eficácia significativa na redução de ansiedade generalizada (TAG) comparável a ansiolíticos leves. Evidência para melhora do sono em idosos e gestantes. Apigenina é o principal flavonoide ativo.",
            "nivel_evidencia": "Moderada",
            "faq": [
                {
                    "pergunta": "Grávidas podem tomar camomila?",
                    "resposta": "Em doses moderadas de chá (1-2 xícaras/dia), geralmente é seguro após o primeiro trimestre. Extratos concentrados devem ser evitados. Consulte seu obstetra.",
                },
                {
                    "pergunta": "Camomila interfere com medicamentos?",
                    "resposta": "Pode potencializar efeitos de anticoagulantes e sedativos. Se usa warfarina ou benzodiazepínicos, consulte seu médico.",
                },
            ],
            "fonte": "base_cientifica",
        },
        {
            "nome": "Gengibre (Zingiber officinale)",
            "categoria": "Planta / Chá",
            "categoria_slug": "planta",
            "dosagem": "Chá: 1-2g de raiz fresca em 250ml. Cápsulas: 250-1000mg/dia. Náusea: 1g dividido em doses.",
            "aplicacoes_clinicas": "Náusea; Anti-inflamatório; Digestão; Dor muscular; Dismenorreia",
            "beneficios": [
                "Potente antiemético (náusea e vômito)",
                "Anti-inflamatório natural (gingeróis)",
                "Melhora da motilidade gástrica",
                "Alívio de dor menstrual",
                "Efeito termogênico",
            ],
            "indicacoes": [
                "Náusea gestacional",
                "Enjoo de movimento",
                "Pós-operatório (náusea)",
                "Dismenorreia",
                "Osteoartrite",
            ],
            "contraindicacoes": [
                "Cálculos biliares (estimula bile)",
                "Distúrbios hemorrágicos",
                "Pré-operatório (suspender 1 semana antes)",
            ],
            "interacoes": [
                "Anticoagulantes (aumenta risco de sangramento)",
                "Medicamentos para diabetes (pode potencializar hipoglicemia)",
                "Anti-hipertensivos",
            ],
            "efeitos_colaterais": [
                "Azia em doses altas",
                "Desconforto abdominal",
                "Dermatite de contato (uso tópico)",
            ],
            "alertas": [
                "Limitar a 1g/dia na gravidez",
                "Suspender antes de cirurgias",
                "Pode causar azia se tomado em jejum em pessoas sensíveis",
            ],
            "referencias": [
                "https://pubmed.ncbi.nlm.nih.gov/25872115/",
                "https://pubmed.ncbi.nlm.nih.gov/29065441/",
                "https://pubmed.ncbi.nlm.nih.gov/30680163/",
            ],
            "estudos_resumo": "Cochrane: eficaz para náusea gestacional e pós-operatória. Meta-análise: 1g/dia reduz dismenorreia comparável a ibuprofeno. Anti-inflamatório: gingeróis inibem COX-2 e LOX-5.",
            "nivel_evidencia": "Alta",
            "faq": [
                {
                    "pergunta": "Gengibre é seguro na gravidez?",
                    "resposta": "Sim, até 1g/dia é considerado seguro e eficaz para enjoo matinal. É uma das poucas opções com evidência para náusea gestacional.",
                },
                {
                    "pergunta": "Gengibre emagrece?",
                    "resposta": "Tem efeito termogênico leve e melhora a digestão, mas o efeito direto na perda de peso é modesto. Pode ser um coadjuvante em programas de emagrecimento.",
                },
            ],
            "fonte": "base_cientifica",
        },
    ]

    return expanded + plants


def merge_and_export():
    """Merge all data sources and export."""
    print("Loading knowledge base from SQLite...")
    kb_products = export_knowledge_base()
    print(f"  -> {len(kb_products)} products from knowledge base")

    print("Loading scientific database from Excel...")
    sci_products = export_scientific_database()
    print(f"  -> {len(sci_products)} formulas from scientific database")

    print("Adding expanded supplement/plant data...")
    expanded = expand_scientific_data()
    print(f"  -> {len(expanded)} expanded entries")

    # Merge: scientific DB + expanded first (higher quality), then KB
    all_products = sci_products + expanded + kb_products

    # Deduplicate by normalized name, preferring scientific/expanded data
    seen = {}
    final = []
    for p in all_products:
        norm = normalize_product_name(p["nome"])
        if norm not in seen:
            seen[norm] = True
            final.append(p)

    # Sort by category then name
    cat_order = {
        "formula_mtc": 0,
        "suplemento": 1,
        "planta": 2,
        "oleo_essencial": 3,
        "cosmetico": 4,
        "alimento": 5,
    }
    final.sort(
        key=lambda x: (
            cat_order.get(x.get("categoria_slug", ""), 99),
            x.get("nome", ""),
        )
    )

    # Build category summary
    categories = {}
    for p in final:
        cat = p.get("categoria", "Outro")
        categories[cat] = categories.get(cat, 0) + 1

    output = {
        "versao": "2.0",
        "atualizado_em": datetime.now().strftime("%Y-%m-%d"),
        "total_produtos": len(final),
        "categorias": categories,
        "aviso_legal": "As informações aqui contidas têm caráter estritamente educativo e informativo. Não substituem o aconselhamento médico profissional. Consulte sempre um profissional de saúde qualificado antes de iniciar qualquer tratamento ou suplementação.",
        "produtos": final,
    }

    # Ensure output directory
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nExported {len(final)} products to {OUTPUT_PATH}")
    print(f"Categories: {categories}")
    return output


if __name__ == "__main__":
    merge_and_export()
