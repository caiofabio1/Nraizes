"""Sincroniza dados enriquecidos (descrições IA) com o Bling."""
import sys
sys.path.insert(0, 'src')
from database import get_connection
from bling_client import BlingClient
from dotenv import load_dotenv

# Garante tokens atualizados
load_dotenv('.credentials/bling_api_tokens.env', override=True)

conn = get_connection()
cursor = conn.cursor()

# Buscar propostas aprovadas
cursor.execute('''
    SELECT p.id, p.id_produto, p.tipo, p.conteudo_proposto, pr.nome
    FROM propostas_ia p
    JOIN produtos pr ON p.id_produto = pr.id_bling
    WHERE p.status = 'aprovado'
    ORDER BY p.id_produto, p.tipo
''')
proposals = cursor.fetchall()
conn.close()

if not proposals:
    print("⚠️ Nenhuma proposta aprovada para sincronizar.")
    print("   Use 'python src/optimizer.py approve --all' para aprovar todas as pendentes.")
    exit(0)

print(f"🔄 Sincronizando {len(proposals)} propostas aprovadas com o Bling...")

client = BlingClient()
success = 0
errors = 0

# Agrupar por produto
from collections import defaultdict
by_product = defaultdict(dict)
for prop_id, id_produto, tipo, conteudo, nome in proposals:
    by_product[id_produto]['nome'] = nome
    by_product[id_produto][tipo] = conteudo

# Sincronizar
for id_produto, data in by_product.items():
    nome = data.get('nome', '')[:35]
    try:
        update_payload = {}
        
        # Mapear tipos para campos Bling
        if 'descricao_curta' in data:
            update_payload['descricaoCurta'] = data['descricao_curta']
        if 'descricao_complementar' in data:
            update_payload['observacoes'] = data['descricao_complementar']
        
        if update_payload:
            client.patch_produtos_id_produto(str(id_produto), update_payload)
            print(f"  ✅ {nome}... ({len(update_payload)} campos)")
            success += 1
        else:
            print(f"  ⏭️ {nome}... (nenhum campo aplicável)")
            
    except Exception as e:
        err_msg = str(e)[:80]
        print(f"  ❌ {id_produto}: {err_msg}")
        errors += 1

print(f"\n🎉 Sincronização concluída!")
print(f"   ✅ Sucesso: {success}")
print(f"   ❌ Erros: {errors}")

# Marcar como aplicadas
if success > 0:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE propostas_ia 
        SET status = 'aplicado' 
        WHERE status = 'aprovado'
    ''')
    conn.commit()
    conn.close()
    print(f"   📋 {cursor.rowcount} propostas marcadas como aplicadas")
