import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


def _secret(key: str, default: str = "") -> str:
    """Lê variável do ambiente, com fallback para st.secrets (Streamlit Cloud)."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


_SUPABASE_URL = _secret("SUPABASE_URL")
_SUPABASE_KEY = _secret("SUPABASE_KEY")


def get_client():
    return create_client(_SUPABASE_URL or "", _SUPABASE_KEY or "")


STATUS_LABEL = {
    "pendente": "⏳ Pendente",
    "aprovado": "✅ Aprovado",
    "recusado": "❌ Recusado",
}
TIPO_LABEL = {"elo": "Por Elo", "gema": "Por Gema"}


def load_prints() -> pd.DataFrame:
    """Carrega todas as submissões de prints e normaliza as colunas úteis."""
    client = get_client()
    res = client.table("print_submissions").select("*").order("id", desc=False).execute()
    data = res.data or []
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    if df.empty:
        return df

    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df["status_label"] = df["status"].map(STATUS_LABEL).fillna(df["status"])
    df["tipo_label"] = df["tipo"].map(TIPO_LABEL).fillna(df["tipo"])

    for col in ["user_id", "reviewed_by"]:
        df[col] = df[col].astype(str)
    df["reviewed_by_mention"] = df["reviewed_by"].apply(
        lambda v: f"<@{v}>" if v and v != "None" else "—"
    )
    return df


def load_recruitments() -> pd.DataFrame:
    """Carrega todos os recrutamentos e normaliza colunas úteis."""
    client = get_client()
    res = client.table("recruitments").select("*").order("created_at", desc=False).execute()
    data = res.data or []
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    if df.empty:
        return df

    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df["recruiter_id"] = df["recruiter_id"].astype(str)
    df["recruit_id"] = df["recruit_id"].astype(str)

    # Nome do recrutador: usa a coluna da ficha ou busca na tabela de recrutadores
    try:
        recr = client.table("recruiters").select("recruiter_id", "recruiter_name").execute()
        mapa_nomes = {str(r["recruiter_id"]): r.get("recruiter_name") for r in (recr.data or [])}
    except Exception:
        mapa_nomes = {}

    def nome_recrutador(rid):
        return mapa_nomes.get(str(rid)) or "Sem registro"

    df["recruiter_name"] = df["recruiter_name"].astype(str).replace({"None": "", "nan": ""}).fillna("") if "recruiter_name" in df else ""
    df["recruiter_name"] = df.apply(
        lambda row: row["recruiter_name"] if row["recruiter_name"] else nome_recrutador(row["recruiter_id"]),
        axis=1,
    )

    for col in ["gender", "platform", "recruit_age"]:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("Não informado")
            df[col] = df[col].replace({"": "Não informado", "None": "Não informado"})

    return df