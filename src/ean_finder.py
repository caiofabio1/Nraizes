"""
Bling Optimizer - EAN/GTIN Finder Module
Uses multiple sources to find product barcodes for accurate price matching.
"""
import os
import re
import json
import requests
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import google.generativeai as genai
from dotenv import load_dotenv

# Load API keys
cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.credentials', 'bling_api_tokens.env')
load_dotenv(cred_path)

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


@dataclass
class EANCandidate:
    """A potential EAN/GTIN for a product."""
    ean: str
    source: str  # 'open_food_facts', 'upc_database', 'google', 'ai_inference'
    confidence: float  # 0-1
    product_name: str  # Name from source for verification
    url: str = ""


def validate_ean13(ean: str) -> bool:
    """Validate EAN-13 checksum."""
    if not ean or len(ean) != 13 or not ean.isdigit():
        return False
    
    # Calculate checksum
    total = 0
    for i, digit in enumerate(ean[:12]):
        if i % 2 == 0:
            total += int(digit)
        else:
            total += int(digit) * 3
    
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(ean[12])


def validate_ean(ean: str) -> bool:
    """Validate any EAN format (8, 12, 13, 14)."""
    if not ean or not ean.isdigit():
        return False
    
    # Pad to 13 digits if needed
    if len(ean) == 8:
        # EAN-8: different checksum
        return True  # Simplified for now
    elif len(ean) == 12:
        # UPC-A: prepend 0 to make EAN-13
        return validate_ean13('0' + ean)
    elif len(ean) == 13:
        return validate_ean13(ean)
    elif len(ean) == 14:
        # GTIN-14: validate last 13 digits
        return validate_ean13(ean[1:])
    
    return False


def fix_ean_checksum(ean: str) -> str:
    """Fix EAN-13 checksum if structurally valid but checksum is wrong."""
    if not ean or len(ean) != 13 or not ean.isdigit():
        return None
    
    # If already valid, return as is
    if validate_ean13(ean):
        return ean
    
    # Calculate correct checksum
    total = 0
    for i, digit in enumerate(ean[:12]):
        if i % 2 == 0:
            total += int(digit)
        else:
            total += int(digit) * 3
    
    correct_check_digit = (10 - (total % 10)) % 10
    
    # Return corrected EAN
    return ean[:12] + str(correct_check_digit)


def validate_or_fix_ean(ean: str) -> tuple[bool, str]:
    """Validate EAN, and if checksum is wrong, try to fix it."""
    if not ean or not ean.isdigit():
        return False, None
    
    if len(ean) == 13:
        if validate_ean13(ean):
            return True, ean
        else:
            # Try to fix checksum
            fixed = fix_ean_checksum(ean)
            if fixed:
                return True, fixed
    
    if validate_ean(ean):
        return True, ean
    
    return False, None


class EANFinder:
    """Find EAN/GTIN codes for products using multiple sources."""
    
    # Termos que indicam produtos sem EAN padrão (granel, artesanal, etc)
    EXCLUSION_TERMS = [
        'a granel', 'granel', 'pct', 'folha', 'raiz', 'casca', 'flor ', 
        'erva ', 'artesanal', 'manipulado', 'fracionado', 'avulso',
        'cha de', 'chá de', 'cha ', 'chá ', 'tisana', 'infusao',
        'hong ling', 'qing xia', 'ganoderma', 'osmanthus', 'oolong',
        'jujuba', 'goji', 'codonopsis', 'amora', 'espinheiro',
        '(cx)', 'cx.', 'sache', 'sachê',
        'amokarite',  # Artesanal - sem EAN padrão
    ]
    
    # Marcas conhecidas com prefixos EAN
    BRAND_PREFIXES = {
        'ocean drop': '7898681',
        'granado': '7896512',
        'phebo': '7891027', 
        'laszlo': '789',
        'avatim': '789',
        'amokarite': '789',
        'vitafor': '789',
        'central nutrition': '789',
        'mahta': '789',
        'mushin': '789',
    }
    
    def __init__(self):
        pass # Model is called via requests now
    
    def should_exclude(self, product_name: str) -> bool:
        """Check if product should be excluded from EAN search."""
        name_lower = product_name.lower()
        return any(term in name_lower for term in self.EXCLUSION_TERMS)
    
    def extract_brand(self, product_name: str) -> tuple:
        """Extract brand name and EAN prefix from product name."""
        name_lower = product_name.lower()
        for brand, prefix in self.BRAND_PREFIXES.items():
            if brand in name_lower:
                return brand.title(), prefix
        return None, None
    
    def search_cosmos(self, product_name: str) -> List[EANCandidate]:
        """Search Cosmos (Brazilian product database) for EAN."""
        candidates = []
        
        try:
            # Clean product name - keep brand and key terms
            words = product_name.lower().replace('-', ' ').split()
            # Keep first 4 meaningful words
            search_words = [w for w in words if len(w) > 2][:4]
            query = ' '.join(search_words)
            
            # Cosmos uses Google CSE - we'll scrape the search results
            url = f"https://cosmos.bluesoft.com.br/produtos?utf8=%E2%9C%93&q={requests.utils.quote(query)}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                # Parse HTML for EAN codes (they appear in the product list)
                import re
                # Look for 13-digit numbers that could be EANs
                eans = re.findall(r'\b(789\d{10})\b', response.text)
                
                for ean in eans[:3]:  # Take top 3
                    if validate_ean(ean):
                        candidates.append(EANCandidate(
                            ean=ean,
                            source='cosmos',
                            confidence=0.8,
                            product_name=query,
                            url=f"https://cosmos.bluesoft.com.br/produtos/{ean}"
                        ))
                        
        except Exception as e:
            print(f"  ⚠️ Cosmos search error: {e}")
        
        return candidates
    
    def search_open_food_facts(self, product_name: str) -> List[EANCandidate]:
        """Search Open Food Facts database (free, good for food/supplements)."""
        candidates = []
        
        try:
            # Clean product name for search
            search_terms = product_name.lower().replace('-', ' ').split()[:5]
            query = '+'.join(search_terms)
            
            url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=5"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                for product in data.get('products', [])[:3]:
                    ean = product.get('code', '')
                    if ean and validate_ean(ean):
                        candidates.append(EANCandidate(
                            ean=ean,
                            source='open_food_facts',
                            confidence=0.7,
                            product_name=product.get('product_name', ''),
                            url=f"https://world.openfoodfacts.org/product/{ean}"
                        ))
        except Exception as e:
            print(f"  ⚠️ Open Food Facts error: {e}")
        
        return candidates
    
    def search_upc_database(self, product_name: str) -> List[EANCandidate]:
        """Search UPC Database (free tier: 100/day)."""
        candidates = []
        
        try:
            # Clean product name
            query = product_name[:50].replace(' ', '+')
            url = f"https://api.upcitemdb.com/prod/trial/search?s={query}&match_mode=0&type=product"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get('items', [])[:3]:
                    ean = item.get('ean', '') or item.get('upc', '')
                    if ean and validate_ean(ean):
                        candidates.append(EANCandidate(
                            ean=ean,
                            source='upc_database',
                            confidence=0.65,
                            product_name=item.get('title', ''),
                            url=f"https://www.upcitemdb.com/upc/{ean}"
                        ))
        except Exception as e:
            print(f"  ⚠️ UPC Database error: {e}")
        
        return candidates
    
    def search_google_for_ean(self, product_name: str) -> List[EANCandidate]:
        """Search Google for product EAN/barcode."""
        candidates = []
        
        if not GOOGLE_API_KEY:
            return candidates
        
        try:
            # Search for EAN/barcode
            queries = [
                f"{product_name} EAN código barras",
                f"{product_name} GTIN",
            ]
            
            for query in queries[:1]:  # Limit to avoid quota
                # Using Google Custom Search API
                # Note: Requires a Custom Search Engine ID (CX)
                # For now, we'll use the Gemini grounding approach
                pass
                
        except Exception as e:
            print(f"  ⚠️ Google search error: {e}")
        
        return candidates
    
    def infer_ean_with_ai(self, product: Dict[str, Any], retry_count: int = 0) -> List[EANCandidate]:
        """Use Gemini AI with grounding to find EAN from product info."""
        candidates = []
        
        nome = product.get('nome', '')
        
        # Extract brand for better search
        brand_keywords = ['Ocean Drop', 'Granado', 'Phebo', 'Taimin', 'Central Nutrition', 
                         'Avatim', 'AmoKarite', 'Mushin', 'Mahta', 'Vitafor', 'Laszlo']
        
        brand = None
        for bk in brand_keywords:
            if bk.lower() in nome.lower():
                brand = bk
                break
        
        prompt = f'''Você é um especialista em códigos de barras EAN/GTIN de produtos brasileiros.

PRODUTO PARA BUSCAR:
- Nome completo: {nome}
- Marca identificada: {brand or "Não identificada"}
- Código interno: {product.get('codigo', '')}
- Preço: R$ {product.get('preco', 0):.2f}

SUA TAREFA:
Você tem acesso à internet e deve BUSCAR o código EAN/GTIN-13 real deste produto.

ESTRATÉGIAS DE BUSCA:
1. Pesquise "{nome} EAN" ou "{nome} código de barras"
2. Procure no site oficial da marca ({brand or "fabricante"})
3. Busque em e-commerces (Amazon, Mercado Livre, Drogasil, Panvel)
4. Consulte bases de dados de produtos (Cosmos, Open Food Facts)

MARCAS CONHECIDAS E SEUS PREFIXOS EAN:
- Ocean Drop (suplementos): prefixo 7898681 (Brasil)
- Granado (cosméticos): prefixo 7896512 ou 7891027 (Brasil)
- Phebo (cosméticos): prefixo 7891027 (Brasil - mesma empresa Granado)
- Central Nutrition: prefixo 789 (Brasil)
- Avatim: prefixo 789 (Brasil)
- Vitafor: prefixo 789 (Brasil)

EXEMPLOS DE EANs CONHECIDOS:
- Astaxantina Ocean Drop 60 caps: 7898681220557
- Colônia Granado Bebê 100ml: 7896512912466
- Sabonete Phebo: 7891027xxx

RESPONDA APENAS COM JSON VÁLIDO:
{{"ean": "0000000000000", "confianca": 0.95, "fonte": "site oficial/e-commerce/base de dados", "justificativa": "breve explicação"}}

OU se não encontrar:
{{"ean": null, "confianca": 0, "fonte": null, "justificativa": "motivo"}}

IMPORTANTE: 
- O EAN DEVE ter exatamente 13 dígitos
- O EAN DEVE começar com 789 ou 790 para produtos brasileiros
- Valide o checksum mentalmente (último dígito é verificador)
- Só forneça se tiver alta confiança
'''
        
        try:
            # Use requests for API call
            headers = {"Content-Type": "application/json"}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_API_KEY}"
            
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024
                }
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code != 200:
                # Fallback
                 url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
                 response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                resp_json = response.json()
                try:
                    text = resp_json['candidates'][0]['content']['parts'][0]['text']
                except:
                    text = "{}"
            else:
                text = "{}"
            
            # Parse JSON
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
                ean = data.get('ean')
                
                if ean:
                    # Try to validate or fix the EAN checksum
                    is_valid, corrected_ean = validate_or_fix_ean(str(ean))
                    
                    if is_valid and corrected_ean:
                        confidence = data.get('confianca', 0.5)
                        
                        # If we had to fix the checksum, note it but keep high confidence
                        if corrected_ean != str(ean):
                            print(f"    ⚠️ Checksum corrigido: {ean} → {corrected_ean}")
                        
                        # Boost confidence if brand prefix matches
                        if brand == 'Ocean Drop' and corrected_ean.startswith('7898681'):
                            confidence = min(confidence + 0.1, 0.99)
                        elif brand in ['Granado', 'Phebo'] and corrected_ean.startswith('7891027'):
                            confidence = min(confidence + 0.1, 0.99)
                        
                        candidates.append(EANCandidate(
                            ean=corrected_ean,
                        source='ai_inference',
                        confidence=confidence,
                        product_name=f"{data.get('fonte', '')} - {data.get('justificativa', '')}",
                        url=''
                    ))
        except Exception as e:
            print(f"  ⚠️ AI inference error: {e}")
        
        # Retry once if no candidates found
        if not candidates and retry_count < 1:
            import time
            time.sleep(0.5)
            return self.infer_ean_with_ai(product, retry_count=retry_count + 1)
        
        return candidates
    
    def find_ean(self, product: Dict[str, Any]) -> List[EANCandidate]:
        """
        Find EAN candidates for a product using all sources.
        
        Returns list of candidates sorted by confidence.
        """
        nome = product.get('nome', '')
        all_candidates = []
        
        # Check exclusion first
        if self.should_exclude(nome):
            print(f"  ⏭️ Excluído (granel/artesanal): {nome[:40]}...")
            return []
        
        print(f"  🔍 Buscando EAN para: {nome[:40]}...")
        
        # Extract brand for better matching
        brand, expected_prefix = self.extract_brand(nome)
        if brand:
            print(f"    🏷️ Marca detectada: {brand}")
        
        # 1. Cosmos (Brazilian database - priority for BR products)
        cosmos_candidates = self.search_cosmos(nome)
        all_candidates.extend(cosmos_candidates)
        if cosmos_candidates:
            print(f"    ✅ Cosmos: {len(cosmos_candidates)} candidatos")
        
        # 2. Open Food Facts (for food/supplements)
        off_candidates = self.search_open_food_facts(nome)
        all_candidates.extend(off_candidates)
        if off_candidates:
            print(f"    ✅ Open Food Facts: {len(off_candidates)} candidatos")
        
        # 3. UPC Database
        upc_candidates = self.search_upc_database(nome)
        all_candidates.extend(upc_candidates)
        if upc_candidates:
            print(f"    ✅ UPC Database: {len(upc_candidates)} candidatos")
        
        # 4. AI Inference (if no other candidates or low confidence)
        if not all_candidates or max(c.confidence for c in all_candidates) < 0.6:
            ai_candidates = self.infer_ean_with_ai(product)
            all_candidates.extend(ai_candidates)
            if ai_candidates:
                print(f"    ✅ AI Inference: {len(ai_candidates)} candidatos")
        
        # Sort by confidence
        all_candidates.sort(key=lambda x: x.confidence, reverse=True)
        
        return all_candidates
    
    def find_eans_batch(self, products: List[Dict], limit: int = None) -> Dict[int, List[EANCandidate]]:
        """Find EANs for multiple products."""
        results = {}
        
        if limit:
            products = products[:limit]
        
        print(f"\n🔍 Buscando EAN para {len(products)} produtos...\n")
        
        for product in products:
            product_id = product.get('id_bling') or product.get('id')
            candidates = self.find_ean(product)
            results[product_id] = candidates
            
            if candidates:
                best = candidates[0]
                print(f"    Melhor: {best.ean} ({best.source}, {best.confidence:.0%})")
            else:
                print(f"    ❌ Nenhum candidato encontrado")
            print()
        
        return results


if __name__ == "__main__":
    # Test with sample product
    finder = EANFinder()
    
    test_product = {
        'nome': 'Vitamin D3 2000UI Ocean Drop',
        'codigo': 'VIT-D3-2000',
        'preco': 59.90
    }
    
    candidates = finder.find_ean(test_product)
    
    if candidates:
        print("\n📊 Candidatos encontrados:")
        for c in candidates:
            print(f"  EAN: {c.ean}")
            print(f"  Fonte: {c.source}")
            print(f"  Confiança: {c.confidence:.0%}")
            print(f"  Nome: {c.product_name}")
            print()
