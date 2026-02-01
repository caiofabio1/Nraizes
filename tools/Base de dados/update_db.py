
import pandas as pd
import numpy as np

file_path = r'c:\Users\caiof\NRAIZES\tools\Base de dados\base_dados_cientifica_produtos.xlsx'

# Load the existing data
df = pd.read_excel(file_path)

# Updates dictionary
# Key: Formula Name, Value: Dict of columns to update
updates = {
    "Qiju Dihuang Wan": {
        "Evidência Científica (Resumo)": "Meta-análises indicam eficácia em Hipertensão (1.45x sup. a drogas convencionais) e Olho Seco (melhora tempo de ruptura do filme lacrimal). Mecanismos: regulação de lipídios, inflamação e via AKT1.",
        "DOI/Referência Principal": "10.1007/s11655-016-2744-2; 10.1016/j.jep.2019.112177",
        "Nível de Evidência": "Moderada-Alta",
        "Aplicações Clínicas Baseadas em Evidências": "Hipertensão (renal/gravidez); Síndrome do Olho Seco; Glaucoma (adjunto); Retinopatia diabética (suporte)"
    },
    "Guifu Dihuang Jiaonang": {
        "Evidência Científica (Resumo)": "Meta-análise (14 estudos, 1586 part.): seguro para Diabetes Tipo 2; combinado com hipoglicemiantes reduz HbA1c e glicemia jejum. Eficaz em hipersecreção de muco na DPOC (via supressão Muc5ac).",
        "DOI/Referência Principal": "10.1155/2013/846396; 10.3389/fphar.2020.00539",
        "Nível de Evidência": "Moderada",
        "Aplicações Clínicas Baseadas em Evidências": "Diabetes Tipo 2 (adjunto); DPOC (hipersecreção muco); Hipotireoidismo (Yang renal def.); Síndrome nefrótica (suporte)"
    },
    "Qinggan Lidan Jiaonang": {
        "Evidência Científica (Resumo)": "Estudos pré-clínicos/clínicos sugerem benefício em colecistite e icterícia neonatal (reduz tempo regressão, via fórmulas correlatas). Mecanismo: regulação NRF2/KEAP1 e transporte lipídico em lesão hepática alcoólica.",
        "DOI/Referência Principal": "10.3389/fphar.2021.686036; 10.12659/MSM.928646",
        "Nível de Evidência": "Baixa-Moderada",
        "Aplicações Clínicas Baseadas em Evidências": "Colecistite; Icterícia neonatal (suporte); Doença hepática alcoólica (potencial); Colangite biliar primária (adjunto)"
    },
    "Qufeng Zhitong Pian": {
        "Evidência Científica (Resumo)": "Ensaios clínicos e meta-análises em rede suportam uso em Artrite Reumatoide (com metotrexato) e Hérnia de Disco Lombar (melhora escores JOA). Mecanismo: inibição via TLR4/NF-κB em dor neuropática.",
        "DOI/Referência Principal": "10.1186/s13063-020-04987-2; 10.1016/j.jep.2021.114382",
        "Nível de Evidência": "Moderada",
        "Aplicações Clínicas Baseadas em Evidências": "Artrite Reumatoide (Frio-Umidade); Hérnia de Disco Lombar; Osteoartrite; Dor Neuropática"
    },
    "Renshen Shouwu Jiaonang": {
        "Evidência Científica (Resumo)": "Polygonum multiflorum (He Shou Wu) tem efeitos anti-envelhecimento (neuroproteção, mitocôndria) e potencial em crescimento capilar (estudos animais/tradicional). Atenção: monitorar função hepática.",
        "DOI/Referência Principal": "10.1016/j.jep.2015.01.019; 10.3390/molecules21010041",
        "Nível de Evidência": "Baixa-Moderada",
        "Aplicações Clínicas Baseadas em Evidências": "Alopecia/Queda de cabelo; Anti-envelhecimento (tônico geral); Fadiga crônica; Suporte cognitivo (neuroproteção)"
    },
    "Xiang Sha Yang Wei Wan": {
        "Evidência Científica (Resumo)": "Forte evidência (Meta-análise: 18 RCTs, 1720 pct) para Gastrite Crônica (atrófica/superficial): taxa efetiva superior a med. ocidental (92% vs 78%), reduz Hp. Melhora sintomas em Dispepsia Funcional (ansiedade/depressão).",
        "DOI/Referência Principal": "10.1186/s12906-021-03223-z; 10.1155/2019/3231761",
        "Nível de Evidência": "Alta",
        "Aplicações Clínicas Baseadas em Evidências": "Gastrite Crônica (Hp associada); Dispepsia Funcional; Refluxo/DRGE; Úlcera péptica (cicatrização)"
    },
    "Fu Fang Yi Mu Cao Jiao Nang": {
        "Evidência Científica (Resumo)": "Meta-análises (literatura chinesa/global) indicam benefício em Dismenorreia Primária (especialmente com Vit B6 e acupuntura). Estudos animais confirmam redução de contratilidade uterina e inflamação.",
        "DOI/Referência Principal": "CNKI: 10.3969/j.issn.1005-2216.2016.09.006; 10.1002/14651858.CD005288",
        "Nível de Evidência": "Moderada",
        "Aplicações Clínicas Baseadas em Evidências": "Dismenorreia Primária; Recuperação Pós-parto (involução uterina); Hemorragia uterina funcional (estase)"
    }
}

# Apply updates
for index, row in df.iterrows():
    formula_name = row['Fórmula (Pinyin)']
    if formula_name in updates:
        print(f"Updating {formula_name}...")
        for col, value in updates[formula_name].items():
            df.at[index, col] = value

# Save the updated file
df.to_excel(file_path, index=False)
print("Database updated successfully!")
