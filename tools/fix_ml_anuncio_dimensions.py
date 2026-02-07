#!/usr/bin/env python3
"""
Recria anúncios ML que estão sem atributos de embalagem (SELLER_PACKAGE_*).

O ML exige Largura, Comprimento, Altura e Peso da embalagem como atributos
do anúncio. A API Bling v3 NÃO permite adicionar esses atributos via PUT
em rascunhos existentes. A solução é DELETAR o anúncio e RECRIAR com todos
os atributos corretos desde o início.

Uso:
    python tools/fix_ml_anuncio_dimensions.py              # Dry-run
    python tools/fix_ml_anuncio_dimensions.py --executar   # Deleta e recria
"""

import sys, os, time, json

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)
from bling_client import BlingClient

ML_STORE = 205294269
executar = "--executar" in sys.argv
client = BlingClient()


def get_product_dims(pid):
    """Get dimensions from the product record."""
    try:
        resp = client.get_produtos_id_produto(pid)
        d = resp.get("data", resp)
        dim = d.get("dimensoes", {})
        return {
            "largura": dim.get("largura", 0) or 0,
            "altura": dim.get("altura", 0) or 0,
            "profundidade": dim.get("profundidade", 0) or 0,
            "pesoBruto": d.get("pesoBruto", 0) or 0,
        }
    except:
        return None


# ============================================================
# 1. List all ML anuncios
# ============================================================
print("Buscando anúncios ML...")
all_anuncios = []
for sit in [1, 2, 3, 4]:
    page = 1
    while True:
        try:
            resp = client.get_anuncios(
                tipoIntegracao="MercadoLivre",
                idLoja=ML_STORE,
                limite=100,
                situacao=sit,
                pagina=page,
            )
            data = resp.get("data", [])
            if not data:
                break
            all_anuncios.extend(data)
            page += 1
            time.sleep(0.3)
        except:
            break

print(f"Total anúncios: {len(all_anuncios)}\n")

# ============================================================
# 2. Check which are missing package attributes
# ============================================================
to_fix = []
already_ok = []

for a in all_anuncios:
    aid = a["id"]
    titulo = a.get("titulo", "?")

    try:
        resp = client._request(
            "GET",
            f"{client.base_url}/anuncios/{aid}",
            params={"tipoIntegracao": "MercadoLivre"},
        )
        d = resp.get("data", resp)
        pid = d.get("produto", {}).get("id")
        attrs = d.get("atributos", [])
        attr_map = {at.get("id_externo", ""): at for at in attrs}

        has_pkg = all(
            attr_map.get(k, {}).get("valor")
            for k in [
                "SELLER_PACKAGE_WIDTH",
                "SELLER_PACKAGE_LENGTH",
                "SELLER_PACKAGE_HEIGHT",
                "SELLER_PACKAGE_WEIGHT",
            ]
        )

        if has_pkg:
            already_ok.append((aid, titulo))
        else:
            to_fix.append(
                {
                    "aid": aid,
                    "pid": pid,
                    "titulo": titulo,
                    "existing_attrs": attrs,
                }
            )
    except Exception as e:
        print(f"  ERRO lendo anúncio {aid}: {e}")
    time.sleep(0.3)

print(f"Já com embalagem: {len(already_ok)}")
print(f"Faltam atributos: {len(to_fix)}")
print()

# ============================================================
# 3. Get product dimensions and build update payloads
# ============================================================
updates = []
for item in to_fix:
    dims = get_product_dims(item["pid"])
    time.sleep(0.2)

    if not dims or (dims["largura"] == 0 and dims["altura"] == 0):
        print(f"  SKIP (sem dimensões no produto) | {item['titulo'][:55]}")
        continue

    # ML expects: "10 cm", "100 g"
    largura_cm = dims["largura"]
    comprimento_cm = dims["profundidade"]  # profundidade = comprimento
    altura_cm = dims["altura"]
    peso_g = int(dims["pesoBruto"] * 1000)

    # Build new attributes list: keep existing + add/update package attrs
    new_attrs = []
    pkg_ids = {
        "SELLER_PACKAGE_WIDTH",
        "SELLER_PACKAGE_LENGTH",
        "SELLER_PACKAGE_HEIGHT",
        "SELLER_PACKAGE_WEIGHT",
    }

    for at in item["existing_attrs"]:
        if at.get("id_externo") not in pkg_ids:
            new_attrs.append(at)

    new_attrs.extend(
        [
            {"id_externo": "SELLER_PACKAGE_WIDTH", "valor": f"{largura_cm} cm"},
            {"id_externo": "SELLER_PACKAGE_LENGTH", "valor": f"{comprimento_cm} cm"},
            {"id_externo": "SELLER_PACKAGE_HEIGHT", "valor": f"{altura_cm} cm"},
            {"id_externo": "SELLER_PACKAGE_WEIGHT", "valor": f"{peso_g} g"},
        ]
    )

    item["new_attrs"] = new_attrs
    item["dims_display"] = f"{largura_cm}x{altura_cm}x{comprimento_cm}cm {peso_g}g"
    updates.append(item)

# ============================================================
# 4. Report
# ============================================================
print(f"\nProntos para atualizar: {len(updates)}")
if updates:
    print(f"\n{'ID':>12} {'Dimensões':>22}  Título")
    print("-" * 95)
    for u in updates:
        print(f"{u['aid']:>12} {u['dims_display']:>22}  {u['titulo'][:55]}")

if not executar:
    print(f"\n*** DRY-RUN: nenhuma alteração. Use --executar para aplicar. ***")
    sys.exit(0)

if not updates:
    print("\nNada a atualizar.")
    sys.exit(0)

# ============================================================
# 5. DELETE + RECREATE anuncios (PUT não suporta adicionar SELLER_PACKAGE_*)
# ============================================================
print(f"\n=== DELETANDO E RECRIANDO ANÚNCIOS ({len(updates)}) ===\n")

ok = 0
err = 0
for u in updates:
    aid = u["aid"]

    # 5a. Get full anuncio data for recreation
    try:
        resp = client._request(
            "GET",
            f"{client.base_url}/anuncios/{aid}",
            params={"tipoIntegracao": "MercadoLivre"},
        )
        ad = resp.get("data", resp)
    except Exception as e:
        err += 1
        print(f"  ERR GET {aid}  {str(e)[:60]}")
        continue

    # 5b. Delete old anuncio
    try:
        client._request(
            "DELETE",
            f"{client.base_url}/anuncios/{aid}",
            params={"tipoIntegracao": "MercadoLivre", "idLoja": ML_STORE},
        )
    except Exception as e:
        err += 1
        print(f"  ERR DEL {aid}  {str(e)[:60]}")
        continue
    time.sleep(0.3)

    # 5c. Recreate with all attrs including SELLER_PACKAGE_*
    new_body = {
        "produto": ad.get("produto", {}),
        "integracao": {"tipo": "MercadoLivre"},
        "loja": {"id": ML_STORE},
        "nome": ad.get("titulo", ""),
        "descricao": ad.get("descricao", ""),
        "preco": ad.get("preco", {}),
        "categoria": ad.get("categoria", {}),
        "atributos": u["new_attrs"],
        "imagens": ad.get("imagens", []),
    }
    # Copy ML-specific config if present
    if ad.get("mercadoLivre"):
        new_body["mercadoLivre"] = ad["mercadoLivre"]

    try:
        resp = client.post_anuncios(new_body)
        new_aid = resp.get("data", {}).get("id", "?")
        ok += 1
        print(f"  OK  {aid} -> {new_aid}  {u['dims_display']:>18}  {u['titulo'][:40]}")
    except Exception as e:
        err += 1
        print(f"  ERR POST {aid}  {str(e)[:60]}")
    time.sleep(0.5)

print(f"\n=== RESULTADO ===")
print(f"Recriados: {ok}")
print(f"Erros: {err}")
print(f"Total: {len(updates)}")
