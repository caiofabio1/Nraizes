import pandas as pd
import os

# File connection
file_path = r'c:\Users\caiof\NRAIZES\tools\Base de dados\base_dados_cientifica_produtos.xlsx'

# Load existing data
try:
    df_existing = pd.read_excel(file_path)
    print("Base de dados carregada com sucesso.")
except FileNotFoundError:
    print("Arquivo não encontrado. Criando novo.")
    df_existing = pd.DataFrame()

# Define new supplements data
new_data = [
    {
        'Fórmula (Pinyin)': 'Coenzyme Q10 (CoQ10)',
        'Nome Chinês': 'Fǔ Méi Q10 (辅酶Q10)',
        'Indicação Principal (MTC)': 'Saúde Cardiovascular, Fertilidade, Energia',
        'Dosagem Usual': '100-200mg/dia (Geral); 400-600mg (Enxaqueca/Fertilidade). Preferir Ubiquinol.',
        'Evidência Científica (Resumo)': 'Meta-análises mostram benefícios significativos na insuficiência cardíaca (redução de mortalidade), melhora na qualidade do esperma/óvulos em infertilidade e redução na frequência de enxaquecas.',
        'Aplicações Clínicas Baseadas em Evidências': 'Insuficiência Cardíaca, Enxaqueca, Infertilidade Masculina e Feminina, Fibromialgia, Diabetes.',
        'Nível de Evidência': 'Alta (Meta-análises)',
        'DOI/Referência Principal': 'https://pubmed.ncbi.nlm.nih.gov/25282031/; https://pubmed.ncbi.nlm.nih.gov/29966133/; https://pubmed.ncbi.nlm.nih.gov/28169956/'
    },
    {
        'Fórmula (Pinyin)': 'Spirulina',
        'Nome Chinês': 'Luó Xuán Zǎo (螺旋藻)',
        'Indicação Principal (MTC)': 'Nutrição, Perfil Lipídico, Rinite',
        'Dosagem Usual': '1-8g/dia. Comum: 2g (Rinite/Glicemia); 4-10g (Lipídios).',
        'Evidência Científica (Resumo)': 'Estudos indicam eficácia robusta na redução de colesterol LDL e triglicerídeos, melhora do controle glicêmico em diabéticos e alívio de sintomas de rinite alérgica.',
        'Aplicações Clínicas Baseadas em Evidências': 'Dislipidemia, Diabetes Tipo 2, Rinite Alérgica, Melhora de Performance Atlética.',
        'Nível de Evidência': 'Alta/Moderada',
        'DOI/Referência Principal': 'https://pubmed.ncbi.nlm.nih.gov/26433766/; https://pubmed.ncbi.nlm.nih.gov/26813468/; https://pubmed.ncbi.nlm.nih.gov/32201986/'
    },
    {
        'Fórmula (Pinyin)': 'Magnesium (Magnésio)',
        'Nome Chinês': 'Měi (镁)',
        'Indicação Principal (MTC)': 'Relaxamento, Sono, Enxaqueca',
        'Dosagem Usual': '300-450mg/dia (Elementar). Formas: Glicinato (Sono/Ansiedade), Citrato (Constipação/Enxaqueca), Treonato (Cognição).',
        'Evidência Científica (Resumo)': 'Evidência forte para prevenção de enxaqueca (citrato/óxido 500mg) e controle de pré-eclâmpsia. Dados promissores mas mistos para sono e ansiedade; benéfico para sensibilidade à insulina.',
        'Aplicações Clínicas Baseadas em Evidências': 'Enxaqueca, Insônia, Diabetes Tipo 2, Hipertensão, Cãibras Musculares.',
        'Nível de Evidência': 'Alta (Enxaqueca/Metabólico)',
        'DOI/Referência Principal': 'https://pubmed.ncbi.nlm.nih.gov/29123461/; https://pubmed.ncbi.nlm.nih.gov/29387426/; https://app.jblearning.com/'
    },
    {
        'Fórmula (Pinyin)': 'Curcumin (Cúrcuma)',
        'Nome Chinês': 'Jiāng Huáng Sù (姜黄素)',
        'Indicação Principal (MTC)': 'Anti-inflamatório, Dor Articular',
        'Dosagem Usual': '500-1500mg/dia. Necessita Piperina ou formulação lipossomal/Meriva para absorção.',
        'Evidência Científica (Resumo)': 'Potente efeito anti-inflamatório comparável a AINEs em osteoartrite, com menos efeitos colaterais. Reduz PCR e melhora marcadores metabólicos em síndrome metabólica.',
        'Aplicações Clínicas Baseadas em Evidências': 'Osteoartrite, Artrite Reumatoide, Síndrome Metabólica, Depressão (adjuvante).',
        'Nível de Evidência': 'Alta (Osteoartrite)',
        'DOI/Referência Principal': 'https://pubmed.ncbi.nlm.nih.gov/27043777/; https://pubmed.ncbi.nlm.nih.gov/27270034/; https://pubmed.ncbi.nlm.nih.gov/30022718/'
    },
    {
        'Fórmula (Pinyin)': 'Omega-3 (EPA/DHA)',
        'Nome Chinês': 'Ouh Měi Jiā 3 (欧米伽-3)',
        'Indicação Principal (MTC)': 'Saúde Cardiovascular, Inflamação',
        'Dosagem Usual': '1-4g/dia. Manutenção: 250-500mg; Hipertrigliceridemia/AR: 2-4g.',
        'Evidência Científica (Resumo)': 'Reduz significativamente triglicerídeos e inflamação (Artrite Reumatoide). Eficácia cardiovascular depende da dose (ex: REDUCE-IT usou 4g). Modesto efeito em ansiedade/depressão.',
        'Aplicações Clínicas Baseadas em Evidências': 'Hipertrigliceridemia, Artrite Reumatoide, Prevenção Cardiovascular Secundária, Saúde Ocular.',
        'Nível de Evidência': 'Alta',
        'DOI/Referência Principal': 'https://pubmed.ncbi.nlm.nih.gov/28551061/; https://pubmed.ncbi.nlm.nih.gov/31567003/; https://doi.org/10.1161/CIR.0000000000000709'
    }
]

df_new = pd.DataFrame(new_data)

# Check for duplicates (optional: based on name)
# Assuming we append, but let's check if they exist first to avoid double entry
df_final = pd.concat([df_existing, df_new], ignore_index=True)

# Drop duplicates if exactly same name (keeping new one usually better if update, but here we append)
df_final = df_final.drop_duplicates(subset=['Fórmula (Pinyin)'], keep='last')

# Save
try:
    df_final.to_excel(file_path, index=False)
    print("Novos suplementos adicionados com sucesso!")
    print(df_final.tail())
except Exception as e:
    print(f"Erro ao salvar: {e}")
