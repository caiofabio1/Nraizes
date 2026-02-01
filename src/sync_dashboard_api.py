"""
Sync Dashboard API - Multi-Store Product Synchronization
Flask API for the Bling multi-store sync dashboard with WooCommerce integration
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from bling_client import BlingClient
from collections import defaultdict
import unicodedata
import re

app = Flask(__name__, static_folder='../tools')
CORS(app)

# Initialize Bling client
# Initialize Bling client
bling = BlingClient()
WOO_STORE_ID = 205326820 # WooCommerce Store ID (Target)

# WooCommerce client (optional - may fail)
woo = None
woo_products_cache = None
woo_available = False

def init_woo():
    """Try to initialize WooCommerce client."""
    global woo, woo_available
    try:
        from woo_client import WooClient
        woo = WooClient()
        woo_available = True
        print("[WooCommerce] Client initialized")
    except Exception as e:
        print(f"[WooCommerce] Not available: {e}")
        woo_available = False

init_woo()


def get_woo_products():
    """Get WooCommerce products with error handling."""
    global woo_products_cache
    if not woo_available or woo is None:
        return []
    
    if woo_products_cache is not None:
        return woo_products_cache
    
    try:
        print("[WooCommerce] Fetching products (30 per page to avoid timeout)...")
        all_products = []
        page = 1
        max_pages = 10  # Max 300 products
        while page <= max_pages:
            products = woo.get_products(per_page=30, page=page)  # Reduced from 100 to avoid server timeout
            if not products:
                break
            all_products.extend(products)
            print(f"[WooCommerce] Page {page}: {len(products)} products")
            page += 1
            if len(products) < 30:
                break
        woo_products_cache = all_products
        print(f"[WooCommerce] Total: {len(all_products)} products loaded")
        return all_products
    except Exception as e:
        print(f"[WooCommerce] Error fetching products: {e}")
        return []


def normalize_name(name: str) -> str:
    """Normalize product name for comparison."""
    if not name:
        return ""
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    name = re.sub(r'\s+', ' ', name.lower().strip())
    name = re.sub(r'[^\w\s]', '', name)
    return name


def check_woo_sync(bling_product):
    """Check if a Bling product is synced with WooCommerce."""
    woo_products = get_woo_products()
    if not woo_products:
        return {'synced': False, 'woo_id': None, 'match_type': None}
    
    bling_sku = str(bling_product.get('codigo', '')).strip()
    bling_name = normalize_name(bling_product.get('nome', ''))
    
    for woo_p in woo_products:
        woo_sku = str(woo_p.get('sku', '')).strip()
        woo_name = normalize_name(woo_p.get('name', ''))
        
        if bling_sku and woo_sku and bling_sku == woo_sku:
            return {'synced': True, 'woo_id': woo_p['id'], 'match_type': 'sku'}
        if bling_name and woo_name and bling_name == woo_name:
            return {'synced': True, 'woo_id': woo_p['id'], 'match_type': 'name'}
    
    return {'synced': False, 'woo_id': None, 'match_type': None}


@app.route('/')
def serve_dashboard():
    return send_from_directory(app.static_folder, 'sync_dashboard.html')


@app.route('/api/lojas')
def get_lojas():
    """Get all configured stores."""
    try:
        print("[API] GET /api/lojas")
        all_links = bling.get_all_produtos_lojas(limite=100)
        
        lojas_map = {
            0: {'id': 0, 'descricao': 'Bling (PDV/Loja Física)', 'tipo': 'bling', 'vinculos_count': 0}
        }
        
        for link in all_links:
            loja = link.get('loja', {})
            loja_id = loja.get('id')
            if loja_id and loja_id not in lojas_map:
                lojas_map[loja_id] = {
                    'id': loja_id,
                    'descricao': f'Integração {loja_id}',
                    'tipo': 'integracao',
                    'vinculos_count': 0
                }
            if loja_id:
                lojas_map[loja_id]['vinculos_count'] += 1
        
        print(f"[API] Found {len(lojas_map)} stores")
        return jsonify({'success': True, 'data': list(lojas_map.values()), 'total': len(lojas_map)})
    except Exception as e:
        print(f"[API] Error in /api/lojas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/produtos')
def get_produtos():
    """Get products with store link status."""
    try:
        print("[API] GET /api/produtos")
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        search = request.args.get('search', '').lower()
        
        result = bling.get_produtos(pagina=page, limite=limit, criterio=2)
        produtos = result.get('data', [])
        print(f"[API] Got {len(produtos)} products from Bling")
        
        enriched = []
        for p in produtos:
            if search and search not in p.get('nome', '').lower() and search not in str(p.get('codigo', '')).lower():
                continue
            
            enriched.append({
                'id': p['id'],
                'nome': p.get('nome', ''),
                'codigo': p.get('codigo', ''),
                'preco': p.get('preco', 0),
                'situacao': p.get('situacao', ''),
                'lojas': [],
                'sync_status': 'active',
                'loja_count': 0
            })
        
        return jsonify({'success': True, 'data': enriched, 'page': page, 'total': len(enriched)})
    except Exception as e:
        print(f"[API] Error in /api/produtos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/duplicados')
def get_duplicados():
    """Detect duplicate products with robust link-based sync check."""
    try:
        print("[API] GET /api/duplicados - Starting...")
        
        # 1. Fetch ALL product-store links for the target WooCommerce store
        print(f"[API] Fetching links for Store {WOO_STORE_ID}...")
        try:
            store_links = bling.get_all_produtos_lojas(idLoja=WOO_STORE_ID, limite=100)
        except Exception as e:
            print(f"[API] Warning: Failed to fetch store links: {e}")
            store_links = []
            
        print(f"[API] Found {len(store_links)} links for Store {WOO_STORE_ID}")
        
        # 2. Build Sync Validation Map
        # Logic: If multiple Bling Products link to the SAME External ID, we must resolve collision.
        # We prioritize the NEWEST Link (highest ID) as the valid one.
        link_map = defaultdict(list) # external_id -> list of links
        
        for link in store_links:
            ext_id = link.get('codigo') # WooCommerce ID
            if ext_id:
                link_map[ext_id].append(link)
                
        valid_synced_ids = {} # bling_product_id -> woo_id
        collision_count = 0
        
        for ext_id, links in link_map.items():
            # Sort links by ID descending (newest first)
            links.sort(key=lambda x: x['id'], reverse=True)
            
            # The newest link is the winner
            active_link = links[0]
            billing_prod_id = active_link['produto']['id']
            valid_synced_ids[billing_prod_id] = ext_id
            
            if len(links) > 1:
                collision_count += 1
                
        print(f"[API] Validated {len(valid_synced_ids)} synced products ({collision_count} collisions resolved)")

        # 3. Get all active products from Bling
        print("[API] Fetching all products from Bling...")
        all_products = bling.get_all_produtos(criterio=2, limite=100)
        print(f"[API] Got {len(all_products)} products from Bling")
        
        # 4. Group by normalized name & SKU (Bling Duplicate Detection)
        by_name = defaultdict(list)
        by_sku = defaultdict(list)
        
        for p in all_products:
            name = normalize_name(p.get('nome', ''))
            sku = str(p.get('codigo', '')).strip()
            
            if name:
                by_name[name].append(p)
            if sku and sku != '0' and sku != '':
                by_sku[sku].append(p)
        
        print(f"[API] Analyzing duplicates...")
        duplicates = []
        seen_ids = set()
        
        def format_product(p):
            pid = p['id']
            is_synced = pid in valid_synced_ids
            woo_id = valid_synced_ids.get(pid)
            
            return {
                'id': pid,
                'nome': p.get('nome'),
                'codigo': p.get('codigo', ''),
                'preco': p.get('preco'),
                'situacao': p.get('situacao'),
                'woo_synced': is_synced,
                'woo_id': woo_id,
                'collision_warning': False # TODO: Add warning if it WAS linked but lost to collision?
            }
        
        # Find name duplicates
        for name, products in by_name.items():
            if len(products) > 1:
                ids = tuple(sorted([p['id'] for p in products]))
                if ids not in seen_ids:
                    seen_ids.add(ids)
                    
                    products_list = [format_product(p) for p in sorted(products, key=lambda x: x['id'])]
                    
                    # Sort: WooCommerce synced first, then by ID
                    products_list.sort(key=lambda x: (not x['woo_synced'], x['id']))
                    
                    duplicates.append({
                        'type': 'name',
                        'key': name,
                        'products': products_list,
                        'recommended_keep': products_list[0]['id']
                    })
        
        # Find SKU duplicates
        for sku, products in by_sku.items():
            if len(products) > 1:
                ids = tuple(sorted([p['id'] for p in products]))
                if ids not in seen_ids:
                    seen_ids.add(ids)
                    
                    products_list = [format_product(p) for p in sorted(products, key=lambda x: x['id'])]
                    
                    products_list.sort(key=lambda x: (not x['woo_synced'], x['id']))
                    
                    duplicates.append({
                        'type': 'sku',
                        'key': sku,
                        'products': products_list,
                        'recommended_keep': products_list[0]['id']
                    })
        
        print(f"[API] Found {len(duplicates)} duplicate groups")
        
        return jsonify({
            'success': True,
            'data': duplicates,
            'total_groups': len(duplicates),
            'total_products': sum(len(d['products']) for d in duplicates)
        })
    except Exception as e:
        print(f"[API] Error in /api/duplicados: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/duplicados/check-woo', methods=['POST'])
def check_woo_for_duplicates():
    """Check WooCommerce sync for specific product IDs - separate endpoint."""
    try:
        data = request.json
        product_ids = data.get('product_ids', [])
        
        print(f"[API] Checking WooCommerce for {len(product_ids)} products...")
        
        results = {}
        for pid in product_ids:
            product = bling.get_produtos_id_produto(str(pid)).get('data', {})
            woo_sync = check_woo_sync(product)
            results[pid] = woo_sync
        
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/merge/execute', methods=['POST'])
def merge_execute():
    """Execute merge: update SKU on keep product, inactivate duplicates."""
    try:
        data = request.json
        keep_id = data.get('keep_id')
        remove_ids = data.get('remove_ids', [])
        new_sku = data.get('new_sku')
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({'success': False, 'error': 'Confirmacao obrigatoria. Envie confirm=true'}), 400
        
        if not keep_id or not remove_ids:
            return jsonify({'success': False, 'error': 'Missing keep_id or remove_ids'}), 400
        
        print(f"[API] Executing merge: keep={keep_id}, remove={remove_ids}")
        results = []
        
        if new_sku:
            try:
                keep_product = bling.get_produtos_id_produto(str(keep_id)).get('data', {})
                update_body = {
                    'nome': keep_product.get('nome'),
                    'tipo': keep_product.get('tipo', 'P'),
                    'formato': keep_product.get('formato', 'S'),
                    'situacao': 'A',
                    'codigo': new_sku
                }
                bling.put_produtos_id_produto(str(keep_id), update_body)
                results.append({'id': keep_id, 'status': 'sku_updated', 'new_sku': new_sku})
                print(f"[API] Updated SKU for {keep_id} in Bling")
                
                # Update WooCommerce if linked
                if woo_available and woo:
                    try:
                        # Find link to WooCommerce Store
                        links = bling.get_produtos_lojas(idProduto=keep_id, idLoja=WOO_STORE_ID)
                        if 'data' in links and links['data']:
                            # Sort by newest link just in case
                            links['data'].sort(key=lambda x: x['id'], reverse=True)
                            link = links['data'][0]
                            woo_id = link.get('codigo') # This is the External ID (Woo Product ID)
                            
                            if woo_id:
                                print(f"[API] Updating WooCommerce Product {woo_id} SKU to {new_sku}")
                                woo.update_product(woo_id, {'sku': new_sku})
                                results.append({'id': keep_id, 'status': 'woo_sku_updated', 'woo_id': woo_id})
                            else:
                                print(f"[API] Warning: Link found but no external code for {keep_id}")
                    except Exception as we:
                        print(f"[API] WooCommerce Update Error: {we}")
                        results.append({'id': keep_id, 'status': 'woo_update_error', 'error': str(we)})

            except Exception as e:
                results.append({'id': keep_id, 'status': 'sku_update_error', 'error': str(e)})
        
        for rid in remove_ids:
            try:
                current = bling.get_produtos_id_produto(str(rid)).get('data', {})
                update_body = {
                    'nome': current.get('nome'),
                    'tipo': current.get('tipo', 'P'),
                    'formato': current.get('formato', 'S'),
                    'situacao': 'I'
                }
                bling.put_produtos_id_produto(str(rid), update_body)
                results.append({'id': rid, 'status': 'inativado'})
                print(f"[API] Inactivated {rid}")
            except Exception as e:
                results.append({'id': rid, 'status': 'erro', 'error': str(e)})
        
        return jsonify({
            'success': True,
            'results': results,
            'message': f'{len([r for r in results if r["status"] == "inativado"])} produtos inativados'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/status')
def get_status():
    """Get overall sync status."""
    try:
        print("[API] GET /api/status")
        active_products = bling.get_produtos(limite=100, criterio=2)
        links = bling.get_produtos_lojas(limite=100)
        
        unique_lojas = set()
        for link in links.get('data', []):
            loja_id = link.get('loja', {}).get('id')
            if loja_id:
                unique_lojas.add(loja_id)
        
        return jsonify({
            'success': True,
            'status': {
                'produtos_ativos': len(active_products.get('data', [])),
                'lojas_configuradas': len(unique_lojas) + 1,  # +1 for Bling base
                'vinculos_ativos': len(links.get('data', [])),
                'woo_available': woo_available
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("Starting Sync Dashboard API on http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
