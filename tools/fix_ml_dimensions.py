#!/usr/bin/env python3
"""
Preenche dimensões e peso da embalagem nos produtos vinculados ao ML.

Classifica cada produto pelo nome/tipo e atribui dimensões realistas
de embalagem (largura, altura, profundidade em cm e peso bruto em kg).

Uso:
    python tools/fix_ml_dimensions.py              # Dry-run (mostra o que faria)
    python tools/fix_ml_dimensions.py --executar   # Aplica via PATCH no Bling
"""

import sys, os, time, re

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)
from bling_client import BlingClient

ML_STORE = 205294269
executar = "--executar" in sys.argv
client = BlingClient()


# ============================================================
# Tabela de dimensões por tipo de produto (cm / kg)
# Formato: (largura, altura, profundidade, pesoBruto)
# ============================================================
def classify_dimensions(nome, peso_liquido=0):
    """Retorna (largura, altura, profundidade, pesoBruto) baseado no nome."""
    n = nome.lower()

    # --- Serum / líquido pequeno (30ml) ---
    if any(x in n for x in ["serum", "sérum", "facial"]):
        return (6, 6, 14, 0.12)

    # --- Sachês / Display (caixa com 30 sachês) ---
    if any(x in n for x in ["sachê", "sache", "sachés", "saches", "display"]):
        if "90g" in n:
            # Display pequeno (3 sachês)
            return (12, 8, 18, 0.20)
        # Caixa 30 sachês
        return (18, 12, 22, 0.60)

    # --- Colágeno Miya (caixa 10 unidades) ---
    if "miya" in n and ("colag" in n or "10 unid" in n):
        return (20, 10, 12, 0.45)

    # --- Pó grande (840g-1kg) ---
    if any(x in n for x in ["840g", "1kg"]):
        return (16, 16, 24, 1.10)

    # --- Pó médio (420g-600g) ---
    if any(x in n for x in ["600g", "500g", "450g", "420g"]):
        return (14, 14, 20, 0.80)

    # --- Pó pequeno-médio (220g-360g) ---
    if any(x in n for x in ["220g", "240g", "300g", "360g"]):
        return (12, 12, 18, 0.45)

    # --- Pó pequeno (150g) ---
    if "150g" in n:
        return (10, 10, 15, 0.30)

    # --- Proteína vegetal (pote 450g) ---
    if "proteina vegetal" in n or "proteína vegetal" in n:
        return (14, 14, 20, 0.70)

    # --- Creatina (pote 500g) ---
    if "creatina" in n:
        return (14, 14, 20, 0.70)

    # --- Cápsulas 180 unidades ---
    if "180" in n and ("capsul" in n or "cápsul" in n):
        return (9, 9, 16, 0.35)

    # --- Cápsulas 120 unidades ---
    if "120" in n and ("capsul" in n or "cápsul" in n):
        return (8, 8, 14, 0.25)

    # --- Cápsulas 90 unidades ---
    if "90" in n and ("capsul" in n or "cápsul" in n):
        return (8, 8, 13, 0.22)

    # --- Cápsulas 60 unidades ---
    if "60" in n and ("capsul" in n or "cápsul" in n):
        return (7, 7, 12, 0.18)

    # --- Pré-treino genérico (pote) ---
    if any(x in n for x in ["pré-treino", "pre-treino", "pre treino", "pretreino"]):
        return (12, 12, 18, 0.50)

    # --- Chá solúvel / café funcional (pote 220g) ---
    if any(x in n for x in ["chá", "cha ", "café", "cafe", "leite em po"]):
        return (12, 12, 18, 0.40)

    # --- Vitaminas / cápsulas genérico ---
    if any(x in n for x in ["vitamina", "capsul", "cápsul"]):
        return (7, 7, 12, 0.18)

    # --- Fallback genérico (suplemento médio) ---
    return (12, 12, 16, 0.35)


# ============================================================
# 1. Buscar todos os produtos vinculados ao ML
# ============================================================
print("Buscando vínculos ML...")
links = client.get_all_produtos_lojas(idLoja=ML_STORE)
print(f"Total vínculos: {len(links)}\n")

seen = set()
products = []
for l in links:
    pid = l.get("produto", {}).get("id")
    if not pid or pid in seen:
        continue
    seen.add(pid)

    try:
        resp = client.get_produtos_id_produto(pid)
        d = resp.get("data", resp)
        dim = d.get("dimensoes", {})
        products.append(
            {
                "pid": pid,
                "sku": d.get("codigo", "?"),
                "nome": d.get("nome", "?"),
                "situacao": d.get("situacao", "?"),
                "pesoBruto": d.get("pesoBruto", 0) or 0,
                "pesoLiquido": d.get("pesoLiquido", 0) or 0,
                "largura": dim.get("largura", 0),
                "altura": dim.get("altura", 0),
                "profundidade": dim.get("profundidade", 0),
            }
        )
    except Exception as e:
        print(f"  ERRO ao buscar {pid}: {e}")
    time.sleep(0.2)

# ============================================================
# 2. Classificar e calcular dimensões
# ============================================================
to_update = []
already_ok = []

for p in products:
    has_dims = (
        p["largura"] > 0
        and p["altura"] > 0
        and p["profundidade"] > 0
        and p["pesoBruto"] > 0.05
    )
    if has_dims:
        already_ok.append(p)
        continue

    larg, alt, prof, peso = classify_dimensions(p["nome"], p["pesoLiquido"])
    p["new_largura"] = larg
    p["new_altura"] = alt
    p["new_profundidade"] = prof
    p["new_pesoBruto"] = peso
    to_update.append(p)

# ============================================================
# 3. Relatório
# ============================================================
print(f"Já com dimensões: {len(already_ok)}")
print(f"Precisam atualizar: {len(to_update)}")
print()

if to_update:
    print(f"{'SKU':<28} {'Sit':>3} {'L':>3}{'A':>4}{'P':>4} {'Peso':>5}  Nome")
    print("-" * 105)
    for p in to_update:
        print(
            f"{p['sku'][:27]:<28} {p['situacao']:>3} "
            f"{p['new_largura']:>3}{p['new_altura']:>4}{p['new_profundidade']:>4} "
            f"{p['new_pesoBruto']:>5.2f}  {p['nome'][:45]}"
        )

# ============================================================
# 4. Aplicar via PATCH
# ============================================================
if not executar:
    print(f"\n*** DRY-RUN: nenhuma alteração feita. Use --executar para aplicar. ***")
    sys.exit(0)

if not to_update:
    print("\nNada a atualizar.")
    sys.exit(0)

print(f"\n=== APLICANDO DIMENSÕES ({len(to_update)} produtos) ===\n")

ok = 0
err = 0
for p in to_update:
    body = {
        "pesoBruto": p["new_pesoBruto"],
        "pesoLiquido": p["pesoLiquido"]
        if p["pesoLiquido"] > 0
        else p["new_pesoBruto"] * 0.85,
        "dimensoes": {
            "largura": p["new_largura"],
            "altura": p["new_altura"],
            "profundidade": p["new_profundidade"],
            "unidadeMedida": 1,  # centímetros
        },
    }
    try:
        client.patch_produtos_id_produto(str(p["pid"]), body)
        ok += 1
        print(
            f"  OK  {p['sku'][:27]:<28} {p['new_largura']}x{p['new_altura']}x{p['new_profundidade']}cm "
            f"{p['new_pesoBruto']:.2f}kg  {p['nome'][:40]}"
        )
    except Exception as e:
        err += 1
        print(f"  ERR {p['sku'][:27]:<28} {str(e)[:70]}")
    time.sleep(0.5)

print(f"\n=== RESULTADO ===")
print(f"Atualizados: {ok}")
print(f"Erros: {err}")
print(f"Total: {len(to_update)}")
