#!/usr/bin/env python3
"""
Vincular TOP 50 produtos ao Mercado Livre via Bling API
========================================================

Seleciona os 50 melhores produtos para o Mercado Livre com base em:
- Margem após taxas ML (15%) >= 25%
- Preço base >= R$30 (viabilidade de frete no ML)
- Prioriza: maior margem, tem imagem, tem descrição, maior ticket
- Remove duplicatas (variações do mesmo produto)

Uso:
    python tools/vincular_produtos_ml.py                # Dry-run (simulação)
    python tools/vincular_produtos_ml.py --executar      # Cria vínculos de verdade
    python tools/vincular_produtos_ml.py --status        # Apenas mostra seleção
"""

import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

from bling_client import BlingClient
from database import VaultDB
from logger import get_logger

# =========================================================================
# CONFIGURAÇÃO
# =========================================================================

LOJA_ML_ID = 205294269  # Mercado Livre no Bling
ML_MULTIPLIER = 1.15  # 15% taxas ML
MIN_MARGIN_ML = 25.0  # Margem mínima após taxas ML
MIN_PRICE = 30.0  # Preço mínimo base (viabilidade frete)
MAX_PRODUCTS = 50  # Quantidade de produtos a selecionar
RATE_LIMIT_DELAY = 0.5  # Delay entre chamadas Bling (s)
RETRY_MAX = 3
RETRY_BACKOFF = 2.0

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

logger = get_logger("vincular_ml")

# =========================================================================
# SELEÇÃO DE PRODUTOS
# =========================================================================

# IDs de produtos que são duplicatas (variações já representadas por outro SKU)
# Manter apenas 1 representante de cada "família" de variação
DUPLICATES_TO_SKIP = {
    # AMINNU variations - keep only 16472604733 (Tangerina, com imagem+desc)
    16383136270,  # AMINNU LIVRE DE XILITOL sem img/desc
    16472604742,  # AMINNU duplicata sem img/desc
    16472604726,  # AMINNU duplicata sem img/desc
    16521485852,  # AMINNU duplicata sem img/desc
    16521488408,  # AMINNU duplicata sem img/desc
    # ENERGY ATP variations - keep only 16398743608 (original, com img+desc)
    16474780715,  # ENERGY ATP Tangerina (duplicata)
    16459170180,  # ENERGY ATP Limao (duplicata)
    # GUARDIAN variations - keep only 16458844600 (Limao, com img+desc)
    16383136375,  # GUARDIAN sem img/desc
    16458844610,  # GUARDIAN Tangerina (duplicata)
    16458853562,  # GUARDIAN Sem Sabor (duplicata)
    # CREATINA COLLCREATINE - keep only 16459222778 (com img+desc)
    16383136318,  # COLLCREATINE sem imagem
    16459226408,  # Creatina Limao (duplicata)
    # SUPERFOODS MAHTA 840g - keep only 16443287915 (com img+desc)
    16451626844,  # Superfoods Cacau 840g (duplicata)
    16451626839,  # Superfoods Acai 840g (sem img/desc)
    # SUPERFOODS MAHTA 360g - keep only 16443288140 (com img+desc)
    16451621839,  # Superfoods Cacau 360g (duplicata)
    # PROTEINA VEGETAL OCEAN DROP - keep 16443287920 (pai) + sabores individuais
    # Actually keep Baunilha and Chocolate as separate listings (different flavors sell well)
    # Fatia Torta De Limao - food item, not suitable for ML shipping
    16383136361,  # Fatia Torta (perecível)
}

# Products to manually exclude (perishable food, problematic for ML logistics)
PERISHABLE_EXCLUDE = {
    16383136361,  # Fatia Torta De Limao
    16398743413,  # Fatia Torta Quiche De Alho Poro
    16398743793,  # Fatia Torta Quiche Tomate Manjericao
    16383136440,  # Pão De Queijo Coquetel
}


def select_top_products(db: VaultDB) -> List[Dict]:
    """
    Select top 50 products for Mercado Livre based on margin, price, and data quality.
    Returns list of product dicts with ML pricing info.
    """
    import sqlite3

    conn = sqlite3.connect(os.path.join(DATA_DIR, "vault.db"))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id_bling, nome, codigo, preco, preco_custo,
               descricao_curta, imagem_url
        FROM produtos 
        WHERE situacao = 'A' AND tipo = 'P' AND preco > 0 AND preco_custo > 0
    """)

    candidates = []
    for row in cur.fetchall():
        p = dict(row)
        bid = p["id_bling"]

        # Skip duplicates and perishables
        if bid in DUPLICATES_TO_SKIP or bid in PERISHABLE_EXCLUDE:
            continue

        preco = p["preco"]
        custo = p["preco_custo"]

        # Skip low-price items (not viable on ML due to shipping)
        if preco < MIN_PRICE:
            continue

        preco_ml = round(preco * ML_MULTIPLIER, 2)
        margem_ml = round((preco_ml - custo) / preco_ml * 100, 1)

        # Skip low margin
        if margem_ml < MIN_MARGIN_ML:
            continue

        p["preco_ml"] = preco_ml
        p["margem_ml"] = margem_ml
        p["has_image"] = bool(p["imagem_url"])
        p["has_desc"] = bool(p["descricao_curta"] and p["descricao_curta"].strip())

        # Scoring
        score = 0
        score += margem_ml * 2  # Margin is king
        score += min(preco, 300) * 0.1  # Higher price = better (capped)
        if p["has_image"]:
            score += 15  # Image is critical for ML
        if p["has_desc"]:
            score += 8  # Description helps conversion
        p["score"] = round(score, 1)

        candidates.append(p)

    conn.close()

    # Sort by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Take top N
    selected = candidates[:MAX_PRODUCTS]

    return selected


def print_selection(products: List[Dict]):
    """Print the selected products in a formatted table."""
    print()
    print("=" * 130)
    print(f"  TOP {len(products)} PRODUTOS SELECIONADOS PARA MERCADO LIVRE")
    print(
        f"  Loja ML ID: {LOJA_ML_ID} | Multiplicador: {ML_MULTIPLIER}x (+{int((ML_MULTIPLIER - 1) * 100)}% taxas)"
    )
    print("=" * 130)
    print(
        f"{'#':>3} {'Score':>6} {'Margem':>7} {'Preco Base':>11} {'Preco ML':>10} {'Custo':>9} {'IMG':>4} {'DESC':>5} {'SKU':<25} {'Produto'}"
    )
    print("-" * 130)

    total_revenue_potential = 0
    for i, p in enumerate(products, 1):
        img = "SIM" if p["has_image"] else "---"
        desc = "SIM" if p["has_desc"] else "---"
        total_revenue_potential += p["preco_ml"]
        print(
            f"{i:3d} {p['score']:6.1f} {p['margem_ml']:6.1f}% R${p['preco']:9.2f} R${p['preco_ml']:8.2f} R${p['preco_custo']:7.2f} {img:>4} {desc:>5} {(p['codigo'] or '-----'):<25} {p['nome'][:48]}"
        )

    # Stats
    margens = [p["margem_ml"] for p in products]
    precos = [p["preco_ml"] for p in products]
    sem_img = [p for p in products if not p["has_image"]]
    sem_desc = [p for p in products if not p["has_desc"]]

    print()
    print("=" * 130)
    print(f"  RESUMO DA SELEÇÃO")
    print("-" * 130)
    print(f"  Produtos selecionados:  {len(products)}")
    print(f"  Margem ML média:        {sum(margens) / len(margens):.1f}%")
    print(f"  Margem ML mínima:       {min(margens):.1f}%")
    print(f"  Margem ML máxima:       {max(margens):.1f}%")
    print(f"  Preço ML médio:         R${sum(precos) / len(precos):.2f}")
    print(f"  Preço ML mínimo:        R${min(precos):.2f}")
    print(f"  Preço ML máximo:        R${max(precos):.2f}")
    print(f"  Com imagem:             {len(products) - len(sem_img)}/{len(products)}")
    print(f"  Com descrição:          {len(products) - len(sem_desc)}/{len(products)}")
    print("=" * 130)

    if sem_img:
        print(
            f"\n  [ATENÇÃO] {len(sem_img)} produto(s) SEM IMAGEM (priorize adicionar antes de ativar no ML):"
        )
        for p in sem_img:
            print(f"    - {p['codigo']}: {p['nome'][:60]}")

    if sem_desc:
        print(
            f"\n  [ATENÇÃO] {len(sem_desc)} produto(s) SEM DESCRIÇÃO (rode o enrichment da IA):"
        )
        for p in sem_desc:
            print(f"    - {p['codigo']}: {p['nome'][:60]}")

    print()
    return products


# =========================================================================
# VINCULAÇÃO
# =========================================================================


def _criar_vinculo_ml(
    bling: BlingClient,
    db: VaultDB,
    bling_id: int,
    sku: str,
    preco_ml: float,
) -> Tuple[bool, str]:
    """Cria vínculo produto -> Mercado Livre no Bling com preço ML."""
    payload = {
        "produto": {"id": bling_id},
        "loja": {"id": LOJA_ML_ID},
        "codigo": sku,
        "preco": preco_ml,
    }

    for attempt in range(1, RETRY_MAX + 1):
        try:
            time.sleep(RATE_LIMIT_DELAY)
            result = bling.post_produtos_lojas(payload)
            # Save to local DB
            if result and "data" in result:
                try:
                    db.upsert_vinculo(result["data"])
                except Exception:
                    pass
            return True, "criado"

        except Exception as e:
            msg = str(e)
            if "409" in msg or "conflict" in msg.lower():
                return True, "já existia (409)"
            if "429" in msg:
                wait = RETRY_BACKOFF**attempt * 2
                logger.warning(
                    f"Rate limit 429, esperando {wait:.0f}s (tentativa {attempt})"
                )
                time.sleep(wait)
                continue
            if attempt < RETRY_MAX:
                time.sleep(RETRY_BACKOFF**attempt)
                continue
            return False, msg[:200]

    return False, "máximo de tentativas"


def executar_vinculacao(products: List[Dict], dry_run: bool = True):
    """Vincula os produtos selecionados ao Mercado Livre."""
    bling = BlingClient()
    db = VaultDB()
    modo = "DRY-RUN" if dry_run else "EXECUÇÃO REAL"

    print()
    print("=" * 70)
    print(f"  VINCULAÇÃO AO MERCADO LIVRE")
    print("=" * 70)
    print(f"  Loja:     {LOJA_ML_ID} (Mercado Livre)")
    print(f"  Modo:     {modo}")
    print(f"  Produtos: {len(products)}")
    print("=" * 70)

    # Check existing links
    if not dry_run:
        print("\n  Verificando vínculos existentes...")
        try:
            existing_links = bling.get_all_produtos_lojas(idLoja=LOJA_ML_ID, limite=100)
            linked_ids = set()
            for lk in existing_links:
                pid = lk.get("produto", {}).get("id")
                if pid:
                    linked_ids.add(pid)
            print(f"  {len(linked_ids)} produtos já vinculados ao ML")
        except Exception as e:
            print(f"  [AVISO] Não foi possível verificar vínculos existentes: {e}")
            linked_ids = set()
    else:
        linked_ids = set()

    print()
    criados = 0
    ja_vinculados = 0
    falhas = 0
    erros = []
    detalhes = []
    inicio = datetime.now()

    for i, p in enumerate(products, 1):
        bling_id = p["id_bling"]
        sku = p["codigo"]
        preco_ml = p["preco_ml"]
        nome = p["nome"]

        if bling_id in linked_ids:
            ja_vinculados += 1
            if i <= 5 or i % 10 == 0:
                print(f"  [{i:3d}/{len(products)}] {sku:<25} JÁ VINCULADO")
            detalhes.append(
                {"sku": sku, "bling_id": bling_id, "status": "já vinculado"}
            )
            continue

        if dry_run:
            print(
                f"  [{i:3d}/{len(products)}] {sku:<25} R${preco_ml:8.2f} -> seria vinculado | {nome[:40]}"
            )
            criados += 1
            detalhes.append(
                {
                    "sku": sku,
                    "bling_id": bling_id,
                    "preco_ml": preco_ml,
                    "status": "dry_run",
                }
            )
        else:
            ok, msg = _criar_vinculo_ml(bling, db, bling_id, sku, preco_ml)
            if ok:
                criados += 1
                linked_ids.add(bling_id)
                detalhes.append(
                    {
                        "sku": sku,
                        "bling_id": bling_id,
                        "preco_ml": preco_ml,
                        "status": msg,
                    }
                )
                if i <= 10 or i % 10 == 0 or i == len(products):
                    print(
                        f"  [{i:3d}/{len(products)}] {sku:<25} R${preco_ml:8.2f} OK ({msg})"
                    )
            else:
                falhas += 1
                erros.append({"sku": sku, "bling_id": bling_id, "erro": msg})
                print(f"  [{i:3d}/{len(products)}] {sku:<25} FALHA: {msg[:60]}")
                logger.error(f"Falha {sku} Bling#{bling_id}: {msg}")

    fim = datetime.now()
    duracao = fim - inicio

    # Report
    print()
    print("=" * 70)
    print("  RESULTADO")
    print("=" * 70)
    print(f"  Vínculos criados:      {criados}")
    print(f"  Já vinculados:         {ja_vinculados}")
    print(f"  Falhas:                {falhas}")
    print(f"  Total processados:     {len(products)}")
    print(f"  Duração:               {duracao.seconds // 60}m {duracao.seconds % 60}s")
    print("=" * 70)

    if erros:
        print("\n  ERROS:")
        for e in erros[:20]:
            print(f"    SKU={e['sku']:<22} Bling#{e['bling_id']}: {e['erro'][:50]}")

    # Save report
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(LOG_DIR, f"vinculacao_ml_{ts}.json")
        report = {
            "modo": modo,
            "loja_ml_id": LOJA_ML_ID,
            "multiplicador": ML_MULTIPLIER,
            "total_produtos": len(products),
            "criados": criados,
            "ja_vinculados": ja_vinculados,
            "falhas": falhas,
            "duracao_s": duracao.seconds,
            "erros": erros,
            "detalhes": detalhes,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n  Relatório: {path}")
    except Exception as e:
        logger.error(f"Erro ao salvar relatório: {e}")

    # Save selected products list
    try:
        export_path = os.path.join(DATA_DIR, "ml_50_selecionados.json")
        export_data = []
        for p in products:
            export_data.append(
                {
                    "id_bling": p["id_bling"],
                    "nome": p["nome"],
                    "codigo": p["codigo"],
                    "preco_base": p["preco"],
                    "preco_ml": p["preco_ml"],
                    "preco_custo": p["preco_custo"],
                    "margem_ml": p["margem_ml"],
                    "score": p["score"],
                    "has_image": p["has_image"],
                    "has_desc": p["has_desc"],
                }
            )
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        print(f"  Seleção exportada: {export_path}")
    except Exception as e:
        logger.error(f"Erro ao exportar seleção: {e}")

    print()


# =========================================================================
# CLI
# =========================================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Selecionar e vincular top 50 produtos ao Mercado Livre via Bling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python tools/vincular_produtos_ml.py              # Dry-run (simulação)
  python tools/vincular_produtos_ml.py --executar   # Criar vínculos ML
  python tools/vincular_produtos_ml.py --status     # Apenas mostrar seleção
        """,
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Criar vínculos de verdade (sem flag = dry-run)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Apenas mostrar seleção sem vincular",
    )
    args = parser.parse_args()

    db = VaultDB()

    # 1. Select products
    print("\n  Selecionando produtos para Mercado Livre...")
    products = select_top_products(db)

    if not products:
        print("  [ERRO] Nenhum produto viável encontrado!")
        return 1

    # 2. Show selection
    print_selection(products)

    # 3. Execute or dry-run
    if args.status:
        print("  Modo --status: apenas exibição, nenhum vínculo será criado.\n")
        return 0

    executar_vinculacao(products, dry_run=not args.executar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
