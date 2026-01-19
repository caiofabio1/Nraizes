
import pandas as pd
import os
import re

file_path = "c:\\Users\\caiof\\NRAIZES\\relatorio_produtos (4).xlsx"
output_path = "c:\\Users\\caiof\\NRAIZES\\ncm_mapping.csv"

def normalize_text(text):
    if not isinstance(text, str):
        return str(text)
    return text.upper().strip()

try:
    print(f"Lendo excel: {file_path}")
    df = pd.read_excel(file_path, header=None)
    
    header_idx = -1
    for index, row in df.iterrows():
        # Search for NCM and (Nome or Cód. interno)
        row_str = " ".join(row.astype(str).tolist()).upper()
        if "NCM" in row_str and ("NOME" in row_str or "CÓD. INTERNO" in row_str or "COD. INTERNO" in row_str):
            header_idx = index
            print(f"Header found at index: {header_idx}")
            break
            
    if header_idx != -1:
        # Identificar indices pelo header
        header_values = [str(val).strip() for val in df.iloc[header_idx].values]
        print(f"Header values: {header_values}")
        
        col_idx_map = {}
        for i, h in enumerate(header_values):
            h_upper = h.upper()
            if 'NCM' in h_upper:
                col_idx_map['NCM'] = i
            elif 'DESCRI' in h_upper or 'NOME' in h_upper or 'PRODUTO' in h_upper:
                col_idx_map['Nome'] = i
            elif 'INTERNO' in h_upper: # Prioriza Cod. Interno
                col_idx_map['SKU'] = i
            elif ('CÓD' in h_upper or 'COD' in h_upper) and 'BARRA' not in h_upper and 'SKU' not in col_idx_map:
                 col_idx_map['SKU'] = i

                
        if 'NCM' not in col_idx_map:
            print("Coluna NCM nao encontrada apos header match.")
            exit()

        ncm_col_idx = col_idx_map['NCM']
        nome_col_idx = col_idx_map.get('Nome')
        sku_col_idx = col_idx_map.get('SKU')
        
        print(f"Indices: NCM={ncm_col_idx}, Nome={nome_col_idx}, SKU={sku_col_idx}")

        # Extrair dados
        results = []
        
        # Começar da linha seguinte ao header
        count_ignored = 0
        for i in range(header_idx + 1, len(df)):
            row = df.iloc[i]
            ncm = str(row[ncm_col_idx]).strip()
            
            # Limpar NCM
            if not ncm or ncm.lower() == 'nan' or ncm == '':
                count_ignored += 1
                continue
                
            ncm = ncm.replace('.', '').replace(' ', '')
            if ncm.endswith('.0'):
                ncm = ncm[:-2]
                
            if len(ncm) < 4: # Ignorar lixo
                count_ignored += 1
                continue

            item = {'NCM': ncm}
            
            if nome_col_idx is not None:
                nome = str(row[nome_col_idx]).strip()
                if nome and nome.lower() != 'nan':
                    item['Nome'] = nome
                    
            if sku_col_idx is not None:
                sku = str(row[sku_col_idx]).strip()
                if sku and sku.lower() != 'nan':
                    item['SKU'] = sku
            
            results.append(item)

        print(f"Linhas ignoradas (sem NCM valido): {count_ignored}")

        # Salvar CSV
        result_df = pd.DataFrame(results)
        
        # Garantir colunas
        cols = []
        if 'SKU' in result_df.columns: cols.append('SKU')
        if 'Nome' in result_df.columns: cols.append('Nome')
        cols.append('NCM')
        
        result_df = result_df[cols]
        
        result_df.to_csv(output_path, index=False, sep=';', encoding='utf-8')
        print(f"Extraidos {len(result_df)} NCMs. Salvo em: {output_path}")
        
        if not result_df.empty:
            print("Preview:")
            print(result_df.head(5).to_string())
            
    else:
        print("Header row not found.")

except Exception as e:
    print(f"Error: {e}")
