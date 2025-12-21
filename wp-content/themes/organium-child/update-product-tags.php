<?php
/**
 * Product Tags Updater
 * Adiciona tags de benefício aos produtos baseado em categoria e descrição
 * 
 * IMPORTANTE: Fórmulas Chinesas NÃO recebem tags de benefício (restrição ANVISA)
 * 
 * @package Organium-Child
 */

// Only run when explicitly called
if (!defined('NRAIZES_UPDATE_TAGS')) {
    return;
}

/**
 * Mapeamento de palavras-chave para tags
 */
function nraizes_get_tag_mappings() {
    return array(
        // ===== BENEFÍCIOS =====
        'Antioxidante' => array(
            'keywords' => array('antioxidante', 'oxidativo', 'radicais livres', 'astaxantina', 'resveratrol', 'vitamina c', 'vitamina e'),
            'categories' => array('nutraceuticos', 'cosmeticos'),
        ),
        'Imunidade' => array(
            'keywords' => array('imunidade', 'imunológico', 'defesa', 'própolis', 'vitamina d', 'zinco', 'equinácea'),
            'categories' => array('nutraceuticos', 'fitoterapia'),
        ),
        'Energia' => array(
            'keywords' => array('energia', 'disposição', 'vitalidade', 'cansaço', 'fadiga', 'guaraná', 'ginseng', 'maca'),
            'categories' => array('nutraceuticos', 'fitness'),
        ),
        'Relaxante' => array(
            'keywords' => array('relaxa', 'calma', 'stress', 'estresse', 'ansiedade', 'lavanda', 'camomila', 'passiflora', 'valeriana'),
            'categories' => array('aromaterapia', 'fitoterapia', 'nutraceuticos'),
        ),
        'Sono' => array(
            'keywords' => array('sono', 'dormir', 'insônia', 'melatonina', 'triptofano'),
            'categories' => array('nutraceuticos', 'aromaterapia', 'fitoterapia'),
        ),
        'Digestão' => array(
            'keywords' => array('digestão', 'digestivo', 'intestino', 'probiótico', 'fibra', 'enzima'),
            'categories' => array('nutraceuticos', 'fitoterapia', 'alimentos'),
        ),
        'Anti-inflamatório' => array(
            'keywords' => array('inflamat', 'cúrcuma', 'curcumina', 'ômega', 'omega'),
            'categories' => array('nutraceuticos', 'antiinflamatorio'),
        ),
        'Detox' => array(
            'keywords' => array('detox', 'desintoxic', 'limpeza', 'depurat', 'clorofila'),
            'categories' => array('nutraceuticos', 'fitoterapia', 'alimentos'),
        ),
        'Pele' => array(
            'keywords' => array('pele', 'colágeno', 'hidratação', 'elasticidade', 'rugas', 'anti-idade'),
            'categories' => array('nutraceuticos', 'cosmeticos'),
        ),
        'Cabelo e Unhas' => array(
            'keywords' => array('cabelo', 'unhas', 'biotina', 'queratina', 'crescimento capilar'),
            'categories' => array('nutraceuticos', 'cosmeticos'),
        ),
        'Foco e Memória' => array(
            'keywords' => array('foco', 'memória', 'cognit', 'concentração', 'mental', 'alecrim', 'ginkgo'),
            'categories' => array('nutraceuticos', 'aromaterapia'),
        ),
        'Articulações' => array(
            'keywords' => array('articulação', 'articulações', 'colágeno tipo 2', 'condroitina', 'glucosamina', 'artrose'),
            'categories' => array('nutraceuticos'),
        ),
        
        // ===== INGREDIENTES/ATIVOS =====
        'Vitamina D' => array(
            'keywords' => array('vitamina d', 'colecalciferol'),
            'categories' => array('nutraceuticos'),
        ),
        'Vitamina C' => array(
            'keywords' => array('vitamina c', 'ácido ascórbico'),
            'categories' => array('nutraceuticos'),
        ),
        'Ômega 3' => array(
            'keywords' => array('ômega 3', 'omega 3', 'óleo de peixe', 'dha', 'epa'),
            'categories' => array('nutraceuticos'),
        ),
        'Colágeno' => array(
            'keywords' => array('colágeno', 'colageno'),
            'categories' => array('nutraceuticos', 'cosmeticos'),
        ),
        'Magnésio' => array(
            'keywords' => array('magnésio', 'magnesio'),
            'categories' => array('nutraceuticos'),
        ),
        'Própolis' => array(
            'keywords' => array('própolis', 'propolis'),
            'categories' => array('nutraceuticos', 'fitoterapia'),
        ),
        'Aloe Vera' => array(
            'keywords' => array('aloe vera', 'babosa', 'aloegel'),
            'categories' => array('cosmeticos', 'fitoterapia'),
        ),
        
        // ===== AROMATERAPIA =====
        'Óleo Essencial' => array(
            'keywords' => array('óleo essencial', 'oleo essencial'),
            'categories' => array('aromaterapia'),
        ),
        'Difusão' => array(
            'keywords' => array('difusor', 'aromático', 'ambiente'),
            'categories' => array('aromaterapia'),
        ),
        'Massagem' => array(
            'keywords' => array('massagem', 'corporal'),
            'categories' => array('aromaterapia', 'cosmeticos'),
        ),
        
        // ===== PÚBLICO =====
        'Vegano' => array(
            'keywords' => array('vegano', 'vegan', 'plant based', 'origem vegetal'),
            'categories' => array('nutraceuticos', 'cosmeticos', 'alimentos'),
        ),
        'Sem Glúten' => array(
            'keywords' => array('sem glúten', 'gluten free'),
            'categories' => array('nutraceuticos', 'alimentos'),
        ),
        'Orgânico' => array(
            'keywords' => array('orgânico', 'organico', 'organic'),
            'categories' => array('nutraceuticos', 'alimentos', 'cosmeticos', 'aromaterapia'),
        ),
        
        // ===== FITNESS =====
        'Pré-treino' => array(
            'keywords' => array('pré-treino', 'pre treino', 'pre-workout'),
            'categories' => array('fitness', 'nutraceuticos'),
        ),
        'Pós-treino' => array(
            'keywords' => array('pós-treino', 'pos treino', 'recuperação muscular'),
            'categories' => array('fitness', 'nutraceuticos'),
        ),
        'Proteína' => array(
            'keywords' => array('proteína', 'proteina', 'whey', 'aminoácido'),
            'categories' => array('fitness', 'nutraceuticos'),
        ),
        'BCAA' => array(
            'keywords' => array('bcaa', 'leucina', 'isoleucina', 'valina'),
            'categories' => array('fitness'),
        ),
        'Glutamina' => array(
            'keywords' => array('glutamina', 'l-glutamina'),
            'categories' => array('fitness', 'nutraceuticos'),
        ),
    );
}

/**
 * Categorias de MTC que NÃO devem receber tags de benefício
 */
function nraizes_get_mtc_categories() {
    return array(
        'formulas-chinesas',
        'formulas-chinesas1',
        'eliminam-vento',
        'clareiam-o-calor-e-eliminam-umidade',
        'harmonizadoras',
        'formulas-chinesas-adstringentes',
        'tonicos-de-qi-e-sangue',
        'tonicos-de-yang',
        'acalmam-a-mente',
        'regulam-o-sangue',
        'aquecem-o-aquecedor-medio',
    );
}

/**
 * Verifica se produto é da categoria MTC
 */
function nraizes_is_mtc_product($product_id) {
    $mtc_categories = nraizes_get_mtc_categories();
    $product_cats = wp_get_post_terms($product_id, 'product_cat', array('fields' => 'slugs'));
    
    if (is_wp_error($product_cats)) {
        return false;
    }
    
    foreach ($product_cats as $cat_slug) {
        if (in_array($cat_slug, $mtc_categories)) {
            return true;
        }
    }
    
    return false;
}

/**
 * Encontra tags aplicáveis para um produto
 */
function nraizes_find_applicable_tags($product_id) {
    // Não adicionar tags de benefício em MTC (ANVISA)
    if (nraizes_is_mtc_product($product_id)) {
        return array();
    }
    
    $product = wc_get_product($product_id);
    if (!$product) {
        return array();
    }
    
    // Obter texto do produto
    $title = strtolower($product->get_name());
    $description = strtolower($product->get_description());
    $short_desc = strtolower($product->get_short_description());
    $full_text = $title . ' ' . $description . ' ' . $short_desc;
    
    // Obter categorias do produto
    $product_cats = wp_get_post_terms($product_id, 'product_cat', array('fields' => 'slugs'));
    if (is_wp_error($product_cats)) {
        $product_cats = array();
    }
    
    $applicable_tags = array();
    $tag_mappings = nraizes_get_tag_mappings();
    
    foreach ($tag_mappings as $tag_name => $config) {
        // Verificar se produto está em categoria elegível
        $category_match = false;
        foreach ($product_cats as $cat_slug) {
            foreach ($config['categories'] as $allowed_cat) {
                if (strpos($cat_slug, $allowed_cat) !== false) {
                    $category_match = true;
                    break 2;
                }
            }
        }
        
        if (!$category_match) {
            continue;
        }
        
        // Verificar se alguma keyword está no texto
        foreach ($config['keywords'] as $keyword) {
            if (strpos($full_text, strtolower($keyword)) !== false) {
                $applicable_tags[] = $tag_name;
                break;
            }
        }
    }
    
    return array_unique($applicable_tags);
}

/**
 * Atualiza tags de todos os produtos
 */
function nraizes_update_product_tags() {
    $args = array(
        'post_type'      => 'product',
        'posts_per_page' => -1,
        'post_status'    => 'publish',
        'fields'         => 'ids',
    );
    
    $product_ids = get_posts($args);
    $results = array(
        'updated' => array(),
        'skipped_mtc' => array(),
        'no_tags' => array(),
        'errors' => array(),
    );
    
    foreach ($product_ids as $product_id) {
        $product = wc_get_product($product_id);
        if (!$product) {
            continue;
        }
        
        // Verificar se é MTC
        if (nraizes_is_mtc_product($product_id)) {
            $results['skipped_mtc'][] = $product->get_name();
            continue;
        }
        
        // Encontrar tags aplicáveis
        $tags_to_add = nraizes_find_applicable_tags($product_id);
        
        if (empty($tags_to_add)) {
            $results['no_tags'][] = $product->get_name();
            continue;
        }
        
        // Adicionar tags ao produto
        $result = wp_set_object_terms($product_id, $tags_to_add, 'product_tag', true);
        
        if (is_wp_error($result)) {
            $results['errors'][] = $product->get_name() . ': ' . $result->get_error_message();
        } else {
            $results['updated'][] = array(
                'name' => $product->get_name(),
                'tags' => $tags_to_add,
            );
        }
    }
    
    return $results;
}

// Execute and show results
$result = nraizes_update_product_tags();

echo '<pre style="font-family: monospace; padding: 20px; background: #f5f5f5;">';
echo "============================================\n";
echo "   ATUALIZAÇÃO DE TAGS DE PRODUTOS\n";
echo "============================================\n\n";

echo "📊 RESUMO:\n";
echo "  ✅ Atualizados: " . count($result['updated']) . "\n";
echo "  ⏭️  MTC (sem tags): " . count($result['skipped_mtc']) . "\n";
echo "  ❔ Sem matches: " . count($result['no_tags']) . "\n";
echo "  ❌ Erros: " . count($result['errors']) . "\n\n";

if (!empty($result['updated'])) {
    echo "✅ PRODUTOS ATUALIZADOS:\n";
    echo "----------------------------------------\n";
    foreach ($result['updated'] as $item) {
        echo "  • " . $item['name'] . "\n";
        echo "    Tags: " . implode(', ', $item['tags']) . "\n\n";
    }
}

if (!empty($result['errors'])) {
    echo "\n❌ ERROS:\n";
    echo "----------------------------------------\n";
    foreach ($result['errors'] as $error) {
        echo "  • {$error}\n";
    }
}

echo '</pre>';
