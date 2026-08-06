import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

DONO_ID = 644667253324775454
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://botmud-jdtjhqn2gwzwpglrbetjhw.streamlit.app/")


def e_admin_ou_dono():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == DONO_ID:
            return True
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


class PainelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="painel", description="Gera o link de acesso ao painel de dados")
    @e_admin_ou_dono()
    async def painel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📊 Painel de Dados",
            description=(
                f"**Acesse o painel com os dados do servidor:**\n\n"
                f"🔗 {DASHBOARD_URL}\n\n"
                f"*O painel é hospedado separadamente no Streamlit Cloud e contém "
                f"os dashboards de Prints, Membros e Recrutamento.*"
            ),
            color=0x3498db,
        )
        embed.set_footer(text="Comando restrito a administradores")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(PainelCog(bot))
