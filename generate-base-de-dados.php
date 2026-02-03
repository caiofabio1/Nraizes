<?php
/**
 * Standalone HTML Generator for "Base de Dados" page.
 *
 * Reads the JSON data, CSS, and JS source files from the theme directory,
 * renders all product cards server-side (without WordPress), and writes
 * a self-contained HTML file.
 *
 * Usage:  php generate-base-de-dados.php
 *
 * @package Organium-Child
 */

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
$base_dir   = __DIR__ . '/wp-content/themes/organium-child';
$json_path  = $base_dir . '/data/consulta-produtos.json';
$css_path   = $base_dir . '/assets/css/consulta-produtos.css';
$js_path    = $base_dir . '/assets/js/consulta-produtos.js';
$output_path = $base_dir . '/base-de-dados.html';

// ---------------------------------------------------------------------------
// Load source assets
// ---------------------------------------------------------------------------
$json_content = file_get_contents($json_path);
if ($json_content === false) {
    fwrite(STDERR, "ERROR: Cannot read JSON file: $json_path\n");
    exit(1);
}

$data = json_decode($json_content, true);
if (!$data) {
    fwrite(STDERR, "ERROR: Invalid JSON in $json_path\n");
    exit(1);
}

$css_content = file_get_contents($css_path);
if ($css_content === false) {
    fwrite(STDERR, "ERROR: Cannot read CSS file: $css_path\n");
    exit(1);
}

$js_content = file_get_contents($js_path);
if ($js_content === false) {
    fwrite(STDERR, "ERROR: Cannot read JS file: $js_path\n");
    exit(1);
}

// ---------------------------------------------------------------------------
// WordPress function replacements
// ---------------------------------------------------------------------------
function esc_html($text) {
    return htmlspecialchars((string)$text, ENT_QUOTES, 'UTF-8');
}

function esc_attr($text) {
    return htmlspecialchars((string)$text, ENT_QUOTES, 'UTF-8');
}

function esc_url($url) {
    $url = trim((string)$url);
    if ($url === '') return '';
    // Basic sanitisation: encode entities but keep valid URL chars
    return htmlspecialchars($url, ENT_QUOTES, 'UTF-8');
}

function sanitize_title($title) {
    $title = mb_strtolower(trim((string)$title));
    // Transliterate common Portuguese accented chars
    $map = [
        'á'=>'a','à'=>'a','ã'=>'a','â'=>'a','ä'=>'a',
        'é'=>'e','è'=>'e','ê'=>'e','ë'=>'e',
        'í'=>'i','ì'=>'i','î'=>'i','ï'=>'i',
        'ó'=>'o','ò'=>'o','õ'=>'o','ô'=>'o','ö'=>'o',
        'ú'=>'u','ù'=>'u','û'=>'u','ü'=>'u',
        'ç'=>'c','ñ'=>'n',
        'Á'=>'a','À'=>'a','Ã'=>'a','Â'=>'a','Ä'=>'a',
        'É'=>'e','È'=>'e','Ê'=>'e','Ë'=>'e',
        'Í'=>'i','Ì'=>'i','Î'=>'i','Ï'=>'i',
        'Ó'=>'o','Ò'=>'o','Õ'=>'o','Ô'=>'o','Ö'=>'o',
        'Ú'=>'u','Ù'=>'u','Û'=>'u','Ü'=>'u',
        'Ç'=>'c','Ñ'=>'n',
    ];
    $title = strtr($title, $map);
    $title = preg_replace('/[^a-z0-9\-_ ]/', '', $title);
    $title = preg_replace('/[\s_]+/', '-', $title);
    $title = preg_replace('/-+/', '-', $title);
    return trim($title, '-');
}

// ---------------------------------------------------------------------------
// Helper functions (adapted from consulta-produtos.php)
// ---------------------------------------------------------------------------

function nraizes_render_reference($ref) {
    $ref = trim($ref);
    if (empty($ref)) return '';

    if (strpos($ref, 'http') === 0) {
        $label = $ref;
        if (strpos($ref, 'pubmed.ncbi.nlm.nih.gov') !== false) {
            $pmid = preg_replace('/[^0-9]/', '', basename(parse_url($ref, PHP_URL_PATH)));
            $label = 'PubMed PMID: ' . $pmid;
        }
        return '<li><cite><a href="' . esc_url($ref) . '" target="_blank" rel="noopener noreferrer">' . esc_html($label) . '</a></cite></li>';
    } elseif (preg_match('/^10\.\d{4,}/', $ref)) {
        return '<li><cite><a href="https://doi.org/' . esc_attr($ref) . '" target="_blank" rel="noopener noreferrer">DOI: ' . esc_html($ref) . '</a></cite></li>';
    } else {
        return '<li><cite>' . esc_html($ref) . '</cite></li>';
    }
}

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

function nraizes_evidence_class($nivel) {
    $n = mb_strtolower($nivel);
    if (strpos($n, 'alta') !== false && strpos($n, 'moderada') !== false) return 'moderada-alta';
    if (strpos($n, 'alta') !== false) return 'alta';
    if (strpos($n, 'moderada') !== false && strpos($n, 'baixa') !== false) return 'baixa-moderada';
    if (strpos($n, 'moderada') !== false) return 'moderada';
    if (strpos($n, 'muito') !== false) return 'muito-baixa';
    return 'baixa';
}

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

    $contraindicacoes = $p['contraindicacoes'] ?? [];
    $interacoes      = $p['interacoes'] ?? [];
    $efeitos_col     = $p['efeitos_colaterais'] ?? [];
    $alertas         = $p['alertas'] ?? [];
    $ingredientes    = $p['ingredientes'] ?? [];
    $princ_ativos    = $p['principios_ativos'] ?? [];
    $certificacoes   = $p['certificacoes'] ?? [];
    $referencias     = $p['referencias'] ?? [];
    $faq             = $p['faq'] ?? [];

    if ($cat_slug === 'suplemento' || $categoria === 'Suplemento Ocidental') {
        $display_slug = 'suplemento';
    } else {
        $display_slug = $cat_slug;
    }

    // Build searchable text for JS filtering
    $search_parts = array($nome, $nome_cn, $categoria, $ind_mtc, $aplicacoes, $modo_uso, $dosagem, $estudos, $origem);
    foreach (array($ingredientes, $princ_ativos, $contraindicacoes, $alertas, $certificacoes) as $arr) {
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

                <?php if ($aplicacoes) : ?>
                <section class="nrc-section" aria-label="Aplicacoes clinicas">
                    <h4 class="nrc-section-title">Aplicacoes Clinicas Baseadas em Evidencias</h4>
                    <p class="nrc-text-block"><?php echo esc_html($aplicacoes); ?></p>
                </section>
                <?php endif; ?>

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

                <?php if ($estudos) : ?>
                <section class="nrc-section" aria-label="Evidencia cientifica">
                    <h4 class="nrc-section-title">Evidencia Cientifica</h4>
                    <blockquote class="nrc-text-block nrc-evidence-block" cite="https://pubmed.ncbi.nlm.nih.gov/">
                        <p><?php echo esc_html($estudos); ?></p>
                    </blockquote>
                </section>
                <?php endif; ?>

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

                <div class="nrc-card-cta">
                    <a href="https://wa.me/5511999927588?text=<?php echo rawurlencode('Oi! Gostaria de saber sobre ' . $nome . '. Vocês têm disponível na loja?'); ?>"
                       class="nrc-cta-btn nrc-cta-btn--whatsapp" target="_blank" rel="noopener noreferrer"
                       aria-label="Perguntar sobre <?php echo esc_attr($nome); ?> no WhatsApp">
                        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2 22l4.832-1.438A9.955 9.955 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18c-1.66 0-3.203-.508-4.484-1.375l-.316-.191-2.828.84.84-2.828-.191-.316A7.953 7.953 0 014 12c0-4.411 3.589-8 8-8s8 3.589 8 8-3.589 8-8 8z"/></svg>
                        Consultar disponibilidade
                    </a>
                    <a href="https://www.google.com/maps/search/R.+Dr.+Nicolau+de+Sousa+Queir%C3%B3s,+34+-+Vila+Mariana,+S%C3%A3o+Paulo+-+SP"
                       class="nrc-cta-btn nrc-cta-btn--map" target="_blank" rel="noopener noreferrer"
                       aria-label="Ver localiza&#231;&#227;o da loja no mapa">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
                        Como chegar
                    </a>
                </div>

                <meta itemprop="author" content="Novas Raizes - nraizes.com.br">
                <meta itemprop="datePublished" content="<?php echo esc_attr(date('Y-m-d')); ?>">
                <meta itemprop="publisher" content="Novas Raizes">

            </div><!-- .nrc-card-content -->
        </details>
    </article>
    <?php
    return ob_get_clean();
}

// ---------------------------------------------------------------------------
// Build the main container HTML (replicates nraizes_consulta_shortcode)
// ---------------------------------------------------------------------------
$produtos = $data['produtos'] ?? [];
$total    = count($produtos);
$updated  = $data['atualizado_em'] ?? date('Y-m-d');
$aviso    = $data['aviso_legal'] ?? '';

// Merge categories for display (same logic as original)
$display_cats = [];
foreach (($data['categorias'] ?? []) as $cat => $count) {
    if ($cat === 'Suplemento Ocidental') {
        $display_cats['Suplemento'] = ($display_cats['Suplemento'] ?? 0) + $count;
    } else {
        $display_cats[$cat] = ($display_cats[$cat] ?? 0) + $count;
    }
}

// Render all product cards
ob_start();
foreach ($produtos as $i => $produto) {
    echo nraizes_render_product_card($produto, $i);
}
$cards_html = ob_get_clean();

// Store hours (static for standalone page)
$hora_atual = (int) date('G');
$dia_semana = (int) date('w');
$aberto = ($dia_semana >= 1 && $dia_semana <= 6 && $hora_atual >= 9 && $hora_atual < 18);
if ($aberto) {
    $store_hours_html = '<span class="nrc-store-open">Aberto agora</span> &middot; Fecha &agrave;s 18:30';
} elseif ($dia_semana === 0) {
    $store_hours_html = '<span class="nrc-store-closed">Fechado</span> &middot; Abre segunda &agrave;s 09:00';
} else {
    $store_hours_html = '<span class="nrc-store-closed">Fechado</span> &middot; Seg-S&aacute;b 09:00-18:30';
}

// Build category filter buttons
$cat_buttons_html = '';
foreach ($display_cats as $cat => $count) {
    $cat_slug = sanitize_title($cat);
    $cat_buttons_html .= '<button class="nrc-filter-btn" data-categoria="' . esc_attr($cat_slug) . '" aria-pressed="false">'
        . esc_html($cat) . ' <span class="nrc-badge">' . intval($count) . '</span></button>' . "\n";
}

$formatted_date = date('d/m/Y', strtotime($updated));
$wa_store_msg = rawurlencode('Olá! Vi o Guia de Produtos Naturais no site e gostaria de saber mais. Posso visitar a loja?');

// ---------------------------------------------------------------------------
// Assemble the full HTML document
// ---------------------------------------------------------------------------
$html = <<<HTML
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Base de Dados - Novas Ra&iacute;zes</title>
    <style>
{$css_content}
    </style>
</head>
<body>

    <div id="nraizes-consulta" class="nrc-container" role="main"
         itemscope itemtype="https://schema.org/MedicalWebPage">

        <meta itemprop="specialty" content="Medicina Integrativa e Produtos Naturais">
        <meta itemprop="medicalAudience" content="Paciente">
        <meta itemprop="lastReviewed" content="{$updated}">

        <!-- HEADER -->
        <header class="nrc-header">
            <h1 class="nrc-title" itemprop="name">
                Guia de Produtos Naturais e Suplementos
            </h1>
            <p class="nrc-subtitle" itemprop="description">
                Base de dados curada com {$total} produtos naturais, formulas da Medicina Tradicional Chinesa,
                suplementos, plantas medicinais e oleos essenciais. Cada produto apresenta um resumo baseado
                exclusivamente no que os estudos cientificos referenciam e embasam, com citacoes de revistas
                indexadas (PubMed, Cochrane, etc.).
                <strong>Este conteudo nao substitui orientacao de um profissional de saude.</strong>
            </p>
            <div class="nrc-stats" role="status">
                <span class="nrc-stat">
                    <strong id="nrc-total-visible">{$total}</strong> produtos catalogados
                </span>
                <span class="nrc-stat">
                    Atualizado em <time datetime="{$updated}">{$formatted_date}</time>
                </span>
            </div>
        </header>

        <!-- SEARCH & FILTERS -->
        <nav class="nrc-controls" aria-label="Filtros de busca">
            <div class="nrc-search-wrap">
                <label for="nrc-search" class="screen-reader-text">Buscar produtos naturais</label>
                <svg class="nrc-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input type="search"
                       id="nrc-search"
                       class="nrc-search-input"
                       placeholder="Buscar por nome, ingrediente, estudo ou aplicacao..."
                       autocomplete="off"
                       aria-describedby="nrc-search-help">
                <span id="nrc-search-help" class="screen-reader-text">
                    Digite para filtrar entre {$total} produtos naturais, suplementos e formulas
                </span>
                <button id="nrc-clear-search" class="nrc-clear-btn" style="display:none;" aria-label="Limpar busca">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                        <line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>

            <div class="nrc-filters" role="group" aria-label="Filtrar por categoria">
                <button class="nrc-filter-btn nrc-active" data-categoria="todos" aria-pressed="true">
                    Todos <span class="nrc-badge">{$total}</span>
                </button>
                {$cat_buttons_html}
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

        <!-- NO RESULTS -->
        <div id="nrc-no-results" class="nrc-no-results" style="display:none;" role="status">
            <p>Nenhum produto encontrado para esta busca.</p>
            <button class="nrc-reset-btn" id="nrc-reset-filters">Limpar filtros</button>
        </div>

        <!-- PRODUCT CARDS -->
        <div id="nrc-results" class="nrc-results" role="feed" aria-label="Resultados da consulta">
            {$cards_html}
        </div>

        <!-- DISCLAIMER -->
        <aside class="nrc-disclaimer" role="note" aria-label="Aviso legal obrigatorio">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" aria-hidden="true">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <div>
                <strong>Aviso Legal Importante:</strong>
                <p>{$aviso}</p>
                <p>Em conformidade com a legislacao brasileira (ANVISA - RDC 243/2018 e IN 28/2018),
                informamos que: <strong>suplementos alimentares nao sao medicamentos</strong> e nao se destinam
                a diagnosticar, tratar, curar ou prevenir qualquer doenca. As informacoes sobre estudos
                cientificos sao apresentadas com finalidade exclusivamente educativa e informativa, e nao
                constituem recomendacao terapeutica. <strong>Consulte sempre um profissional de saude
                habilitado</strong> antes de iniciar qualquer suplementacao. A automedicacao pode ser
                prejudicial a saude.</p>
            </div>
        </aside>

        <!-- STORE CTA BANNER -->
        <div class="nrc-store-cta" itemscope itemtype="https://schema.org/LocalBusiness">
            <meta itemprop="name" content="Novas Ra&iacute;zes &amp; Mivegan">
            <meta itemprop="telephone" content="+5511999927588">
            <meta itemprop="url" content="https://nraizes.com.br">
            <meta itemprop="image" content="https://nraizes.com.br/wp-content/uploads/logo-novas-raizes.png">
            <meta itemprop="priceRange" content="$$">
            <div itemprop="address" itemscope itemtype="https://schema.org/PostalAddress">
                <meta itemprop="streetAddress" content="R. Dr. Nicolau de Sousa Queir&oacute;s, 34">
                <meta itemprop="addressLocality" content="S&atilde;o Paulo">
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
                    R. Dr. Nicolau de Sousa Queir&oacute;s, 34 - Vila Mariana, S&atilde;o Paulo - SP
                </p>
                <p class="nrc-store-cta-hours">
                    {$store_hours_html}
                </p>
            </div>
            <div class="nrc-store-cta-actions">
                <a href="https://www.google.com/maps/search/R.+Dr.+Nicolau+de+Sousa+Queir%C3%B3s,+34+-+Vila+Mariana,+S%C3%A3o+Paulo+-+SP"
                   class="nrc-cta-btn nrc-cta-btn--map" target="_blank" rel="noopener noreferrer"
                   aria-label="Ver localiza&ccedil;&atilde;o no Google Maps">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
                    Como chegar
                </a>
                <a href="https://wa.me/5511999927588?text={$wa_store_msg}"
                   class="nrc-cta-btn nrc-cta-btn--whatsapp" target="_blank" rel="noopener noreferrer"
                   aria-label="Falar com a loja no WhatsApp">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2 22l4.832-1.438A9.955 9.955 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18c-1.66 0-3.203-.508-4.484-1.375l-.316-.191-2.828.84.84-2.828-.191-.316A7.953 7.953 0 014 12c0-4.411 3.589-8 8-8s8 3.589 8 8-3.589 8-8 8z"/></svg>
                    WhatsApp
                </a>
            </div>
        </div>

        <!-- GEO FOOTER -->
        <footer class="nrc-geo-footer" aria-label="Sobre esta base de dados">
            <div itemprop="about" itemscope itemtype="https://schema.org/MedicalCondition">
                <meta itemprop="name" content="Saude Integrativa e Medicina Natural">
            </div>
            <p class="nrc-geo-text">
                Esta base de dados e mantida pela <strong>Novas Raizes</strong> (nraizes.com.br),
                loja especializada em produtos naturais, suplementos alimentares, formulas da
                Medicina Tradicional Chinesa (MTC), plantas medicinais e oleos essenciais.
                As informacoes sao compiladas a partir de estudos cientificos publicados em
                revistas indexadas como PubMed, Cochrane Library e bases de dados de fitoterapia
                baseada em evidencias. Cada produto apresenta exclusivamente o que os estudos
                referenciam e embasam, com dosagem recomendada, contraindicacoes,
                interacoes medicamentosas e referencias cientificas verificaveis.
            </p>
            <p class="nrc-geo-text">
                Categorias disponiveis: Formulas da Medicina Tradicional Chinesa (Liu Wei Dihuang Wan,
                Xiao Yao Wan, Gui Pi Wan, Ba Zhen Wan, Guizhi Fuling Wan), Suplementos (Vitamina D3,
                Vitamina C, Vitamina B12, Omega-3, CoQ10, Ashwagandha, Melatonina, Magnesio, Zinco,
                Colageno, Probioticos, Curcuma, Spirulina, Clorella, Propolis, Creatina, Biotina,
                Calcio + K2, Triptofano/5-HTP, Selenio, NAC, Ferro Quelado, Glutamina),
                Plantas Medicinais (Camomila, Gengibre, Valeriana, Passiflora, Melissa, Boldo,
                Cavalinha, Espinheira-santa, Hibisco, Hortela-pimenta, Guaco, Unha-de-gato,
                Ginseng, Ginkgo, Equinacea, Rhodiola, Saw Palmetto, Cardo-mariano) e
                Oleos Essenciais (Lavanda, Melaleuca, Eucalipto, Alecrim, Hortela-pimenta,
                Limao, Laranja-doce, Ylang Ylang, Copaiba, Incenso/Olibano).
                Loja fisica na Vila Mariana, Sao Paulo - SP. Seg-Sab 09:00 as 18:30.
            </p>
            <div itemscope itemtype="https://schema.org/Organization" itemprop="publisher">
                <meta itemprop="name" content="Novas Raizes &amp; Mivegan">
                <meta itemprop="url" content="https://nraizes.com.br">
                <meta itemprop="telephone" content="+5511999927588">
                <meta itemprop="description" content="Loja de produtos naturais, suplementos, Medicina Tradicional Chinesa e oleos essenciais na Vila Mariana, Sao Paulo - SP. Seg-Sab 09:00-18:30.">
                <div itemprop="address" itemscope itemtype="https://schema.org/PostalAddress">
                    <meta itemprop="streetAddress" content="R. Dr. Nicolau de Sousa Queiros, 34">
                    <meta itemprop="addressLocality" content="Sao Paulo">
                    <meta itemprop="addressRegion" content="SP">
                    <meta itemprop="postalCode" content="04105-000">
                    <meta itemprop="addressCountry" content="BR">
                    <meta itemprop="neighborhood" content="Vila Mariana">
                </div>
            </div>
        </footer>

    </div><!-- .nrc-container -->

    <script>
{$js_content}
    </script>
</body>
</html>
HTML;

// ---------------------------------------------------------------------------
// Write output file
// ---------------------------------------------------------------------------
$bytes = file_put_contents($output_path, $html);
if ($bytes === false) {
    fwrite(STDERR, "ERROR: Could not write output file: $output_path\n");
    exit(1);
}

echo "OK: Generated $output_path (" . number_format($bytes) . " bytes, $total products)\n";
