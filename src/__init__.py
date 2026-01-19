# Bling Optimizer Package
"""
Bling Optimizer - Sistema de otimização de produtos para e-commerce.

Módulos:
- bling_client: Cliente para API Bling v3
- database: Banco de dados SQLite local
- enrichment: Enriquecimento com IA (Gemini)
- pricing: Motor de precificação dinâmica
- optimizer: Interface de linha de comando
"""

from .bling_client import BlingClient
from .database import VaultDB
from .enrichment import ProductEnricher
from .pricing import PricingEngine

__version__ = "1.0.0"
__all__ = ['BlingClient', 'VaultDB', 'ProductEnricher', 'PricingEngine']
