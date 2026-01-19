"""
Bling Optimizer - Batch Approval Script
Approves proposals from a JSON file or approves all pending proposals.
"""
import sqlite3
import json
import sys
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'vault.db')


def approve_all():
    """Approve all pending proposals."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE propostas_ia 
        SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
        WHERE status = 'pendente'
    ''')
    
    count = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ Aprovadas {count} propostas")
    return count


def approve_from_file(filepath):
    """Approve proposals from a JSON file containing list of IDs."""
    with open(filepath, 'r') as f:
        ids = json.load(f)
    
    if not ids:
        print("❌ Nenhum ID no arquivo")
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    placeholders = ','.join('?' * len(ids))
    cursor.execute(f'''
        UPDATE propostas_ia 
        SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
        WHERE id IN ({placeholders})
    ''', ids)
    
    count = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ Aprovadas {count} propostas")
    return count


def approve_by_type(tipo):
    """Approve all proposals of a specific type."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE propostas_ia 
        SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
        WHERE status = 'pendente' AND tipo = ?
    ''', (tipo,))
    
    count = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"✅ Aprovadas {count} propostas do tipo '{tipo}'")
    return count


def show_stats():
    """Show approval statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT status, COUNT(*) FROM propostas_ia GROUP BY status")
    stats = dict(cursor.fetchall())
    
    cursor.execute("SELECT tipo, COUNT(*) FROM propostas_ia WHERE status = 'pendente' GROUP BY tipo")
    by_type = dict(cursor.fetchall())
    
    conn.close()
    
    print("\n📊 Estatísticas de Propostas:")
    print(f"  Pendentes:  {stats.get('pendente', 0)}")
    print(f"  Aprovadas:  {stats.get('aprovado', 0)}")
    print(f"  Rejeitadas: {stats.get('rejeitado', 0)}")
    
    if by_type:
        print("\n📝 Pendentes por tipo:")
        for tipo, count in by_type.items():
            print(f"  {tipo}: {count}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python approve_batch.py --all              # Aprova todas")
        print("  python approve_batch.py --type descricao_curta  # Aprova por tipo")
        print("  python approve_batch.py propostas.json     # Aprova IDs do arquivo")
        print("  python approve_batch.py --stats            # Mostra estatísticas")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    if arg == '--all':
        approve_all()
    elif arg == '--stats':
        show_stats()
    elif arg == '--type' and len(sys.argv) > 2:
        approve_by_type(sys.argv[2])
    elif arg.endswith('.json'):
        approve_from_file(arg)
    else:
        print(f"❌ Argumento inválido: {arg}")
