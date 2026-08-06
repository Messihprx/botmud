# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px

from lib.db import load_recruitments

st.set_page_config(page_title="Recrutamento", page_icon="🤝", layout="wide")

st.title("🤝 Recrutamento — Painel de Análise")
st.divider()


@st.cache_data(ttl=60, show_spinner="Carregando recrutamentos...")
def _recruitments() -> pd.DataFrame:
    return load_recruitments()


df = _recruitments()

if df.empty:
    st.info("Nenhum recrutamento encontrado no banco.")
    st.stop()

# ----------------------------------------------------------------------
# Filtros
# ----------------------------------------------------------------------
generos = ["Todos"] + sorted(df["gender"].dropna().unique().tolist())
plataformas = ["Todos"] + sorted(df["platform"].dropna().unique().tolist())
recrutadores = ["Todos"] + sorted(df["recruiter_name"].dropna().unique().tolist())
min_date = df["created_at"].min()
max_date = df["created_at"].max()

with st.sidebar:
    st.subheader("🔍 Filtros")
    genero = st.multiselect("Gênero", generos, default=["Todos"])
    plataforma = st.multiselect("Plataforma", plataformas, default=["Todos"])
    recrutador = st.multiselect("Recrutador", recrutadores, default=["Todos"])
    busca = st.text_input("Buscar recrutado (nome/nick)", "").strip().lower()
    busca_id = st.text_input("Buscar recrutado por ID", "").strip()
    if pd.notna(min_date) and pd.notna(max_date):
        periodo = st.date_input(
            "Período",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )
    else:
        periodo = None

# ----------------------------------------------------------------------
# Aplicar filtros
# ----------------------------------------------------------------------
def aplicar(data: pd.DataFrame) -> pd.DataFrame:
    out = data.copy()
    if genero and "Todos" not in genero:
        out = out[out["gender"].isin(genero)]
    if plataforma and "Todos" not in plataforma:
        out = out[out["platform"].isin(plataforma)]
    if recrutador and "Todos" not in recrutador:
        out = out[out["recruiter_name"].isin(recrutador)]
    if busca:
        out = out[
            out["recruit_roblox_name"].astype(str).str.lower().str.contains(busca, na=False)
            | out["recruit_roblox_nick"].astype(str).str.lower().str.contains(busca, na=False)
            | out["recruit_discord_nick"].astype(str).str.lower().str.contains(busca, na=False)
        ]
    if busca_id:
        out = out[out["recruit_id"].astype(str).str.contains(busca_id, na=False)]
    if periodo and isinstance(periodo, tuple) and len(periodo) == 2:
        start = pd.Timestamp(periodo[0], tz="UTC")
        end = pd.Timestamp(periodo[1], tz="UTC") + pd.Timedelta(days=1)
        out = out[(out["created_at"] >= start) & (out["created_at"] < end)]
    return out


df_f = aplicar(df)

# ----------------------------------------------------------------------
# KPIs
# ----------------------------------------------------------------------
total = len(df_f)
saidas = int(df_f["saidas_count"].fillna(0).astype(int).sum()) if "saidas_count" in df_f else 0
ativos = max(total - saidas, 0)
generos_cnt = df_f["gender"].value_counts()
plataformas_cnt = df_f["platform"].value_counts()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total recrutados", total)
k2.metric("Saídas", saidas)
k3.metric("Ativos", ativos)
k4.metric("Gênero predominante", generos_cnt.index[0] if not generos_cnt.empty else "—")

st.divider()

# ----------------------------------------------------------------------
# Gráficos interativos
# ----------------------------------------------------------------------
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🍩 Por gênero")
    if not generos_cnt.empty:
        g = generos_cnt.reset_index()
        g.columns = ["Gênero", "Contagem"]
        fig = px.pie(g, names="Gênero", values="Contagem", hole=0.4)
        fig.update_traces(textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("🍩 Por plataforma")
    if not plataformas_cnt.empty:
        p = plataformas_cnt.reset_index()
        p.columns = ["Plataforma", "Contagem"]
        fig = px.pie(p, names="Plataforma", values="Contagem", hole=0.4)
        fig.update_traces(textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True)

col_c, col_d = st.columns(2)

with col_c:
    st.subheader("📊 Por recrutador")
    rec = df_f.groupby("recruiter_name").size().sort_values(ascending=True)
    if not rec.empty:
        rdf = rec.reset_index()
        rdf.columns = ["Recrutador", "Contagem"]
        fig = px.bar(rdf, x="Contagem", y="Recrutador", orientation="h")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

with col_d:
    st.subheader("⏳ Evolução mensal")
    if not df_f.empty:
        evol = df_f.set_index("created_at").resample("ME").size().rename("Recrutados")
        if not evol.empty:
            fig = px.line(evol, labels={"created_at": "Mês", "Recrutados": "Recrutados"})
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------
# Tabela
# ----------------------------------------------------------------------
st.subheader("📋 Recrutamentos filtrados")

cols = ["recruit_id", "recruiter_name", "recruiter_id", "recruit_roblox_name", "recruit_roblox_nick", "recruit_age", "gender", "platform", "saidas_count", "created_at"]
tabela = df_f[cols].copy() if all(c in df_f for c in cols) else df_f.copy()
tabela = tabela.rename(columns={
    "recruit_id": "ID Recrutado",
    "recruiter_name": "Recrutador",
    "recruiter_id": "ID Recrutador",
    "recruit_roblox_name": "Nome",
    "recruit_roblox_nick": "Nick",
    "recruit_age": "Idade",
    "gender": "Gênero",
    "platform": "Plataforma",
    "saidas_count": "Saídas",
    "created_at": "Quando",
})
tabela["Quando"] = pd.to_datetime(tabela["Quando"], utc=True).dt.strftime("%d/%m/%Y")
st.dataframe(tabela, use_container_width=True, hide_index=True)

st.download_button(
    "⬇️ Baixar CSV",
    data=tabela.to_csv(index=False).encode("utf-8"),
    file_name="recrutamentos.csv",
    mime="text/csv",
)