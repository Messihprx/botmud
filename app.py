import streamlit as st

st.set_page_config(
    page_title="Painel de Dados",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Painel de Dados")
st.markdown(
    "Dashboard central do bot. Selecione uma análise no menu lateral.\n\n"
    "**Dashboards disponíveis:**\n"
    "- 📊 **Prints** — análise das submissões de prints (KPIs, gráficos e tabela filtrada)."
)

st.divider()
st.caption("Feito com Streamlit · dados do Supabase")
