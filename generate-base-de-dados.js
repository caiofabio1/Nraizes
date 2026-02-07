#!/usr/bin/env node
/**
 * generate-base-de-dados.js
 *
 * Reads consulta-produtos.json, .css and .js assets, then generates
 * a complete standalone HTML page (base-de-dados.html) that replicates
 * the PHP shortcode output from consulta-produtos.php.
 *
 * Usage:  node generate-base-de-dados.js
 */

'use strict';

const fs   = require('fs');
const path = require('path');
const url  = require('url');

/* ================================================================
   PATHS
   ================================================================ */
const THEME_DIR  = path.join(__dirname, 'wp-content', 'themes', 'organium-child');
const JSON_PATH  = path.join(THEME_DIR, 'data', 'consulta-produtos.json');
const CSS_PATH   = path.join(THEME_DIR, 'assets', 'css', 'consulta-produtos.css');
const JS_PATH    = path.join(THEME_DIR, 'assets', 'js', 'consulta-produtos.js');
const OUTPUT     = path.join(THEME_DIR, 'base-de-dados.html');

/* ================================================================
   LOAD FILES
   ================================================================ */
const data    = JSON.parse(fs.readFileSync(JSON_PATH, 'utf8'));
const cssText = fs.readFileSync(CSS_PATH, 'utf8');
const jsText  = fs.readFileSync(JS_PATH, 'utf8');

const produtos = data.produtos || [];
const total    = produtos.length;
const updated  = data.atualizado_em || new Date().toISOString().slice(0, 10);
const aviso    = data.aviso_legal || '';

/* ================================================================
   HELPER: escHtml  (htmlspecialchars equivalent)
   ================================================================ */
function escHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/* ================================================================
   HELPER: escAttr  (same as escHtml for attributes)
   ================================================================ */
function escAttr(str) {
    return escHtml(str);
}

/* ================================================================
   HELPER: sanitizeTitle  (WordPress sanitize_title equivalent)
   ================================================================ */
function sanitizeTitle(str) {
    if (!str) return '';
    // Lowercase
    let s = str.toLowerCase();
    // Replace accented characters
    const map = {
        'á':'a','à':'a','â':'a','ã':'a','ä':'a','å':'a',
        'é':'e','è':'e','ê':'e','ë':'e',
        'í':'i','ì':'i','î':'i','ï':'i',
        'ó':'o','ò':'o','ô':'o','õ':'o','ö':'o',
        'ú':'u','ù':'u','û':'u','ü':'u',
        'ç':'c','ñ':'n','ý':'y','ÿ':'y',
        'ð':'d','ø':'o','æ':'ae','ß':'ss',
        'Á':'a','À':'a','Â':'a','Ã':'a','Ä':'a','Å':'a',
        'É':'e','È':'e','Ê':'e','Ë':'e',
        'Í':'i','Ì':'i','Î':'i','Ï':'i',
        'Ó':'o','Ò':'o','Ô':'o','Õ':'o','Ö':'o',
        'Ú':'u','Ù':'u','Û':'u','Ü':'u',
        'Ç':'c','Ñ':'n','Ý':'y',
    };
    s = s.replace(/[^\x00-\x7F]/g, (ch) => map[ch] || ch);
    // Replace non-alphanumeric with hyphens
    s = s.replace(/[^a-z0-9]+/g, '-');
    // Trim hyphens from ends
    s = s.replace(/^-+|-+$/g, '');
    return s;
}

/* ================================================================
   HELPER: renderReference
   ================================================================ */
function renderReference(ref) {
    ref = (ref || '').trim();
    if (!ref) return '';

    if (ref.indexOf('http') === 0) {
        // PubMed / direct URL
        let label = ref;
        if (ref.indexOf('pubmed.ncbi.nlm.nih.gov') !== -1) {
            try {
                const parsed = new URL(ref);
                const basename = path.basename(parsed.pathname);
                const pmid = basename.replace(/[^0-9]/g, '');
                label = 'PubMed PMID: ' + pmid;
            } catch (_) { /* keep label as URL */ }
        }
        return '<li><cite><a href="' + escAttr(ref) + '" target="_blank" rel="noopener noreferrer">' + escHtml(label) + '</a></cite></li>';
    } else if (/^10\.\d{4,}/.test(ref)) {
        // DOI
        return '<li><cite><a href="https://doi.org/' + escAttr(ref) + '" target="_blank" rel="noopener noreferrer">DOI: ' + escHtml(ref) + '</a></cite></li>';
    } else {
        // Plain text citation
        return '<li><cite>' + escHtml(ref) + '</cite></li>';
    }
}

/* ================================================================
   HELPER: renderTags
   ================================================================ */
function renderTags(items, cssModifier) {
    if (!items || !Array.isArray(items) || items.length === 0) return '';
    const cls = cssModifier ? ' nrc-tag--' + cssModifier : '';
    let html = '<ul class="nrc-tags" role="list">';
    for (const item of items) {
        const trimmed = (item || '').trim();
        if (trimmed) {
            html += '<li class="nrc-tag' + cls + '">' + escHtml(trimmed) + '</li>';
        }
    }
    html += '</ul>';
    return html;
}

/* ================================================================
   HELPER: evidenceClass
   ================================================================ */
function evidenceClass(nivel) {
    const n = (nivel || '').toLowerCase();
    if (n.indexOf('alta') !== -1 && n.indexOf('moderada') !== -1) return 'moderada-alta';
    if (n.indexOf('alta') !== -1) return 'alta';
    if (n.indexOf('moderada') !== -1 && n.indexOf('baixa') !== -1) return 'baixa-moderada';
    if (n.indexOf('moderada') !== -1) return 'moderada';
    if (n.indexOf('muito') !== -1) return 'muito-baixa';
    return 'baixa';
}

/* ================================================================
   HELPER: formatDate  (dd/mm/yyyy)
   ================================================================ */
function formatDate(dateStr) {
    const d = new Date(dateStr + 'T00:00:00');
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    return dd + '/' + mm + '/' + yyyy;
}

/* ================================================================
   HELPER: todayISO
   ================================================================ */
function todayISO() {
    const d = new Date();
    return d.getFullYear() + '-' +
        String(d.getMonth() + 1).padStart(2, '0') + '-' +
        String(d.getDate()).padStart(2, '0');
}

/* ================================================================
   RENDER: Product Card
   ================================================================ */
function renderProductCard(p, index) {
    const nome        = p.nome || '';
    const nome_cn     = p.nome_chines || '';
    const categoria   = p.categoria || '';
    const cat_slug    = p.categoria_slug || 'outro';
    const nivel_ev    = p.nivel_evidencia || '';
    const dosagem     = p.dosagem || '';
    const modo_uso    = p.modo_uso || '';
    const ind_mtc     = p.indicacao_mtc || '';
    const aplicacoes  = p.aplicacoes_clinicas || '';
    const estudos     = p.estudos_resumo || '';
    const armazen     = p.armazenamento || '';
    const origem      = p.origem || '';

    const contraindicacoes = p.contraindicacoes || [];
    const interacoes       = p.interacoes || [];
    const efeitos_col      = p.efeitos_colaterais || [];
    const alertas          = p.alertas || [];
    const ingredientes     = p.ingredientes || [];
    const princ_ativos     = p.principios_ativos || [];
    const certificacoes    = p.certificacoes || [];
    const referencias      = p.referencias || [];
    const faq              = p.faq || [];

    // Normalize slug for display grouping
    let display_slug;
    if (cat_slug === 'suplemento' || categoria === 'Suplemento Ocidental') {
        display_slug = 'suplemento';
    } else {
        display_slug = cat_slug;
    }

    // Build searchable text
    const search_parts = [nome, nome_cn, categoria, ind_mtc, aplicacoes, modo_uso, dosagem, estudos, origem];
    for (const arr of [ingredientes, princ_ativos, contraindicacoes, alertas, certificacoes]) {
        if (Array.isArray(arr)) search_parts.push(arr.join(' '));
    }
    if (Array.isArray(faq)) {
        for (const f of faq) {
            if (f.pergunta) search_parts.push(f.pergunta);
            if (f.resposta) search_parts.push(f.resposta);
        }
    }
    const search_text = search_parts.filter(Boolean).join(' ').toLowerCase();

    const ev_class = nivel_ev ? evidenceClass(nivel_ev) : '';
    const slug_id  = sanitizeTitle(nome) + '-' + index;

    let html = '';

    html += `    <article class="nrc-card"
             id="${escAttr(slug_id)}"
             data-categoria="${escAttr(display_slug)}"
             data-evidencia="${escAttr(ev_class)}"
             data-search="${escAttr(search_text)}"
             itemscope
             itemtype="https://schema.org/Article">

        <details>
            <summary class="nrc-card-header">
                <span class="nrc-card-icon nrc-card-icon--${escAttr(display_slug)}" aria-hidden="true"></span>
                <div class="nrc-card-info">
                    <h3 class="nrc-card-name" itemprop="name headline">
                        ${escHtml(nome)}`;

    if (nome_cn) {
        html += `
                            <span class="nrc-card-chinese" lang="zh">${escHtml(nome_cn)}</span>`;
    }

    html += `
                    </h3>
                    <div class="nrc-card-meta">
                        <span class="nrc-card-cat">${escHtml(categoria)}</span>`;

    if (nivel_ev) {
        html += `
                        <span class="nrc-card-evidence nrc-evidence--${escAttr(ev_class)}">
                                <span class="nrc-dot nrc-dot-${escAttr(ev_class)}"></span>
                                ${escHtml(nivel_ev)}
                            </span>`;
    }

    html += `
                    </div>
                </div>
                <span class="nrc-card-toggle" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                </span>
            </summary>

            <div class="nrc-card-content" itemprop="articleBody">
`;

    // --- Dosagem / Modo de Uso / Indicação MTC ---
    if (dosagem || modo_uso || ind_mtc) {
        html += `                <section class="nrc-section" aria-label="Informações de uso">
                    <dl class="nrc-dl-grid">`;

        if (dosagem) {
            html += `
                        <div class="nrc-dl-item">
                            <dt>Dosagem Recomendada</dt>
                            <dd class="nrc-text-block nrc-dosage-block">${escHtml(dosagem)}</dd>
                        </div>`;
        }
        if (modo_uso) {
            html += `
                        <div class="nrc-dl-item">
                            <dt>Modo de Uso</dt>
                            <dd class="nrc-text-block">${escHtml(modo_uso)}</dd>
                        </div>`;
        }
        if (ind_mtc) {
            html += `
                        <div class="nrc-dl-item">
                            <dt>Indicação na Medicina Tradicional Chinesa</dt>
                            <dd class="nrc-text-block">${escHtml(ind_mtc)}</dd>
                        </div>`;
        }

        html += `
                    </dl>
                </section>
`;
    }

    // --- Aplicações Clínicas ---
    if (aplicacoes) {
        html += `                <section class="nrc-section" aria-label="Aplicações clínicas">
                    <h4 class="nrc-section-title">Aplicações Clínicas Baseadas em Evidências</h4>
                    <p class="nrc-text-block">${escHtml(aplicacoes)}</p>
                </section>
`;
    }

    // --- Segurança ---
    if (contraindicacoes.length || interacoes.length || efeitos_col.length || alertas.length) {
        html += `                <section class="nrc-section nrc-safety" aria-label="Segurança e precauções">
                    <h4 class="nrc-section-title">Segurança e Precauções</h4>
                    <div class="nrc-section-grid">`;

        if (contraindicacoes.length) {
            html += `
                        <div>
                            <h5 class="nrc-subsection-title">Contraindicações</h5>
                            ${renderTags(contraindicacoes, 'danger')}
                        </div>`;
        }
        if (interacoes.length) {
            html += `
                        <div>
                            <h5 class="nrc-subsection-title">Interações Medicamentosas</h5>
                            ${renderTags(interacoes, 'interaction')}
                        </div>`;
        }
        if (efeitos_col.length) {
            html += `
                        <div>
                            <h5 class="nrc-subsection-title">Efeitos Colaterais</h5>
                            ${renderTags(efeitos_col, 'warning')}
                        </div>`;
        }
        if (alertas.length) {
            html += `
                        <div>
                            <h5 class="nrc-subsection-title">Alertas</h5>
                            ${renderTags(alertas, 'warning')}
                        </div>`;
        }

        html += `
                    </div>
                </section>
`;
    }

    // --- Evidência Científica ---
    if (estudos) {
        html += `                <section class="nrc-section" aria-label="Evidência científica">
                    <h4 class="nrc-section-title">Evidência Científica</h4>
                    <blockquote class="nrc-text-block nrc-evidence-block" cite="https://pubmed.ncbi.nlm.nih.gov/">
                        <p>${escHtml(estudos)}</p>
                    </blockquote>
                </section>
`;
    }

    // --- Ingredientes / Princípios Ativos ---
    if (ingredientes.length || princ_ativos.length) {
        html += `                <section class="nrc-section" aria-label="Composição">
                    <h4 class="nrc-section-title">Composição</h4>
                    <div class="nrc-section-grid">`;

        if (ingredientes.length) {
            html += `
                        <div>
                            <h5 class="nrc-subsection-title">Ingredientes</h5>
                            ${renderTags(ingredientes, '')}
                        </div>`;
        }
        if (princ_ativos.length) {
            html += `
                        <div>
                            <h5 class="nrc-subsection-title">Princípios Ativos</h5>
                            ${renderTags(princ_ativos, '')}
                        </div>`;
        }

        html += `
                    </div>
                </section>
`;
    }

    // --- Armazenamento / Origem / Certificações ---
    if (armazen || origem || certificacoes.length) {
        html += `                <section class="nrc-section" aria-label="Informações adicionais">
                    <dl class="nrc-dl-grid">`;

        if (armazen) {
            html += `
                        <div class="nrc-dl-item">
                            <dt>Armazenamento</dt>
                            <dd class="nrc-text-block">${escHtml(armazen)}</dd>
                        </div>`;
        }
        if (origem) {
            html += `
                        <div class="nrc-dl-item">
                            <dt>Origem</dt>
                            <dd class="nrc-text-block">${escHtml(origem)}</dd>
                        </div>`;
        }

        html += `
                    </dl>`;

        if (certificacoes.length) {
            html += `
                        <h5 class="nrc-subsection-title">Certificações</h5>
                        ${renderTags(certificacoes, 'cert')}`;
        }

        html += `
                </section>
`;
    }

    // --- Referências Científicas ---
    if (referencias.length) {
        html += `                <section class="nrc-section nrc-references-section" aria-label="Referências científicas">
                    <h4 class="nrc-section-title">Referências Científicas</h4>
                    <ol class="nrc-references">
`;
        for (const ref of referencias) {
            html += '                        ' + renderReference(ref) + '\n';
        }
        html += `                    </ol>
                </section>
`;
    }

    // --- FAQ ---
    if (faq.length) {
        html += `                <section class="nrc-section nrc-faq-section" aria-label="Perguntas frequentes sobre ${escAttr(nome)}">
                    <h4 class="nrc-section-title">Perguntas Frequentes</h4>
`;
        for (const item of faq) {
            if (item.pergunta) {
                html += `                        <div class="nrc-faq-item" itemscope itemtype="https://schema.org/Question">
                            <h5 class="nrc-faq-q" itemprop="name">${escHtml(item.pergunta)}</h5>
                            <div itemscope itemtype="https://schema.org/Answer" itemprop="acceptedAnswer">
                                <p class="nrc-faq-a" itemprop="text">${escHtml(item.resposta || '')}</p>
                            </div>
                        </div>
`;
            }
        }
        html += `                </section>
`;
    }

    // --- CTA ---
    const waMsg = encodeURIComponent('Oi! Gostaria de saber sobre ' + nome + '. Vocês têm disponível na loja?');
    html += `                <div class="nrc-card-cta">
                    <a href="https://wa.me/5511999927588?text=${waMsg}"
                       class="nrc-cta-btn nrc-cta-btn--whatsapp" target="_blank" rel="noopener noreferrer"
                       aria-label="Perguntar sobre ${escAttr(nome)} no WhatsApp">
                        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2 22l4.832-1.438A9.955 9.955 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18c-1.66 0-3.203-.508-4.484-1.375l-.316-.191-2.828.84.84-2.828-.191-.316A7.953 7.953 0 014 12c0-4.411 3.589-8 8-8s8 3.589 8 8-3.589 8-8 8z"/></svg>
                        Consultar disponibilidade
                    </a>
                    <a href="https://www.google.com/maps/search/R.+Dr.+Nicolau+de+Sousa+Queir%C3%B3s,+34+-+Vila+Mariana,+S%C3%A3o+Paulo+-+SP"
                       class="nrc-cta-btn nrc-cta-btn--map" target="_blank" rel="noopener noreferrer"
                       aria-label="Ver localização da loja no mapa">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
                        Como chegar
                    </a>
                </div>

                <meta itemprop="author" content="Novas Raízes - nraizes.com.br">
                <meta itemprop="datePublished" content="${escAttr(todayISO())}">
                <meta itemprop="publisher" content="Novas Raízes">

            </div><!-- .nrc-card-content -->
        </details>
    </article>
`;

    return html;
}

/* ================================================================
   MERGE CATEGORIES  (Suplemento Ocidental -> Suplemento)
   ================================================================ */
const display_cats = {};
for (const [cat, count] of Object.entries(data.categorias || {})) {
    if (cat === 'Suplemento Ocidental') {
        display_cats['Suplemento'] = (display_cats['Suplemento'] || 0) + count;
    } else {
        display_cats[cat] = (display_cats[cat] || 0) + count;
    }
}

/* ================================================================
   STORE HOURS
   ================================================================ */
const now = new Date();
const hora_atual = now.getHours();
const dia_semana = now.getDay(); // 0=dom

let storeHoursHtml;
const aberto = (dia_semana >= 1 && dia_semana <= 6 && hora_atual >= 9 && hora_atual < 18);
if (aberto) {
    storeHoursHtml = '<span class="nrc-store-open">Aberto agora</span> \u00b7 Fecha \u00e0s 18:30';
} else if (dia_semana === 0) {
    storeHoursHtml = '<span class="nrc-store-closed">Fechado</span> \u00b7 Abre segunda \u00e0s 09:00';
} else {
    storeHoursHtml = '<span class="nrc-store-closed">Fechado</span> \u00b7 Seg-S\u00e1b 09:00-18:30';
}

/* ================================================================
   JSON-LD STRUCTURED DATA
   ================================================================ */
const pageUrl = 'https://nraizes.com.br/base-de-dados/';

// 1. MedicalWebPage
const medicalPage = {
    '@context': 'https://schema.org',
    '@type': 'MedicalWebPage',
    '@id': pageUrl + '#webpage',
    'name': 'Guia de Produtos Naturais e Suplementos - Novas Raízes',
    'description': 'Base de dados com ' + total + ' produtos naturais, fórmulas da Medicina Tradicional Chinesa, suplementos e plantas medicinais com informações baseadas em evidências científicas e referências a PubMed.',
    'url': pageUrl,
    'inLanguage': 'pt-BR',
    'lastReviewed': updated,
    'reviewedBy': { '@type': 'Organization', 'name': 'Novas Raízes', 'url': 'https://nraizes.com.br' },
    'specialty': { '@type': 'MedicalSpecialty', 'name': 'Medicina Integrativa' },
    'medicalAudience': { '@type': 'MedicalAudience', 'audienceType': 'Patient' },
    'about': [
        { '@type': 'MedicalTherapy', 'name': 'Fitoterapia' },
        { '@type': 'MedicalTherapy', 'name': 'Medicina Tradicional Chinesa' },
        { '@type': 'MedicalTherapy', 'name': 'Suplementação Nutricional' },
    ],
    'mainEntity': { '@type': 'Dataset', '@id': pageUrl + '#dataset' },
    'speakable': { '@type': 'SpeakableSpecification', 'cssSelector': ['.nrc-title', '.nrc-subtitle', '.nrc-geo-text'] },
    'publisher': {
        '@type': 'Organization',
        '@id': 'https://nraizes.com.br/#organization',
        'name': 'Novas Raízes',
        'url': 'https://nraizes.com.br',
        'logo': { '@type': 'ImageObject', 'url': 'https://nraizes.com.br/wp-content/uploads/logo-novas-raizes.png' },
        'sameAs': ['https://www.instagram.com/nraizes'],
    },
};

// 2. Dataset
const categoriesList = [];
for (const [cat, count] of Object.entries(data.categorias || {})) {
    categoriesList.push(cat + ' (' + count + ')');
}

const dataset = {
    '@context': 'https://schema.org',
    '@type': 'Dataset',
    '@id': pageUrl + '#dataset',
    'name': 'Base de Dados de Produtos Naturais e Suplementos - Novas Raízes',
    'description': 'Base de dados com informações científicas de ' + total + ' produtos incluindo fórmulas da Medicina Tradicional Chinesa (MTC), suplementos alimentares, plantas medicinais e óleos essenciais. Cada registro inclui dosagem, contraindicações, interações medicamentosas, resumo de evidências e referências científicas (PubMed/Cochrane).',
    'url': pageUrl,
    'license': 'https://creativecommons.org/licenses/by-nc/4.0/',
    'inLanguage': 'pt-BR',
    'dateModified': updated,
    'datePublished': '2025-01-01',
    'keywords': [
        'produtos naturais', 'suplementos alimentares', 'medicina tradicional chinesa',
        'MTC', 'fitoterapia', 'óleos essenciais', 'plantas medicinais',
        'evidências científicas', 'PubMed', 'contraindicações', 'dosagem',
        'Novas Raízes', 'saúde integrativa', 'medicina natural',
    ],
    'variableMeasured': [
        'dosagem recomendada', 'nível de evidência científica',
        'contraindicações', 'interações medicamentosas', 'resumo de evidências',
    ],
    'measurementTechnique': 'Revisão de literatura científica (PubMed, Cochrane, CNKI)',
    'size': total + ' produtos',
    'distribution': { '@type': 'DataDownload', 'encodingFormat': 'text/html', 'contentUrl': pageUrl },
    'creator': { '@type': 'Organization', 'name': 'Novas Raízes', 'url': 'https://nraizes.com.br' },
};

// 3. FAQPage
const faqItems = [];
for (const p of produtos) {
    if (p.faq && Array.isArray(p.faq)) {
        for (const f of p.faq) {
            if (f.pergunta && f.resposta) {
                faqItems.push({
                    '@type': 'Question',
                    'name': f.pergunta,
                    'acceptedAnswer': { '@type': 'Answer', 'text': f.resposta },
                });
            }
        }
    }
}

const faqSchema = faqItems.length ? {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    'name': 'Perguntas Frequentes sobre Produtos Naturais e Suplementos',
    'description': 'Respostas baseadas em evidências científicas para perguntas frequentes sobre suplementos, fórmulas MTC, plantas medicinais e produtos naturais.',
    'mainEntity': faqItems.slice(0, 100),
} : null;

// 4. LocalBusiness
const localBusiness = {
    '@context': 'https://schema.org',
    '@type': ['LocalBusiness', 'HealthAndBeautyBusiness'],
    '@id': 'https://nraizes.com.br/#localbusiness',
    'name': 'Novas Ra\u00edzes & Mivegan',
    'description': 'Loja de produtos naturais, suplementos alimentares, Medicina Tradicional Chinesa, \u00f3leos essenciais e plantas medicinais na Vila Mariana, S\u00e3o Paulo.',
    'url': 'https://nraizes.com.br',
    'telephone': '+5511999927588',
    'priceRange': '$$',
    'image': 'https://nraizes.com.br/wp-content/uploads/logo-novas-raizes.png',
    'address': {
        '@type': 'PostalAddress',
        'streetAddress': 'R. Dr. Nicolau de Sousa Queir\u00f3s, 34',
        'addressLocality': 'S\u00e3o Paulo',
        'addressRegion': 'SP',
        'postalCode': '04105-000',
        'addressCountry': 'BR',
    },
    'geo': { '@type': 'GeoCoordinates', 'latitude': -23.5714, 'longitude': -46.6350 },
    'openingHoursSpecification': [{
        '@type': 'OpeningHoursSpecification',
        'dayOfWeek': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
        'opens': '09:00',
        'closes': '18:30',
    }],
    'sameAs': ['https://www.instagram.com/nraizes'],
    'hasMap': 'https://www.google.com/maps/search/R.+Dr.+Nicolau+de+Sousa+Queir%C3%B3s,+34+-+Vila+Mariana,+S%C3%A3o+Paulo+-+SP',
    'knowsAbout': [
        'Produtos Naturais', 'Suplementos Alimentares', 'Medicina Tradicional Chinesa',
        '\u00d3leos Essenciais', 'Plantas Medicinais', 'Fitoterapia', 'Aromaterapia',
    ],
};

// 5. BreadcrumbList
const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    'itemListElement': [
        { '@type': 'ListItem', 'position': 1, 'name': 'Início', 'item': 'https://nraizes.com.br/' },
        { '@type': 'ListItem', 'position': 2, 'name': 'Guia de Produtos Naturais', 'item': pageUrl },
    ],
};

// 6. ItemList (products with evidence)
const productSchemas = [];
for (const p of produtos) {
    if (!p.nivel_evidencia && !p.estudos_resumo) continue;
    if (productSchemas.length >= 50) break;

    const catSlug = p.categoria_slug || '';
    let schemaType = 'Product';
    if (['suplemento', 'formula_mtc'].includes(catSlug)) {
        schemaType = 'DietarySupplement';
    }

    const item = {
        '@type': schemaType,
        'name': p.nome,
        'description': p.estudos_resumo || p.aplicacoes_clinicas || '',
        'category': p.categoria || '',
    };

    if (p.dosagem) {
        item.doseSchedule = { '@type': 'RecommendedDoseSchedule', 'frequency': p.dosagem };
    }
    if (p.contraindicacoes && p.contraindicacoes.length) {
        item.warning = p.contraindicacoes.join('; ');
    }
    if (p.interacoes && p.interacoes.length) {
        item.interactingDrug = p.interacoes;
    }
    if (p.referencias && p.referencias.length) {
        const citations = [];
        for (const ref of p.referencias) {
            const r = (ref || '').trim();
            if (r.indexOf('http') === 0) {
                citations.push({ '@type': 'ScholarlyArticle', 'url': r });
            } else if (/^10\.\d{4,}/.test(r)) {
                citations.push({ '@type': 'ScholarlyArticle', 'url': 'https://doi.org/' + r });
            }
        }
        if (citations.length) item.citation = citations;
    }

    productSchemas.push(item);
}

let itemsListSchema = null;
if (productSchemas.length) {
    itemsListSchema = {
        '@context': 'https://schema.org',
        '@type': 'ItemList',
        'name': 'Produtos Naturais com Evidência Científica',
        'numberOfItems': productSchemas.length,
        'itemListElement': productSchemas.map((item, idx) => ({
            '@type': 'ListItem',
            'position': idx + 1,
            'item': item,
        })),
    };
}

function jsonLd(obj) {
    return '<script type="application/ld+json">' + JSON.stringify(obj) + '</script>';
}

/* ================================================================
   RENDER: Category filter buttons
   ================================================================ */
let categoryButtonsHtml = '';
for (const [cat, count] of Object.entries(display_cats)) {
    categoryButtonsHtml += `                <button class="nrc-filter-btn"
                        data-categoria="${escAttr(sanitizeTitle(cat))}"
                        aria-pressed="false">
                    ${escHtml(cat)}
                    <span class="nrc-badge">${count}</span>
                </button>
`;
}

/* ================================================================
   RENDER: Product cards
   ================================================================ */
let productCardsHtml = '';
for (let i = 0; i < produtos.length; i++) {
    productCardsHtml += renderProductCard(produtos[i], i);
}

/* ================================================================
   RENDER: WhatsApp CTA in store banner
   ================================================================ */
const storeBannerWaMsg = encodeURIComponent('Olá! Vi o Guia de Produtos Naturais no site e gostaria de saber mais. Posso visitar a loja?');

/* ================================================================
   BUILD FULL HTML
   ================================================================ */
const fullHtml = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Base de Dados - Novas Raízes</title>
    <meta name="citation_title" content="Guia de Produtos Naturais e Suplementos - Novas Raízes">
    <meta name="citation_author" content="Novas Raízes">
    <meta name="citation_publication_date" content="${escAttr(updated)}">
    <meta name="dc.title" content="Guia de Produtos Naturais e Suplementos">
    <meta name="dc.creator" content="Novas Raízes">
    <meta name="dc.subject" content="Produtos Naturais; Suplementos; Medicina Tradicional Chinesa; Fitoterapia; Evidências Científicas">
    <meta name="dc.description" content="Base de dados com ${total} produtos naturais e suplementos com dosagem, contraindicações e referências científicas">
    <meta name="dc.language" content="pt-BR">
    <meta name="dc.type" content="Dataset">
    ${jsonLd(medicalPage)}
${jsonLd(dataset)}
${faqSchema ? jsonLd(faqSchema) : ''}
${jsonLd(localBusiness)}
${jsonLd(breadcrumb)}
${itemsListSchema ? jsonLd(itemsListSchema) : ''}
    <style>${cssText}</style>
</head>
<body style="margin:0; padding:0; background:#f8faf9;">
    <div id="nraizes-consulta" class="nrc-container" role="main"
         itemscope itemtype="https://schema.org/MedicalWebPage">

        <meta itemprop="specialty" content="Medicina Integrativa e Produtos Naturais">
        <meta itemprop="medicalAudience" content="Paciente">
        <meta itemprop="lastReviewed" content="${escAttr(updated)}">

        <header class="nrc-header">
            <h1 class="nrc-title" itemprop="name">
                Guia de Produtos Naturais e Suplementos
            </h1>
            <p class="nrc-subtitle" itemprop="description">
                Base de dados curada com ${total} produtos naturais, fórmulas da Medicina Tradicional Chinesa,
                suplementos, plantas medicinais e óleos essenciais. Cada produto apresenta um resumo baseado
                exclusivamente no que os estudos científicos referenciam e embasam, com citações de revistas
                indexadas (PubMed, Cochrane, etc.).
                <strong>Este conteúdo não substitui orientação de um profissional de saúde.</strong>
            </p>
            <div class="nrc-stats" role="status">
                <span class="nrc-stat">
                    <strong id="nrc-total-visible">${total}</strong> produtos catalogados
                </span>
                <span class="nrc-stat">
                    Atualizado em <time datetime="${escAttr(updated)}">${escHtml(formatDate(updated))}</time>
                </span>
            </div>
        </header>

        <nav class="nrc-controls" aria-label="Filtros de busca">
            <div class="nrc-search-wrap">
                <label for="nrc-search" class="screen-reader-text">Buscar produtos naturais</label>
                <svg class="nrc-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input type="search"
                       id="nrc-search"
                       class="nrc-search-input"
                       placeholder="Buscar por nome, ingrediente, estudo ou aplicação..."
                       autocomplete="off"
                       aria-describedby="nrc-search-help">
                <span id="nrc-search-help" class="screen-reader-text">
                    Digite para filtrar entre ${total} produtos naturais, suplementos e fórmulas
                </span>
                <button id="nrc-clear-search" class="nrc-clear-btn" style="display:none;" aria-label="Limpar busca">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                        <line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>

            <div class="nrc-filters" role="group" aria-label="Filtrar por categoria">
                <button class="nrc-filter-btn nrc-active" data-categoria="todos" aria-pressed="true">
                    Todos <span class="nrc-badge">${total}</span>
                </button>
${categoryButtonsHtml}            </div>

            <div class="nrc-evidence-filters" role="group" aria-label="Filtrar por nível de evidência">
                <span class="nrc-evidence-label">Nível de Evidência:</span>
                <button class="nrc-evidence-btn nrc-active" data-nivel="todos" aria-pressed="true">Todos</button>
                <button class="nrc-evidence-btn" data-nivel="alta" aria-pressed="false">
                    <span class="nrc-dot nrc-dot-alta" aria-hidden="true"></span> Alta
                </button>
                <button class="nrc-evidence-btn" data-nivel="moderada" aria-pressed="false">
                    <span class="nrc-dot nrc-dot-moderada" aria-hidden="true"></span> Moderada
                </button>
                <button class="nrc-evidence-btn" data-nivel="baixa" aria-pressed="false">
                    <span class="nrc-dot nrc-dot-baixa" aria-hidden="true"></span> Baixa
                </button>
            </div>
        </nav>

        <div id="nrc-no-results" class="nrc-no-results" style="display:none;" role="status">
            <p>Nenhum produto encontrado para esta busca.</p>
            <button class="nrc-reset-btn" id="nrc-reset-filters">Limpar filtros</button>
        </div>

        <div id="nrc-results" class="nrc-results" role="feed" aria-label="Resultados da consulta">
${productCardsHtml}        </div>

        <aside class="nrc-disclaimer" role="note" aria-label="Aviso legal obrigatório">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" aria-hidden="true">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <div>
                <strong>Aviso Legal Importante:</strong>
                <p>${escHtml(aviso)}</p>
                <p>Em conformidade com a legislação brasileira (ANVISA - RDC 243/2018 e IN 28/2018),
                informamos que: <strong>suplementos alimentares não são medicamentos</strong> e não se destinam
                a diagnosticar, tratar, curar ou prevenir qualquer doença. As informações sobre estudos
                científicos são apresentadas com finalidade exclusivamente educativa e informativa, e não
                constituem recomendação terapêutica. <strong>Consulte sempre um profissional de saúde
                habilitado</strong> antes de iniciar qualquer suplementação. A automedicação pode ser
                prejudicial à saúde.</p>
            </div>
        </aside>

        <div class="nrc-store-cta" itemscope itemtype="https://schema.org/LocalBusiness">
            <meta itemprop="name" content="Novas Ra\u00edzes & Mivegan">
            <meta itemprop="telephone" content="+5511999927588">
            <meta itemprop="url" content="https://nraizes.com.br">
            <meta itemprop="image" content="https://nraizes.com.br/wp-content/uploads/logo-novas-raizes.png">
            <meta itemprop="priceRange" content="$$">
            <div itemprop="address" itemscope itemtype="https://schema.org/PostalAddress">
                <meta itemprop="streetAddress" content="R. Dr. Nicolau de Sousa Queir\u00f3s, 34">
                <meta itemprop="addressLocality" content="S\u00e3o Paulo">
                <meta itemprop="addressRegion" content="SP">
                <meta itemprop="postalCode" content="04105-000">
                <meta itemprop="addressCountry" content="BR">
            </div>
            <div itemprop="geo" itemscope itemtype="https://schema.org/GeoCoordinates">
                <meta itemprop="latitude" content="-23.5714">
                <meta itemprop="longitude" content="-46.6350">
            </div>
            <meta itemprop="openingHours" content="Mo-Sa 09:00-18:30">
            <span class="nrc-store-cta-icon" aria-hidden="true">&#x1F3EA;</span>
            <div class="nrc-store-cta-body">
                <h3 class="nrc-store-cta-title">Visite nossa loja na Vila Mariana</h3>
                <p class="nrc-store-cta-address" itemprop="description">
                    R. Dr. Nicolau de Sousa Queir\u00f3s, 34 - Vila Mariana, S\u00e3o Paulo - SP
                </p>
                <p class="nrc-store-cta-hours">
                    ${storeHoursHtml}
                </p>
            </div>
            <div class="nrc-store-cta-actions">
                <a href="https://www.google.com/maps/search/R.+Dr.+Nicolau+de+Sousa+Queir%C3%B3s,+34+-+Vila+Mariana,+S%C3%A3o+Paulo+-+SP"
                   class="nrc-cta-btn nrc-cta-btn--map" target="_blank" rel="noopener noreferrer"
                   aria-label="Ver localiza\u00e7\u00e3o no Google Maps">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
                    Como chegar
                </a>
                <a href="https://wa.me/5511999927588?text=${storeBannerWaMsg}"
                   class="nrc-cta-btn nrc-cta-btn--whatsapp" target="_blank" rel="noopener noreferrer"
                   aria-label="Falar com a loja no WhatsApp">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2 22l4.832-1.438A9.955 9.955 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18c-1.66 0-3.203-.508-4.484-1.375l-.316-.191-2.828.84.84-2.828-.191-.316A7.953 7.953 0 014 12c0-4.411 3.589-8 8-8s8 3.589 8 8-3.589 8-8 8z"/></svg>
                    WhatsApp
                </a>
            </div>
        </div>

        <footer class="nrc-geo-footer" aria-label="Sobre esta base de dados">
            <div itemprop="about" itemscope itemtype="https://schema.org/MedicalCondition">
                <meta itemprop="name" content="Saúde Integrativa e Medicina Natural">
            </div>
            <p class="nrc-geo-text">
                Esta base de dados é mantida pela <strong>Novas Raízes</strong> (nraizes.com.br),
                loja especializada em produtos naturais, suplementos alimentares, fórmulas da
                Medicina Tradicional Chinesa (MTC), plantas medicinais e óleos essenciais.
                As informações são compiladas a partir de estudos científicos publicados em
                revistas indexadas como PubMed, Cochrane Library e bases de dados de fitoterapia
                baseada em evidências. Cada produto apresenta exclusivamente o que os estudos
                referenciam e embasam, com dosagem recomendada, contraindicações,
                interações medicamentosas e referências científicas verificáveis.
            </p>
            <p class="nrc-geo-text">
                Categorias disponíveis: Fórmulas da Medicina Tradicional Chinesa (Liu Wei Dihuang Wan,
                Xiao Yao Wan, Gui Pi Wan, Ba Zhen Wan, Guizhi Fuling Wan), Suplementos (Vitamina D3,
                Vitamina C, Vitamina B12, Omega-3, CoQ10, Ashwagandha, Melatonina, Magnésio, Zinco,
                Colágeno, Probióticos, Cúrcuma, Spirulina, Clorella, Própolis, Creatina, Biotina,
                Cálcio + K2, Triptofano/5-HTP, Selênio, NAC, Ferro Quelado, Glutamina),
                Plantas Medicinais (Camomila, Gengibre, Valeriana, Passiflora, Melissa, Boldo,
                Cavalinha, Espinheira-santa, Hibisco, Hortelã-pimenta, Guaco, Unha-de-gato,
                Ginseng, Ginkgo, Equinácea, Rhodiola, Saw Palmetto, Cardo-mariano) e
                Óleos Essenciais (Lavanda, Melaleuca, Eucalipto, Alecrim, Hortelã-pimenta,
                Limão, Laranja-doce, Ylang Ylang, Copaíba, Incenso/Olibano).
                Loja física na Vila Mariana, São Paulo - SP. Seg-Sáb 09:00 às 18:30.
            </p>
            <div itemscope itemtype="https://schema.org/Organization" itemprop="publisher">
                <meta itemprop="name" content="Novas Raízes & Mivegan">
                <meta itemprop="url" content="https://nraizes.com.br">
                <meta itemprop="telephone" content="+5511999927588">
                <meta itemprop="description" content="Loja de produtos naturais, suplementos, Medicina Tradicional Chinesa e óleos essenciais na Vila Mariana, São Paulo - SP. Seg-Sáb 09:00-18:30.">
                <div itemprop="address" itemscope itemtype="https://schema.org/PostalAddress">
                    <meta itemprop="streetAddress" content="R. Dr. Nicolau de Sousa Queirós, 34">
                    <meta itemprop="addressLocality" content="São Paulo">
                    <meta itemprop="addressRegion" content="SP">
                    <meta itemprop="postalCode" content="04105-000">
                    <meta itemprop="addressCountry" content="BR">
                    <meta itemprop="neighborhood" content="Vila Mariana">
                </div>
            </div>
        </footer>

    </div><!-- .nrc-container -->
    <script>${jsText}</script>
</body>
</html>
`;

/* ================================================================
   WRITE OUTPUT
   ================================================================ */
fs.writeFileSync(OUTPUT, fullHtml, 'utf8');
console.log('base-de-dados.html gerado com sucesso!');
console.log('  Produtos: ' + total);
console.log('  Caminho:  ' + OUTPUT);
