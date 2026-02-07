#!/usr/bin/env python3
"""
Analyze products in vault.db and select top 50 candidates for Mercado Livre.

Criteria:
- Active products (situacao='A', tipo='P')
- Has price and cost price
- Margin after ML fees (15%) >= 25%
- Price >= R$15 (ML viability - shipping economics)
- Prioritize: higher margin, has image, has description, higher price
"""

import sqlite3
import os
import json

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "vault.db"
)
ML_MULTIPLIER = 1.15  # 15% ML fees


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all active products with price and cost
    cur.execute("""
        SELECT id_bling, nome, codigo, preco, preco_custo,
               descricao_curta, imagem_url
        FROM produtos 
        WHERE situacao = 'A' AND tipo = 'P' AND preco > 0 AND preco_custo > 0
        ORDER BY nome
    """)

    products = []
    for row in cur.fetchall():
        p = dict(row)
        preco = p["preco"]
        custo = p["preco_custo"]
        preco_ml = round(preco * ML_MULTIPLIER, 2)
        margem_base = round((preco - custo) / preco * 100, 1) if preco > 0 else 0
        margem_ml = round((preco_ml - custo) / preco_ml * 100, 1) if preco_ml > 0 else 0

        p["preco_ml"] = preco_ml
        p["margem_base"] = margem_base
        p["margem_ml"] = margem_ml
        p["has_image"] = bool(p["imagem_url"])
        p["has_desc"] = bool(p["descricao_curta"] and p["descricao_curta"].strip())
        products.append(p)

    print(f"Total produtos com preco + custo: {len(products)}")
    print()

    # Filter viable for ML
    viable = [p for p in products if p["margem_ml"] >= 25 and p["preco"] >= 15]
    print(f"Viaveis para ML (margem_ml >= 25%, preco >= R$15): {len(viable)}")
    print()

    # Score for ranking
    for p in viable:
        score = 0
        score += p["margem_ml"] * 2  # margin weight
        score += min(p["preco"], 300) * 0.1  # higher price = better (capped)
        if p["has_image"]:
            score += 10
        if p["has_desc"]:
            score += 5
        # Penalize sachets/small items (low absolute profit)
        if p["preco"] < 20:
            score -= 15
        p["score"] = round(score, 1)

    # Sort by score
    viable.sort(key=lambda x: x["score"], reverse=True)

    # Show all viable
    print("=" * 120)
    print(
        f"{'#':>3} {'Score':>6} {'Margem ML':>9} {'Preco':>9} {'Preco ML':>9} {'Custo':>8} {'IMG':>4} {'DESC':>5} {'SKU':<22} {'Nome'}"
    )
    print("-" * 120)

    for i, p in enumerate(viable, 1):
        img = "SIM" if p["has_image"] else "---"
        desc = "SIM" if p["has_desc"] else "---"
        marker = " <<<" if i <= 50 else ""
        print(
            f"{i:3d} {p['score']:6.1f} {p['margem_ml']:8.1f}% R${p['preco']:8.2f} R${p['preco_ml']:8.2f} R${p['preco_custo']:7.2f} {img:>4} {desc:>5} {(p['codigo'] or '-----'):<22} {p['nome'][:50]}{marker}"
        )

    print()
    print(f"Total viaveis: {len(viable)}")
    print(f"Top 50 marcados com <<<")

    # Stats on top 50
    top50 = viable[:50]
    if top50:
        margens = [p["margem_ml"] for p in top50]
        precos = [p["preco_ml"] for p in top50]
        print(f"\n=== TOP 50 STATS ===")
        print(f"Margem ML media: {sum(margens) / len(margens):.1f}%")
        print(f"Margem ML min: {min(margens):.1f}%")
        print(f"Margem ML max: {max(margens):.1f}%")
        print(f"Preco ML medio: R${sum(precos) / len(precos):.2f}")
        print(f"Preco ML min: R${min(precos):.2f}")
        print(f"Preco ML max: R${max(precos):.2f}")
        print(f"Com imagem: {sum(1 for p in top50 if p['has_image'])}")
        print(f"Com descricao: {sum(1 for p in top50 if p['has_desc'])}")

        # Missing data alerts
        sem_img = [p for p in top50 if not p["has_image"]]
        sem_desc = [p for p in top50 if not p["has_desc"]]
        if sem_img:
            print(f"\n[ALERTA] {len(sem_img)} produtos no top 50 SEM imagem:")
            for p in sem_img:
                print(f"  - {p['codigo']}: {p['nome'][:60]}")
        if sem_desc:
            print(f"\n[ALERTA] {len(sem_desc)} produtos no top 50 SEM descricao:")
            for p in sem_desc:
                print(f"  - {p['codigo']}: {p['nome'][:60]}")

    # Export top 50 as JSON for the linking script
    export = []
    for p in top50:
        export.append(
            {
                "id_bling": p["id_bling"],
                "nome": p["nome"],
                "codigo": p["codigo"],
                "preco": p["preco"],
                "preco_custo": p["preco_custo"],
                "preco_ml": p["preco_ml"],
                "margem_base": p["margem_base"],
                "margem_ml": p["margem_ml"],
                "has_image": p["has_image"],
                "has_desc": p["has_desc"],
                "score": p["score"],
            }
        )

    export_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "ml_top50_candidates.json",
    )
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    print(f"\nExportado: {export_path}")

    conn.close()


if __name__ == "__main__":
    main()
