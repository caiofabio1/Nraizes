# NRAIZES WordPress Site

Repositório para gerenciamento do tema filho e customizações do site NRAIZES.

## Estrutura

```
wp-content/
└── themes/
    └── organium-child/
        ├── functions.php    # Customizações PHP
        └── style.css        # Estilos customizados
```

## Deploy Automático (CI/CD)

Este repositório está configurado com GitHub Actions para deploy automático.

### Como funciona

1. Faça alterações nos arquivos localmente
2. Commit e push para a branch `main`
3. O GitHub Actions faz deploy automático via SFTP

### Branches

- `main` - Produção (deploy automático)
- `develop` - Desenvolvimento

## Configuração Inicial

### Secrets necessários no GitHub

Configure os seguintes secrets em Settings → Secrets → Actions:

| Secret | Descrição |
|--------|-----------|
| `SFTP_HOST` | nbd.448.myftpupload.com |
| `SFTP_USER` | client_23d482ca87_712121 |
| `SFTP_PASSWORD` | Senha SFTP |
| `SFTP_PATH` | /html/wp-content/themes/organium-child |

## Desenvolvimento Local

```bash
# Clone o repositório
git clone https://github.com/caiofabio1/nraizes-wordpress.git

# Faça suas alterações
# Commit e push
git add .
git commit -m "Descrição das alterações"
git push origin main
```

## Licença

Este tema filho é baseado no tema Organium por Artureanec.
