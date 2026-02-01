# 📊 Guia de Implementação - Correção do Analytics Novas Raízes

**Data:** Janeiro 2026  
**Problema Principal:** 99% do tráfego aparece como "(direct) / (none)"  
**Solução:** Implementação unificada de Analytics

## 🚨 Problema Diagnosticado

### 1. Múltiplas Implementações Conflitantes
- **Google Analytics 4** via código PHP customizado
- **Google Tag Manager** via plugin GTM4WP  
- **Google Site Kit** gerenciando consent mode

### 2. Ordem de Execução Incorreta
1. Site Kit define `analytics_storage: denied`
2. GA4 tenta enviar dados
3. Sem cookies = sem atribuição = tudo vira "direct/none"

### 3. Consent Mode Mal Configurado
- Analytics bloqueado por padrão para TODOS os países
- Eventos disparando antes do consentimento
- DataLayer duplicado múltiplas vezes

## ✅ Solução Implementada

Criamos o arquivo `analytics_unified.php` que resolve todos os problemas:

### Recursos da Nova Implementação:

1. **Consent Mode Inteligente**
   - Analytics permitido por padrão no Brasil
   - GDPR compliance para países da UE
   - Atualização dinâmica após consentimento

2. **Ordem de Carregamento Correta**
   - Consent definido ANTES de qualquer tag
   - GTM e GA4 carregados após consent
   - Eventos só disparam com permissão

3. **Preservação de UTMs**
   - UTMs mantidos durante navegação
   - Atribuição correta de campanhas
   - Suporte para gclid e fbclid

4. **E-commerce Enhanced**
   - Todos os eventos padrão implementados
   - Compatible com GTM e GA4 direto
   - Prevenção de duplicação

## 📋 Passos de Implementação

### Passo 1: Backup
```bash
# Faça backup do arquivo atual
cp wp-content/themes/organium-child/inc/analytics.php wp-content/themes/organium-child/inc/analytics_backup.php
```

### Passo 2: Atualizar functions.php
```php
// Remover linha antiga:
// require_once get_stylesheet_directory() . '/inc/analytics.php';

// Adicionar nova linha:
require_once get_stylesheet_directory() . '/inc/analytics_unified.php';
```

### Passo 3: Configurar GTM4WP
No painel WordPress:
1. Vá para Configurações > Google Tag Manager
2. Marque "Container code is manually placed" 
3. Mantenha dataLayer habilitado
4. Salve as configurações

### Passo 4: Configurar Site Kit
1. Mantenha o Site Kit instalado para outras funcionalidades
2. Não precisa alterar configurações de consent (já tratamos isso)

### Passo 5: Testar Implementação
```javascript
// No console do navegador, verifique:
console.log(window.dataLayer);

// Deve mostrar eventos sendo enviados corretamente
```

## 🔍 Verificação no Google Analytics

### Após 24-48 horas, verifique:

1. **Relatório de Aquisição**
   - Tráfego orgânico aparecendo
   - Redes sociais identificadas
   - Campanhas com UTM rastreadas

2. **Relatório em Tempo Real**
   - Fontes de tráfego corretas
   - Eventos de e-commerce funcionando

3. **DebugView**
   - Ative o modo debug
   - Confirme ordem dos eventos

## 🛠️ Configurações Adicionais Recomendadas

### 1. Filtros de IP no GA4
```
Admin > Data Streams > Configure tag settings > Define internal traffic
- Adicione IPs da equipe
- Marque tráfego como "internal"
- Crie filtro para excluir
```

### 2. Cross-domain Tracking
```
Admin > Data Streams > Configure tag settings > Configure your domains
- Adicione todos os domínios usados
- Ex: nraizes.com.br, app.nraizes.com.br
```

### 3. Enhanced Measurement
```
Admin > Data Streams > Enhanced measurement
- Ative todos os eventos relevantes
- Especialmente "Site search" e "Form interactions"
```

## 📊 Monitoramento Pós-Implementação

### Semana 1
- [ ] Verificar se direct/none está diminuindo
- [ ] Confirmar eventos de e-commerce
- [ ] Testar links com UTM

### Semana 2
- [ ] Analisar relatório de aquisição
- [ ] Verificar taxa de conversão por fonte
- [ ] Ajustar eventos se necessário

### Semana 4
- [ ] Gerar relatório comparativo
- [ ] Documentar melhorias
- [ ] Planejar próximas otimizações

## ⚠️ Troubleshooting

### Problema: Ainda vejo muito tráfego direto
**Solução:** 
1. Verifique se o arquivo foi incluído corretamente
2. Limpe cache do WordPress e CDN
3. Teste em aba anônima

### Problema: Eventos duplicados
**Solução:**
1. Desative temporariamente GTM4WP
2. Verifique se não há outros plugins de analytics
3. Use o DebugView para identificar origem

### Problema: Consent não funciona
**Solução:**
1. Verifique qual plugin de cookies está usando
2. Adapte os event listeners no código
3. Teste com console.log nos eventos

## 📞 Suporte

Para dúvidas sobre esta implementação:
1. Verifique os logs no console do navegador
2. Use o Google Tag Assistant
3. Consulte o DebugView no GA4

---

**Importante:** Após implementar, aguarde 24-48 horas para ver mudanças significativas nos dados. O Google Analytics precisa deste tempo para processar e exibir as correções de atribuição.