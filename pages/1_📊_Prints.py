# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd

from lib.db import load_prints

st.set_page_config(page_title="Prints — Análise", page_icon="📊", layout="wide")

st.title("🖼️ Análise de Prints")
st.divider()


@st.cache_data(ttl=60, show_spinner="Carregando dados do Supabase...")
def _cached_prints() -> pd.DataFrame:
    return load_prints()


df = _cached_prints()

if df.empty:
    st.info("Nenhuma print encontrada no banco.")
    st.stop()

# ----------------------------------------------------------------------
# Filtros
# ----------------------------------------------------------------------
status_opts = ["Todos"] + sorted(df["status"].dropna().unique().tolist())
tipo_opts = ["Todos"] + sorted(df["tipo"].dropna().unique().tolist())
min_date = df["created_at"].min()
max_date = df["created_at"].max()

with st.sidebar:
    st.subheader("🔍 Filtros")
    status = st.multiselect("Status", status_opts, default=["Todos"])
    tipo = st.multiselect("Tipo", tipo_opts, default=["Todos"])
    username = st.text_input("Buscar por usuário", "").strip().lower()
    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.date_input(
            "Período",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )
    else:
        date_range = None

# ----------------------------------------------------------------------
# Aplicar filtros
# ----------------------------------------------------------------------
def apply_filters(data: pd.DataFrame) -> pd.DataFrame:
    out = data.copy()
    if status and "Todos" not in status:
        out = out[out["status"].isin(status)]
    if tipo and "Todos" not in tipo:
        out = out[out["tipo"].isin(tipo)]
    if username:
        out = out[out["username"].astype(str).str.lower().str.contains(username, na=False)]
    if date_range and isinstance(date_range, tuple) and len(date_range) == 2:
        start = pd.Timestamp(date_range[0], tz="UTC")
        end = pd.Timestamp(date_range[1], tz="UTC") + pd.Timedelta(days=1)
        out = out[(out["created_at"] >= start) & (out["created_at"] < end)]
    return out


df_filtrado = apply_filters(df)

# ----------------------------------------------------------------------
# KPIs
# ----------------------------------------------------------------------
total = len(df_filtrado)
aprovadas = int((df_filtrado["status"] == "aprovado").sum())
recusadas = int((df_filtrado["status"] == "recusado").sum())
pendentes = int((df_filtrado["status"] == "pendente").sum())
taxa = (aprovadas / total * 100) if total else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total", total)
k2.metric("✅ Aprovadas", aprovadas)
k3.metric("❌ Recusadas", recusadas)
k4.metric("⏳ Pendentes", pendentes)
k5.metric("Taxa de aprovação", f"{taxa:.1f}%")

st.divider()

# ----------------------------------------------------------------------
# Gráficos
# ----------------------------------------------------------------------
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Prints por status")
    cont_status = df_filtrado.groupby("status_label").size().reset_index(name="count")
    if not cont_status.empty:
        st.bar_chart(cont_status.set_index("status_label"))

with col_b:
    st.subheader("Prints por tipo")
    cont_tipo = df_filtrado.groupby("tipo_label").size().reset_index(name="count")
    if not cont_tipo.empty:
        st.bar_chart(cont_tipo.set_index("tipo_label"))

st.subheader("📈 Evolução ao longo do tempo")
if not df_filtrado.empty:
    evol = df_filtrado.set_index("created_at").resample("D").size().rename("count")
    if not evol.empty:
        st.line_chart(evol)

st.divider()

# ----------------------------------------------------------------------
# Tabela filtrada
# ----------------------------------------------------------------------
st.subheader("📋 Tabela de prints")

tabela = df_filtrado[["id", "username", "tipo_label", "status_label", "reviewed_by_mention", "motivo_recusa", "created_at"]].copy()
tabela.columns = ["ID", "Usuário", "Tipo", "Status", "Analisado por", "Motivo da recusa", "Enviada em"]
tabela["Enviada em"] = tabela["Enviada em"].dt.strftime("%d/%m/%Y %H:%M")

st.dataframe(tabela, use_container_width=True, hide_index=True)

st.download_button(
    "⬇️ Baixar CSV",
    data=tabela.to_csv(index=False).encode("utf-8"),
    file_name="prints.csv",
    mime="text/csv",
)

st.divider()

# ----------------------------------------------------------------------
# Detalhe da print
# ----------------------------------------------------------------------
st.subheader("🔍 Detalhe de uma print")

if not df_filtrado.empty:
    selecao = st.selectbox(
        "Escolha uma print para ver o detalhe:",
        options=df_filtrado["id"].tolist(),
        format_func=lambda i: (
            f"#{i} — {df_filtrado.loc[df_filtrado['id'] == i, 'username'].iloc[0]} "
            f"({df_filtrado.loc[df_filtrado['id'] == i, 'status_label'].iloc[0]})"
        ),
    )
    row = df_filtrado[df_filtrado["id"] == selecao].iloc[0]

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(
            f"**ID:** `{row['id']}`  \n"
            f"**Usuário:** {row['username']} (`{row['user_id']}`)  \n"
            f"**Tipo:** {row['tipo_label']}  \n"
            f"**Status:** {row['status_label']}"
        )
    with c2:
        st.markdown(
            f"**Enviada em:** {row['created_at'].strftime('%d/%m/%Y %H:%M')}  \n"
            f"**Analisado por:** {row['reviewed_by_mention']}  \n"
            f"**Motivo da recusa:** {row.get('motivo_recusa') or '—'}  \n"
            f"[Abrir imagem]({row['image_url']})"
        )

    if row.get("image_url"):
        st.image(row["image_url"], use_container_width=True)
else:
    st.info("Nenhuma print para exibir com os filtros selecionados.")
