import os
import requests
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


_DISCORD_TOKEN = _secret("DISCORD_TOKEN")
_BASE = "https://discord.com/api/v10"
_HEADERS = {
    "Authorization": f"Bot {_DISCORD_TOKEN}",
    "User-Agent": "DiscordBot (dashboard, 1.0.0)",
}


def get_guilds() -> list[dict]:
    """Retorna os servidores em que o bot está."""
    resp = requests.get(f"{_BASE}/users/@me/guilds", headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_guild_members(guild_id: int | str) -> list[dict]:
    """Busca todos os membros de um servidor, paginando de 1000 em 1000.

    Requer a intenção privilegiada GUILD_MEMBERS habilitada no bot.
    """
    members: list[dict] = []
    after = None
    while True:
        params = {"limit": 1000}
        if after:
            params["after"] = after
        resp = requests.get(
            f"{_BASE}/guilds/{guild_id}/members",
            headers=_HEADERS,
            params=params,
            timeout=20,
        )
        if resp.status_code == 403:
            raise PermissionError(
                "O bot não tem a intenção GUILD_MEMBERS (Server Members Intent) habilitada. "
                "Ative em: Discord Developer Portal > Bot > Privileged Gateway Intents."
            )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        members.extend(batch)
        if len(batch) < 1000:
            break
        after = batch[-1]["user"]["id"]
    return members


def get_guild_roles(guild_id: int | str) -> list[dict]:
    """Retorna as roles do servidor (id, name, color, position)."""
    resp = requests.get(f"{_BASE}/guilds/{guild_id}/roles", headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()