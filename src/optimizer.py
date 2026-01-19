"""
Bling Optimizer - Central CLI
Ferramenta de linha de comando para gerenciar todas as otimizações.
"""
import sys
import os
import click
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from strategic_dashboard import StrategicDashboard
from price_adjuster import PriceAdjuster
from price_monitor import PriceMonitor
from ean_finder import EANFinder
from database import init_database, get_connection, VaultDB
from bling_client import BlingClient
from enrichment import ProductEnricher
from review_dashboard import generate_review_dashboard

@click.group()
def cli():
    """Bling Optimizer - Ferramentas de Otimização e Inteligência."""
    pass

@cli.command()
def init():
    """Inicializa o banco de dados."""
    init_database()
    click.echo("✅ Banco de dados inicializado.")


@cli.command()
def dashboard():
    """Inicia o dashboard web unificado (http://localhost:5000)."""
    click.echo("🚀 Iniciando Dashboard Web Unificado...")
    click.echo("📍 Acesse: http://localhost:5000")
    click.echo("   Pressione Ctrl+C para encerrar.\n")
    
    import webbrowser
    webbrowser.open('http://localhost:5000')
    
    from web_dashboard import app
    app.run(host='0.0.0.0', port=5000, debug=False)

# ==============================================================================
# DASHBOARD ESTRATÉGICO
# ==============================================================================

@cli.command()
def dashboard_analyze():
    """Executa análise estratégica diária com IA."""
    click.echo("🚀 Iniciando análise estratégica...")
    dashboard = StrategicDashboard()
    result = dashboard.run_daily_analysis()
    
    if 'error' in result['analysis']:
        click.secho(f"❌ Erro: {result['analysis']['error']}", fg='red')
    else:
        click.secho("\n✅ Análise concluída e salva no banco.", fg='green')

@cli.command()
def dashboard_view():
    """Visualiza o último relatório estratégico."""
    dashboard = StrategicDashboard()
    report = dashboard.get_latest_report()
    
    if report:
        click.echo_via_pager(report)
    else:
        click.echo("Nenhum relatório encontrado.")

# ==============================================================================
# PRECIFICAÇÃO
# ==============================================================================

@cli.command()
@click.option('--limit', default=20, help='Limite de produtos para monitorar')
def prices_collect(limit):
    """Coleta preços de concorrentes (Mercado Livre, etc)."""
    click.echo(f"🕵️ Iniciando coleta de preços para {limit} produtos...")
    monitor = PriceMonitor()
    monitor.monitor_all(limit=limit)
    click.secho("✅ Coleta concluída!", fg='green')


@cli.command()
def prices_analyze():
    """Analisa preços e sugere ajustes."""
    click.echo("💰 Analisando preços vs mercado...")
    adjuster = PriceAdjuster()
    recomendacoes = adjuster.analisar_todos(apenas_com_dados=False)
    
    if not recomendacoes:
        click.echo("Nenhuma recomendação gerada (talvez falte dados de concorrentes).")
        return

    click.echo(f"\nEncontradas {len(recomendacoes)} recomendações:")
    click.echo("-" * 60)
    
    for rec in recomendacoes:
        color = 'green' if rec.acao.value == 'increase' else 'red' if rec.acao.value == 'decrease' else 'white'
        icon = '🔺' if rec.acao.value == 'increase' else '🔻' if rec.acao.value == 'decrease' else '➡️'
        
        click.secho(f"{icon} {rec.nome_produto[:40]}", fg=color, bold=True)
        click.echo(f"   Atual: R${rec.preco_atual:.2f} -> Sugerido: R${rec.preco_sugerido:.2f} ({rec.diferenca_percent:+.1f}%)")
        click.echo(f"   Motivo: {rec.motivo}")
        click.echo(f"   Confiança: {rec.confianca*100:.0f}% | Auto-ajuste: {'Sim' if rec.pode_auto_aplicar else 'Não'}")
        click.echo("-" * 60)

# ==============================================================================
# EAN FINDER
# ==============================================================================

@cli.command()
@click.option('--limit', default=10, help='Limite de produtos para buscar')
def ean_find(limit):
    """Busca EANs faltantes para produtos."""
    click.echo(f"🔍 Buscando EANs para {limit} produtos...")
    
    finder = EANFinder()
    db = VaultDB()
    
    # Buscar produtos sem GTIN
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM produtos 
        WHERE situacao='A' AND (gtin IS NULL OR gtin = '')
        LIMIT ?
    ''', (limit,))
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not products:
        click.echo("Nenhum produto sem EAN encontrado.")
        return

    click.echo(f"Encontrados {len(products)} produtos sem EAN.")
    
    click.echo(f"Encontrados {len(products)} produtos sem EAN.")
    click.echo("Iniciando busca sequencial com salvamento imediato...")
    
    saved_count = 0
    conn = db._get_conn()
    cursor = conn.cursor()
    
    try:
        for product in products:
            prod_id = product['id_bling']
            # Busca individual para salvar progresso
            candidates = finder.find_ean(product)
            
            if candidates:
                best = candidates[0]
                # Validar se a confiança é aceitável (> 60%)
                if best.confidence > 0.6:
                    click.secho(f"✅ Encontrado para {prod_id}: {best.ean} ({best.confidence*100:.0f}%)", fg='green')
                    
                    cursor.execute('''
                        UPDATE produtos SET gtin = ? WHERE id_bling = ?
                    ''', (best.ean, prod_id))
                    conn.commit()
                    saved_count += 1
                else:
                    click.secho(f"⚠️ Baixa confiança para {prod_id}: {best.ean} ({best.confidence*100:.0f}%) - Ignorado", fg='yellow')
            else:
                click.secho(f"❌ Não encontrado para {prod_id}", fg='red')
                
    except KeyboardInterrupt:
        click.secho("\n⛔ Interrompido pelo usuário. Progresso salvo.", fg='yellow')
    except Exception as e:
        click.secho(f"\n❌ Erro durante o processo: {e}", fg='red')
    finally:
        conn.close()
    
    click.echo(f"\nResumo: {saved_count} novos EANs salvos no banco de dados.")


@cli.command()
@click.option('--limit', default=50, help='Limite de produtos para buscar')
def ean_find_brands(limit):
    """Busca EANs apenas para produtos de marcas conhecidas."""
    click.echo(f"🏷️ Buscando EANs para MARCAS CONHECIDAS (limit: {limit})...")
    
    finder = EANFinder()
    db = VaultDB()
    
    # Marcas conhecidas (excluindo artesanais como Amokarite)
    marcas = ['laszlo', 'phebo', 'granado', 'avatim', 'vitafor', 
              'ocean drop', 'central nutrition', 'mahta', 'pantene', 'dove', 'natura']
    
    # Buscar produtos dessas marcas sem GTIN
    conn = db._get_conn()
    cursor = conn.cursor()
    
    # Build query for brands
    like_clauses = ' OR '.join([f"lower(nome) LIKE '%{m}%'" for m in marcas])
    query = f'''
        SELECT * FROM produtos 
        WHERE situacao='A' AND (gtin IS NULL OR gtin = '')
        AND ({like_clauses})
        LIMIT ?
    '''
    cursor.execute(query, (limit,))
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not products:
        click.echo("✅ Todos os produtos de marcas conhecidas já têm EAN!")
        return
    
    click.echo(f"📦 Encontrados {len(products)} produtos de marcas conhecidas sem EAN.")
    
    saved_count = 0
    conn = db._get_conn()
    cursor = conn.cursor()
    
    try:
        for product in products:
            prod_id = product['id_bling']
            candidates = finder.find_ean(product)
            
            if candidates:
                best = candidates[0]
                if best.confidence > 0.6:
                    click.secho(f"✅ {prod_id}: {best.ean} ({best.confidence*100:.0f}%)", fg='green')
                    cursor.execute('UPDATE produtos SET gtin = ? WHERE id_bling = ?', (best.ean, prod_id))
                    conn.commit()
                    saved_count += 1
                else:
                    click.secho(f"⚠️ Baixa confiança {prod_id}: {best.ean} ({best.confidence*100:.0f}%)", fg='yellow')
            else:
                click.secho(f"❌ Não encontrado para {prod_id}", fg='red')
                
    except KeyboardInterrupt:
        click.secho("\n⛔ Interrompido. Progresso salvo.", fg='yellow')
    finally:
        conn.close()
    
    click.echo(f"\n🎉 {saved_count} novos EANs salvos!")

@cli.command()
def dashboard_html():
    """Gera dashboard visual em HTML."""
    dashboard = StrategicDashboard()
    file_path = dashboard.export_to_html()
    if file_path:
        click.secho(f"✅ Dashboard salvo: {file_path}", fg='green')
        try:
            os.startfile(file_path)
            click.echo("🖥️  Abrindo no navegador...")
        except Exception:
            pass


@cli.command()
@click.option('--limit', default=50, help='Limite de produtos para processar em cada etapa')
def run_pipeline(limit):
    """Executa o pipeline completo de otimização."""
    click.secho("\n🚀 INICIANDO PIPELINE DE OTIMIZAÇÃO COMPLETO\n", fg='white', bold=True, bg='blue')
    
    # ... (steps 1, 2, 3 remains the same)

    # 1. Buscar EANs (apenas se limitar a poucos para não travar o pipeline, ou rodar batch)
    click.secho(f"\n1️⃣  BUSCANDO EANS FALTANTES (Limit: {limit})...", fg='cyan', bold=True)
    try:
        ctx = click.get_current_context()
        ctx.invoke(ean_find, limit=limit)
    except Exception as e:
        click.secho(f"Erro no passo 1: {e}", fg='red')

    # 2. Coletar Preços
    click.secho(f"\n2️⃣  COLETANDO PREÇOS DE MERCADO (Limit: {limit})...", fg='cyan', bold=True)
    try:
        ctx.invoke(prices_collect, limit=limit)
    except Exception as e:
        click.secho(f"Erro no passo 2: {e}", fg='red')

    # 3. Analisar Preços
    click.secho(f"\n3️⃣  ANALISANDO E SUGERINDO AJUSTES...", fg='cyan', bold=True)
    try:
        ctx.invoke(prices_analyze)
    except Exception as e:
        click.secho(f"Erro no passo 3: {e}", fg='red')

    # 4. Dashboard Estratégico
    click.secho(f"\n4️⃣  GERANDO DASHBOARD ESTRATÉGICO...", fg='cyan', bold=True)
    try:
        ctx.invoke(dashboard_analyze)
        
        # 5. Exportar Visual
        click.secho(f"\n5️⃣  CRIANDO VISUALIZAÇÃO...", fg='cyan', bold=True)
        ctx.invoke(dashboard_html)
        
    except Exception as e:
        click.secho(f"Erro no passo 4/5: {e}", fg='red')

    click.secho("\n✅ PIPELINE CONCLUÍDO COM SUCESSO!", fg='green', bold=True)


@cli.command()
@click.option('--prices', default='[]', help='JSON list of price updates ["id:price", ...]')
@click.option('--eans', default='[]', help='JSON list of EAN updates ["id:ean", ...]')
def apply_changes(prices, eans):
    """Aplica atualizações aprovadas no Bling."""
    click.echo("🚀 Iniciando sincronização com Bling...")
    
    try:
        price_list = json.loads(prices)
        ean_list = json.loads(eans)
    except json.JSONDecodeError:
        click.secho("❌ Erro ao decodificar JSON. Verifique o formato.", fg='red')
        return

    client = BlingClient()
    
    # 1. Prices
    if price_list:
        click.echo(f"💰 Atualizando {len(price_list)} preços...")
        for item in price_list:
            if ':' not in item: continue
            try:
                id_bling, new_price = item.split(':')
                # Bling v3: PUT /produtos/{id}
                payload = {'preco': float(new_price)}
                client.put_produtos_id_produto(id_bling, payload)
                click.echo(f"  ✅ Preço ID {id_bling} -> R$ {new_price}")
            except Exception as e:
                click.echo(f"  ❌ Falha ID {id_bling if 'id_bling' in locals() else '?'}: {e}")
                
    # 2. EANs
    if ean_list:
        click.echo(f"🏷️ Atualizando {len(ean_list)} GTINs...")
        for item in ean_list:
            if ':' not in item: continue
            try:
                id_bling, new_ean = item.split(':')
                payload = {'gtin': new_ean}
                client.put_produtos_id_produto(id_bling, payload)
                click.echo(f"  ✅ GTIN ID {id_bling} -> {new_ean}")
            except Exception as e:
                 click.echo(f"  ❌ Falha ID {id_bling if 'id_bling' in locals() else '?'}: {e}")
                 
    click.echo("\n✨ Sincronização concluída!")

# ==============================================================================
# ENRIQUECIMENTO IA
# ==============================================================================

@cli.command()
@click.option('--limit', default=10, help='Limite de produtos para enriquecer')
@click.option('--dry-run', is_flag=True, help='Simula sem salvar no banco')
def enrich(limit, dry_run):
    """Gera descrições e SEO com IA para produtos sem conteúdo."""
    click.echo(f"🤖 Iniciando enriquecimento para {limit} produtos...")
    
    db = VaultDB()
    enricher = ProductEnricher()
    
    # Buscar produtos sem descrição
    products = db.get_produtos_sem_descricao()[:limit]
    
    if not products:
        click.echo("✅ Todos os produtos já possuem descrição!")
        return
    
    click.echo(f"📝 Encontrados {len(products)} produtos para enriquecer.")
    
    if dry_run:
        click.secho("(Modo dry-run: não salvará no banco)", fg='yellow')
        for p in products[:3]:
            click.echo(f"  - {p['nome'][:50]}...")
        return
    
    count = enricher.generate_batch_proposals(products, db)
    click.secho(f"\n✅ {count} propostas criadas! Use 'review' para revisar.", fg='green')


@cli.command()
def review():
    """Gera e abre a interface de revisão de propostas IA."""
    click.echo("📊 Gerando dashboard de revisão...")
    
    output_path = generate_review_dashboard()
    
    try:
        os.startfile(output_path)
        click.secho(f"✅ Dashboard aberto: {output_path}", fg='green')
    except Exception:
        click.echo(f"Abra manualmente: {output_path}")


@cli.command()
@click.option('--all', 'approve_all', is_flag=True, help='Aprovar todas as pendentes')
@click.option('--type', 'tipo', default=None, help='Aprovar por tipo (descricao_curta, descricao_complementar, seo)')
@click.option('--file', 'filepath', default=None, help='Arquivo JSON com IDs para aprovar')
def approve(approve_all, tipo, filepath):
    """Aprova propostas de enriquecimento IA."""
    db = VaultDB()
    conn = get_connection()
    cursor = conn.cursor()
    
    if approve_all:
        cursor.execute('''
            UPDATE propostas_ia 
            SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
            WHERE status = 'pendente'
        ''')
        count = cursor.rowcount
        conn.commit()
        click.secho(f"✅ {count} propostas aprovadas!", fg='green')
        
    elif tipo:
        cursor.execute('''
            UPDATE propostas_ia 
            SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
            WHERE status = 'pendente' AND tipo = ?
        ''', (tipo,))
        count = cursor.rowcount
        conn.commit()
        click.secho(f"✅ {count} propostas do tipo '{tipo}' aprovadas!", fg='green')
        
    elif filepath:
        with open(filepath, 'r') as f:
            ids = json.load(f)
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f'''
            UPDATE propostas_ia 
            SET status = 'aprovado', reviewed_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        ''', ids)
        count = cursor.rowcount
        conn.commit()
        click.secho(f"✅ {count} propostas aprovadas do arquivo!", fg='green')
        
    else:
        # Mostrar estatísticas
        cursor.execute("SELECT status, COUNT(*) FROM propostas_ia GROUP BY status")
        stats = dict(cursor.fetchall())
        click.echo("\n📊 Estatísticas de Propostas:")
        click.echo(f"  Pendentes:  {stats.get('pendente', 0)}")
        click.echo(f"  Aprovadas:  {stats.get('aprovado', 0)}")
        click.echo(f"  Rejeitadas: {stats.get('rejeitado', 0)}")
        click.echo("\nUse --all, --type ou --file para aprovar.")
    
    conn.close()


if __name__ == '__main__':
    cli()
