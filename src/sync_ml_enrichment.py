"""
NRAIZES - Sync ML Enrichment -> Bling API
==========================================
Aplica propostas de enrichment ML aprovadas no dashboard ao Bling via API.

Fluxo:
1. Busca propostas aprovadas dos tipos ML (titulo_ml, descricao_ml, etc.)
2. Agrupa por produto
3. Monta o payload PUT /produtos/{id} com os campos atualizados
4. Envia para o Bling
5. Marca propostas como aplicadas

Uso:
    python src/sync_ml_enrichment.py              # Dry-run (mostra o que faria)
    python src/sync_ml_enrichment.py --aplicar     # Aplica no Bling de verdade
    python src/sync_ml_enrichment.py --status      # Mostra status das propostas ML
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bling_client import BlingClient
from database import VaultDB
from ml_enricher import MLValidator
from logger import get_logger

logger = get_logger("sync_ml")

# Tipos de proposta ML
ML_PROPOSAL_TYPES = {
    "titulo_ml",
    "descricao_curta_ml",
    "descricao_ml",
    "ficha_tecnica_ml",
}

# Rate limit entre chamadas Bling
RATE_LIMIT_DELAY = 0.6
RETRY_MAX = 3
RETRY_BACKOFF = 2.0


def get_ml_proposals(db: VaultDB, status: str = "aprovado") -> List[Dict]:
    """Busca propostas ML por status."""
    conn = db._get_conn()
    cursor = conn.cursor()

    placeholders = ",".join(["?" for _ in ML_PROPOSAL_TYPES])
    cursor.execute(
        f"""
        SELECT p.*, pr.nome as produto_nome, pr.codigo as produto_codigo
        FROM propostas_ia p
        JOIN produtos pr ON p.id_produto = pr.id_bling
        WHERE p.status = ? AND p.tipo IN ({placeholders})
        ORDER BY p.id_produto, p.tipo
    """,
        [status] + list(ML_PROPOSAL_TYPES),
    )

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def group_by_product(proposals: List[Dict]) -> Dict[int, Dict]:
    """Agrupa propostas por produto, montando payload para cada um."""
    products = defaultdict(
        lambda: {
            "proposals": [],
            "nome": "",
            "codigo": "",
            "payload_produto": {},
            "ficha_tecnica": {},
        }
    )

    for p in proposals:
        pid = p["id_produto"]
        products[pid]["proposals"].append(p)
        products[pid]["nome"] = p.get("produto_nome", "")
        products[pid]["codigo"] = p.get("produto_codigo", "")

        tipo = p["tipo"]
        conteudo = p["conteudo_proposto"]

        if tipo == "titulo_ml":
            # Nome do produto no Bling = titulo do anuncio ML
            products[pid]["payload_produto"]["nome"] = conteudo

        elif tipo == "descricao_curta_ml":
            products[pid]["payload_produto"]["descricaoCurta"] = conteudo

        elif tipo == "descricao_ml":
            products[pid]["payload_produto"]["descricaoComplementar"] = conteudo

        elif tipo == "ficha_tecnica_ml":
            try:
                ficha = json.loads(conteudo)
                products[pid]["ficha_tecnica"] = ficha
            except json.JSONDecodeError:
                logger.warning(
                    f"Ficha tecnica invalida para produto {pid}: {conteudo[:100]}"
                )

    return dict(products)


def validate_before_sync(products: Dict[int, Dict]) -> Tuple[List[int], List[Dict]]:
    """
    Valida todos os produtos antes de sincronizar.
    Returns (valid_ids, validation_errors).
    """
    valid_ids = []
    errors = []

    for pid, data in products.items():
        payload = data["payload_produto"]
        issues = []

        # Valida titulo se presente
        if "nome" in payload:
            ok, title_issues = MLValidator.validate_title(payload["nome"])
            if not ok:
                issues.extend(title_issues)

        # Valida descricao se presente
        if "descricaoComplementar" in payload:
            ok, desc_issues = MLValidator.validate_description(
                payload["descricaoComplementar"]
            )
            if not ok:
                issues.extend(desc_issues)

        # Valida ficha tecnica se presente
        if data["ficha_tecnica"]:
            ok, ficha_issues = MLValidator.validate_ficha_tecnica(data["ficha_tecnica"])
            if not ok:
                issues.extend(ficha_issues)

        if issues:
            errors.append(
                {
                    "id_produto": pid,
                    "nome": data["nome"],
                    "codigo": data["codigo"],
                    "issues": issues,
                }
            )
        else:
            valid_ids.append(pid)

    return valid_ids, errors


def sync_product_to_bling(
    bling: BlingClient,
    product_id: int,
    payload: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Envia atualizacao de produto para o Bling via PATCH /produtos/{id}.

    Usa PATCH (update parcial) em vez de PUT (replace completo) para
    evitar erro de campos obrigatorios (tipo, situacao, formato).

    O payload vai diretamente no body (campos top-level):
    {"nome": "...", "descricaoCurta": "...", "descricaoComplementar": "..."}
    """
    for attempt in range(1, RETRY_MAX + 1):
        try:
            time.sleep(RATE_LIMIT_DELAY)
            result = bling.patch_produtos_id_produto(str(product_id), payload)
            return True, "OK"
        except Exception as e:
            msg = str(e)
            if "429" in msg:
                wait = RETRY_BACKOFF**attempt * 2
                logger.warning(
                    f"Rate limit 429, esperando {wait:.0f}s (tentativa {attempt})"
                )
                time.sleep(wait)
                continue
            if "401" in msg:
                # Token refresh e automatico no client
                time.sleep(2)
                continue
            if attempt < RETRY_MAX:
                time.sleep(RETRY_BACKOFF**attempt)
                continue
            return False, msg[:200]

    return False, "maximo de tentativas"


def mark_proposals_applied(db: VaultDB, proposal_ids: List[int]):
    """Marca propostas como aplicadas (status = 'aplicado')."""
    conn = db._get_conn()
    cursor = conn.cursor()
    for pid in proposal_ids:
        cursor.execute(
            """
            UPDATE propostas_ia 
            SET status = 'aplicado', reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (pid,),
        )
    conn.commit()


def print_status(db: VaultDB):
    """Mostra status de todas as propostas ML."""
    conn = db._get_conn()
    cursor = conn.cursor()

    placeholders = ",".join(["?" for _ in ML_PROPOSAL_TYPES])

    # Contagens por status
    cursor.execute(
        f"""
        SELECT status, tipo, COUNT(*) as qtd
        FROM propostas_ia
        WHERE tipo IN ({placeholders})
        GROUP BY status, tipo
        ORDER BY status, tipo
    """,
        list(ML_PROPOSAL_TYPES),
    )

    rows = cursor.fetchall()

    print()
    print("=" * 70)
    print("  STATUS DAS PROPOSTAS ML")
    print("=" * 70)

    if not rows:
        print("  Nenhuma proposta ML encontrada.")
        print("  Rode primeiro: python tools/enrich_ml_products.py")
        print()
        return

    current_status = None
    for row in rows:
        row = dict(row)
        if row["status"] != current_status:
            current_status = row["status"]
            print(f"\n  [{current_status.upper()}]")
        print(f"    {row['tipo']:<25} {row['qtd']:3d} propostas")

    # Total por status
    cursor.execute(
        f"""
        SELECT status, COUNT(*) as qtd
        FROM propostas_ia
        WHERE tipo IN ({placeholders})
        GROUP BY status
    """,
        list(ML_PROPOSAL_TYPES),
    )

    print("\n  RESUMO:")
    for row in cursor.fetchall():
        row = dict(row)
        print(f"    {row['status']:<15} {row['qtd']:3d}")

    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Sincronizar enrichment ML aprovado com Bling API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python src/sync_ml_enrichment.py              # Dry-run
  python src/sync_ml_enrichment.py --aplicar    # Aplica no Bling
  python src/sync_ml_enrichment.py --status     # Status das propostas
        """,
    )
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Aplicar no Bling de verdade (sem flag = dry-run)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Apenas mostrar status das propostas ML",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Pular validacao pre-sync (nao recomendado)",
    )
    args = parser.parse_args()

    db = VaultDB()

    if args.status:
        print_status(db)
        return 0

    # 1. Buscar propostas aprovadas
    print()
    print("=" * 70)
    print("  SYNC ML ENRICHMENT -> BLING API")
    print("=" * 70)

    proposals = get_ml_proposals(db, status="aprovado")

    if not proposals:
        print("  Nenhuma proposta ML aprovada para sincronizar.")
        print("  Aprove propostas no dashboard (localhost:5000) primeiro.")
        print()
        return 0

    print(f"  {len(proposals)} propostas aprovadas encontradas")

    # 2. Agrupar por produto
    products = group_by_product(proposals)
    print(f"  {len(products)} produtos para atualizar")

    # 3. Mostrar o que sera feito
    print()
    print("-" * 70)
    for pid, data in products.items():
        payload = data["payload_produto"]
        ficha = data["ficha_tecnica"]
        changes = []
        if "nome" in payload:
            changes.append(f"titulo: '{payload['nome'][:50]}'")
        if "descricaoCurta" in payload:
            changes.append(f"desc_curta: '{payload['descricaoCurta'][:40]}...'")
        if "descricaoComplementar" in payload:
            word_count = len(payload["descricaoComplementar"].split())
            changes.append(f"desc_ml: {word_count} palavras")
        if ficha:
            changes.append(f"ficha: {', '.join(ficha.keys())}")

        n_proposals = len(data["proposals"])
        print(
            f"  [{data['codigo']:<22}] {n_proposals} propostas | {' | '.join(changes)}"
        )
    print("-" * 70)

    # 4. Validar
    if not args.skip_validation:
        print("\n  Validando conteudo ML...")
        valid_ids, errors = validate_before_sync(products)

        if errors:
            print(f"\n  [AVISO] {len(errors)} produto(s) com problemas de validacao:")
            for err in errors:
                print(f"    {err['codigo']}: {'; '.join(err['issues'][:3])}")

            if not valid_ids:
                print(
                    "\n  NENHUM produto valido para sync. Corrija os problemas primeiro."
                )
                return 1

        print(f"  {len(valid_ids)} produto(s) valido(s) para sync")
    else:
        valid_ids = list(products.keys())

    # 5. Dry-run ou aplicar
    modo = "APLICAR" if args.aplicar else "DRY-RUN"
    print(f"\n  Modo: {modo}")

    if not args.aplicar:
        print("\n  Modo DRY-RUN: nada sera alterado no Bling.")
        print("  Use --aplicar para sincronizar de verdade.")
        print()
        return 0

    # 6. Sincronizar
    bling = BlingClient()
    inicio = datetime.now()
    sucesso = 0
    falhas = 0
    erros_sync = []

    for i, pid in enumerate(valid_ids, 1):
        data = products[pid]
        payload = data["payload_produto"]

        if not payload:
            continue

        print(f"  [{i}/{len(valid_ids)}] Sincronizando {data['codigo']}...", end=" ")

        ok, msg = sync_product_to_bling(bling, pid, payload)

        if ok:
            sucesso += 1
            print("OK")

            # Marcar propostas como aplicadas
            proposal_ids = [p["id"] for p in data["proposals"]]
            mark_proposals_applied(db, proposal_ids)
        else:
            falhas += 1
            erros_sync.append({"codigo": data["codigo"], "erro": msg})
            print(f"FALHA: {msg[:60]}")

    # 7. Relatorio
    fim = datetime.now()
    duracao = fim - inicio

    print()
    print("=" * 70)
    print("  RESULTADO")
    print("=" * 70)
    print(f"  Produtos atualizados:  {sucesso}")
    print(f"  Falhas:                {falhas}")
    print(f"  Duracao:               {duracao.seconds}s")
    print("=" * 70)

    if erros_sync:
        print("\n  ERROS:")
        for e in erros_sync:
            print(f"    {e['codigo']}: {e['erro'][:60]}")

    if sucesso > 0:
        print("\n  PROXIMO PASSO:")
        print("  As descricoes e titulos foram atualizados no Bling.")
        print("  O Bling sincroniza automaticamente com o Mercado Livre")
        print("  (se o produto estiver vinculado a loja ML).")
        print()
        print("  Para ficha tecnica (campos customizados), e necessario")
        print("  configurar os campos no Bling primeiro:")
        print("  Bling > Configuracoes > Campos Customizados > Produtos")

    print()
    return 0 if not erros_sync else 1


if __name__ == "__main__":
    sys.exit(main())
