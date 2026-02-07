"""
Create ML anuncios (Bronze, frete ML, sem garantia) for all eligible products.

Inclui automaticamente:
- Atributos ML (marca, formato, sabor, tipo, classe)
- Atributos de embalagem (SELLER_PACKAGE_WIDTH/LENGTH/HEIGHT/WEIGHT)
- Dimensões estimadas por tipo de produto
- Preço ML = preço Bling * 1.15 (multiplicador global)

Uso:
    python tools/create_ml_anuncios.py              # Dry-run
    python tools/create_ml_anuncios.py --executar   # Cria anúncios de verdade
"""

import requests, os, json, sys, time, re
from dotenv import load_dotenv

load_dotenv(".credentials/woo_api_tokens.env")
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)
from bling_client import BlingClient

woo_key = os.getenv("WOO_CONSUMER_KEY")
woo_secret = os.getenv("WOO_CONSUMER_SECRET")
client = BlingClient()
ML_STORE = 205294269
ML_MULTIPLIER = 1.15
executar = "--executar" in sys.argv

# ============================================================
# 1. Get all remaining ML links
# ============================================================
links = client.get_all_produtos_lojas(idLoja=ML_STORE)
seen = set()
products = []

for l in links:
    pid = l.get("produto", {}).get("id")
    if pid in seen:
        continue
    seen.add(pid)
    sku = l.get("codigo", "?")
    preco_ml = l.get("preco", 0)

    resp = client.get_produtos_id_produto(pid)
    d = resp.get("data", resp)
    nome = d.get("nome", "?")
    marca = d.get("marca", "") or ""
    desc_curta = d.get("descricaoCurta", "") or ""
    desc_comp = d.get("descricaoComplementar", "") or ""
    estoque = d.get("estoque", {}).get("saldoVirtualTotal", 0)
    ext_imgs = d.get("midia", {}).get("imagens", {}).get("externas", [])
    ext_urls = [e.get("link", "") for e in ext_imgs if e.get("link")]

    dim = d.get("dimensoes", {})
    products.append(
        {
            "pid": pid,
            "sku": sku,
            "nome": nome,
            "marca": marca,
            "preco_ml": preco_ml,
            "preco_bling": d.get("preco", 0) or 0,
            "estoque": estoque,
            "desc": desc_comp if desc_comp else desc_curta,
            "bling_imgs": ext_urls,
            "gtin": d.get("gtin", "") or "",
            "pesoBruto": d.get("pesoBruto", 0) or 0,
            "largura": dim.get("largura", 0) or 0,
            "altura": dim.get("altura", 0) or 0,
            "profundidade": dim.get("profundidade", 0) or 0,
        }
    )
    time.sleep(0.15)

print(f"Total produtos vinculados: {len(products)}")
eligible = [p for p in products if p["estoque"] > 0]
print(f"Com estoque > 0: {len(eligible)}")


# ============================================================
# 2. Helper: convert AVIF URL to PNG/WEBP
# ============================================================
def convert_url(url):
    if not url:
        return None
    if not url.endswith(".avif"):
        return url  # assume it works
    base = url.rsplit(".", 1)[0]
    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        try:
            r = requests.head(base + ext, timeout=8, allow_redirects=True)
            if r.status_code == 200:
                return base + ext
        except:
            pass
    return None


# ============================================================
# 3. Helper: search WooCommerce images
# ============================================================
def get_woo_images(nome):
    search = nome.split(" - ")[0][:50]
    try:
        resp = requests.get(
            "https://nraizes.com.br/wp-json/wc/v3/products",
            params={"search": search, "per_page": 3},
            auth=(woo_key, woo_secret),
            timeout=15,
        )
        if resp.ok:
            for p in resp.json():
                imgs = p.get("images", [])
                if imgs:
                    return [i.get("src", "") for i in imgs]
    except:
        pass
    return []


# ============================================================
# 4. Helper: classify ML attributes
# ============================================================
def classify(nome):
    n = nome.lower()

    # FORMAT
    if any(x in n for x in ["capsula", "cápsula", "capsulas", "cápsulas"]):
        fmt = "13856569"  # Cápsula
    elif any(x in n for x in ["gotas", "goteira", "15ml"]):
        fmt = "4567843"  # Óleo
    elif "cha " in n or "chá " in n:
        fmt = "4567845"  # Chá
    else:
        fmt = "4567842"  # Pó

    # FLAVOR
    flavor = "2517530"  # Sem sabor
    if "chocolate" in n or "cacau" in n:
        flavor = "2517712"
    elif "baunilha" in n:
        flavor = "2517713"
    elif "morango" in n:
        flavor = "2472069"
    elif any(x in n for x in ["limão", "limao"]):
        flavor = "2472070"
    elif "tangerina" in n:
        flavor = "2104790"
    elif "abacaxi" in n:
        flavor = "5639164"
    elif any(x in n for x in ["açaí", "acai", "frutas"]):
        flavor = "12471647"

    # TYPE
    if any(
        x in n
        for x in [
            "pre-treino",
            "pré-treino",
            "pretreino",
            "intratreino",
            "creatina",
            "energy atp",
        ]
    ):
        stype = "13117980"  # Nutr/Esport
    elif any(x in n for x in ["colágeno", "colageno", "serum", "facial"]):
        stype = "38405034"  # Beleza
    elif any(x in n for x in ["café", "cafe", "shot matinal"]):
        stype = "13725989"  # Energia
    else:
        stype = "10955015"  # Nutricional

    # CLASS
    if any(x in n for x in ["vitamina", "magnésio", "magnesio"]):
        sclass = "52261836"  # Vitam/Min
    elif any(x in n for x in ["omega", "dha", "astaxantina"]):
        sclass = "52261837"  # Omegas
    elif any(x in n for x in ["proteína", "proteina"]):
        sclass = "52261838"  # Proteínas
    elif any(x in n for x in ["aminoácido", "aminoacido", "aminnu"]):
        sclass = "52261839"  # Aminoácidos
    elif any(x in n for x in ["colágeno", "colageno"]):
        sclass = "52261843"  # Colágeno
    elif "creatina" in n:
        sclass = "52261842"  # Creatina
    elif any(x in n for x in ["spirulina", "curcuma", "cúrcuma", "feno grego"]):
        sclass = "52261841"  # Herbais
    else:
        sclass = "52261844"  # Outros

    return fmt, flavor, stype, sclass


# ============================================================
# 5. Fix titles
# ============================================================
def fix_title(nome):
    title = nome
    title = title.replace("Display Sabor:", "Sachê Unitário")
    title = title.replace("Display ", "Sachê Unitário ")
    title = re.sub(r"<[^>]+>", "", title)
    return title[:60]


def clean_desc(desc):
    clean = re.sub(r"<[^>]+>", "", desc or "")
    clean = clean.strip()
    return clean[:5000] if clean else ""


# ============================================================
# 6. Helper: classify package dimensions (cm/kg)
# ============================================================
def classify_dimensions(nome):
    """Retorna (largura, altura, profundidade, pesoBruto) baseado no nome."""
    n = nome.lower()
    if any(x in n for x in ["serum", "sérum", "facial"]):
        return (6, 6, 14, 0.12)
    if any(x in n for x in ["sachê", "sache", "sachés", "saches", "display"]):
        if "90g" in n:
            return (12, 8, 18, 0.20)
        return (18, 12, 22, 0.60)
    if "miya" in n and ("colag" in n or "10 unid" in n):
        return (20, 10, 12, 0.45)
    if any(x in n for x in ["840g", "1kg"]):
        return (16, 16, 24, 1.10)
    if any(x in n for x in ["600g", "500g", "450g", "420g"]):
        return (14, 14, 20, 0.80)
    if any(x in n for x in ["220g", "240g", "300g", "360g"]):
        return (12, 12, 18, 0.45)
    if "150g" in n:
        return (10, 10, 15, 0.30)
    if "proteina vegetal" in n or "proteína vegetal" in n:
        return (14, 14, 20, 0.70)
    if "creatina" in n:
        return (14, 14, 20, 0.70)
    if "180" in n and ("capsul" in n or "cápsul" in n):
        return (9, 9, 16, 0.35)
    if "120" in n and ("capsul" in n or "cápsul" in n):
        return (8, 8, 14, 0.25)
    if "90" in n and ("capsul" in n or "cápsul" in n):
        return (8, 8, 13, 0.22)
    if "60" in n and ("capsul" in n or "cápsul" in n):
        return (7, 7, 12, 0.18)
    if any(x in n for x in ["pré-treino", "pre-treino", "pre treino", "pretreino"]):
        return (12, 12, 18, 0.50)
    if any(x in n for x in ["chá", "cha ", "café", "cafe", "leite em po"]):
        return (12, 12, 18, 0.40)
    if any(x in n for x in ["vitamina", "capsul", "cápsul"]):
        return (7, 7, 12, 0.18)
    return (12, 12, 16, 0.35)


def get_package_attrs(p):
    """Retorna atributos SELLER_PACKAGE_* para o anúncio ML."""
    # Usa dimensões do produto Bling, ou estima pelo nome
    if (
        p["largura"] > 0
        and p["altura"] > 0
        and p["profundidade"] > 0
        and p["pesoBruto"] > 0.05
    ):
        larg, alt, prof, peso = (
            p["largura"],
            p["altura"],
            p["profundidade"],
            p["pesoBruto"],
        )
    else:
        larg, alt, prof, peso = classify_dimensions(p["nome"])
    peso_g = int(peso * 1000)
    return [
        {"id_externo": "SELLER_PACKAGE_WIDTH", "valor": f"{larg} cm"},
        {"id_externo": "SELLER_PACKAGE_LENGTH", "valor": f"{prof} cm"},
        {"id_externo": "SELLER_PACKAGE_HEIGHT", "valor": f"{alt} cm"},
        {"id_externo": "SELLER_PACKAGE_WEIGHT", "valor": f"{peso_g} g"},
    ]


# ============================================================
# 7. CREATE ANUNCIOS
# ============================================================
print(f"\n=== CRIANDO ANUNCIOS BRONZE ===")

success = 0
failed = 0
skipped = 0

for p in eligible:
    # Get images: first try Bling, then WooCommerce
    img_urls = []

    if p["bling_imgs"]:
        for url in p["bling_imgs"]:
            conv = convert_url(url)
            if conv:
                img_urls.append(conv)

    if not img_urls:
        woo_imgs = get_woo_images(p["nome"])
        for url in woo_imgs:
            conv = convert_url(url)
            if conv:
                img_urls.append(conv)

    if not img_urls:
        skipped += 1
        print(f"  SKIP (no img) | {p['sku'][:25]} | {p['nome'][:40]}")
        continue

    titulo = fix_title(p["nome"])
    desc = clean_desc(p["desc"])
    if not desc:
        desc = f"{p['nome']} - Produto natural de alta qualidade. N Raizes, Vila Mariana SP."

    fmt, flavor, stype, sclass = classify(p["nome"])
    pkg_attrs = get_package_attrs(p)

    # Preço ML: usar o do vínculo, ou calcular 1.15x
    preco_ml = (
        p["preco_ml"]
        if p["preco_ml"] > 0
        else round(p["preco_bling"] * ML_MULTIPLIER, 2)
    )

    atributos = [
        {"id_externo": "BRAND", "valor": p["marca"] or "Genérico"},
        {"id_externo": "SUPPLEMENT_FORMAT", "valor": fmt},
        {"id_externo": "FLAVOR", "valor": flavor},
        {"id_externo": "SUPPLEMENT_TYPE", "valor": stype},
        {"id_externo": "SUPPLEMENT_CLASS", "valor": sclass},
    ]
    # GTIN se disponível
    if p["gtin"]:
        atributos.append({"id_externo": "GTIN", "valor": p["gtin"]})
    # Embalagem (obrigatório para ML)
    atributos.extend(pkg_attrs)

    body = {
        "produto": {"id": p["pid"]},
        "integracao": {"tipo": "MercadoLivre"},
        "loja": {"id": ML_STORE},
        "nome": titulo,
        "descricao": desc,
        "preco": {"valor": preco_ml},
        "categoria": {"id": "MLB264201"},
        "atributos": atributos,
        "mercadoLivre": {"modalidade": "bronze", "frete": {"gratis": False, "tipo": 2}},
        "imagens": [{"url": url, "ordem": i + 1} for i, url in enumerate(img_urls[:6])],
    }

    if not executar:
        print(f"  DRY | R$ {preco_ml:.2f} | {titulo[:50]}")
        success += 1
        continue

    try:
        resp = client.post_anuncios(body)
        aid = resp.get("data", {}).get("id", "?")
        success += 1
        print(f"  OK | {aid} | R$ {preco_ml:.2f} | {titulo[:50]}")
    except Exception as e:
        failed += 1
        err = str(e)[:80]
        print(f"  ERR | {p['sku'][:25]} | {err}")

    time.sleep(0.6)

print(f"\n=== RESULTADO ===")
print(f"Criados: {success}")
print(f"Falharam: {failed}")
print(f"Pulados (sem img): {skipped}")
print(f"Total elegiveis: {len(eligible)}")
