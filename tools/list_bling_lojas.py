#!/usr/bin/env python3
"""List all Bling stores/virtual stores"""
import sys
sys.path.insert(0, 'src')

from bling_client import BlingClient

def main():
    client = BlingClient()
    
    print("=== LOJAS VIRTUAIS NO BLING ===\n")
    lojas = client.get_lojas()
    
    for loja in lojas.get('data', []):
        print(f"ID: {loja['id']}")
        print(f"  Nome: {loja.get('descricao', 'N/A')}")
        print(f"  Tipo: {loja.get('tipo', 'N/A')}")
        print(f"  Situação: {loja.get('situacao', 'N/A')}")
        print()

if __name__ == "__main__":
    main()
