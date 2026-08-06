import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_KEY")


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