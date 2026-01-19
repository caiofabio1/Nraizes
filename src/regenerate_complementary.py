"""
Regenerate Complementary Descriptions with improved prompt.
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from enrichment import ProductEnricher
from database import VaultDB
from sanitizer import clean_text

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vault.db')


def get_products_needing_complementary():
    """Get products that need complementary description regeneration."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get products that don't have a complementary description proposal
    cursor.execute('''
        SELECT DISTINCT p.*
        FROM produtos p
        LEFT JOIN propostas_ia pr ON p.id_bling = pr.id_produto AND pr.tipo = 'descricao_complementar'
        WHERE pr.id IS NULL AND p.situacao = 'A'
    ''')
    
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return products


def regenerate_complementary(limit: int = None):
    """Regenerate complementary descriptions only."""
    products = get_products_needing_complementary()
    
    if limit:
        products = products[:limit]
    
    if not products:
        print("✅ Todos os produtos já têm descrição complementar!")
        return 0
    
    print(f"📝 Regenerando descrições complementares para {len(products)} produtos...")
    
    enricher = ProductEnricher()
    db = VaultDB()
    
    count = 0
    for product in products:
        print(f"🤖 Gerando: {product['nome'][:50]}...")
        
        try:
            enrichment = enricher.enrich_product({
                'nome': product['nome'],
                'codigo': product['codigo'],
                'preco': product['preco'] or 0,
                'id': product['id_bling']
            })
            
            if enrichment and enrichment.get('descricao_complementar'):
                # Clean content
                cleaned = clean_text(enrichment['descricao_complementar'], keep_html=False)
                
                # Only save complementary description
                db.create_proposta(
                    id_produto=product['id_bling'],
                    tipo='descricao_complementar',
                    conteudo_original=product.get('descricao_complementar', ''),
                    conteudo_proposto=cleaned
                )
                count += 1
                
                # Show word count
                word_count = len(cleaned.split())
                print(f"   ✅ {word_count} palavras")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    print(f"\n✅ Geradas {count} descrições complementares detalhadas")
    return count


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='Limit products')
    args = parser.parse_args()
    
    regenerate_complementary(limit=args.limit)
