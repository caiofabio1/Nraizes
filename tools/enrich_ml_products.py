#!/usr/bin/env python3
"""
Enriquecer produtos selecionados para Mercado Livre usando IA (Gemini).

Gera conteudo ML-otimizado:
- Titulo PMME (Produto + Marca + Modelo + Especificacao, max 60 chars)
- Descricao complementar (400-600 palavras, sem HTML, regras ML)
- Descricao curta (max 150 chars)
- Ficha tecnica (marca, formato, tipo, sabor, vegano, sem gluten)

As propostas ficam na tabela propostas_ia com status 'pendente'.
Depois de revisar no dashboard (localhost:5000), aprovar e sincronizar com Bling:
    python src/sync_ml_enrichment.py --aplicar

Uso:
    python tools/enrich_ml_products.py              # Enriquecer todos sem descricao
    python tools/enrich_ml_products.py --preview     # Apenas listar o que seria enriquecido
    python tools/enrich_ml_products.py --all         # Enriquecer TODOS os 50 (mesmo com descricao)
    python tools/enrich_ml_products.py --validate    # Validar propostas ML existentes
"""

import sys
import os
import json
import time

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

from database import VaultDB
from ml_enricher import MLProductEnricher, MLValidator
from logger import get_logger

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
ML_SELECTION_FILE = os.path.join(DATA_DIR, "ml_top50_candidates.json")

logger = get_logger("enrich_ml")


def load_ml_products(only_missing_desc: bool = True):
    """Load the ML top 50 selection, optionally filtering to those missing descriptions."""
    # Try curated selection first, then candidates
    if os.path.exists(os.path.join(DATA_DIR, "ml_50_selecionados.json")):
        path = os.path.join(DATA_DIR, "ml_50_selecionados.json")
    elif os.path.exists(ML_SELECTION_FILE):
        path = ML_SELECTION_FILE
    else:
        print("  [ERRO] Nenhum arquivo de selecao ML encontrado.")
        print("  Rode primeiro: python tools/vincular_produtos_ml.py --status")
        return []

    with open(path, "r", encoding="utf-8") as f:
        products = json.load(f)

    if only_missing_desc:
        return [p for p in products if not p.get("has_desc", True)]
    return products


def validate_existing_proposals(db: VaultDB):
    """Valida propostas ML pendentes existentes no banco."""
    conn = db._get_conn()
    cursor = conn.cursor()

    ml_types = ("titulo_ml", "descricao_curta_ml", "descricao_ml", "ficha_tecnica_ml")
    placeholders = ",".join(["?" for _ in ml_types])

    cursor.execute(
        f"""
        SELECT p.*, pr.nome as produto_nome, pr.codigo as produto_codigo
        FROM propostas_ia p
        JOIN produtos pr ON p.id_produto = pr.id_bling
        WHERE p.status = 'pendente' AND p.tipo IN ({placeholders})
        ORDER BY p.id_produto, p.tipo
    """,
        list(ml_types),
    )

    rows = cursor.fetchall()
    if not rows:
        print("  Nenhuma proposta ML pendente para validar.")
        return

    # Agrupar por produto
    from collections import defaultdict

    products = defaultdict(dict)
    for row in rows:
        row = dict(row)
        pid = row["id_produto"]
        products[pid]["nome"] = row.get("produto_nome", "")
        products[pid]["codigo"] = row.get("produto_codigo", "")

        tipo = row["tipo"]
        conteudo = row["conteudo_proposto"]

        if tipo == "titulo_ml":
            products[pid]["titulo_ml"] = conteudo
        elif tipo == "descricao_ml":
            products[pid]["descricao_ml"] = conteudo
        elif tipo == "ficha_tecnica_ml":
            try:
                products[pid]["ficha_tecnica"] = json.loads(conteudo)
            except json.JSONDecodeError:
                products[pid]["ficha_tecnica"] = {}

    print()
    print("=" * 80)
    print("  VALIDACAO DE PROPOSTAS ML PENDENTES")
    print("=" * 80)

    total_ok = 0
    total_issues = 0

    for pid, data in products.items():
        result = MLValidator.validate_all(data)
        status = (
            "OK" if result["all_valid"] else f"{result['total_issues']} problema(s)"
        )

        if result["all_valid"]:
            total_ok += 1
        else:
            total_issues += 1

        print(f"\n  [{data.get('codigo', '???'):<22}] {status}")

        for field, field_result in result.items():
            if isinstance(field_result, dict) and not field_result.get("valid", True):
                for issue in field_result["issues"]:
                    print(f"    -> {issue}")

    print()
    print(f"  RESUMO: {total_ok} OK | {total_issues} com problemas")
    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Enriquecer produtos ML com IA (Gemini) - Titulo PMME + Descricao + Ficha Tecnica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Fluxo completo:
  1. python tools/enrich_ml_products.py           # Gerar propostas IA
  2. python src/web_dashboard.py                   # Revisar no dashboard
  3. python src/sync_ml_enrichment.py --aplicar    # Sincronizar com Bling
        """,
    )
    parser.add_argument(
        "--preview", action="store_true", help="Apenas listar, nao enriquecer"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Enriquecer TODOS os 50 (mesmo os que ja tem descricao)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validar propostas ML pendentes existentes",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash",
        help="Modelo Gemini (default: gemini-2.0-flash)",
    )
    args = parser.parse_args()

    db = VaultDB()

    # Modo validacao
    if args.validate:
        validate_existing_proposals(db)
        return 0

    # 1. Carregar produtos ML
    print()
    print("=" * 80)
    print("  ENRICHMENT ML - TITULO PMME + DESCRICAO + FICHA TECNICA")
    print("=" * 80)

    products_data = load_ml_products(only_missing_desc=not args.all)

    if not products_data:
        if args.all:
            print("  Nenhum produto na selecao ML!")
        else:
            print("  Todos os produtos ML ja tem descricao!")
            print("  Use --all para re-enriquecer todos.")
        return 0

    print(f"  {len(products_data)} produto(s) para enriquecer:")
    print()
    for i, p in enumerate(products_data, 1):
        has_desc = "SIM" if p.get("has_desc") else "---"
        print(
            f"  {i:2d}. {p.get('codigo', '???'):<25} R${p.get('preco', 0):8.2f}  "
            f"DESC={has_desc}  {p.get('nome', '')[:45]}"
        )

    if args.preview:
        print(f"\n  Modo --preview: nada sera alterado.")
        return 0

    # 2. Buscar dados completos do vault.db para cada produto
    print()
    print("-" * 80)
    print(f"  Iniciando enrichment ML com Gemini ({args.model})...")
    print("-" * 80)
    print()

    enricher = MLProductEnricher(model_name=args.model)
    total = len(products_data)
    success = 0
    errors = []

    for i, p in enumerate(products_data, 1):
        bling_id = p.get("id_bling")
        nome = p.get("nome", "")
        codigo = p.get("codigo", "")

        print(f"  [{i:2d}/{total}] {nome[:60]}...")

        # Verificar se ja tem propostas ML (evitar duplicatas)
        conn = db._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM propostas_ia WHERE id_produto = ? AND tipo = 'titulo_ml'",
            (bling_id,),
        )
        if cursor.fetchone()[0] > 0:
            print(f"           [SKIP] Ja tem propostas ML")
            continue

        # Buscar produto completo do DB
        full_product = db.get_produto_by_bling_id(bling_id)
        if not full_product:
            print(f"           [ERRO] Produto {bling_id} nao encontrado no vault.db")
            errors.append({"codigo": codigo, "erro": "Nao encontrado no vault.db"})
            continue

        # Enriquecer
        try:
            enrichment = enricher.enrich_product(full_product)
        except Exception as e:
            print(f"           [ERRO] Gemini falhou: {str(e)[:80]}")
            errors.append({"codigo": codigo, "erro": str(e)[:100]})
            time.sleep(2)
            continue

        if not enrichment:
            print(f"           [ERRO] Enrichment retornou vazio")
            errors.append({"codigo": codigo, "erro": "Retorno vazio"})
            continue

        # Validar resultado
        validation = MLValidator.validate_all(enrichment)
        if not validation["all_valid"]:
            issues_str = []
            for field, res in validation.items():
                if isinstance(res, dict) and not res.get("valid", True):
                    issues_str.extend(res["issues"])
            print(
                f"           [AVISO] {validation['total_issues']} problema(s): {'; '.join(issues_str[:2])}"
            )

        # Criar propostas
        proposals_created = 0

        if enrichment.get("titulo_ml"):
            db.create_proposta(
                id_produto=bling_id,
                tipo="titulo_ml",
                conteudo_original=full_product.get("nome", ""),
                conteudo_proposto=enrichment["titulo_ml"],
            )
            proposals_created += 1

        if enrichment.get("descricao_curta"):
            db.create_proposta(
                id_produto=bling_id,
                tipo="descricao_curta_ml",
                conteudo_original=full_product.get("descricao_curta", "") or "",
                conteudo_proposto=enrichment["descricao_curta"],
            )
            proposals_created += 1

        if enrichment.get("descricao_ml"):
            db.create_proposta(
                id_produto=bling_id,
                tipo="descricao_ml",
                conteudo_original=full_product.get("descricao_complementar", "") or "",
                conteudo_proposto=enrichment["descricao_ml"],
            )
            proposals_created += 1

        if enrichment.get("ficha_tecnica"):
            ficha_json = json.dumps(enrichment["ficha_tecnica"], ensure_ascii=False)
            db.create_proposta(
                id_produto=bling_id,
                tipo="ficha_tecnica_ml",
                conteudo_original="",
                conteudo_proposto=ficha_json,
            )
            proposals_created += 1

        titulo_preview = enrichment.get("titulo_ml", "")[:55]
        print(f'           [OK] {proposals_created} propostas | "{titulo_preview}"')
        success += 1

        # Rate limit (Gemini free tier: ~15 RPM)
        if i < total:
            time.sleep(4)

    # 3. Relatorio
    print()
    print("=" * 80)
    print("  RESULTADO")
    print("=" * 80)
    print(f"  Produtos processados: {total}")
    print(f"  Sucesso:              {success}")
    print(f"  Erros:                {len(errors)}")
    print()

    if errors:
        print("  ERROS:")
        for e in errors:
            print(f"    {e['codigo']}: {e['erro']}")
        print()

    if success > 0:
        print("  PROXIMOS PASSOS:")
        print("  1. Validar propostas:   python tools/enrich_ml_products.py --validate")
        print("  2. Abrir dashboard:     python src/web_dashboard.py")
        print("  3. Revisar e aprovar as propostas na aba 'Enrichment'")
        print("  4. Sincronizar:         python src/sync_ml_enrichment.py --aplicar")
        print()

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
