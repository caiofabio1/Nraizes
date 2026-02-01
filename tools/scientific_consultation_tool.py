
import streamlit as st
import pandas as pd
import os

# Set page config
st.set_page_config(
    page_title="Consulta Científica - Fórmulas MTC",
    page_icon="🌿",
    layout="wide"
)

# Title and Description
st.title("🌿 Ferramenta de Consulta Científica - Suplementos MTC")
st.markdown("""
Esta ferramenta permite consultar a base de dados de fórmulas e suplementos da Medicina Tradicional Chinesa,
com foco em **evidências científicas modernas** (Ensaios Clínicos, Meta-análises).
""")

# Load Data
@st.cache_data
def load_data():
    file_path = os.path.join(os.path.dirname(__file__), 'Base de dados', 'base_dados_cientifica_produtos.xlsx')
    try:
        df = pd.read_excel(file_path)
        # Ensure string columns are strings
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].fillna('')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar a base de dados: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # Sidebar Filters
    st.sidebar.header("Filtros")
    # Search
    search_term = st.sidebar.text_input("Buscar por Nome (Chinês/Pinyin) ou Indicação", "")
    
    # Filter Logic
    if search_term:
        mask = (
            df['Fórmula (Pinyin)'].str.contains(search_term, case=False, na=False) | 
            df['Nome Chinês'].str.contains(search_term, case=False, na=False) |
            df['Indicação Principal (MTC)'].str.contains(search_term, case=False, na=False) |
            df['Aplicações Clínicas Baseadas em Evidências'].str.contains(search_term, case=False, na=False)
        )
        filtered_df = df[mask]
    else:
        filtered_df = df

    # Display Results
    st.write(f"Encontrados {len(filtered_df)} resultados.")

    for index, row in filtered_df.iterrows():
        # Relevance Color based on Evidence Level
        evidence_level = str(row.get('Nível de Evidência', 'Baixa')).lower()
        if 'alta' in evidence_level:
            color = "green"
        elif 'moderada' in evidence_level:
            color = "orange"
        else:
            color = "gray"

        with st.expander(f"💊 {row['Fórmula (Pinyin)']} ({row['Nome Chinês']}) - Nível de Evidência: :{color}[{row['Nível de Evidência']}]"):
            c1, c2 = st.columns([1, 2])
            
            with c1:
                st.markdown("**Indicação Principal (MTC):**")
                st.info(row['Indicação Principal (MTC)'])
                st.markdown("**Dosagem Usual:**")
                st.text(row['Dosagem Usual'])
            
            with c2:
                st.markdown("### 🔬 Evidência Científica")
                st.markdown(f"> {row['Evidência Científica (Resumo)']}")
                
                st.markdown("**Aplicações Clínicas:**")
                st.write(row['Aplicações Clínicas Baseadas em Evidências'])
                
                if row['DOI/Referência Principal']:
                    st.markdown("**Referências (DOI/Link):**")
                    # Handle multiple links if separated by ;
                    links = str(row['DOI/Referência Principal']).split(';')
                    for link in links:
                        link = link.strip()
                        if link.startswith('http') or link.startswith('www'):
                            st.markdown(f"- [{link}]({link})")
                        elif '10.' in link: # Simple DOI check
                             st.markdown(f"- [DOI: {link}](https://doi.org/{link})")
                        else:
                            st.text(f"- {link}")

else:
    st.warning("Nenhum dado encontrado.")

# Footer
st.sidebar.markdown("---")
st.sidebar.warning("⚠️ **AVISO IMPORTANTE**:\\n\\nAs informações aqui contidas têm caráter estritamente educativo e não substituem o aconselhamento médico.\\n\\n**Consulte sempre um profissional de saúde qualificado antes de iniciar qualquer tratamento.**")
st.sidebar.caption("Desenvolvido para fins educativos com base em evidências científicas.")
