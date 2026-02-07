#!/usr/bin/env python3
"""
Normaliza preços ML: todos os vínculos passam a ser preco_bling * 1.15.

Uso:
    python tools/fix_ml_prices.py              # Dry-run (apenas mostra)
    python tools/fix_ml_prices.py --executar   # Aplica as alterações
"""

import sys, os, time

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)
from bling_client import BlingClient

ML_STORE = 205294269
ML_MULTIPLIER = 1.15
TOLERANCE = 0.02  # ignora diferenças < 2% (arredondamento)

executar = "--executar" in sys.argv
client = BlingClient()

# 1. Buscar todos os vínculos ML
print("Buscando vínculos ML...")
links = client.get_all_produtos_lojas(idLoja=ML_STORE)
print(f"Total vínculos: {len(links)}\n")

# 2. Para cada vínculo, buscar preço base do produto
to_fix = []
skipped_no_price = []
already_ok = []

seen = set()
for l in links:
    pid = l.get("produto", {}).get("id")
    link_id = l.get("id")
    if not pid or not link_id or pid in seen:
        continue
    seen.add(pid)

    preco_ml_atual = l.get("preco", 0) or 0
    sku = l.get("codigo", "?")

    try:
        resp = client.get_produtos_id_produto(pid)
        d = resp.get("data", resp)
        preco_bling = d.get("preco", 0) or 0
        nome = d.get("nome", "?")
    except Exception as e:
        print(f"  ERRO ao buscar produto {pid}: {e}")
        continue

    time.sleep(0.2)

    if preco_bling <= 0:
        skipped_no_price.append((sku, nome, preco_ml_atual, link_id, pid))
        continue

    preco_ml_correto = round(preco_bling * ML_MULTIPLIER, 2)
    diff_pct = (
        abs(preco_ml_atual - preco_ml_correto) / preco_ml_correto
        if preco_ml_correto > 0
        else 0
    )

    if diff_pct <= TOLERANCE:
        already_ok.append((sku, nome, preco_bling, preco_ml_atual))
    else:
        to_fix.append(
            {
                "link_id": link_id,
                "pid": pid,
                "sku": sku,
                "nome": nome,
                "preco_bling": preco_bling,
                "preco_ml_atual": preco_ml_atual,
                "preco_ml_correto": preco_ml_correto,
                "mult_atual": round(preco_ml_atual / preco_bling, 2),
            }
        )

# 3. Relatório
print(f"{'=' * 100}")
print(f"RELATÓRIO DE PREÇOS ML (multiplicador global: {ML_MULTIPLIER}x)")
print(f"{'=' * 100}\n")

print(f"OK (dentro da tolerância {TOLERANCE * 100:.0f}%): {len(already_ok)}")
print(f"Sem preço base no Bling (não pode calcular): {len(skipped_no_price)}")
print(f"PRECISAM CORREÇÃO: {len(to_fix)}\n")

if to_fix:
    print(
        f"{'SKU':<25} {'Bling':>8} {'ML Atual':>9} {'ML Correto':>10} {'Mult':>6}  Nome"
    )
    print("-" * 105)
    for p in sorted(
        to_fix, key=lambda x: x["preco_ml_atual"] - x["preco_ml_correto"], reverse=True
    ):
        delta = p["preco_ml_atual"] - p["preco_ml_correto"]
        print(
            f"{p['sku']:<25} {p['preco_bling']:>8.2f} {p['preco_ml_atual']:>9.2f} {p['preco_ml_correto']:>10.2f} {p['mult_atual']:>5.2f}x  {p['nome'][:42]}"
        )

if skipped_no_price:
    print(f"\n--- SEM PREÇO BASE (precisam cadastro no Bling) ---")
    for sku, nome, ml, lid, pid in skipped_no_price:
        print(f"  {sku:<25} ML: R${ml:>8.2f}  {nome[:50]}")

# 4. Aplicar correções
if not executar:
    print(f"\n*** DRY-RUN: nenhuma alteração feita. Use --executar para aplicar. ***")
    sys.exit(0)

if not to_fix:
    print("\nNada a corrigir.")
    sys.exit(0)

print(f"\n=== APLICANDO CORREÇÕES ({len(to_fix)} produtos) ===\n")

ok = 0
err = 0
for p in to_fix:
    body = {
        "idProdutoLoja": p["link_id"],
        "preco": p["preco_ml_correto"],
        "produto": {"id": p["pid"]},
        "loja": {"id": ML_STORE},
    }
    try:
        client.put_produtos_lojas_id(str(p["link_id"]), body)
        ok += 1
        print(
            f"  OK  {p['sku']:<25} R${p['preco_ml_atual']:.2f} -> R${p['preco_ml_correto']:.2f}"
        )
    except Exception as e:
        err += 1
        print(f"  ERR {p['sku']:<25} {str(e)[:60]}")
    time.sleep(0.5)

print(f"\n=== RESULTADO ===")
print(f"Corrigidos: {ok}")
print(f"Erros: {err}")
print(f"Total: {len(to_fix)}")
