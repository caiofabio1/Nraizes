# NRAIZES - Guia de Setup e Deploy

## Visão Geral

Sistema de otimização de e-commerce que integra Bling ERP, Gestão Click e WooCommerce com inteligência artificial (Google Gemini) para automação de gestão de produtos, precificação e análise estratégica.

## Requisitos

### Sistema
- Python 3.10 ou superior
- SQLite 3.x (incluído no Python)
- 2GB+ RAM recomendado

### APIs Externas
- **Bling API v3** - OAuth 2.0
- **Gestão Click API** - Access/Secret Token
- **WooCommerce API v3** - Consumer Key/Secret
- **Google Gemini API** - API Key

## Instalação

### 1. Clone o Repositório
```bash
git clone https://github.com/seu-usuario/nraizes.git
cd nraizes
```

### 2. Crie o Ambiente Virtual
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instale as Dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as Credenciais

Crie a pasta `.credentials` e os arquivos de configuração:

```bash
mkdir .credentials
```

#### Bling API (`.credentials/bling_api_tokens.env`)
```env
ACCESS_TOKEN=seu_access_token_bling
REFRESH_TOKEN=seu_refresh_token_bling
CLIENT_ID=seu_client_id
CLIENT_SECRET=seu_client_secret
GEMINI_API_KEY=sua_api_key_gemini
```

#### Gestão Click API (`.credentials/gestao_api_tokens.env`)
```env
GESTAO_ACCESS_TOKEN=seu_access_token_gestao
GESTAO_SECRET_TOKEN=seu_secret_token_gestao
```

#### WooCommerce API (`.credentials/woo_api_tokens.env`)
```env
WOO_STORE_URL=https://sua-loja.com.br
WOO_CONSUMER_KEY=ck_xxxxxxxxxxxx
WOO_CONSUMER_SECRET=cs_xxxxxxxxxxxx
```

### 5. Inicialize o Banco de Dados
```bash
python src/database.py
```

## Estrutura do Projeto

```
NRAIZES/
├── src/                    # Código fonte principal
│   ├── bling_client.py     # Cliente API Bling
│   ├── gestao_client.py    # Cliente API Gestão Click
│   ├── woo_client.py       # Cliente API WooCommerce
│   ├── database.py         # Banco de dados SQLite
│   ├── pricing.py          # Motor de precificação
│   ├── enrichment.py       # Enriquecimento com IA
│   ├── web_dashboard.py    # Dashboard Flask
│   └── logger.py           # Sistema de logging
├── tests/                  # Testes unitários
├── data/                   # Banco SQLite (gerado)
├── logs/                   # Arquivos de log (gerados)
├── .credentials/           # Credenciais (não versionado)
├── requirements.txt        # Dependências Python
└── docs/                   # Documentação
```

## Uso

### Dashboard Web
```bash
python src/web_dashboard.py
# Acesse: http://localhost:5000
```

### Sincronização de Produtos
```bash
python -c "from src.database import VaultDB; from src.bling_client import BlingClient; VaultDB().sync_produtos_from_bling(BlingClient())"
```

### Enriquecimento com IA
```bash
python src/enrichment.py
```

### Análise Financeira
```bash
python src/financial_analysis.py
```

### Executar Testes
```bash
python -m pytest tests/ -v
```

## Configuração Avançada

### Parâmetros de Precificação

No banco de dados (`config` table):

| Chave | Valor Padrão | Descrição |
|-------|--------------|-----------|
| `MIN_MARGIN_PERCENT` | 20 | Margem mínima obrigatória |
| `MAX_PRICE_SWING_PERCENT` | 15 | Variação máxima diária de preço |
| `PRICING_STRATEGY` | protect_margin | Estratégia: `protect_margin` ou `aggressive` |

### Multiplicadores por Canal

| Canal | Multiplicador | Descrição |
|-------|---------------|-----------|
| WooCommerce | 1.00 | Preço base |
| Mercado Livre | 1.15 | +15% taxas ML |
| Shopee | 1.12 | +12% taxas Shopee |
| Amazon | 1.18 | +18% taxas Amazon |

### Logs

Os logs são salvos em `logs/`:
- `nraizes.log` - Log geral (rotação a cada 5MB)
- `errors.log` - Apenas erros

## Manutenção

### Rotação de Tokens Bling

O sistema renova automaticamente o token OAuth quando expira. Se falhar:

```bash
python scripts/refresh_tokens.py
```

### Backup do Banco

```bash
cp data/vault.db data/vault_backup_$(date +%Y%m%d).db
```

### Limpeza de Logs

```bash
# Manter apenas últimos 7 dias
find logs/ -name "*.log.*" -mtime +7 -delete
```

## Troubleshooting

### Erro: "Token expirado"
1. Verifique se `REFRESH_TOKEN` está correto
2. Execute `python scripts/refresh_tokens.py`
3. Se persistir, reautentique no painel Bling

### Erro: "Connection refused"
1. Verifique conectividade com a internet
2. Verifique se as URLs das APIs estão corretas
3. Consulte os logs em `logs/errors.log`

### Erro: "Database is locked"
1. Feche outras instâncias do aplicativo
2. Verifique se não há processos Python travados
3. Em último caso: `cp data/vault.db data/vault_backup.db && rm data/vault.db`

## Deploy em Produção

### Recomendações

1. **Use variáveis de ambiente** ao invés de arquivos `.env`
2. **Configure HTTPS** para o dashboard
3. **Use um gerenciador de processos** (PM2, Supervisor)
4. **Configure backups automáticos** do banco SQLite
5. **Monitore os logs** com ferramentas como Grafana/Loki

### Exemplo com PM2

```bash
# Instale PM2
npm install -g pm2

# Inicie o dashboard
pm2 start "python src/web_dashboard.py" --name nraizes-dashboard

# Configure auto-start
pm2 startup
pm2 save
```

### Variáveis de Ambiente (Produção)

```bash
export ACCESS_TOKEN="..."
export REFRESH_TOKEN="..."
export CLIENT_ID="..."
export CLIENT_SECRET="..."
export GEMINI_API_KEY="..."
export WOO_STORE_URL="..."
export WOO_CONSUMER_KEY="..."
export WOO_CONSUMER_SECRET="..."
export GESTAO_ACCESS_TOKEN="..."
export GESTAO_SECRET_TOKEN="..."
```

## Contato & Suporte

Para problemas técnicos, consulte os logs em `logs/` e abra uma issue no repositório.
