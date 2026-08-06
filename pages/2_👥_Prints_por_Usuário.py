# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd

from lib.db import get_client
from lib import discord as discord_api

st.set_page_config(page_title="Membros x Prints", page_icon="👥", layout="wide")

st.title("👥 Comparação: Membros do Servidor x Prints")
st.divider()


@st.cache_data(ttl=300, show_spinner="Buscando servidores...")
def _guilds():
    return discord_api.get_guilds()


@st.cache_data(ttl=300, show_spinner="Buscando membros...")
def _members(guild_id):
    return discord_api.get_guild_members(guild_id)


@st.cache_data(ttl=300, show_spinner="Buscando cargos...")
def _roles(guild_id):
    return discord_api.get_guild_roles(guild_id)


@st.cache_data(ttl=60, show_spinner="Carregando prints...")
def _prints():
    client = get_client()
    res = client.table("print_submissions").select("*").execute()
    return pd.DataFrame(res.data or [])


def member_name(item: dict) -> str:
    """Retorna o nome de exibição do membro."""
    return (
        item.get("nick")
        or item.get("user", {}).get("global_name")
        or item.get("user", {}).get("username")
        or "Sem nome"
    )


# ----------------------------------------------------------------------
# Escolha do servidor
# ----------------------------------------------------------------------
try:
    guilds = _guilds()
except Exception as e:
    st.error(f"Erro ao buscar servidores: {e}")
    st.stop()

if not guilds:
    st.info("O bot não está em nenhum servidor.")
    st.stop()

guild_opts = {f"{g['name']} ({g['id']})": g["id"] for g in guilds}
guild_name = st.selectbox("Servidor", list(guild_opts.keys()))
guild_id = guild_opts[guild_name]

# ----------------------------------------------------------------------
# Cargos
# ----------------------------------------------------------------------
try:
    roles = _roles(guild_id)
except Exception as e:
    st.error(f"Erro ao buscar cargos: {e}")
    st.stop()

roles_opts = {f"{r['name']} ({r['id']})": r["id"] for r in roles if r["name"] != "@everyone"}
roles_opts = dict(sorted(roles_opts.items()))
sel_role = st.selectbox(
    "Cargo de referência (limita a análise a quem possui esse cargo)",
    ["— (todos os membros)"] + list(roles_opts.keys()),
)
target_role_id = roles_opts.get(sel_role)

# ----------------------------------------------------------------------
# Membros
# ----------------------------------------------------------------------
try:
    members = _members(guild_id)
except PermissionError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(f"Erro ao buscar membros: {e}")
    st.stop()

# ----------------------------------------------------------------------
# Prints
# ----------------------------------------------------------------------
df_prints = _prints()
if not df_prints.empty and "user_id" in df_prints.columns:
    df_prints["user_id"] = df_prints["user_id"].astype(str)
    enviou_ids = set(df_prints["user_id"].unique())
    qtde = df_prints["user_id"].value_counts().to_dict()
else:
    enviou_ids = set()
    qtde = {}

# ----------------------------------------------------------------------
# Monta dataframe de membros
# ----------------------------------------------------------------------
membros = [
    {
        "user_id": str(m["user"]["id"]),
        "nome": member_name(m),
        "roles": m.get("roles", []),
    }
    for m in members
]
df_membros = pd.DataFrame(membros)

if target_role_id:
    df_membros = df_membros[df_membros["roles"].apply(lambda rl: target_role_id in rl)]

if df_membros.empty:
    st.info("Nenhum membro encontrado com o cargo selecionado.")
    st.stop()

df_membros["enviou"] = df_membros["user_id"].isin(enviou_ids)
df_membros["qtde_prints"] = df_membros["user_id"].map(qtde).fillna(0).astype(int)

nao_enviaram = df_membros[~df_membros["enviou"]]
enviaram = df_membros[df_membros["enviou"]]

# ----------------------------------------------------------------------
# KPIs
# ----------------------------------------------------------------------
total_mem = len(df_membros)
total_env = len(enviaram)
total_n_env = len(nao_enviaram)
pct_env = (total_env / total_mem * 100) if total_mem else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total de membros", total_mem)
k2.metric("✅ Enviaram print", total_env)
k3.metric("❌ Não enviaram", total_n_env)
k4.metric("Cobertura", f"{pct_env:.1f}%")

st.divider()

# ----------------------------------------------------------------------
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("❌ Membros que NÃO enviaram")
    tabela_n = nao_enviaram[["nome", "user_id"]].copy()
    tabela_n.columns = ["Nome", "ID"]
    st.dataframe(tabela_n, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Baixar quem não enviou (CSV)",
        data=tabela_n.to_csv(index=False).encode("utf-8"),
        file_name="nao_enviaram.csv",
        mime="text/csv",
    )

with col_b:
    st.subheader("✅ Membros que enviaram")
    tabela_e = enviaram.sort_values("qtde_prints", ascending=False)[["nome", "user_id", "qtde_prints"]].copy()
    tabela_e.columns = ["Nome", "ID", "Prints"]
    st.dataframe(tabela_e, use_container_width=True, hide_index=True)