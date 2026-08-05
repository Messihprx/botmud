import discord
from discord.ext import commands
from changelog import VERSION, CHANGELOGS
from datetime import datetime, time
import math

# --- CLASSE PARA OS BOTÕES DE NAVEGAÇÃO ---
class ChangelogView(discord.ui.View):
    def __init__(self, changelogs, per_page=3):
        super().__init__(timeout=60) # Botões param de funcionar após 60s
        self.changelogs = changelogs
        self.per_page = per_page
        self.current_page = 0
        self.max_pages = math.ceil(len(changelogs) / per_page)

    def create_embed(self):
        """Cria o embed da página atual"""
        start = self.current_page * self.per_page
        end = start + self.per_page
        items = self.changelogs[start:end]

        embed = discord.Embed(
            title="📜 Histórico de Atualizações (Changelog)",
            description=f"Acompanhe a evolução do bot. Versão atual: **{VERSION}**",
            color=0x3498db
        )

        for item in items:
            changes_text = "\n".join([f"• {change}" for change in item["changes"]])
            embed.add_field(
                name=f"{item['emoji']} Versão {item['version']}",
                value=changes_text,
                inline=False
            )

        embed.set_footer(text=f"Página {self.current_page + 1} de {self.max_pages}")
        return embed

    @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.gray)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.send_message("Você já está na primeira página!", ephemeral=True)

    @discord.ui.button(label="Próximo ➡️", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.send_message("Você já está na última página!", ephemeral=True)

# --- CLASSE UTILITY ---
class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Menu de Ajuda em formato Embed"""
        
        from datetime import datetime
        
        embed = discord.Embed(
            title="Menu de Ajuda - Bot de Tradução",
            description="Bem-vindo! Este bot traduz suas mensagens automaticamente no canal.\n**Prefixo:** `=`",
            color=0x3498db,
            timestamp=datetime.now()
        )

        embed.add_field(
            name="🛠️ Configuração (ADMs)",
            value=(
                "`=activate` - Ativa a tradução neste canal.\n"
                "`=deactivate` - Desativa a tradução neste canal.\n"
                "`=setlang <idioma> <@membro>` - Define o idioma de um membro específico."
            ),
            inline=False
        )

        embed.add_field(
            name="🌍 Tradução",
            value=(
                "`=setlang <idioma>` - Define seu idioma (ex: =setlang pt).\n"
                "`=setlang off` - Desativa sua tradução automática.\n"
                "`=languages` - Lista os idiomas principais suportados.\n"
                "`=translate <idioma>` - Traduz respondendo a uma mensagem.\n"
                "`=translate <idioma> <texto>` - Traduz um texto direto.\n"
                "`=addlang <idioma>` - Adiciona um idioma à sua lista.\n"
                "`=removelang <idioma>` - Remove um idioma da sua lista.\n"
                "`=langs` - Mostra todos os idiomas disponíveis para tradução. (CUIDADO POIS ENVIA MUITAS EMBEDS, HÁ MUITOS IDIOMAS)."
            ),
            inline=False
        )

        embed.add_field(
            name="✨ Funcionalidades",
            value=(
                "`=top` - Exibe o ranking dos usuários com mais traduções.\n"
                "`=perfil` - Exibe seu perfil de tradutor.\n"
                "`=resumo` - Gera um resumo ácido das últimas mensagens.\n"
                "`=insulto @membro` - Gera um insulto criativo."
            ),
            inline=False
        )

        embed.add_field(
            name="📊 Informações & Novidades",
            value=(
                "`=botinfo` - Veja estatísticas globais e latência.\n"
                "`=changelog` - Confira o histórico de atualizações.\n"
                "`=status` - Verifique se a tradução está ativa neste canal.\n"
                "`=niver <data> ou @membro` - Registre seu aniversário no bot ou marque algum membro pra ver o aniversário dele se tiver registrado."
            ),
            inline=False
        )

        # Rodapé conforme o seu modelo
        embed.set_footer(
            text=f"Versão {VERSION} • Solicitado por {ctx.author.display_name}", 
            icon_url=ctx.author.display_avatar.url
        )
        
        # Opcional: Miniatura do bot
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)

    @commands.command(name="changelog")
    async def changelog(self, ctx):
        """Mostra o histórico de atualizações com paginação"""
        view = ChangelogView(CHANGELOGS, per_page=3)
        await ctx.send(embed=view.create_embed(), view=view)

    @commands.command()
    async def status(self, ctx):
        """Mostra se o canal está ativo ou não"""
        is_active = "✅ Ativo" if ctx.channel.id in self.bot.active_channels else "❌ Inativo"
        await ctx.send(f"Status da tradução neste canal: **{is_active}**")

    @commands.command(name="botinfo")
    async def botinfo(self, ctx):
        """Exibe estatísticas e informações técnicas do bot"""
        import time # Garante que o time está disponível para o uptime
        
        # Cálculo de Uptime
        uptime_seconds = int(time.time() - self.bot.start_time)
        horas, resto = divmod(uptime_seconds, 3600)
        minutos, segundos = divmod(resto, 60)
        uptime_str = f"{horas}h {minutos}m {segundos}s"

        # Cálculo de Horários (Host já está em Brasília)
        hora_host = datetime.now().strftime("%H:%M")
        hora_brasilia = hora_host

        try:
            res = self.bot.supabase.table("stats").select("total_translations").eq("id", "global").execute()
            total_traducoes = res.data[0]['total_translations'] if res.data else 0
        except:
            total_traducoes = "Indisponível"

        embed = discord.Embed(title=f"📊 Estatísticas do Messi Bot", color=0x2ecc71)
        embed.add_field(name="🚀 Versão", value=f"`v{VERSION}`", inline=True)
        embed.add_field(name="📡 Latência", value=f"`{round(self.bot.latency * 1000)}ms`", inline=True)
        embed.add_field(name="⏱️ Uptime", value=f"`{uptime_str}`", inline=True)
        
        # Nova seção de Horários
        embed.add_field(name="☁️ Hora Host (UTC)", value=f"`{hora_host}`", inline=True)
        embed.add_field(name="🇧🇷 Hora Brasília", value=f"`{hora_brasilia}`", inline=True)
        
        embed.add_field(name="🌍 Traduções Globais", value=f"`{total_traducoes}`", inline=False)
        
        embed.set_footer(text="Monitoramento de Fuso Horário Ativo")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))