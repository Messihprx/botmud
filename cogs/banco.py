import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import io
import csv

class ExtratoView(discord.ui.View):
    def __init__(self, logs, pagina_atual=0):
        super().__init__(timeout=60)
        self.logs = logs
        self.pagina_atual = pagina_atual
        self.itens_por_pag = 10

    def gerar_embed(self):
        start = self.pagina_atual * self.itens_por_pag
        end = start + self.itens_por_pag
        chunk = self.logs[start:end]

        texto = ""
        for log in chunk:
            emoji = "🟢" if log['tipo'] == "ADICIONAR" else "🔴"
            # Formata data removendo o 'Z' ou offsets para o strftime funcionar bem
            dt = datetime.fromisoformat(log['data'].replace('Z', '+00:00')) - timedelta(hours=3)
            data_f = dt.strftime("%d/%m %H:%M")
            texto += f"{emoji} `{data_f}` | **{log['quantidade']:,}M** | {log['username']}\n└ *{log['motivo']}*\n"

        total_paginas = (len(self.logs) - 1) // self.itens_por_pag + 1
        embed = discord.Embed(title="📋 EXTRATO BANCÁRIO", description=texto, color=0x3498db)
        embed.set_footer(text=f"Página {self.pagina_atual + 1} de {total_paginas}")
        return embed

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.gray)
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.pagina_atual > 0:
            self.pagina_atual -= 1
            await interaction.response.edit_message(embed=self.gerar_embed(), view=self)
        else:
            await interaction.response.send_message("Você já está na primeira página.", ephemeral=True)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.gray)
    async def proximo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.pagina_atual + 1) * self.itens_por_pag < len(self.logs):
            self.pagina_atual += 1
            await interaction.response.edit_message(embed=self.gerar_embed(), view=self)
        else:
            await interaction.response.send_message("Você já está na última página.", ephemeral=True)

class Banco(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.whitelist = [644667253324775454, 433385659760377856, 268690881551269888]

    def eh_autorizado(self, interaction: discord.Interaction):
        return interaction.user.id in self.whitelist

    @app_commands.command(name="banco", description="Mostra o saldo atual de gemas")
    async def banco(self, interaction: discord.Interaction):
        res = self.bot.supabase.table("bank_balance").select("gemas").eq("id", "global").single().execute()
        gemas = res.data['gemas'] if res.data else 0

        # Pega o log mais recente (qualquer tipo) para mostrar a data da última ação
        last_log = self.bot.supabase.table("bank_logs").select("*").order("id", desc=True).limit(1).execute()
        
        status_recente = "Nenhuma movimentação registrada."
        if last_log.data:
            log = last_log.data[0]
            dt = datetime.fromisoformat(log['data'].replace('Z', '+00:00')) - timedelta(hours=3)
            data_f = dt.strftime("%d/%m às %H:%M")
            emoji = "📉 Retirada" if log['tipo'] == "RETIRAR" else "📈 Adição"
            
            status_recente = (
                f"{emoji}: **{log['quantidade']:,}M** por **{log['username']}**\n"
                f"📅 Data: `{data_f}`\n"
                f"📝 Motivo: *{log['motivo']}*"
            )

        embed = discord.Embed(title="💎 BANCO DE GEMAS", color=0x00ff7f)
        embed.add_field(name="💰 Saldo Atual", value=f"**{gemas:,}M** Gemas", inline=False)
        embed.add_field(name="🔄 Última Movimentação", value=status_recente, inline=False)
        embed.set_footer(text=f"Consultado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="adicionar", description="Adiciona gemas ao banco (em M)")
    async def adicionar(self, interaction: discord.Interaction, quantidade: int):
        if not self.eh_autorizado(interaction):
            return await interaction.response.send_message("❌ Acesso negado.", ephemeral=True)

        res = self.bot.supabase.table("bank_balance").select("gemas").eq("id", "global").single().execute()
        novo_total = (res.data['gemas'] if res.data else 0) + quantidade
        self.bot.supabase.table("bank_balance").update({"gemas": novo_total}).eq("id", "global").execute()

        self.bot.supabase.table("bank_logs").insert({
            "user_id": str(interaction.user.id),
            "username": interaction.user.display_name,
            "quantidade": quantidade,
            "tipo": "ADICIONAR",
            "motivo": "Depósito Bancário"
        }).execute()

        await interaction.response.send_message(f"✅ **{quantidade:,}M** gemas adicionadas! Novo saldo: **{novo_total:,}M**")

    @app_commands.command(name="retirar", description="Retira gemas do banco")
    async def retirar(self, interaction: discord.Interaction, quantidade: int, motivo: str):
        if not self.eh_autorizado(interaction):
            return await interaction.response.send_message("❌ Acesso negado.", ephemeral=True)

        res = self.bot.supabase.table("bank_balance").select("gemas").eq("id", "global").single().execute()
        saldo_atual = res.data['gemas'] if res.data else 0

        if quantidade > saldo_atual:
            return await interaction.response.send_message("❌ Saldo insuficiente!", ephemeral=True)

        novo_total = saldo_atual - quantidade
        self.bot.supabase.table("bank_balance").update({"gemas": novo_total}).eq("id", "global").execute()

        self.bot.supabase.table("bank_logs").insert({
            "user_id": str(interaction.user.id),
            "username": interaction.user.display_name,
            "quantidade": quantidade,
            "tipo": "RETIRAR",
            "motivo": motivo
        }).execute()

        await interaction.response.send_message(f"📤 **{quantidade:,}M** gemas retiradas!\nMotivo: {motivo}")

    @app_commands.command(name="extrato", description="Mostra o histórico de transações com páginas")
    async def extrato(self, interaction: discord.Interaction):
        res = self.bot.supabase.table("bank_logs").select("*").order("id", desc=True).execute()
        if not res.data:
            return await interaction.response.send_message("O extrato está vazio.")
        
        view = ExtratoView(res.data)
        # Na primeira chamada, usamos interaction.response.send_message
        await interaction.response.send_message(embed=view.gerar_embed(), view=view)

async def setup(bot):
    await bot.add_cog(Banco(bot))