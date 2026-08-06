import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import io
import time
from datetime import date

from PIL import Image

DONO_ID = 644667253324775454
BUCKET = "prints"
TIPOS = {"elo": "Por Elo", "gema": "Por Gema"}
MAX_LADO = 1920  # Lado maior máximo (px)
QUALIDADE = 85  # Qualidade JPEG
LIMITE_DIARIO_PADRAO = 2

def comprimir_imagem(img_data: bytes, max_lado: int = MAX_LADO, qualidade: int = QUALIDADE) -> bytes:
    """Comprime/redimensiona uma imagem para reduzir o peso no bucket."""
    img = Image.open(io.BytesIO(img_data))
    img = img.convert("RGB")
    img.thumbnail((max_lado, max_lado), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=qualidade, optimize=True)
    return buf.getvalue()



def e_admin_ou_dono():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == DONO_ID:
            return True
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


class TipoPrintView(discord.ui.View):
    def __init__(self, bot, user):
        super().__init__(timeout=120)
        self.bot = bot
        self.user = user
        self.tipo = None

    @discord.ui.button(label="Por Elo", style=discord.ButtonStyle.primary, emoji="🎮")
    async def por_elo(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.tipo = "elo"
        await self._ask_image(interaction)

    @discord.ui.button(label="Por Gema", style=discord.ButtonStyle.success, emoji="💎")
    async def por_gema(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.tipo = "gema"
        await self._ask_image(interaction)

    async def _ask_image(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Esse comando não é seu.", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="📸 **Agora envie o PRINT da conquista neste canal!** (60s)\n> A imagem será salva para análise.",
            view=self
        )
        self.stop()


class PrintCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------- Config interno ----------
    def get_config(self, guild_id):
        try:
            res = self.bot.supabase.table("print_config").select("*").eq("guild_id", guild_id).maybe_single().execute()
            return res.data
        except Exception:
            return None

    def get_eligible_roles(self, guild_id):
        try:
            res = self.bot.supabase.table("print_roles").select("role_id").eq("guild_id", guild_id).execute()
            return [int(r["role_id"]) for r in (res.data or [])]
        except Exception:
            return []

    def get_daily_limit(self, guild_id):
        cfg = self.get_config(guild_id)
        try:
            return int(cfg.get("daily_limit")) if cfg and cfg.get("daily_limit") else LIMITE_DIARIO_PADRAO
        except Exception:
            return LIMITE_DIARIO_PADRAO

    def get_approval_roles(self, guild_id):
        cfg = self.get_config(guild_id)
        try:
            return [int(r) for r in (cfg.get("approval_role_ids") or []) if r]
        except Exception:
            return []

    def can_approve(self, member):
        if member.id == DONO_ID:
            return True
        roles = self.get_approval_roles(member.guild.id)
        if roles and any(r.id in roles for r in member.roles):
            return True
        return member.guild_permissions.administrator

    async def notify_review(self, guild, submission, status, role=None, motivo=None, reviewer=None):
        cfg = self.get_config(guild.id)
        if not cfg or not cfg.get("review_channel_id"):
            return
        channel = self.bot.get_channel(int(cfg["review_channel_id"]))
        if not channel:
            return

        user = guild.get_member(int(submission["user_id"]))
        mention = user.mention if user else f"<@{submission['user_id']}>"

        if status == "aprovado":
            embed = discord.Embed(title="✅ **Print Aprovada**", color=0x2ecc71)
            if role:
                embed.add_field(name="🎖️ Cargo recebido", value=role.mention, inline=False)
            else:
                embed.add_field(name="🎖️ Cargo recebido", value="Nenhum (print por gema)", inline=False)
        else:
            embed = discord.Embed(title="❌ **Print Recusada**", color=0xe74c3c)
            embed.add_field(name="📝 Motivo", value=motivo or "Não informado", inline=False)

        embed.description = f"**Tipo:** {TIPOS.get(submission.get('tipo'), submission.get('tipo'))}"
        if reviewer:
            embed.add_field(name="👤 Analisado por", value=reviewer.mention, inline=False)
        if submission.get("image_url"):
            embed.set_thumbnail(url=submission["image_url"])
        await channel.send(content=mention, embed=embed)

    # ---------- Usuário envia print ----------
    @app_commands.command(name="print", description="Envia um print de conquista para análise")
    async def print(self, interaction: discord.Interaction):
        view = TipoPrintView(self.bot, interaction.user)
        await interaction.response.send_message(
            "🖼️ **Qual o tipo da sua print?**\n> Escolha abaixo:", view=view, ephemeral=True
        )
        await view.wait()
        if not view.tipo:
            return

        def check(m):
            return (m.author.id == interaction.user.id
                    and m.channel.id == interaction.channel.id
                    and m.attachments)

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60.0)
        except asyncio.TimeoutError:
            return await interaction.edit_original_response(content="❌ **Tempo esgotado.** Nenhuma imagem recebida.", view=None)

        attachment = msg.attachments[0]
        if not any(attachment.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):
            try: await msg.delete()
            except: pass
            return await interaction.edit_original_response(content="❌ O arquivo enviado não é uma imagem válida.", view=None)

        await interaction.edit_original_response(content="⏳ **Salvando sua print...**", view=None)

        # Config obrigatório
        cfg = self.get_config(interaction.guild.id)
        if not cfg or not cfg.get("review_channel_id"):
            return await interaction.edit_original_response(content="⚠️ O canal de prints ainda não foi configurado. A imagem não foi salva.", view=None)

        # Verifica se o usuário já tem uma pendência
        try:
            res = self.bot.supabase.table("print_submissions").select("id").eq("user_id", str(interaction.user.id)).eq("status", "pendente").execute()
            if res.data:
                return await interaction.edit_original_response(content="⚠️ Você já tem uma print aguardando análise. Aguarde a resposta.", view=None)
        except Exception:
            pass

        # Limite diário de envios por usuário
        try:
            limite = self.get_daily_limit(interaction.guild.id)
            dia_inicio = f"{date.today().isoformat()}T00:00:00"
            hoje = self.bot.supabase.table("print_submissions").select("id").eq("user_id", str(interaction.user.id)).gte("created_at", dia_inicio).execute()
            if len(hoje.data or []) >= limite:
                return await interaction.edit_original_response(
                    content=f"⚠️ Você atingiu o limite de **{limite}** prints por dia. Tente novamente amanhã.", view=None)
        except Exception:
            pass

        try:
            # Upload imagem (comprimida)
            img_data = await attachment.read()
            try:
                img_data = comprimir_imagem(img_data)
            except Exception as e:
                return await interaction.edit_original_response(content=f"❌ **Não foi possível processar a imagem:** {e}", view=None)
            file_name = f"{interaction.user.id}_{int(time.time())}.jpg"
            self.bot.supabase.storage.from_(BUCKET).upload(
                path=file_name,
                file=img_data,
                file_options={"content-type": "image/jpeg"}
            )
            public_url = self.bot.supabase.storage.from_(BUCKET).get_public_url(file_name)

            # Salva no banco
            self.bot.supabase.table("print_submissions").insert({
                "user_id": str(interaction.user.id),
                "username": interaction.user.display_name,
                "tipo": view.tipo,
                "image_url": str(public_url),
                "status": "pendente",
            }).execute()

            try: await msg.delete()
            except: pass

            await interaction.edit_original_response(content="✅ **Print enviada com sucesso!** Aguarde a análise dos administradores.", view=None)

            # Notifica no canal de review
            try:
                latest = self.bot.supabase.table("print_submissions").select("*").eq("user_id", str(interaction.user.id)).eq("status", "pendente").order("id", desc=True).limit(1).execute()
                sub = latest.data[0] if latest.data else None
                if sub:
                    channel = self.bot.get_channel(int(cfg["review_channel_id"]))
                    if channel:
                        embed = discord.Embed(title="🖼️ **Nova Print para análise**", color=0x3498db)
                        embed.description = f"{interaction.user.mention}\n**Tipo:** {TIPOS.get(sub['tipo'])}\n**ID:** `{sub['id']}`"
                        embed.set_image(url=sub["image_url"])
                        await channel.send(embed=embed)
            except Exception:
                pass

        except Exception as e:
            await interaction.edit_original_response(content=f"❌ **Erro ao salvar a print:** {e}", view=None)

    # ---------- Configuração ----------
    @app_commands.command(name="setprintcanal", description="Define o canal de recebimento/aviso de prints")
    @e_admin_ou_dono()
    async def setprintcanal(self, interaction: discord.Interaction, canal: discord.TextChannel):
        cfg = self.get_config(interaction.guild.id)
        if cfg:
            self.bot.supabase.table("print_config").update({"review_channel_id": canal.id}).eq("guild_id", interaction.guild.id).execute()
        else:
            self.bot.supabase.table("print_config").insert({"guild_id": interaction.guild.id, "review_channel_id": canal.id}).execute()
        await interaction.response.send_message(f"✅ Canal de prints configurado: {canal.mention}")

    @app_commands.command(name="printlimite", description="Define o limite diário de prints por usuário")
    @e_admin_ou_dono()
    async def printlimite(self, interaction: discord.Interaction, limite: int):
        if limite < 1:
            return await interaction.response.send_message("⚠️ O limite precisa ser pelo menos 1.", ephemeral=True)
        cfg = self.get_config(interaction.guild.id)
        if cfg:
            self.bot.supabase.table("print_config").update({"daily_limit": limite}).eq("guild_id", interaction.guild.id).execute()
        else:
            self.bot.supabase.table("print_config").insert({"guild_id": interaction.guild.id, "daily_limit": limite}).execute()
        await interaction.response.send_message(f"✅ Limite diário de prints configurado para **{limite}** por usuário.")

    @app_commands.command(name="addprintrole", description="Adiciona um cargo elegível para print por elo")
    @e_admin_ou_dono()
    async def addprintrole(self, interaction: discord.Interaction, cargo: discord.Role):
        exist = self.bot.supabase.table("print_roles").select("role_id").eq("guild_id", interaction.guild.id).eq("role_id", cargo.id).execute()
        if exist.data:
            return await interaction.response.send_message("⚠️ Esse cargo já está configurado.")
        self.bot.supabase.table("print_roles").insert({
            "guild_id": interaction.guild.id,
            "role_id": cargo.id,
        }).execute()
        await interaction.response.send_message(f"✅ Cargo {cargo.mention} adicionado ao sistema de prints.")

    @app_commands.command(name="remprintrole", description="Remove um cargo elegível do sistema de prints")
    @e_admin_ou_dono()
    async def remprintrole(self, interaction: discord.Interaction, cargo: discord.Role):
        res = self.bot.supabase.table("print_roles").delete().eq("guild_id", interaction.guild.id).eq("role_id", cargo.id).execute()
        if res.data:
            await interaction.response.send_message(f"🗑️ Cargo {cargo.mention} removido.")
        else:
            await interaction.response.send_message("⚠️ Esse cargo não está configurado.")

    @app_commands.command(name="printroles", description="Lista os cargos configurados no sistema de prints")
    @e_admin_ou_dono()
    async def printroles(self, interaction: discord.Interaction):
        res = self.bot.supabase.table("print_roles").select("role_id").eq("guild_id", interaction.guild.id).execute()
        if not res.data:
            return await interaction.response.send_message("⚠️ Nenhum cargo configurado.")
        roles = [interaction.guild.get_role(int(r["role_id"])) for r in res.data]
        txt = "\n".join(f"• {r.mention}" for r in roles if r)
        await interaction.response.send_message(f"**Cargos elegíveis:**\n{txt}")

    @app_commands.command(name="printstatus", description="Mostra a configuração e o resumo do sistema de prints")
    @e_admin_ou_dono()
    async def printstatus(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = self.get_config(interaction.guild.id)
        canal = f"<#{int(cfg['review_channel_id'])}>" if cfg and cfg.get("review_channel_id") else "Não configurado"
        limite = self.get_daily_limit(interaction.guild.id)
        aprova_ids = self.get_approval_roles(interaction.guild.id)
        if aprova_ids:
            aprova = "\n".join(f"• <@&{r}>" for r in aprova_ids)
        else:
            aprova = "Qualquer **Administrador** do servidor"

        res = self.bot.supabase.table("print_submissions").select("status").execute()
        cont = {"pendente": 0, "aprovado": 0, "recusado": 0}
        for r in res.data or []:
            cont[r.get("status")] = cont.get(r.get("status"), 0) + 1

        embed = discord.Embed(title="⚙️ Sistema de Prints", color=0x3498db)
        embed.add_field(name="📌 Canal de prints/avisos", value=canal, inline=False)
        embed.add_field(name="🔢 Limite diário por usuário", value=f"**{limite}**", inline=False)
        embed.add_field(name="🛡️ Cargos aprovadores", value=aprova, inline=False)
        embed.add_field(name="📊 Resumo", value=f"⏳ Pendentes: **{cont['pendente']}**\n✅ Aprovadas: **{cont['aprovado']}**\n❌ Recusadas: **{cont['recusado']}**", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="addprintmod", description="Adiciona um cargo que pode aprovar/recusar prints")
    @e_admin_ou_dono()
    async def addprintmod(self, interaction: discord.Interaction, cargo: discord.Role):
        self._update_approval_role(interaction, cargo.id, add=True)
        await interaction.response.send_message(f"✅ Cargo {cargo.mention} agora pode aprovar/recusar prints.")

    @app_commands.command(name="remprintmod", description="Remove um cargo que pode aprovar/recusar prints")
    @e_admin_ou_dono()
    async def remprintmod(self, interaction: discord.Interaction, cargo: discord.Role):
        self._update_approval_role(interaction, cargo.id, add=False)
        await interaction.response.send_message(f"🗑️ Cargo {cargo.mention} removido dos aprovadores.")

    @app_commands.command(name="printmods", description="Lista os cargos aprovadores de prints")
    @e_admin_ou_dono()
    async def printmods(self, interaction: discord.Interaction):
        ids = self.get_approval_roles(interaction.guild.id)
        if not ids:
            return await interaction.response.send_message("⚠️ Nenhum cargo aprovador configurado. Qualquer administrador pode aprovar.")
        roles = [interaction.guild.get_role(r) for r in ids]
        txt = "\n".join(f"• {r.mention}" for r in roles if r)
        await interaction.response.send_message(f"**Cargos aprovadores:** (além de qualquer administrador)\n{txt}")

    def _update_approval_role(self, interaction, role_id, add: bool):
        cfg = self.get_config(interaction.guild.id)
        atual = set(self.get_approval_roles(interaction.guild.id))
        if add:
            atual.add(int(role_id))
        else:
            atual.discard(int(role_id))
        if cfg:
            self.bot.supabase.table("print_config").update(
                {"approval_role_ids": list(atual)}
            ).eq("guild_id", interaction.guild.id).execute()
        else:
            self.bot.supabase.table("print_config").insert({
                "guild_id": interaction.guild.id,
                "approval_role_ids": list(atual),
            }).execute()

    # ---------- Gerenciamento (Admin) ----------
    @app_commands.command(name="prints", description="Abre a fila de prints para análise")
    @app_commands.choices(status=[
        app_commands.Choice(name="Pendentes", value="pendente"),
        app_commands.Choice(name="Aprovadas", value="aprovado"),
        app_commands.Choice(name="Recusadas", value="recusado"),
        app_commands.Choice(name="Todas", value="todas"),
    ])
    @e_admin_ou_dono()
    async def prints(self, interaction: discord.Interaction, status: str = "pendente"):
        await interaction.response.defer(ephemeral=True)
        try:
            query = self.bot.supabase.table("print_submissions").select("*")
            if status != "todas":
                query = query.eq("status", status)
            res = query.order("id", desc=False).execute()
            if not res.data:
                return await interaction.followup.send(f"✅ Nenhuma print encontrada.", ephemeral=True)

            options = []
            for sub in res.data:
                user = interaction.guild.get_member(int(sub["user_id"]))
                nome = (f"#{sub['id']} - {user.display_name}" if user else f"#{sub['id']} - {sub['username']}")[:90]
                options.append(discord.SelectOption(
                    label=nome,
                    value=str(sub["id"]),
                    description=f"{TIPOS.get(sub['tipo'], sub['tipo'])} | {sub.get('status')}"
                ))

            select = discord.ui.Select(
                placeholder="Selecione uma print...",
                options=options
            )
            view = discord.ui.View()
            review_data = res.data
            guild = interaction.guild

            async def on_select(inner: discord.Interaction):
                if inner.user.id != interaction.user.id:
                    return await inner.response.send_message("❌ Apenas quem abriu pode analisar.", ephemeral=True)
                sub_id = int(select.values[0])
                sub = next((s for s in review_data if s["id"] == sub_id), None)
                if not sub:
                    return await inner.response.send_message("❌ Print não encontrada.", ephemeral=True)
                await PreviewView(self.bot, inner.user, sub, guild).start(inner)

            select.callback = on_select
            view.add_item(select)
            await interaction.followup.send(f"🖼️ **Prints ({status}):** selecione uma:", view=view, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)


class PreviewView(discord.ui.View):
    def __init__(self, bot, admin, submission, guild):
        super().__init__(timeout=120)
        self.bot = bot
        self.admin = admin
        self.submission = submission
        self.guild = guild
        self.value = None

    async def start(self, interaction: discord.Interaction):
        embed = self._embed()
        if self.submission.get("status") != "pendente":
            for child in self.children:
                child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    def _embed(self):
        sub = self.submission
        user = self.guild.get_member(int(sub["user_id"]))
        user_ref = user.mention if user else f"<@{sub['user_id']}>"
        status = sub.get("status", "desconhecido")
        cor = {"pendente": 0x3498db, "aprovado": 0x2ecc71, "recusado": 0xe74c3c}.get(status, 0x3498db)
        emoji_status = {"pendente": "⏳", "aprovado": "✅", "recusado": "❌"}.get(status, "❔")
        embed = discord.Embed(
            title=f"🖼️ Print #{sub['id']}",
            color=cor
        )
        embed.description = (
            f"**Usuário:** {user_ref}\n"
            f"**Tipo:** {TIPOS.get(sub['tipo'], sub['tipo'])}\n"
            f"**Status:** {emoji_status} {status}"
        )
        if status == "aprovado" and sub.get("granted_role_id"):
            role = self.guild.get_role(int(sub["granted_role_id"]))
            embed.add_field(name="🎖️ Cargo concedido", value=role.mention if role else "Cargo excluído", inline=False)
        if sub.get("motivo_recusa"):
            embed.add_field(name="📝 Motivo da recusa", value=sub["motivo_recusa"], inline=False)
        if sub.get("reviewed_by"):
            embed.add_field(name="👤 Analisado por", value=f"<@{sub['reviewed_by']}>", inline=False)
        embed.set_image(url=sub["image_url"])
        embed.set_footer(text="Escolha uma ação abaixo" if status == "pendente" else f"Print {status}")
        return embed

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, emoji="✅")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.bot.get_cog("PrintCog").can_approve(interaction.user):
            return await interaction.response.send_message("❌ Você não tem permissão para aprovar prints.", ephemeral=True)
        sub = self.submission
        tipo = sub["tipo"]

        if tipo == "gema":
            self.bot.supabase.table("print_submissions").update({
                "status": "aprovado",
                "reviewed_by": str(interaction.user.id),
            }).eq("id", sub["id"]).execute()
            await self.notify_approve(interaction, role=None)
            return

        # Por elo -> escolher cargo
        eligible = self.bot.get_cog("PrintCog").get_eligible_roles(self.guild.id)
        available = [self.guild.get_role(r) for r in eligible if self.guild.get_role(r)]
        if not available:
            return await interaction.response.send_message("⚠️ Nenhum cargo elegível configurado. Use /addprintrole.", ephemeral=True)

        options = [discord.SelectOption(label=r.name, value=str(r.id)) for r in available[:25]]
        select = discord.ui.Select(placeholder="Escolha o cargo...", options=options)
        view = discord.ui.View()

        async def on_role(inner: discord.Interaction):
            role = self.guild.get_role(int(select.values[0]))
            self.bot.supabase.table("print_submissions").update({
                "status": "aprovado",
                "granted_role_id": role.id,
                "reviewed_by": str(inner.user.id),
            }).eq("id", sub["id"]).execute()
            await self.grant_and_notify(inner, role)

        select.callback = on_role
        view.add_item(select)
        await interaction.response.edit_message(content="🎖️ **Escolha o cargo a ser dado:**", embed=None, view=view)

    @discord.ui.button(label="Recusar", style=discord.ButtonStyle.danger, emoji="❌")
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.bot.get_cog("PrintCog").can_approve(interaction.user):
            return await interaction.response.send_message("❌ Você não tem permissão para recusar prints.", ephemeral=True)
        modal = RecusaModal(self.bot, self)
        await interaction.response.send_modal(modal)

    async def grant_and_notify(self, interaction: discord.Interaction, role):
        sub = self.submission
        member = self.guild.get_member(int(sub["user_id"]))
        msg_extra = ""
        if member:
            try:
                await member.add_roles(role)
            except Exception:
                msg_extra = " (não foi possível atribuir o cargo ao usuário)"
        await self.notify_approve(interaction, role=role, msg_extra=msg_extra)

    async def notify_approve(self, interaction: discord.Interaction, role=None, msg_extra=""):
        sub = self.submission
        await self.bot.get_cog("PrintCog").notify_review(self.guild, sub, "aprovado", role=role, reviewer=interaction.user)
        texto = f"✅ Print **#{sub['id']}** aprovada!"
        if role:
            texto += f"\nCargo {role.mention} concedido{msg_extra}."
        else:
            texto += "\nNenhum cargo (print por gema)."
        await interaction.response.edit_message(content=texto, embed=None, view=None)


class RecusaModal(discord.ui.Modal, title="Recusar Print"):
    motivo = discord.ui.TextInput(label="Motivo da recusa", style=discord.TextStyle.paragraph, placeholder="Explique o motivo...", max_length=500, required=True)

    def __init__(self, bot, preview_view: PreviewView):
        super().__init__()
        self.bot = bot
        self.preview = preview_view

    async def on_submit(self, interaction: discord.Interaction):
        sub = self.preview.submission
        self.bot.supabase.table("print_submissions").update({
            "status": "recusado",
            "motivo_recusa": self.motivo.value,
            "reviewed_by": str(interaction.user.id),
        }).eq("id", sub["id"]).execute()
        await self.preview.bot.get_cog("PrintCog").notify_review(
            self.preview.guild, sub, "recusado", motivo=self.motivo.value, reviewer=interaction.user
        )
        embed = discord.Embed(title=f"❌ Print #{sub['id']} recusada", color=0xe74c3c)
        embed.add_field(name="Motivo", value=self.motivo.value)
        await interaction.response.edit_message(content=None, embed=embed, view=None)


async def setup(bot):
    await bot.add_cog(PrintCog(bot))