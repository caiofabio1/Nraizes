#!/usr/bin/env python3
"""
Vincular Produtos WooCommerce ao Bling
=======================================

Cadastra cada produto do WooCommerce na loja virtual WooCommerce dentro do
Bling (POST /produtos/lojas), usando o SKU como chave de correspondência.

Os SKUs já são iguais nos dois sistemas. O script apenas:
1. Busca todos os produtos do WooCommerce
2. Busca todos os produtos ativos do Bling (indexa por SKU)
3. Busca vínculos já existentes na loja WooCommerce do Bling
4. Para cada produto WooCommerce cujo SKU exista no Bling mas ainda não
   esteja vinculado à loja, cria o vínculo via POST /produtos/lojas

Uso:
    python src/vincular_woocommerce.py              # Dry-run (simulação)
    python src/vincular_woocommerce.py --executar   # Cria vínculos de verdade
    python src/vincular_woocommerce.py --status     # Apenas mostra diagnóstico
"""

import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bling_client import BlingClient
from woo_client import WooClient
from database import VaultDB
from logger import get_logger

# =========================================================================
# CONFIGURAÇÃO
# =========================================================================

LOJA_WOOCOMMERCE_ID = 205326820  # ID da loja WooCommerce no Bling
LOJAS_CONHECIDAS = {
    205326820: "WooCommerce",
    205282664: "Google Shopping",
}
RATE_LIMIT_DELAY = 0.5  # Delay entre chamadas Bling (s)
RETRY_MAX = 3
RETRY_BACKOFF = 2.0
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

logger = get_logger("vincular_woo")


# =========================================================================
# FUNÇÕES AUXILIARES
# =========================================================================


def _criar_vinculo(
    bling: BlingClient,
    db: VaultDB,
    bling_id: int,
    sku: str,
    preco=None,
    loja_id: int = LOJA_WOOCOMMERCE_ID,
) -> Tuple[bool, str]:
    """Cria vínculo produto↔loja no Bling com retry e rate-limit."""
    payload: Dict = {
        "produto": {"id": bling_id},
        "loja": {"id": loja_id},
        "codigo": sku,
    }
    if preco and float(preco) > 0:
        payload["preco"] = float(preco)

    for attempt in range(1, RETRY_MAX + 1):
        try:
            time.sleep(RATE_LIMIT_DELAY)
            result = bling.post_produtos_lojas(payload)
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


# =========================================================================
# DIAGNÓSTICO (--status)
# =========================================================================


def mostrar_status(loja_id: int = LOJA_WOOCOMMERCE_ID):
    """Mostra diagnóstico completo sem alterar nada."""
    bling = BlingClient()
    woo = WooClient()
    loja_nome = LOJAS_CONHECIDAS.get(loja_id, f"Loja {loja_id}")

    print()
    print("=" * 70)
    print(f"  DIAGNÓSTICO: VINCULAÇÃO WOOCOMMERCE <-> BLING ({loja_nome})")
    print("=" * 70)

    # 1) Produtos WooCommerce
    print("\n[1/3] Buscando produtos WooCommerce...")
    woo_products = woo.get_all_products(per_page=30, max_pages=50)
    woo_skus = {
        str(p.get("sku", "")).strip(): p
        for p in woo_products
        if str(p.get("sku", "")).strip()
    }
    print(f"  {len(woo_products)} produtos ({len(woo_skus)} com SKU)")

    # 2) Produtos Bling
    print("[2/3] Buscando produtos ativos Bling...")
    bling_products = bling.get_all_produtos(criterio=2, limite=100)
    bling_by_sku: Dict[str, Dict] = {}
    for p in bling_products:
        sku = str(p.get("codigo", "")).strip()
        if sku and sku != "0":
            bling_by_sku.setdefault(sku, p)
    print(f"  {len(bling_products)} produtos ({len(bling_by_sku)} SKUs únicos)")

    # 3) Vínculos existentes
    print("[3/3] Buscando vínculos existentes...")
    links = bling.get_all_produtos_lojas(idLoja=loja_id, limite=100)
    linked_bling_ids = set()
    for lk in links:
        pid = lk.get("produto", {}).get("id")
        if pid:
            linked_bling_ids.add(pid)
    print(f"  {len(linked_bling_ids)} vínculos ativos")

    # Análise
    ja_vinculados = 0
    para_vincular = []
    sem_match = []

    for sku, woo_p in woo_skus.items():
        bling_p = bling_by_sku.get(sku)
        if not bling_p:
            sem_match.append((sku, woo_p))
            continue
        if bling_p["id"] in linked_bling_ids:
            ja_vinculados += 1
        else:
            para_vincular.append((sku, woo_p, bling_p))

    # Produtos Woo sem SKU
    sem_sku = [p for p in woo_products if not str(p.get("sku", "")).strip()]

    total = len(woo_skus)
    cobertura = (ja_vinculados / total * 100) if total else 100

    print()
    print("-" * 70)
    print(f"  Produtos WooCommerce com SKU: {total}")
    print(f"  Sem SKU (ignorados):          {len(sem_sku)}")
    print(f"  Já vinculados no Bling:       {ja_vinculados}")
    print(f"  Para vincular (match OK):     {len(para_vincular)}")
    print(f"  Sem match no Bling:           {len(sem_match)}")
    print(f"  COBERTURA:                    {cobertura:.1f}%")
    print("-" * 70)

    if para_vincular:
        print("\n  PRONTOS PARA VINCULAR:")
        print("  " + "-" * 66)
        for sku, woo_p, bling_p in para_vincular[:40]:
            print(f"  {sku:<20} WOO#{woo_p['id']:<6} -> Bling#{bling_p['id']}")
        if len(para_vincular) > 40:
            print(f"  ... e mais {len(para_vincular) - 40}")

    if sem_match:
        print("\n  SEM CORRESPONDENTE NO BLING (verificar SKU):")
        print("  " + "-" * 66)
        for sku, woo_p in sem_match[:20]:
            print(f"  SKU={sku:<18} WOO#{woo_p['id']:<6} {woo_p.get('name', '')[:35]}")
        if len(sem_match) > 20:
            print(f"  ... e mais {len(sem_match) - 20}")

    if sem_sku:
        print("\n  PRODUTOS WOOCOMMERCE SEM SKU (ignorados):")
        print("  " + "-" * 66)
        for p in sem_sku[:10]:
            print(f"  WOO#{p['id']:<6} {p.get('name', '')[:50]}")
        if len(sem_sku) > 10:
            print(f"  ... e mais {len(sem_sku) - 10}")

    print()


# =========================================================================
# EXECUÇÃO (dry-run / --executar)
# =========================================================================


def executar_vinculacao(dry_run: bool = True, loja_id: int = LOJA_WOOCOMMERCE_ID):
    """Vincula todos os produtos WooCommerce ao Bling."""
    bling = BlingClient()
    woo = WooClient()
    db = VaultDB()
    loja_nome = LOJAS_CONHECIDAS.get(loja_id, f"Loja {loja_id}")

    modo = "DRY-RUN" if dry_run else "EXECUÇÃO REAL"
    print()
    print("=" * 70)
    print(f"  VINCULAR PRODUTOS WOOCOMMERCE -> BLING ({loja_nome})")
    print("=" * 70)
    print(f"  Modo:  {modo}")
    print(f"  Loja:  {loja_id} ({loja_nome})")
    print("=" * 70)

    # ---- Carregar dados ----
    print("\n[1/4] Buscando produtos WooCommerce...")
    woo_products = woo.get_all_products(per_page=30, max_pages=50)
    woo_skus = {}
    for p in woo_products:
        sku = str(p.get("sku", "")).strip()
        if sku:
            woo_skus[sku] = p
    print(f"  {len(woo_products)} produtos ({len(woo_skus)} com SKU)")

    print("[2/4] Buscando produtos Bling...")
    bling_products = bling.get_all_produtos(criterio=2, limite=100)
    bling_by_sku: Dict[str, Dict] = {}
    for p in bling_products:
        sku = str(p.get("codigo", "")).strip()
        if sku and sku != "0":
            bling_by_sku.setdefault(sku, p)
    print(f"  {len(bling_products)} produtos ({len(bling_by_sku)} SKUs)")

    print("[3/4] Buscando vínculos existentes...")
    links = bling.get_all_produtos_lojas(idLoja=loja_id, limite=100)
    linked_bling_ids = set()
    for lk in links:
        pid = lk.get("produto", {}).get("id")
        if pid:
            linked_bling_ids.add(pid)
        try:
            db.upsert_vinculo(lk)
        except Exception:
            pass
    print(f"  {len(linked_bling_ids)} vínculos existentes")

    # ---- Identificar faltantes ----
    para_vincular: List[Tuple[str, Dict, Dict]] = []  # (sku, woo_p, bling_p)
    ja_vinculados = 0
    sem_match = 0

    for sku, woo_p in woo_skus.items():
        bling_p = bling_by_sku.get(sku)
        if not bling_p:
            sem_match += 1
            logger.warning(
                f"Sem match: SKU={sku} WOO#{woo_p['id']} '{woo_p.get('name', '')}'"
            )
            continue
        if bling_p["id"] in linked_bling_ids:
            ja_vinculados += 1
            continue
        para_vincular.append((sku, woo_p, bling_p))

    print()
    print(f"  Já vinculados:    {ja_vinculados}")
    print(f"  Para vincular:    {len(para_vincular)}")
    print(f"  Sem match Bling:  {sem_match}")

    if not para_vincular:
        print("\n  Nada a fazer -- todos os produtos WooCommerce já estão vinculados!")
        return

    # ---- Criar vínculos ----
    print(
        f"\n[4/4] {'Simulando' if dry_run else 'Criando'} {len(para_vincular)} vínculos...\n"
    )

    criados = 0
    falhas = 0
    erros: List[Dict] = []
    detalhes: List[Dict] = []
    inicio = datetime.now()

    for i, (sku, woo_p, bling_p) in enumerate(para_vincular, 1):
        bling_id = bling_p["id"]
        preco = bling_p.get("preco")
        nome = woo_p.get("name", "")

        if dry_run:
            print(
                f"  [{i:3d}/{len(para_vincular)}] {sku:<20} Bling#{bling_id} -> seria vinculado"
            )
            criados += 1
            detalhes.append({"sku": sku, "bling_id": bling_id, "status": "dry_run"})
        else:
            ok, msg = _criar_vinculo(bling, db, bling_id, sku, preco, loja_id=loja_id)
            if ok:
                criados += 1
                linked_bling_ids.add(bling_id)
                detalhes.append({"sku": sku, "bling_id": bling_id, "status": msg})
                if i <= 10 or i % 25 == 0 or i == len(para_vincular):
                    print(f"  [{i:3d}/{len(para_vincular)}] {sku:<20} OK ({msg})")
            else:
                falhas += 1
                erros.append({"sku": sku, "bling_id": bling_id, "erro": msg})
                print(f"  [{i:3d}/{len(para_vincular)}] {sku:<20} FALHA: {msg[:60]}")
                logger.error(f"Falha {sku} Bling#{bling_id}: {msg}")

    fim = datetime.now()
    duracao = fim - inicio

    # ---- Relatório ----
    print()
    print("=" * 70)
    print("  RESULTADO")
    print("=" * 70)
    print(f"  Produtos WooCommerce:  {len(woo_skus)}")
    print(f"  Já vinculados:         {ja_vinculados}")
    print(f"  Vínculos criados:      {criados}")
    print(f"  Falhas:                {falhas}")
    print(f"  Sem match no Bling:    {sem_match}")
    total = ja_vinculados + criados
    cobertura = (total / len(woo_skus) * 100) if woo_skus else 100
    print(f"  Cobertura final:       {cobertura:.1f}%")
    print(f"  Duração:               {duracao.seconds // 60}m {duracao.seconds % 60}s")
    print("=" * 70)

    if erros:
        print("\n  ERROS:")
        for e in erros[:20]:
            print(f"  SKU={e['sku']:<18} Bling#{e['bling_id']}: {e['erro'][:50]}")

    # Salvar relatório
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(LOG_DIR, f"vinculacao_woo_{ts}.json")
        report = {
            "modo": modo,
            "total_woo": len(woo_skus),
            "ja_vinculados": ja_vinculados,
            "criados": criados,
            "falhas": falhas,
            "sem_match": sem_match,
            "cobertura": round(cobertura, 1),
            "duracao_s": duracao.seconds,
            "erros": erros,
            "detalhes": detalhes,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n  Relatório: {path}")
    except Exception as e:
        logger.error(f"Erro ao salvar relatório: {e}")

    print()


# =========================================================================
# CLI
# =========================================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Vincular produtos WooCommerce à loja no Bling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python src/vincular_woocommerce.py              # Dry-run WooCommerce
  python src/vincular_woocommerce.py --executar   # Criar vínculos WooCommerce
  python src/vincular_woocommerce.py --status     # Apenas diagnóstico
  python src/vincular_woocommerce.py --loja 205282664 --executar  # Google Shopping
        """,
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Criar vínculos de verdade (sem flag = dry-run)",
    )
    parser.add_argument(
        "--status", action="store_true", help="Apenas mostrar diagnóstico"
    )
    parser.add_argument(
        "--loja",
        type=int,
        default=LOJA_WOOCOMMERCE_ID,
        help=f"ID da loja no Bling (default: {LOJA_WOOCOMMERCE_ID} WooCommerce). "
        f"Google Shopping: 205282664",
    )
    args = parser.parse_args()

    loja_nome = LOJAS_CONHECIDAS.get(args.loja, f"Loja {args.loja}")
    print(f"\n  Loja selecionada: {args.loja} ({loja_nome})")

    if args.status:
        mostrar_status(loja_id=args.loja)
        return 0

    executar_vinculacao(dry_run=not args.executar, loja_id=args.loja)
    return 0


if __name__ == "__main__":
    sys.exit(main())
