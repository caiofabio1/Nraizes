"""
Bling Optimizer - Regenerate Truncated Proposals
Identifies and regenerates proposals that appear to be cut off.
"""
import sqlite3
import os
import sys
import re

sys.path.insert(0, os.path.dirname(__file__))

from enrichment import ProductEnricher
from database import VaultDB
from sanitizer import clean_text

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vault.db')


def find_truncated_proposals(min_length: int = 100):
    """Find proposals that appear to be truncated."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Find proposals that seem truncated
    cursor.execute('''
        SELECT DISTINCT p.id_produto, pr.nome, pr.codigo, pr.preco, pr.id_bling
        FROM propostas_ia p
        JOIN produtos pr ON p.id_produto = pr.id_bling
        WHERE p.status = 'pendente'
        AND (
            -- Descriptions that are too short
            (p.tipo = 'descricao_complementar' AND length(p.conteudo_proposto) < ?)
            -- Or end with incomplete patterns
            OR p.conteudo_proposto LIKE '%...'
            OR p.conteudo_proposto LIKE '%, e'
            OR p.conteudo_proposto LIKE '%, ou'
            OR p.conteudo_proposto LIKE '%- '
        )
    ''', (min_length,))
    
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return products


def delete_proposals_for_product(id_produto: int):
    """Delete existing proposals for a product before regenerating."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM propostas_ia WHERE id_produto = ? AND status = "pendente"', (id_produto,))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


def regenerate_truncated(dry_run: bool = False, limit: int = None):
    """Find and regenerate truncated proposals."""
    truncated = find_truncated_proposals()
    
    if limit:
        truncated = truncated[:limit]
    
    if not truncated:
        print("✅ Nenhuma proposta cortada encontrada!")
        return 0
    
    print(f"🔍 Encontradas {len(truncated)} produtos com propostas potencialmente cortadas:")
    
    for p in truncated[:10]:
        print(f"  - {p['nome'][:50]}")
    
    if len(truncated) > 10:
        print(f"  ... e mais {len(truncated) - 10}")
    
    if dry_run:
        print("\n🔍 DRY RUN - Nenhuma alteração será feita")
        return 0
    
    print(f"\n🔄 Regenerando {len(truncated)} produtos...")
    
    enricher = ProductEnricher()
    db = VaultDB()
    
    regenerated = 0
    
    for product in truncated:
        print(f"\n📝 Regenerando: {product['nome'][:40]}...")
        
        # Delete old proposals
        deleted = delete_proposals_for_product(product['id_bling'])
        print(f"   Removidas {deleted} propostas antigas")
        
        # Regenerate
        enrichment = enricher.enrich_product({
            'nome': product['nome'],
            'codigo': product['codigo'],
            'preco': product['preco'],
            'id': product['id_bling']
        })
        
        if enrichment:
            # Clean the content before saving
            if enrichment.get('descricao_curta'):
                enrichment['descricao_curta'] = clean_text(enrichment['descricao_curta'], keep_html=False)
                db.create_proposta(
                    id_produto=product['id_bling'],
                    tipo='descricao_curta',
                    conteudo_original='',
                    conteudo_proposto=enrichment['descricao_curta']
                )
            
            if enrichment.get('descricao_complementar'):
                enrichment['descricao_complementar'] = clean_text(enrichment['descricao_complementar'], keep_html=False)
                db.create_proposta(
                    id_produto=product['id_bling'],
                    tipo='descricao_complementar',
                    conteudo_original='',
                    conteudo_proposto=enrichment['descricao_complementar']
                )
            
            if enrichment.get('seo_title') or enrichment.get('seo_meta'):
                import json
                seo_data = json.dumps({
                    'title': enrichment.get('seo_title', ''),
                    'meta': enrichment.get('seo_meta', ''),
                    'keywords': enrichment.get('keywords', '')
                }, ensure_ascii=False)
                
                db.create_proposta(
                    id_produto=product['id_bling'],
                    tipo='seo',
                    conteudo_original='',
                    conteudo_proposto=seo_data
                )
            
            regenerated += 1
            print(f"   ✅ Regenerado com sucesso")
        else:
            print(f"   ❌ Falha ao regenerar")
    
    print(f"\n✅ Regeneradas {regenerated} de {len(truncated)} propostas")
    return regenerated


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Regenerate truncated AI proposals')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    parser.add_argument('--limit', type=int, help='Limit number of products')
    parser.add_argument('--find-only', action='store_true', help='Only find, do not regenerate')
    
    args = parser.parse_args()
    
    if args.find_only:
        truncated = find_truncated_proposals()
        print(f"\n📊 Encontradas {len(truncated)} propostas potencialmente cortadas")
        for p in truncated:
            print(f"  - {p['nome'][:60]}")
    else:
        regenerate_truncated(dry_run=args.dry_run, limit=args.limit)
