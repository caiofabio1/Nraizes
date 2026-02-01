#!/usr/bin/env python3
"""
Vincular produtos do Bling à loja WooCommerce
Cria o vínculo de produtos não vinculados via API POST /produtos/lojas
"""

import sys
import time

sys.path.insert(0, "src")

from bling_client import BlingClient

# Configuration
LOJA_WOOCOMMERCE_ID = 205326820

# Produtos a vincular (SKU extraído da mensagem de erro de sync de preços)
PRODUTOS_PARA_VINCULAR = [
    # --- Lote 1 (erros originais) ---
    "NVR-PM-CHIASEM",
    "NVR-PM-CAMOMIL",
    "NVR-PM-MULUNGU",
    "NVR-PM-ROSARUB",
    "NVR-PM-LAVANDA",
    "NVR-PM-HIBISCUS",
    "XTR-SP-H2GECAF",
    "MAH-SP-MAHTSUPE02",
    "MAH-SP-MAHTSUPE",
    "MUS-CF-MUSHCOFF02",
    "MUS-CF-MUSHCHAI",
    "PHY-SP-GELDENT",
    "CEN-VT-BIOB12",
    "CEN-AX-OMEGVEGA",
    "MUS-CF-MUSHCOFF",
    "CEN-SP-PURECAFF",
    "CEN-SP-NEURHEAL",
    "XTR-SP-H2GEXTRA",
    "CEN-SP-COENQ1002",
    "CEN-SP-COENQ10",
    # --- Lote 2 (Laszlo, Solar, Granado, Amokarite, etc.) ---
    "LAS-OE-CRISPEEL",
    "LAS-OE-ALOELASZ",
    "LAS-OE-OLEOESSE09",
    "LAS-OE-OLEOESSE10",
    "SOL-SB-SABOFACI",
    "SOL-SH-SHAMCABE",
    "LAS-OE-SINEMULH",
    "LAS-OE-OLOESSE",
    "LAS-OE-OLEOJURE",
    "LAS-OE-SINEINSP",
    # --- Lote 3 (Xtratus displays, Mushin, Central) ---
    "XTR-FOO-ABACA2",
    "XTR-FOO-MATEVE",
    "XTR-FOO-BETER2",
    "MUS-FOO-CARAME",
    "MUS-FOO-FRUTAS",
    "CEN-FOO-TANGE4",
    "CEN-FOO-TANGE3",
    "CEN-FOO-LIMAO4",
    "CEN-FOO-TANGE2",
    "CEN-FOO-LIMAO3",
    # --- Lote 4 (Laszlo manteigas/hidrolatos, Granado velas/colônias) ---
    "LAS-OIL-MANGA",
    "LAS-OIL-KARITE",
    "LAS-OIL-ALECR7",
    "GRA-COS-CHABRA",
    # --- Lote 5 (mais erros de sync) ---
    "XTR-SP-DISPPRIN",
    "BRA-CH-CHAGELA05",
    "BRA-CH-CHAGELA04",
    "BRA-CH-CHAGELA03",
    "BRA-CH-CHAGELA02",
    "BRA-CH-CHAGELA",
    "BRA-CH-GELABRAZ",
    "MAH-SP-LEITCAST02",
    "CEN-SP-ENERATP",
    "CEN-VT-RESTVITA",
    "CEN-SP-GUARCENT",
    "CEN-AA-AMINLIVR",
    "GRA-COS-ERVA",
    "GRA-COS-DESEMB",
    "GRA-COS-NEUTRO",
    "GRA-COS-SUAVE",
    "CEN-SUP-GUARD2",
    "CEN-SUP-GUARD",
    # --- Lote 6 (Amokarite bases) ---
    "AMO-COS-AK80",
    "AMO-COS-AK70",
    "AMO-COS-AK60",
    "AMO-COS-TONAK11",
    "AMO-COS-TONAK10",
    "AMO-COS-TONAK9",
    "AMO-COS-TONAK8",
    "AMO-COS-TONAK7",
    "AMO-COS-TONAK6",
    "AMO-COS-TONAK5",
    "AMO-COS-TONAK4",
    "AMO-COS-TONAK3",
    "AMO-COS-TONAK2",
    "AMO-COS-TONAKA",
    # --- Lote 7 (Granado, Phebo, Laszlo, Xtratus, misc) ---
    "GRA-CN-SABLIQ",
    "PHE-PF-COLOLIMA",
    "GRA-CN-SABLIMA",
    "LAS-OE-SINEINSP02",
    "XTR-SP-INTRABAC",
    "LAS-OE-MANTKARI",
    "AMO-SP-ILUMMINE",
    "MAH-SP-SUPEACAI",
    # --- Lote 8 (NVR ervas/grãos) ---
    "NVR-SP-QUINGRAO",
    "NVR-SP-TUDOLENH",
    "NVR-SP-JATOFRUT",
    "NVR-SP-GENGRAIZ",
    "NVR-SP-CACHRAIZ",
    "NVR-SP-RUIBRAIZ",
    "NVR-SP-MACAELEF",
    "NVR-SP-IPEROXO",
    "NVR-SP-JALACASC",
    "NVR-SP-PIMEMACA",
    "NVR-SP-QUEBPEDR",
    "NVR-SP-ASSAPEIX",
    "NVR-SP-TILIFLOR",
    "NVR-SP-JAPEPCT",
    # --- Lote 9 (produtos pai / variações) ---
    "LAS-OE-HIDRLASZ",
    "LAS-OE-MANTVEGE",
    "GRA-PF-COLOBEBE",
    "GRA-CN-VELAPERF",
    "GRA-SH-SHAMPET",
    "AMO-SP-BASESOLI",
    "CEN-SP-GUARCENT02",
    # --- Lote 10 (Phebo, Mushin, Amokarite, Central) ---
    "PHE-CN-SABROSA",
    "PHE-PF-COLOGERA",
    "MUS-SP-BARRMUSH02",
    "MUS-CF-FANTOAT",
    "MUS-SP-BARRMUSH",
    "AMO-SK-BATOSOLI02",
    "AMO-SP-SUPOMAQU",
    "AMO-SB-SABOLIQ",
    "NVR-SP-DELIOLHO",
    "AMO-SP-MASCFORT",
    "AMO-SK-BALSDEMA",
    "AMO-SP-LIPTINT02",
    "AMO-HC-BALMHIDR",
    "AMO-SK-BATOSOLI",
    "AMO-SK-DUOBATO",
    "AMO-SP-ESFOMULT",
    "MAH-SP-SUPECACA",
    "MUS-SP-BARRVANI02",
    "MUS-SP-BARRVANI",
    "XTR-SP-H2GENEUT",
    # --- Lote 11 (Central Nutrition variações, Creatina, Mel) ---
    "CEN-SUP-ENERG4",
    "CEN-FOO-SEM2",
    "CEN-FOO-LIMAO2",
    "CEN-PF-CREACOLL",
    "CEN-SP-SACHENER",
    "CEN-SUP-ENERG2",
    "CEN-FOO-SEM",
    "CEN-FOO-TANGE",
    "CEN-FOO-LIMAO",
    "CEN-AA-SACHAMIN",
    "EMP-AP-MELFLOR",
]


def buscar_produto_por_sku(client: BlingClient, sku: str):
    """Busca produto pelo código/SKU"""
    try:
        # Bling API v3 requer "codigos[]" como nome do parâmetro array
        result = client.get_produtos(**{"codigos[]": [sku], "limite": 1})
        data = result.get("data", [])
        if data:
            # Confirmar que o SKU retornado bate (API pode retornar qualquer coisa)
            for p in data:
                if str(p.get("codigo", "")).strip() == sku:
                    return p
            # Se nenhum bate exato, retornar primeiro mas avisar
            print(f"  [AVISO] API retornou {data[0].get('codigo')} ao buscar {sku}")
            return None
        return None
    except Exception as e:
        print(f"  [ERRO] Falha ao buscar SKU {sku}: {e}")
        return None
    except Exception as e:
        print(f"  [ERRO] Falha ao buscar SKU {sku}: {e}")
        return None


def verificar_vinculo_existe(client: BlingClient, produto_id: int, loja_id: int):
    """Verifica se já existe vínculo entre produto e loja"""
    try:
        result = client.get_produtos_lojas(
            idProduto=produto_id, idLoja=loja_id, limite=1
        )
        data = result.get("data", [])
        return len(data) > 0
    except Exception as e:
        print(f"  [AVISO] Não foi possível verificar vínculo: {e}")
        return False


def criar_vinculo(
    client: BlingClient, produto_id: int, sku: str, loja_id: int, preco: float = None
):
    """Cria vínculo produto-loja"""
    payload = {
        "codigo": sku,
        "produto": {"id": produto_id},
        "loja": {"id": loja_id},
    }

    if preco:
        payload["preco"] = preco

    try:
        result = client.post_produtos_lojas(payload)
        return True, result
    except Exception as e:
        return False, str(e)


def main(dry_run: bool = False):
    client = BlingClient()

    print("=" * 60)
    print("VINCULAÇÃO DE PRODUTOS À LOJA WOOCOMMERCE")
    print("=" * 60)
    print(f"Loja ID: {LOJA_WOOCOMMERCE_ID}")
    print(f"Produtos a processar: {len(PRODUTOS_PARA_VINCULAR)}")
    print(f"Modo: {'DRY-RUN (simulação)' if dry_run else 'EXECUÇÃO REAL'}")
    print("=" * 60)
    print()

    sucesso = 0
    falhas = 0
    ja_vinculados = 0
    nao_encontrados = 0

    for i, sku in enumerate(PRODUTOS_PARA_VINCULAR, 1):
        print(f"[{i:02d}/{len(PRODUTOS_PARA_VINCULAR)}] Processando SKU: {sku}")

        # Rate limiting
        if i > 1:
            time.sleep(0.5)  # 2 req/s para ficar abaixo do limite de 3 req/s

        # 1. Buscar produto
        produto = buscar_produto_por_sku(client, sku)

        if not produto:
            print(f"  [AVISO] Produto não encontrado no Bling")
            nao_encontrados += 1
            continue

        produto_id = produto.get("id")
        produto_nome = produto.get("nome")
        preco = produto.get("preco")

        print(f"  Produto: {produto_nome}")
        print(f"  ID: {produto_id}, Preço: R$ {preco}")

        time.sleep(0.4)

        # 2. Verificar se já vinculado
        if verificar_vinculo_existe(client, produto_id, LOJA_WOOCOMMERCE_ID):
            print(f"  [OK] Já vinculado à loja")
            ja_vinculados += 1
            continue

        # 3. Criar vínculo
        if dry_run:
            print(
                f"  [DRY-RUN] Criaria vínculo: produto {produto_id} -> loja {LOJA_WOOCOMMERCE_ID}"
            )
            sucesso += 1
        else:
            time.sleep(0.4)
            ok, result = criar_vinculo(
                client, produto_id, sku, LOJA_WOOCOMMERCE_ID, preco
            )

            if ok:
                print(f"  [OK] Vínculo criado com sucesso!")
                sucesso += 1
            else:
                print(f"  [ERRO] Falha ao criar vínculo: {result}")
                falhas += 1

        print()

    print("=" * 60)
    print("RESUMO")
    print("=" * 60)
    print(f"Vínculos criados: {sucesso}")
    print(f"Já vinculados: {ja_vinculados}")
    print(f"Falhas: {falhas}")
    print(f"Não encontrados: {nao_encontrados}")
    print("=" * 60)

    return falhas == 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Vincular produtos à loja WooCommerce no Bling"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Modo simulação (não cria vínculos)"
    )
    args = parser.parse_args()

    success = main(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
