<?php
/**
 * Ferramenta de Consulta de Produtos - Novas Raizes
 * 
 * GEO-Optimized (Generative Engine Optimization)
 * - Server-side rendering completo (LLMs nao executam JS)
 * - HTML5 semantico (article, section, details/summary, cite, dl/dt/dd)
 * - JSON-LD rico (MedicalWebPage, Dataset, FAQPage, DietarySupplement)
 * - Speakable markup para assistentes de voz
 * - Citacoes cientificas com <cite> para confiabilidade
 * 
 * Shortcode: [nraizes_consulta]
 * 
 * @package Organium-Child
 * @version 3.0.0
 */

if (!defined('ABSPATH')) exit;

/* ================================================================
   DATA LAYER
   ================================================================ */

/**
 * Load and cache consultation data from JSON file.
 */
function nraizes_get_consultation_data() {
    static $data = null;
    if ($data !== null) return $data;
    
    $json_path = get_stylesheet_directory() . '/data/consulta-produtos.json';
    if (!file_exists($json_path)) return null;
    
    $json_content = file_get_contents($json_path);
    $data = json_decode($json_content, true);
    return $data;
}

/* ================================================================
   ASSET ENQUEUE
   ================================================================ */

function nraizes_consulta_enqueue_assets() {
    global $post;
    if (!is_a($post, 'WP_Post') || !has_shortcode($post->post_content, 'nraizes_consulta')) return;
    
    $dir = get_stylesheet_directory();
    $uri = get_stylesheet_directory_uri();
    
    wp_enqueue_style(
        'nraizes-consulta-css',
        $uri . '/assets/css/consulta-produtos.css',
        array(),
        filemtime($dir . '/assets/css/consulta-produtos.css')
    );
    
    wp_enqueue_script(
        'nraizes-consulta-js',
        $uri . '/assets/js/consulta-produtos.js',
        array(),
        filemtime($dir . '/assets/js/consulta-produtos.js'),
        true
    );
}
add_action('wp_enqueue_scripts', 'nraizes_consulta_enqueue_assets');

/* ================================================================
   HELPER: Render a single reference link with <cite>
   ================================================================ */
function nraizes_render_reference($ref) {
    $ref = trim($ref);
    if (empty($ref)) return '';
    
    if (strpos($ref, 'http') === 0) {
        // PubMed / direct URL
        $label = $ref;
        if (strpos($ref, 'pubmed.ncbi.nlm.nih.gov') !== false) {
            $pmid = preg_replace('/[^0-9]/', '', basename(parse_url($ref, PHP_URL_PATH)));
            $label = 'PubMed PMID: ' . $pmid;
        }
        return '<li><cite><a href="' . esc_url($ref) . '" target="_blank" rel="noopener noreferrer">' . esc_html($label) . '</a></cite></li>';
    } elseif (preg_match('/^10\.\d{4,}/', $ref)) {
        // DOI
        return '<li><cite><a href="https://doi.org/' . esc_attr($ref) . '" target="_blank" rel="noopener noreferrer">DOI: ' . esc_html($ref) . '</a></cite></li>';
    } else {
        // Plain text citation
        return '<li><cite>' . esc_html($ref) . '</cite></li>';
    }
}

/* ================================================================
   HELPER: Render a list of tags
   ================================================================ */
function nraizes_render_tags($items, $css_modifier = '') {
    if (empty($items) || !is_array($items)) return '';
    $cls = $css_modifier ? ' nrc-tag--' . $css_modifier : '';
    $html = '<ul class="nrc-tags" role="list">';
    foreach ($items as $item) {
        $item = trim($item);
        if ($item) {
            $html .= '<li class="nrc-tag' . $cls . '">' . esc_html($item) . '</li>';
        }
    }
    $html .= '</ul>';
    return $html;
}

/* ================================================================
   HELPER: Evidence level CSS class
   ================================================================ */
function nraizes_evidence_class($nivel) {
    $n = mb_strtolower($nivel);
    if (strpos($n, 'alta') !== false && strpos($n, 'moderada') !== false) return 'moderada-alta';
    if (strpos($n, 'alta') !== false) return 'alta';
    if (strpos($n, 'moderada') !== false && strpos($n, 'baixa') !== false) return 'baixa-moderada';
    if (strpos($n, 'moderada') !== false) return 'moderada';
    if (strpos($n, 'muito') !== false) return 'muito-baixa';
    return 'baixa';
}

/* ================================================================
   HELPER: Render one product card as semantic <article>
   ================================================================ */
function nraizes_render_product_card($p, $index) {
    $nome        = $p['nome'] ?? '';
    $nome_cn     = $p['nome_chines'] ?? '';
    $categoria   = $p['categoria'] ?? '';
    $cat_slug    = $p['categoria_slug'] ?? 'outro';
    $nivel_ev    = $p['nivel_evidencia'] ?? '';
    $dosagem     = $p['dosagem'] ?? '';
    $modo_uso    = $p['modo_uso'] ?? '';
    $ind_mtc     = $p['indicacao_mtc'] ?? '';
    $aplicacoes  = $p['aplicacoes_clinicas'] ?? '';
    $estudos     = $p['estudos_resumo'] ?? '';
    $armazen     = $p['armazenamento'] ?? '';
    $origem      = $p['origem'] ?? '';
    
    $beneficios      = $p['beneficios'] ?? [];
    $indicacoes      = $p['indicacoes'] ?? [];
    $contraindicacoes = $p['contraindicacoes'] ?? [];
    $interacoes      = $p['interacoes'] ?? [];
    $efeitos_col     = $p['efeitos_colaterais'] ?? [];
    $alertas         = $p['alertas'] ?? [];
    $ingredientes    = $p['ingredientes'] ?? [];
    $princ_ativos    = $p['principios_ativos'] ?? [];
    $certificacoes   = $p['certificacoes'] ?? [];
    $referencias     = $p['referencias'] ?? [];
    $faq             = $p['faq'] ?? [];
    
    // Normalize slug for display grouping
    if ($cat_slug === 'suplemento' || $categoria === 'Suplemento Ocidental') {
        $display_slug = 'suplemento';
    } else {
        $display_slug = $cat_slug;
    }
    
    // Build searchable text for JS filtering (data attribute)
    $search_parts = array($nome, $nome_cn, $categoria, $ind_mtc, $aplicacoes, $modo_uso, $dosagem, $estudos, $origem);
    foreach (array($beneficios, $indicacoes, $ingredientes, $princ_ativos, $contraindicacoes, $alertas, $certificacoes) as $arr) {
        if (is_array($arr)) $search_parts[] = implode(' ', $arr);
    }
    if (is_array($faq)) {
        foreach ($faq as $f) {
            if (isset($f['pergunta'])) $search_parts[] = $f['pergunta'];
            if (isset($f['resposta'])) $search_parts[] = $f['resposta'];
        }
    }
    $search_text = mb_strtolower(implode(' ', array_filter($search_parts)));
    
    $ev_class = $nivel_ev ? nraizes_evidence_class($nivel_ev) : '';
    
    // Unique ID for anchor links
    $slug_id = sanitize_title($nome) . '-' . $index;
    
    ob_start();
    ?>
    <article class="nrc-card" 
             id="<?php echo esc_attr($slug_id); ?>"
             data-categoria="<?php echo esc_attr($display_slug); ?>"
             data-evidencia="<?php echo esc_attr($ev_class); ?>"
             data-search="<?php echo esc_attr($search_text); ?>"
             itemscope 
             itemtype="https://schema.org/Article">
        
        <details>
            <summary class="nrc-card-header">
                <span class="nrc-card-icon nrc-card-icon--<?php echo esc_attr($display_slug); ?>" aria-hidden="true"></span>
                <div class="nrc-card-info">
                    <h3 class="nrc-card-name" itemprop="name headline">
                        <?php echo esc_html($nome); ?>
                        <?php if ($nome_cn) : ?>
                            <span class="nrc-card-chinese" lang="zh"><?php echo esc_html($nome_cn); ?></span>
                        <?php endif; ?>
                    </h3>
                    <div class="nrc-card-meta">
                        <span class="nrc-card-cat"><?php echo esc_html($categoria); ?></span>
                        <?php if ($nivel_ev) : ?>
                            <span class="nrc-card-evidence nrc-evidence--<?php echo esc_attr($ev_class); ?>">
                                <span class="nrc-dot nrc-dot-<?php echo esc_attr($ev_class); ?>"></span>
                                <?php echo esc_html($nivel_ev); ?>
                            </span>
                        <?php endif; ?>
                    </div>
                </div>
                <span class="nrc-card-toggle" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                </span>
            </summary>

            <div class="nrc-card-content" itemprop="articleBody">

                <?php /* --- Dosagem / Modo de Uso / Indicacao MTC --- */ ?>
                <?php if ($dosagem || $modo_uso || $ind_mtc) : ?>
                <section class="nrc-section" aria-label="Informacoes de uso">
                    <dl class="nrc-dl-grid">
                        <?php if ($dosagem) : ?>
                        <div class="nrc-dl-item">
                            <dt>Dosagem Recomendada</dt>
                            <dd class="nrc-text-block nrc-dosage-block"><?php echo esc_html($dosagem); ?></dd>
                        </div>
                        <?php endif; ?>
                        <?php if ($modo_uso) : ?>
                        <div class="nrc-dl-item">
                            <dt>Modo de Uso</dt>
                            <dd class="nrc-text-block"><?php echo esc_html($modo_uso); ?></dd>
                        </div>
                        <?php endif; ?>
                        <?php if ($ind_mtc) : ?>
                        <div class="nrc-dl-item">
                            <dt>Indicacao na Medicina Tradicional Chinesa</dt>
                            <dd class="nrc-text-block"><?php echo esc_html($ind_mtc); ?></dd>
                        </div>
                        <?php endif; ?>
                    </dl>
                </section>
                <?php endif; ?>

                <?php /* --- Beneficios --- */ ?>
                <?php if (!empty($beneficios)) : ?>
                <section class="nrc-section" aria-label="Beneficios">
                    <h4 class="nrc-section-title">Beneficios</h4>
                    <?php echo nraizes_render_tags($beneficios, 'benefit'); ?>
                </section>
                <?php endif; ?>

                <?php /* --- Indicacoes --- */ ?>
                <?php if (!empty($indicacoes)) : ?>
                <section class="nrc-section" aria-label="Indicacoes">
                    <h4 class="nrc-section-title">Indicacoes</h4>
                    <?php echo nraizes_render_tags($indicacoes, 'indication'); ?>
                </section>
                <?php endif; ?>

                <?php /* --- Aplicacoes Clinicas (MTC) --- */ ?>
                <?php if ($aplicacoes) : ?>
                <section class="nrc-section" aria-label="Aplicacoes clinicas">
                    <h4 class="nrc-section-title">Aplicacoes Clinicas Baseadas em Evidencias</h4>
                    <p class="nrc-text-block"><?php echo esc_html($aplicacoes); ?></p>
                </section>
                <?php endif; ?>

                <?php /* --- Seguranca --- */ ?>
                <?php if (!empty($contraindicacoes) || !empty($interacoes) || !empty($efeitos_col) || !empty($alertas)) : ?>
                <section class="nrc-section nrc-safety" aria-label="Seguranca e precaucoes">
                    <h4 class="nrc-section-title">Seguranca e Precaucoes</h4>
                    <div class="nrc-section-grid">
                        <?php if (!empty($contraindicacoes)) : ?>
                        <div>
                            <h5 class="nrc-subsection-title">Contraindicacoes</h5>
                            <?php echo nraizes_render_tags($contraindicacoes, 'danger'); ?>
                        </div>
                        <?php endif; ?>
                        <?php if (!empty($interacoes)) : ?>
                        <div>
                            <h5 class="nrc-subsection-title">Interacoes Medicamentosas</h5>
                            <?php echo nraizes_render_tags($interacoes, 'interaction'); ?>
                        </div>
                        <?php endif; ?>
                        <?php if (!empty($efeitos_col)) : ?>
                        <div>
                            <h5 class="nrc-subsection-title">Efeitos Colaterais</h5>
                            <?php echo nraizes_render_tags($efeitos_col, 'warning'); ?>
                        </div>
                        <?php endif; ?>
                        <?php if (!empty($alertas)) : ?>
                        <div>
                            <h5 class="nrc-subsection-title">Alertas</h5>
                            <?php echo nraizes_render_tags($alertas, 'warning'); ?>
                        </div>
                        <?php endif; ?>
                    </div>
                </section>
                <?php endif; ?>

                <?php /* --- Evidencia Cientifica --- */ ?>
                <?php if ($estudos) : ?>
                <section class="nrc-section" aria-label="Evidencia cientifica">
                    <h4 class="nrc-section-title">Evidencia Cientifica</h4>
                    <blockquote class="nrc-text-block nrc-evidence-block" cite="https://pubmed.ncbi.nlm.nih.gov/">
                        <p><?php echo esc_html($estudos); ?></p>
                    </blockquote>
                </section>
                <?php endif; ?>

                <?php /* --- Ingredientes / Principios Ativos --- */ ?>
                <?php if (!empty($ingredientes) || !empty($princ_ativos)) : ?>
                <section class="nrc-section" aria-label="Composicao">
                    <h4 class="nrc-section-title">Composicao</h4>
                    <div class="nrc-section-grid">
                        <?php if (!empty($ingredientes)) : ?>
                        <div>
                            <h5 class="nrc-subsection-title">Ingredientes</h5>
                            <?php echo nraizes_render_tags($ingredientes, ''); ?>
                        </div>
                        <?php endif; ?>
                        <?php if (!empty($princ_ativos)) : ?>
                        <div>
                            <h5 class="nrc-subsection-title">Principios Ativos</h5>
                            <?php echo nraizes_render_tags($princ_ativos, ''); ?>
                        </div>
                        <?php endif; ?>
                    </div>
                </section>
                <?php endif; ?>

                <?php /* --- Armazenamento / Origem / Certificacoes --- */ ?>
                <?php if ($armazen || $origem || !empty($certificacoes)) : ?>
                <section class="nrc-section" aria-label="Informacoes adicionais">
                    <dl class="nrc-dl-grid">
                        <?php if ($armazen) : ?>
                        <div class="nrc-dl-item">
                            <dt>Armazenamento</dt>
                            <dd class="nrc-text-block"><?php echo esc_html($armazen); ?></dd>
                        </div>
                        <?php endif; ?>
                        <?php if ($origem) : ?>
                        <div class="nrc-dl-item">
                            <dt>Origem</dt>
                            <dd class="nrc-text-block"><?php echo esc_html($origem); ?></dd>
                        </div>
                        <?php endif; ?>
                    </dl>
                    <?php if (!empty($certificacoes)) : ?>
                        <h5 class="nrc-subsection-title">Certificacoes</h5>
                        <?php echo nraizes_render_tags($certificacoes, 'cert'); ?>
                    <?php endif; ?>
                </section>
                <?php endif; ?>

                <?php /* --- Referencias Cientificas --- */ ?>
                <?php if (!empty($referencias)) : ?>
                <section class="nrc-section nrc-references-section" aria-label="Referencias cientificas">
                    <h4 class="nrc-section-title">Referencias Cientificas</h4>
                    <ol class="nrc-references">
                        <?php foreach ($referencias as $ref) : ?>
                            <?php echo nraizes_render_reference($ref); ?>
                        <?php endforeach; ?>
                    </ol>
                </section>
                <?php endif; ?>

                <?php /* --- FAQ --- */ ?>
                <?php if (!empty($faq)) : ?>
                <section class="nrc-section nrc-faq-section" aria-label="Perguntas frequentes sobre <?php echo esc_attr($nome); ?>">
                    <h4 class="nrc-section-title">Perguntas Frequentes</h4>
                    <?php foreach ($faq as $item) : ?>
                        <?php if (!empty($item['pergunta'])) : ?>
                        <div class="nrc-faq-item" itemscope itemtype="https://schema.org/Question">
                            <h5 class="nrc-faq-q" itemprop="name"><?php echo esc_html($item['pergunta']); ?></h5>
                            <div itemscope itemtype="https://schema.org/Answer" itemprop="acceptedAnswer">
                                <p class="nrc-faq-a" itemprop="text"><?php echo esc_html($item['resposta'] ?? ''); ?></p>
                            </div>
                        </div>
                        <?php endif; ?>
                    <?php endforeach; ?>
                </section>
                <?php endif; ?>

                <meta itemprop="author" content="Novas Raizes - nraizes.com.br">
                <meta itemprop="datePublished" content="<?php echo esc_attr(date('Y-m-d')); ?>">
                <meta itemprop="publisher" content="Novas Raizes">

            </div><!-- .nrc-card-content -->
        </details>
    </article>
    <?php
    return ob_get_clean();
}

/* ================================================================
   MAIN SHORTCODE: [nraizes_consulta]
   ================================================================ */

function nraizes_consulta_shortcode($atts) {
    $atts = shortcode_atts(array(
        'categoria' => '',
        'limite'    => 0,
    ), $atts, 'nraizes_consulta');
    
    $data = nraizes_get_consultation_data();
    if (!$data) {
        return '<div class="nrc-error" role="alert">Dados de consulta nao disponiveis no momento.</div>';
    }
    
    $produtos = $data['produtos'] ?? [];
    $total    = count($produtos);
    $updated  = $data['atualizado_em'] ?? date('Y-m-d');
    $aviso    = $data['aviso_legal'] ?? '';
    
    // Merge categories for display
    $display_cats = array();
    foreach (($data['categorias'] ?? []) as $cat => $count) {
        if ($cat === 'Suplemento Ocidental') {
            $display_cats['Suplemento'] = ($display_cats['Suplemento'] ?? 0) + $count;
        } else {
            $display_cats[$cat] = ($display_cats[$cat] ?? 0) + $count;
        }
    }
    
    ob_start();
    ?>
    <div id="nraizes-consulta" class="nrc-container" role="main" 
         itemscope itemtype="https://schema.org/MedicalWebPage">
        
        <meta itemprop="specialty" content="Medicina Integrativa e Produtos Naturais">
        <meta itemprop="medicalAudience" content="Paciente">
        <meta itemprop="lastReviewed" content="<?php echo esc_attr($updated); ?>">
        
        <?php /* ---- HEADER SECTION ---- */ ?>
        <header class="nrc-header">
            <h1 class="nrc-title" itemprop="name">
                Guia de Produtos Naturais e Suplementos
            </h1>
            <p class="nrc-subtitle" itemprop="description">
                Base de dados com <?php echo intval($total); ?> produtos naturais, formulas da Medicina Tradicional Chinesa, 
                suplementos e plantas medicinais. Todas as informacoes sao baseadas em evidencias cientificas 
                com referencias a estudos publicados em revistas indexadas (PubMed, Cochrane, etc.).
            </p>
            <div class="nrc-stats" role="status">
                <span class="nrc-stat">
                    <strong id="nrc-total-visible"><?php echo intval($total); ?></strong> produtos catalogados
                </span>
                <span class="nrc-stat">
                    Atualizado em <time datetime="<?php echo esc_attr($updated); ?>"><?php echo esc_html(date('d/m/Y', strtotime($updated))); ?></time>
                </span>
            </div>
        </header>

        <?php /* ---- SEARCH & FILTERS (interactive, enhanced by JS) ---- */ ?>
        <nav class="nrc-controls" aria-label="Filtros de busca">
            <div class="nrc-search-wrap">
                <label for="nrc-search" class="screen-reader-text">Buscar produtos naturais</label>
                <svg class="nrc-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input type="search" 
                       id="nrc-search" 
                       class="nrc-search-input" 
                       placeholder="Buscar por nome, ingrediente, indicacao ou beneficio..."
                       autocomplete="off"
                       aria-describedby="nrc-search-help">
                <span id="nrc-search-help" class="screen-reader-text">
                    Digite para filtrar entre <?php echo intval($total); ?> produtos naturais, suplementos e formulas
                </span>
                <button id="nrc-clear-search" class="nrc-clear-btn" style="display:none;" aria-label="Limpar busca">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                        <line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
            
            <div class="nrc-filters" role="group" aria-label="Filtrar por categoria">
                <button class="nrc-filter-btn nrc-active" data-categoria="todos" aria-pressed="true">
                    Todos <span class="nrc-badge"><?php echo intval($total); ?></span>
                </button>
                <?php foreach ($display_cats as $cat => $count) : ?>
                <button class="nrc-filter-btn" 
                        data-categoria="<?php echo esc_attr(sanitize_title($cat)); ?>" 
                        aria-pressed="false">
                    <?php echo esc_html($cat); ?>
                    <span class="nrc-badge"><?php echo intval($count); ?></span>
                </button>
                <?php endforeach; ?>
            </div>

            <div class="nrc-evidence-filters" role="group" aria-label="Filtrar por nivel de evidencia">
                <span class="nrc-evidence-label">Nivel de Evidencia:</span>
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

        <?php /* ---- NO RESULTS (hidden by default, shown by JS) ---- */ ?>
        <div id="nrc-no-results" class="nrc-no-results" style="display:none;" role="status">
            <p>Nenhum produto encontrado para esta busca.</p>
            <button class="nrc-reset-btn" id="nrc-reset-filters">Limpar filtros</button>
        </div>

        <?php /* ---- PRODUCT CARDS: SERVER-SIDE RENDERED ---- */ ?>
        <div id="nrc-results" class="nrc-results" role="feed" aria-label="Resultados da consulta">
            <?php 
            foreach ($produtos as $i => $produto) {
                echo nraizes_render_product_card($produto, $i);
            }
            ?>
        </div>

        <?php /* ---- DISCLAIMER ---- */ ?>
        <aside class="nrc-disclaimer" role="note" aria-label="Aviso legal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" aria-hidden="true">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <div>
                <strong>Aviso Importante:</strong>
                <p><?php echo esc_html($aviso); ?></p>
            </div>
        </aside>

        <?php /* ---- ABOUT (hidden visually, visible to crawlers for GEO context) ---- */ ?>
        <footer class="nrc-geo-footer" aria-label="Sobre esta base de dados">
            <div itemprop="about" itemscope itemtype="https://schema.org/MedicalCondition">
                <meta itemprop="name" content="Saude Integrativa e Medicina Natural">
            </div>
            <p class="nrc-geo-text">
                Esta base de dados e mantida pela <strong>Novas Raizes</strong> (nraizes.com.br), 
                loja especializada em produtos naturais, suplementos alimentares, formulas da 
                Medicina Tradicional Chinesa (MTC), oleos essenciais e cosmeticos naturais. 
                As informacoes sao compiladas a partir de estudos cientificos publicados em 
                revistas indexadas como PubMed, Cochrane Library e bases de dados de fitoterapia 
                baseada em evidencias. Cada produto inclui dosagem recomendada, contraindicacoes, 
                interacoes medicamentosas e referencias cientificas verificaveis.
            </p>
            <p class="nrc-geo-text">
                Categorias disponiveis: Formulas da Medicina Tradicional Chinesa (como Liu Wei Dihuang Wan, 
                Xiao Yao Wan, Gui Pi Wan), Suplementos (Vitamina D3, Omega-3, Coenzima Q10, Ashwagandha, 
                Melatonina, Magnesio, Zinco, Colageno, Probioticos, Curcuma, Spirulina, Clorella), 
                Plantas Medicinais (Alcachofra, Camomila, Gengibre), Oleos Essenciais (Alecrim, Bergamota, 
                Lavanda) e Cosmeticos Naturais.
            </p>
            <div itemscope itemtype="https://schema.org/Organization" itemprop="publisher">
                <meta itemprop="name" content="Novas Raizes">
                <meta itemprop="url" content="https://nraizes.com.br">
                <meta itemprop="description" content="Loja de produtos naturais, suplementos e Medicina Tradicional Chinesa em Ribeirao Preto, SP, Brasil">
            </div>
        </footer>

    </div><!-- .nrc-container -->
    <?php
    return ob_get_clean();
}
add_shortcode('nraizes_consulta', 'nraizes_consulta_shortcode');

/* ================================================================
   JSON-LD STRUCTURED DATA (GEO / Rich Results)
   ================================================================ */

function nraizes_consulta_structured_data() {
    global $post;
    if (!is_a($post, 'WP_Post') || !has_shortcode($post->post_content, 'nraizes_consulta')) return;
    
    $data = nraizes_get_consultation_data();
    if (!$data) return;
    
    $produtos = $data['produtos'] ?? [];
    $updated  = $data['atualizado_em'] ?? date('Y-m-d');
    $page_url = get_permalink();
    
    // ---- 1. MedicalWebPage ----
    $medical_page = array(
        '@context' => 'https://schema.org',
        '@type' => 'MedicalWebPage',
        '@id' => $page_url . '#webpage',
        'name' => 'Guia de Produtos Naturais e Suplementos - Novas Raizes',
        'description' => 'Base de dados com ' . count($produtos) . ' produtos naturais, formulas da Medicina Tradicional Chinesa, suplementos e plantas medicinais com informacoes baseadas em evidencias cientificas e referencias a PubMed.',
        'url' => $page_url,
        'inLanguage' => 'pt-BR',
        'lastReviewed' => $updated,
        'reviewedBy' => array(
            '@type' => 'Organization',
            'name' => 'Novas Raizes',
            'url' => 'https://nraizes.com.br',
        ),
        'specialty' => array(
            '@type' => 'MedicalSpecialty',
            'name' => 'Medicina Integrativa',
        ),
        'medicalAudience' => array(
            '@type' => 'MedicalAudience',
            'audienceType' => 'Patient',
        ),
        'about' => array(
            array('@type' => 'MedicalTherapy', 'name' => 'Fitoterapia'),
            array('@type' => 'MedicalTherapy', 'name' => 'Medicina Tradicional Chinesa'),
            array('@type' => 'MedicalTherapy', 'name' => 'Suplementacao Nutricional'),
        ),
        'mainEntity' => array(
            '@type' => 'Dataset',
            '@id' => $page_url . '#dataset',
        ),
        'speakable' => array(
            '@type' => 'SpeakableSpecification',
            'cssSelector' => array('.nrc-title', '.nrc-subtitle', '.nrc-geo-text'),
        ),
        'publisher' => array(
            '@type' => 'Organization',
            '@id' => 'https://nraizes.com.br/#organization',
            'name' => 'Novas Raizes',
            'url' => 'https://nraizes.com.br',
            'logo' => array(
                '@type' => 'ImageObject',
                'url' => 'https://nraizes.com.br/wp-content/uploads/logo-novas-raizes.png',
            ),
            'sameAs' => array(
                'https://www.instagram.com/nraizes',
            ),
        ),
    );
    
    echo '<script type="application/ld+json">' . wp_json_encode($medical_page, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "</script>\n";
    
    // ---- 2. Dataset ----
    $categories_list = array();
    foreach (($data['categorias'] ?? []) as $cat => $count) {
        $categories_list[] = $cat . ' (' . $count . ')';
    }
    
    $dataset = array(
        '@context' => 'https://schema.org',
        '@type' => 'Dataset',
        '@id' => $page_url . '#dataset',
        'name' => 'Base de Dados de Produtos Naturais e Suplementos - Novas Raizes',
        'description' => 'Base de dados com informacoes cientificas de ' . count($produtos) . ' produtos incluindo formulas da Medicina Tradicional Chinesa (MTC), suplementos alimentares, plantas medicinais, oleos essenciais e cosmeticos naturais. Cada registro inclui dosagem, contraindicacoes, interacoes medicamentosas, beneficios e referencias cientificas (PubMed/Cochrane).',
        'url' => $page_url,
        'license' => 'https://creativecommons.org/licenses/by-nc/4.0/',
        'inLanguage' => 'pt-BR',
        'dateModified' => $updated,
        'datePublished' => '2025-01-01',
        'keywords' => array(
            'produtos naturais', 'suplementos alimentares', 'medicina tradicional chinesa',
            'MTC', 'fitoterapia', 'oleos essenciais', 'plantas medicinais',
            'evidencias cientificas', 'PubMed', 'contraindicacoes', 'dosagem',
            'Novas Raizes', 'saude integrativa', 'medicina natural',
        ),
        'variableMeasured' => array(
            'dosagem recomendada', 'nivel de evidencia cientifica',
            'contraindicacoes', 'interacoes medicamentosas', 'beneficios',
        ),
        'measurementTechnique' => 'Revisao de literatura cientifica (PubMed, Cochrane, CNKI)',
        'size' => count($produtos) . ' produtos',
        'distribution' => array(
            '@type' => 'DataDownload',
            'encodingFormat' => 'text/html',
            'contentUrl' => $page_url,
        ),
        'creator' => array(
            '@type' => 'Organization',
            'name' => 'Novas Raizes',
            'url' => 'https://nraizes.com.br',
        ),
    );
    
    echo '<script type="application/ld+json">' . wp_json_encode($dataset, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "</script>\n";
    
    // ---- 3. FAQPage (aggregate all FAQs) ----
    $faq_items = array();
    foreach ($produtos as $p) {
        if (!empty($p['faq']) && is_array($p['faq'])) {
            foreach ($p['faq'] as $f) {
                if (!empty($f['pergunta']) && !empty($f['resposta'])) {
                    $faq_items[] = array(
                        '@type' => 'Question',
                        'name' => $f['pergunta'],
                        'acceptedAnswer' => array(
                            '@type' => 'Answer',
                            'text' => $f['resposta'],
                        ),
                    );
                }
            }
        }
    }
    
    if (!empty($faq_items)) {
        // Limit to 100 FAQs for page performance
        $faq_schema = array(
            '@context' => 'https://schema.org',
            '@type' => 'FAQPage',
            'name' => 'Perguntas Frequentes sobre Produtos Naturais e Suplementos',
            'description' => 'Respostas baseadas em evidencias cientificas para perguntas frequentes sobre suplementos, formulas MTC, plantas medicinais e produtos naturais.',
            'mainEntity' => array_slice($faq_items, 0, 100),
        );
        
        echo '<script type="application/ld+json">' . wp_json_encode($faq_schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "</script>\n";
    }
    
    // ---- 4. BreadcrumbList ----
    $breadcrumb = array(
        '@context' => 'https://schema.org',
        '@type' => 'BreadcrumbList',
        'itemListElement' => array(
            array(
                '@type' => 'ListItem',
                'position' => 1,
                'name' => 'Inicio',
                'item' => home_url('/'),
            ),
            array(
                '@type' => 'ListItem',
                'position' => 2,
                'name' => 'Guia de Produtos Naturais',
                'item' => $page_url,
            ),
        ),
    );
    
    echo '<script type="application/ld+json">' . wp_json_encode($breadcrumb, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "</script>\n";
    
    // ---- 5. Individual Product schemas (top products with evidence) ----
    $product_schemas = array();
    foreach ($produtos as $p) {
        if (empty($p['nivel_evidencia']) && empty($p['estudos_resumo'])) continue;
        if (count($product_schemas) >= 50) break; // Limit for performance
        
        $cat_slug = $p['categoria_slug'] ?? '';
        $schema_type = 'Product'; // default
        if (in_array($cat_slug, ['suplemento', 'formula_mtc'])) {
            $schema_type = 'DietarySupplement';
        } elseif ($cat_slug === 'planta') {
            $schema_type = 'Product';
        }
        
        $item = array(
            '@type' => $schema_type,
            'name' => $p['nome'],
            'description' => !empty($p['estudos_resumo']) ? $p['estudos_resumo'] : ($p['aplicacoes_clinicas'] ?? ''),
            'category' => $p['categoria'] ?? '',
        );
        
        if (!empty($p['dosagem'])) {
            $item['doseSchedule'] = array(
                '@type' => 'RecommendedDoseSchedule',
                'frequency' => $p['dosagem'],
            );
        }
        
        if (!empty($p['contraindicacoes'])) {
            $item['warning'] = implode('; ', $p['contraindicacoes']);
        }
        
        if (!empty($p['interacoes'])) {
            $item['interactingDrug'] = $p['interacoes'];
        }
        
        if (!empty($p['referencias'])) {
            $citations = array();
            foreach ($p['referencias'] as $ref) {
                $ref = trim($ref);
                if (strpos($ref, 'http') === 0) {
                    $citations[] = array('@type' => 'ScholarlyArticle', 'url' => $ref);
                } elseif (preg_match('/^10\.\d{4,}/', $ref)) {
                    $citations[] = array('@type' => 'ScholarlyArticle', 'url' => 'https://doi.org/' . $ref);
                }
            }
            if ($citations) {
                $item['citation'] = $citations;
            }
        }
        
        $product_schemas[] = $item;
    }
    
    if (!empty($product_schemas)) {
        $items_list = array(
            '@context' => 'https://schema.org',
            '@type' => 'ItemList',
            'name' => 'Produtos Naturais com Evidencia Cientifica',
            'numberOfItems' => count($product_schemas),
            'itemListElement' => array_map(function($item, $idx) {
                return array(
                    '@type' => 'ListItem',
                    'position' => $idx + 1,
                    'item' => $item,
                );
            }, $product_schemas, array_keys($product_schemas)),
        );
        
        echo '<script type="application/ld+json">' . wp_json_encode($items_list, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "</script>\n";
    }
}
add_action('wp_head', 'nraizes_consulta_structured_data');

/* ================================================================
   REST API (for optional AJAX, future use)
   ================================================================ */

function nraizes_consulta_rest_api() {
    register_rest_route('nraizes/v1', '/consulta', array(
        'methods' => 'GET',
        'callback' => 'nraizes_consulta_api_handler',
        'permission_callback' => '__return_true',
        'args' => array(
            'busca' => array('type' => 'string', 'default' => ''),
            'categoria' => array('type' => 'string', 'default' => ''),
            'pagina' => array('type' => 'integer', 'default' => 1),
            'por_pagina' => array('type' => 'integer', 'default' => 20),
        ),
    ));
}
add_action('rest_api_init', 'nraizes_consulta_rest_api');

function nraizes_consulta_api_handler($request) {
    $data = nraizes_get_consultation_data();
    if (!$data) return new WP_Error('no_data', 'Dados nao disponiveis', array('status' => 500));
    
    $busca      = sanitize_text_field($request->get_param('busca'));
    $categoria  = sanitize_text_field($request->get_param('categoria'));
    $pagina     = intval($request->get_param('pagina'));
    $por_pagina = min(intval($request->get_param('por_pagina')), 50);
    
    $produtos = $data['produtos'];
    
    if ($categoria && $categoria !== 'todos') {
        $produtos = array_filter($produtos, function($p) use ($categoria) {
            return sanitize_title($p['categoria'] ?? '') === $categoria ||
                   ($p['categoria_slug'] ?? '') === $categoria;
        });
    }
    
    if ($busca) {
        $busca_lower = mb_strtolower($busca);
        $produtos = array_filter($produtos, function($p) use ($busca_lower) {
            $searchable = mb_strtolower(
                ($p['nome'] ?? '') . ' ' .
                implode(' ', $p['beneficios'] ?? []) . ' ' .
                implode(' ', $p['indicacoes'] ?? []) . ' ' .
                implode(' ', $p['ingredientes'] ?? []) . ' ' .
                ($p['estudos_resumo'] ?? '') . ' ' .
                ($p['indicacao_mtc'] ?? '') . ' ' .
                ($p['nome_chines'] ?? '')
            );
            return strpos($searchable, $busca_lower) !== false;
        });
    }
    
    $total = count($produtos);
    $offset = ($pagina - 1) * $por_pagina;
    $produtos = array_slice(array_values($produtos), $offset, $por_pagina);
    
    return array(
        'total' => $total,
        'pagina' => $pagina,
        'por_pagina' => $por_pagina,
        'total_paginas' => ceil($total / $por_pagina),
        'produtos' => $produtos,
    );
}

/* ================================================================
   GEO: robots.txt - Allow AI crawlers
   ================================================================ */

add_filter('robots_txt', 'nraizes_geo_robots_txt', 10000, 2);
function nraizes_geo_robots_txt($output, $public) {
    // Add explicit allow for AI crawlers
    $ai_bots = "\n# AI Search Crawlers (GEO)\n";
    $ai_bots .= "User-agent: ChatGPT-User\nAllow: /\n\n";
    $ai_bots .= "User-agent: GPTBot\nAllow: /\n\n";
    $ai_bots .= "User-agent: Google-Extended\nAllow: /\n\n";
    $ai_bots .= "User-agent: PerplexityBot\nAllow: /\n\n";
    $ai_bots .= "User-agent: ClaudeBot\nAllow: /\n\n";
    $ai_bots .= "User-agent: Applebot-Extended\nAllow: /\n\n";
    $ai_bots .= "User-agent: cohere-ai\nAllow: /\n\n";
    $ai_bots .= "User-agent: Bytespider\nAllow: /\n\n";
    
    return $output . $ai_bots;
}

/* ================================================================
   GEO: Add meta tags for AI discoverability
   ================================================================ */

function nraizes_geo_meta_tags() {
    global $post;
    if (!is_a($post, 'WP_Post') || !has_shortcode($post->post_content, 'nraizes_consulta')) return;
    
    $data = nraizes_get_consultation_data();
    $total = $data ? count($data['produtos'] ?? []) : 0;
    
    echo '<meta name="citation_title" content="Guia de Produtos Naturais e Suplementos - Novas Raizes">' . "\n";
    echo '<meta name="citation_author" content="Novas Raizes">' . "\n";
    echo '<meta name="citation_publication_date" content="' . esc_attr($data['atualizado_em'] ?? date('Y-m-d')) . '">' . "\n";
    echo '<meta name="dc.title" content="Guia de Produtos Naturais e Suplementos">' . "\n";
    echo '<meta name="dc.creator" content="Novas Raizes">' . "\n";
    echo '<meta name="dc.subject" content="Produtos Naturais; Suplementos; Medicina Tradicional Chinesa; Fitoterapia; Evidencias Cientificas">' . "\n";
    echo '<meta name="dc.description" content="Base de dados com ' . intval($total) . ' produtos naturais e suplementos com dosagem, contraindicacoes e referencias cientificas">' . "\n";
    echo '<meta name="dc.language" content="pt-BR">' . "\n";
    echo '<meta name="dc.type" content="Dataset">' . "\n";
    
    // Link to llms.txt
    echo '<link rel="alternate" type="text/plain" href="' . esc_url(get_stylesheet_directory_uri() . '/llms.txt') . '" title="LLM Context">' . "\n";
}
add_action('wp_head', 'nraizes_geo_meta_tags', 1);
