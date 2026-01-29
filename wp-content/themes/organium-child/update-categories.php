<?php
/**
 * Category Descriptions Updater
 * Run once to update category descriptions, then delete this file
 * 
 * @package Organium-Child
 */

// Only run when explicitly called
if (!defined('NRAIZES_UPDATE_CATEGORIES')) {
    return;
}

/**
 * Update WooCommerce category descriptions for SEO
 */
function nraizes_update_category_descriptions() {
    
    $descriptions = array(
        // Main Categories (Parent = 0)
        'formulas-chinesas1' => 'Descubra nossa coleção exclusiva de Fórmulas Chinesas tradicionais. Produzidas com ervas selecionadas seguindo os princípios milenares da Medicina Tradicional Chinesa, nossas fórmulas são desenvolvidas para promover o equilíbrio energético e o bem-estar integral. Cada produto é formulado por especialistas em fitoterapia chinesa, garantindo qualidade e eficácia. Encontre o apoio natural que você precisa para sua saúde.',
        
        'nutraceuticos' => 'Explore nossa linha completa de Nutracêuticos selecionados para complementar sua alimentação com nutrientes essenciais. Oferecemos vitaminas, minerais, antioxidantes, proteínas e compostos bioativos de alta qualidade para apoiar seu bem-estar diário. Todos os produtos são criteriosamente escolhidos para fornecer o melhor suporte nutricional ao seu organismo.',
        
        'cosmeticos' => 'Cuide da sua pele e beleza com nossa seleção de Cosméticos naturais. Produtos formulados com ingredientes de origem natural, sem crueldade animal, para hidratação, proteção e nutrição da pele. Descubra marcas premium como Granado, Phebo e AmoKarité para uma rotina de cuidados pessoais mais saudável e consciente.',
        
        'aromaterapia' => 'Transforme seu ambiente e bem-estar com nossa linha de Aromaterapia. Óleos essenciais puros, difusores de qualidade e produtos aromáticos para criar atmosferas relaxantes e revigorantes. A aromaterapia é uma forma natural de promover equilíbrio emocional, aliviar o estresse e melhorar a qualidade de vida.',
        
        'fitoterapia' => 'Conheça nossa seleção de produtos de Fitoterapia, a ciência das plantas medicinais. Oferecemos extratos, tinturas e compostos herbais desenvolvidos com base em conhecimentos tradicionais e científicos. Uma abordagem natural para apoiar diversas funções do organismo e promover saúde de forma integral.',
        
        'alimentos' => 'Descubra nossa categoria de Alimentos funcionais e naturais. Bebidas nutritivas, superfoods amazônicos, snacks saudáveis e produtos que combinam sabor com benefícios para a saúde. Alimente-se de forma consciente com ingredientes que nutrem corpo e mente.',
        
        'livro' => 'Amplie seus conhecimentos com nossa seleção de Livros sobre saúde natural, fitoterapia chinesa e bem-estar. Conteúdo educativo para quem deseja aprofundar seu entendimento sobre medicina tradicional, plantas medicinais e práticas de vida saudável.',
        
        'higiene-pessoal' => 'Produtos de Higiene Pessoal naturais e sustentáveis para o cuidado diário. Sabonetes, desodorantes e itens essenciais formulados com ingredientes suaves e eficazes, respeitando sua pele e o meio ambiente.',
        
        'kids' => 'Produtos especialmente desenvolvidos para o cuidado das crianças. Nossa linha Kids oferece cosméticos suaves, produtos de higiene gentis e itens seguros para os pequenos, com ingredientes naturais que os pais podem confiar.',
        
        'pet' => 'Cuide do bem-estar do seu melhor amigo com nossa linha Pet. Produtos naturais desenvolvidos especialmente para animais de estimação, proporcionando cuidados gentis e eficazes para cães e gatos.',
        
        // Subcategories of Fórmulas Chinesas
        'eliminam-vento' => 'Fórmulas tradicionais chinesas que auxiliam na eliminação do vento patogênico. Indicadas segundo a MTC para condições relacionadas a invasões de vento externo ou interno, promovendo alívio e equilíbrio energético.',
        
        'clareiam-o-calor-e-eliminam-umidade' => 'Composições que ajudam a clarear o calor e eliminar a umidade do organismo segundo os princípios da Medicina Tradicional Chinesa. Indicadas para padrões de calor-umidade.',
        
        'harmonizadoras' => 'Fórmulas harmonizadoras da fitoterapia chinesa, desenvolvidas para equilibrar e regular as funções do organismo. Auxiliam na manutenção da harmonia entre Yin e Yang.',
        
        'formulas-chinesas-adstringentes' => 'Fórmulas adstringentes tradicionais da medicina chinesa, utilizadas para conter perdas e consolidar a essência. Indicadas segundo a MTC para padrões de deficiência.',
        
        'tonicos-de-qi-e-sangue' => 'Fórmulas tônicas de Qi e Sangue da fitoterapia chinesa. Nutriem e fortalecem a energia vital e o sangue, indicadas para padrões de deficiência de Qi e Sangue segundo a MTC.',
        
        'tonicos-de-yang' => 'Tônicos de Yang da medicina tradicional chinesa. Fórmulas que aquecem e fortalecem o Yang do organismo, indicadas para padrões de deficiência de Yang.',
        
        'oleo-essencial' => 'Óleos essenciais 100% puros para aromaterapia e uso terapêutico. Extraídos de plantas aromáticas de alta qualidade, nossos óleos essenciais proporcionam benefícios para corpo e mente. Ideais para difusão, massagens aromáticas e cuidados naturais.',
        
        // Subcategories of Nutracêuticos
        'fitness' => 'Suplementos e produtos para quem busca performance física e vida ativa. Nossa linha Fitness inclui aminoácidos, pré-treinos, proteínas e suplementos para apoiar seus objetivos de treino e recuperação muscular.',
        
        'antiinflamatorio' => 'Produtos com propriedades anti-inflamatórias naturais. Plantas medicinais e compostos herbais que auxiliam no manejo da inflamação de forma natural, apoiando o bem-estar do organismo.',
    );
    
    $updated = array();
    $errors = array();
    
    foreach ($descriptions as $slug => $description) {
        $term = get_term_by('slug', $slug, 'product_cat');
        
        if ($term && !is_wp_error($term)) {
            // Only update if description is empty or different
            if (empty($term->description) || $term->description !== $description) {
                $result = wp_update_term($term->term_id, 'product_cat', array(
                    'description' => $description
                ));
                
                if (is_wp_error($result)) {
                    $errors[] = $slug . ': ' . $result->get_error_message();
                } else {
                    $updated[] = $slug;
                }
            }
        } else {
            $errors[] = $slug . ': Categoria não encontrada';
        }
    }
    
    return array(
        'updated' => $updated,
        'errors' => $errors,
        'total' => count($descriptions)
    );
}

// Execute and show results
$result = nraizes_update_category_descriptions();
echo '<pre>';
echo "Categorias atualizadas: " . count($result['updated']) . "/" . $result['total'] . "\n\n";

if (!empty($result['updated'])) {
    echo "✅ Atualizadas:\n";
    foreach ($result['updated'] as $slug) {
        echo "  - " . esc_html($slug) . "\n";
    }
}

if (!empty($result['errors'])) {
    echo "\n❌ Erros:\n";
    foreach ($result['errors'] as $error) {
        echo "  - " . esc_html($error) . "\n";
    }
}
echo '</pre>';
