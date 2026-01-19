"""
Bling Optimizer - Price Monitor Module
Coleta preços de concorrentes via Mercado Livre e outras fontes.
"""
import os
import requests
import sqlite3
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv

from database import VaultDB, get_connection

# Load API keys
cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.credentials', 'bling_api_tokens.env')
load_dotenv(cred_path)

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')


@dataclass
class CompetitorPrice:
    """Preço de concorrente encontrado."""
    fonte: str  # 'mercado_livre', 'google', etc
    vendedor: str
    preco: float
    url: str
    titulo: str
    disponivel: bool = True
    coletado_em: datetime = None
    
    def __post_init__(self):
        if not self.coletado_em:
            self.coletado_em = datetime.now()


class PriceMonitor:
    """Monitora preços de concorrentes."""
    
    def __init__(self):
        self.db = VaultDB()
        self.google_api_key = GOOGLE_API_KEY
    
    def search_mercado_livre(self, query: str) -> List[CompetitorPrice]:
        """Busca preços no Mercado Livre via Scraping (API bloqueada)."""
        prices = []
        try:
            # Clean query
            clean_query = query.replace(' ', '-')
            url = f"https://lista.mercadolivre.com.br/{clean_query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.find_all('li', class_='ui-search-layout__item')
                
                for item in items[:5]:
                    # ... (parsing logic) ...
                    # Tentar encontrar preço
                    price_fraction = item.find('span', class_='andes-money-amount__fraction')
                    price_cents = item.find('span', class_='andes-money-amount__cents')
                    
                    if not price_fraction:
                        continue
                        
                    price_text = price_fraction.get_text().replace('.', '')
                    if price_cents:
                        price_text += f".{price_cents.get_text()}"
                    
                    try:
                        price = float(price_text)
                    except ValueError:
                        continue
                        
                    # Tentar encontrar título
                    title_tag = item.find('h2', class_='ui-search-item__title')
                    if not title_tag:
                        title_tag = item.find('a', class_='ui-search-item__group__element')
                    
                    title = title_tag.get_text().strip() if title_tag else "Sem Título"
                    
                    # Link
                    link_tag = item.find('a', class_='ui-search-link')
                    url = link_tag['href'] if link_tag else ''
                    
                    # Vendedor
                    vendedor = "Mercado Livre"
                            
                    prices.append(CompetitorPrice(
                        fonte='mercado_livre',
                        vendedor=vendedor,
                        preco=price,
                        url=url,
                        titulo=title
                    ))
            else:
                print(f"    ⚠️ ML Bloqueio/Erro: Status {response.status_code}")
                
        except Exception as e:
            print(f"    ⚠️ Erro Mercado Livre (Exceção): {e}")
        
        return prices

    # ... (middleware methods) ...

    def monitor_all(self, limit: int = 10):
        """Monitora múltiplos produtos (com EAN preferencialmente)."""
        import time
        import random
        
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Priorizar produtos com GTIN ou marcas importantes
        cursor.execute('''
            SELECT * FROM produtos 
            WHERE situacao = 'A' 
            ORDER BY gtin DESC, tipo DESC
            LIMIT ?
        ''', (limit,))
        
        products = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        print(f"🔍 Iniciando monitoramento para {len(products)} produtos...")
        for p in products:
            self.monitor_product(p)
            # Delay aleatório para evitar bloqueio
            time.sleep(random.uniform(1.5, 3.5))
