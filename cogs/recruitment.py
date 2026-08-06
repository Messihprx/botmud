import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import requests
import io
import time
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
ROLE_IDS = {
    "Homem": 1346696409436651572,   
    "Mulher": 1333842342792401050,  
    "PC": 1261978808840622183,      
    "Mobile": 1261978809985536031,  
    "Console": 1327362104998629397, 
    "Geral": 1261978783498371106,   
    "Maior": 1313370442383491163,   
    "Menor": 1313370703319531561    
}

ID_CANAL_AVISO = 1261978939681669192
CARGO_ESPERA_ID = 1261978807917875251
MEU_ID_DISCORD = 644667253324775454
ID_CANAL_LOGS = 1475551667285004423

def e_moderador_ou_dono():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == MEU_ID_DISCORD:
            return True
        return interaction.user.guild_permissions.manage_messages
    return app_commands.check(predicate)

def e_admin_ou_dono():
    async def predicate(interaction: discord.Interaction) -> bool:
        # 1. Verifica se é você pelo ID (Dono do Bot)
        # Substituímos pela comparação direta com o seu ID
        if interaction.user.id == 644667253324775454:
            return True
            
        # 2. Verifica se o usuário tem permissão de Administrador no servidor
        return interaction.user.guild_permissions.administrator
        
    return app_commands.check(predicate)

# --- VIEWS DE PAGINAÇÃO ---
class RecentesPaginator(discord.ui.View):
    def __init__(self, embeds, autor_id):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.autor_id = autor_id
        self.pagina_atual = 0

    async def atualizar_mensagem(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.embeds[self.pagina_atual], view=self)

    @discord.ui.button(label="Anterior", style=discord.ButtonStyle.gray, emoji="⬅️")
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.autor_id:
            return await interaction.response.send_message("❌ Você não pode controlar esta lista.", ephemeral=True)
        
        if self.pagina_atual > 0:
            self.pagina_atual -= 1
            await self.atualizar_mensagem(interaction)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Próximo", style=discord.ButtonStyle.gray, emoji="➡️")
    async def proximo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.autor_id:
            return await interaction.response.send_message("❌ Você não pode controlar esta lista.", ephemeral=True)
        
        if self.pagina_atual < len(self.embeds) - 1:
            self.pagina_atual += 1
            await self.atualizar_mensagem(interaction)
        else:
            await interaction.response.defer()

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, autor_id):
        super().__init__(timeout=40)
        self.autor_id = autor_id
        self.confirmado = False

    @discord.ui.button(label="Iniciar Exclusão", style=discord.ButtonStyle.danger, emoji="🔓")
    async def first_click(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.autor_id:
            return await interaction.response.send_message("❌ Você não iniciou este comando.", ephemeral=True)
        
        button.disabled = True
        button.label = "Aguarde 5 segundos..."
        await interaction.response.edit_message(view=self)

        await asyncio.sleep(5)

        second_button = discord.ui.Button(label="CONFIRMAR AGORA", style=discord.ButtonStyle.danger, emoji="🔥")
        
        async def second_click_callback(inter: discord.Interaction):
            if inter.user.id != self.autor_id: return
            self.confirmado = True
            self.stop()
            await inter.response.defer()

        second_button.callback = second_click_callback
        self.add_item(second_button)
        await interaction.edit_original_response(content="⚠️ **Sistema Desbloqueado:** Clique em Confirmar Agora para deletar permanentemente.", view=self)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.autor_id: return
        self.confirmado = False
        self.stop()
        await interaction.response.edit_message(content="✅ Exclusão cancelada.", view=None, embed=None)

# --- MODAL E VIEWS DE RECRUTAMENTO ---
class RecruitmentModal(discord.ui.Modal, title='Dados do Recrutado'):
    roblox_name = discord.ui.TextInput(label="Nome no Roblox", placeholder="Nome no roblox / Nome da pessoa no servidor", max_length=27)
    roblox_nick = discord.ui.TextInput(label="Nick no Roblox", placeholder="Ex: @Jogador123")
    age = discord.ui.TextInput(label="Idade", placeholder="Ex: 17", min_length=1, max_length=2)
    discord_nick = discord.ui.TextInput(label="Confirmar Nick Discord")

    def __init__(self, bot, target_member):
        super().__init__()
        self.bot = bot
        self.target_member = target_member
        self.discord_nick.default = target_member.name

    async def on_submit(self, interaction: discord.Interaction):
        if not self.age.value.isdigit():
            return await interaction.response.send_message("❌ A idade precisa ser um número!", ephemeral=True)

        data = {
            "recruiter_id": str(interaction.user.id),
            "recruit_id": str(self.target_member.id),
            "roblox_name": self.roblox_name.value,
            "roblox_nick": self.roblox_nick.value,
            "age": int(self.age.value),
            "discord_nick": self.target_member.name
        }
        
        view = GenderView(data, self.bot, self.target_member)
        await interaction.response.send_message(f"Selecione o Gênero para {self.target_member.mention}:", view=view, ephemeral=True)

class GenderView(discord.ui.View):
    def __init__(self, data, bot, target_member):
        super().__init__(timeout=None)
        self.data = data
        self.bot = bot
        self.target_member = target_member

    @discord.ui.button(label="Homem", style=discord.ButtonStyle.primary)
    async def male(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.data["gender"] = "Homem"
        view = PlatformView(self.data, self.bot, self.target_member)
        await interaction.response.edit_message(content="Selecione a Plataforma:", view=view)

    @discord.ui.button(label="Mulher", style=discord.ButtonStyle.danger)
    async def female(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.data["gender"] = "Mulher"
        view = PlatformView(self.data, self.bot, self.target_member)
        await interaction.response.edit_message(content="Selecione a Plataforma:", view=view)

class PlatformView(discord.ui.View):
    def __init__(self, data, bot, target_member):
        super().__init__(timeout=None)
        self.data = data
        self.bot = bot
        self.target_member = target_member

    @discord.ui.button(label="PC", style=discord.ButtonStyle.secondary)
    async def pc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_finish(interaction, "PC")

    @discord.ui.button(label="Mobile", style=discord.ButtonStyle.secondary)
    async def mobile(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_finish(interaction, "Mobile")

    @discord.ui.button(label="Console", style=discord.ButtonStyle.secondary)
    async def console(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_finish(interaction, "Console")

    async def handle_finish(self, interaction: discord.Interaction, platform: str):
        self.data["platform"] = platform
        await interaction.response.edit_message(content="📸 **Envie o PRINT do recrutamento no chat agora!** (60s)", view=None)

        def check(m):
            return m.author.id == interaction.user.id and len(m.attachments) > 0

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            attachment = msg.attachments[0]
            await interaction.edit_original_response(content="⏳ **Salvando imagem e dados no Supabase...**")

            img_data = requests.get(attachment.url).content
            file_name = f"print_{self.data['recruit_id']}_{int(asyncio.get_event_loop().time())}.png"
            
            self.bot.supabase.storage.from_('recrutamentos').upload(
                path=file_name,
                file=img_data,
                file_options={"content-type": attachment.content_type}
            )

            public_url = self.bot.supabase.storage.from_('recrutamentos').get_public_url(file_name)
            self.data["recruit_image"] = str(public_url)

            try: await msg.delete()
            except: pass

        except asyncio.TimeoutError:
            return await interaction.edit_original_response(content="❌ **Tempo esgotado!** A ficha não foi salva.")
        except Exception as e:
            return await interaction.edit_original_response(content=f"❌ **Erro no Storage:** {e}")

        try:
            # Nome do recrutador registrado (ou None) para salvar na ficha
            nome_recrutador = None
            try:
                r = self.bot.supabase.table("recruiters").select("recruiter_name").eq("recruiter_id", str(self.data["recruiter_id"])).maybe_single().execute()
                if r.data and r.data.get("recruiter_name"):
                    nome_recrutador = r.data["recruiter_name"]
            except Exception:
                pass

            # Salvamos o insert em uma variável 'res' para pegar o ID gerado
            res = self.bot.supabase.table("recruitments").insert({
                "recruiter_id": str(self.data["recruiter_id"]),
                "recruiter_name": nome_recrutador,
                "recruit_id": str(self.data["recruit_id"]),
                "recruit_roblox_name": self.data["roblox_name"],
                "recruit_roblox_nick": self.data["roblox_nick"],
                "recruit_age": str(self.data["age"]),
                "recruit_discord_nick": self.data["discord_nick"],
                "gender": self.data["gender"],
                "platform": self.data["platform"],
                "recruit_image": self.data["recruit_image"],
                "saidas_count": 0
            }).execute()

            # Pega o ID da ficha que acabou de ser criada
            ficha_id = res.data[0]['registro_id'] if res.data else "???"

            guild = interaction.guild
            roles_to_add = []
            for key in [self.data["gender"], self.data["platform"], "Geral"]:
                role = guild.get_role(ROLE_IDS.get(key))
                if role: roles_to_add.append(role)
            
            age_type = "Maior" if self.data["age"] >= 18 else "Menor"
            age_role = guild.get_role(ROLE_IDS.get(age_type))
            if age_role: roles_to_add.append(age_role)

            if roles_to_add: await self.target_member.add_roles(*roles_to_add)
            
            cargo_espera = guild.get_role(CARGO_ESPERA_ID)
            if cargo_espera and cargo_espera in self.target_member.roles:
                await self.target_member.remove_roles(cargo_espera)
            
            try: await self.target_member.edit(nick=f"ᴹᴰ | {self.data['roblox_name']}")
            except: pass 

            channel = self.bot.get_channel(ID_CANAL_AVISO)
            if channel:
                embed = discord.Embed(title="📝 Novo Recrutamento", color=0x2ecc71)
                embed.set_image(url=self.data["recruit_image"])
                embed.add_field(name="Recrutador", value=f"<@{self.data['recruiter_id']}>")
                embed.add_field(name="Recrutado", value=self.target_member.mention)
                embed.set_footer(text=f"ID do Registro: {ficha_id}")
                await channel.send(embed=embed)

            await interaction.edit_original_response(content="## FICHA CRIADA COM SUCESSO ✅")
            
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ **Erro no Banco de Dados:** {e}")

# --- COG PRINCIPAL ---
class Recruitment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            res = self.bot.supabase.table("recruitments").select("registro_id", "saidas_count").eq("recruit_id", str(member.id)).execute()
            if res.data:
                ficha = res.data[0]
                novo_total = (ficha.get('saidas_count') or 0) + 1
                self.bot.supabase.table("recruitments").update({"saidas_count": novo_total}).eq("registro_id", ficha['registro_id']).execute()
        except Exception as e:
            print(f"Erro ao registrar saída automática: {e}")

    # ---------- Registro de Recrutadores ----------
    def get_recruiter_name(self, recruiter_id):
        """Retorna o nome registrado do recrutador ou None."""
        if not recruiter_id:
            return None
        try:
            res = self.bot.supabase.table("recruiters").select("recruiter_name").eq("recruiter_id", str(recruiter_id)).maybe_single().execute()
            if res.data and res.data.get("recruiter_name"):
                return res.data["recruiter_name"]
        except Exception:
            pass
        return None

    def resolver_recrutador(self, recruiter_id):
        """Retorna (nome, id). Nome vira 'Sem registro' se não cadastrado. ID sempre presente."""
        nome = self.get_recruiter_name(recruiter_id)
        exib_nome = nome if nome else "Sem registro"
        return exib_nome, str(recruiter_id)

    @app_commands.command(name="registrarrecrutador", description="Registra seu nome como recrutador para aparecer nas fichas")
    async def registrarrecrutador(self, interaction: discord.Interaction, nome: str):
        if not nome or not nome.strip():
            return await interaction.response.send_message("⚠️ Informe um nome válido.", ephemeral=True)
        if len(nome.strip()) > 60:
            return await interaction.response.send_message("⚠️ Nome muito longo (máx 60 caracteres).", ephemeral=True)

        rid = str(interaction.user.id)
        # Verifica se já existe
        ex = self.bot.supabase.table("recruiters").select("recruiter_id").eq("recruiter_id", rid).maybe_single().execute()
        if ex and ex.data:
            self.bot.supabase.table("recruiters").update({"recruiter_name": nome.strip()}).eq("recruiter_id", rid).execute()
            acao = "atualizado"
        else:
            self.bot.supabase.table("recruiters").insert({"recruiter_id": rid, "recruiter_name": nome.strip()}).execute()
            acao = "registrado"

        # Verificação automática: atualiza fichas existentes com o nome do recrutador
        try:
            res = self.bot.supabase.table("recruitments").select("registro_id").eq("recruiter_id", rid).execute()
            fichas = res.data or []
            if fichas:
                ids = [f["registro_id"] for f in fichas]
                for fid in ids:
                    try:
                        self.bot.supabase.table("recruitments").update({"recruiter_name": nome.strip()}).eq("registro_id", fid).execute()
                    except Exception:
                        pass
        except Exception:
            fichas = []

        await interaction.response.send_message(
            f"✅ Nome **{nome.strip()}** {acao} no registro de recrutadores!\n"
            f"👥 **{len(fichas)}** ficha(s) existente(s) foi/foram atualizada(s) com seu nome.",
            ephemeral=True
        )

    @app_commands.command(name="rec", description="Inicia recrutamento")
    @e_moderador_ou_dono()
    async def rec(self, interaction: discord.Interaction, membro: discord.Member):
        await interaction.response.send_modal(RecruitmentModal(self.bot, membro))

    @app_commands.command(name="ficha", description="Consulta a ficha")
    @app_commands.describe(membro="Membro (opcional)", id_registro="ID da ficha (opcional)", roblox_nick="Nick do Roblox (opcional)")
    @e_moderador_ou_dono()
    async def ficha(self, interaction: discord.Interaction, membro: discord.Member = None, id_registro: int = None, roblox_nick: str = None):
        await interaction.response.defer()
        try:
            query = self.bot.supabase.table("recruitments").select("*")
            if id_registro:
                response = query.eq("registro_id", id_registro).execute()
            elif membro:
                response = query.eq("recruit_id", str(membro.id)).execute()
            elif roblox_nick:
                response = query.ilike("recruit_roblox_nick", f"%{roblox_nick}%").execute()
            else:
                return await interaction.followup.send("❌ Informe o @membro, o ID ou o nick do Roblox!", ephemeral=True)

            if not response.data:
                return await interaction.followup.send(f"❌ Ficha não encontrada.", ephemeral=True)

            dados = response.data[0]
            data_br = "Data não disponível"
            if 'created_at' in dados:
                dt = datetime.fromisoformat(dados['created_at'].replace('Z', '+00:00'))
                dt_br = dt - timedelta(hours=3) 
                data_br = dt_br.strftime('%d/%m/%Y às %H:%M')
            
            guild = interaction.guild
            recruit_id = dados.get('recruit_id')
            try:
                member_in_guild = guild.get_member(int(recruit_id)) if recruit_id and str(recruit_id).isdigit() else None
            except (ValueError, TypeError):
                member_in_guild = None
            status_servidor = "✅ **Presente**" if member_in_guild else "❌ **Fora do Servidor**"
            saidas = dados.get('saidas_count', 0)

            # Nome do recrutador (registrado ou "Sem registro"), sempre com o ID
            nome_recrutador = dados.get('recruiter_name') or self.get_recruiter_name(dados.get('recruiter_id'))
            if not nome_recrutador:
                nome_recrutador = "Sem registro"
            recrutador_ref = f"{nome_recrutador} (<@{dados['recruiter_id']}>)" if dados.get('recruiter_id') else "Sem registro"

            cargos_lista = [f"<@&{ROLE_IDS.get(dados['gender'])}>", f"<@&{ROLE_IDS.get(dados['platform'])}>", f"<@&{ROLE_IDS.get('Geral')}>"]
            faixa_id = ROLE_IDS.get("Maior" if int(dados['recruit_age']) >= 18 else "Menor")
            cargos_lista.append(f"<@&{faixa_id}>")
            cargos_marcados = ", ".join(cargos_lista)

            mensagem_ficha = (
                f"> # :page_facing_up:  **𝙁𝙞𝙘𝙝𝙖 𝙙𝙚 𝙍𝙚𝙘𝙧𝙪𝙩𝙖𝙢𝙚𝙣𝙩𝙤 #{dados['registro_id']}**\n"
                f"> ### RECRUTADOR: {recrutador_ref}\n"
                f"> ### RECRUTADO: {dados['recruit_roblox_name']}\n"
                f"> ### NICK DA CONTA: `{dados['recruit_roblox_nick']}`\n"
                f"> ### IDADE: `{dados['recruit_age']} anos`\n"
                f"> ### DISCORD: `{dados['recruit_discord_nick']}`\n"
                f"> ### STATUS: {status_servidor}\n"
                f"> ### SAÍDAS: `{saidas}` 🚪\n"
                f"> ### CARGOS SETADOS: {cargos_marcados}"
            )

            embed = discord.Embed(color=0x2b2d31)
            if dados.get('recruit_image'): embed.set_image(url=dados['recruit_image'])
            embed.set_footer(text=f"Recrutamento realizado em: {data_br}")

            # --- ALTERAÇÃO AQUI: Salvamos a mensagem enviada ---
            msg = await interaction.followup.send(content=mensagem_ficha, embed=embed)

            # Aguarda 30 segundos e deleta
            await asyncio.sleep(60)
            try:
                await msg.delete()
            except:
                pass # Evita erro se o usuário apagar a mensagem antes do tempo

        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

    @app_commands.command(name="edit", description="Edita dados de uma ficha")
    @e_moderador_ou_dono()
    async def edit(self, interaction: discord.Interaction, 
                id_registro: int, 
                novo_recrutado: str = None, 
                novo_nick_conta: str = None, 
                nova_idade: int = None, 
                novo_discord_user: str = None, 
                novo_discord_id: str = None,
                editar_imagem: bool = False,
                novo_recrutador: discord.Member = None):
    
        # Deferir para evitar o erro de "O aplicativo não responde"
        await interaction.response.defer(ephemeral=True)
        
        try:
            # 1. Busca os dados atuais da ficha no Supabase
            res = self.bot.supabase.table("recruitments").select("*").eq("registro_id", id_registro).execute()
            if not res.data: 
                return await interaction.followup.send("❌ Ficha não encontrada.", ephemeral=True)
            
            dados_antigos = res.data[0]
            
            # --- TRAVA DE SEGURANÇA ATUALIZADA ---
            # Os 3 IDs permitidos (Você + os dois que você enviou)
            IDS_AUTORIZADOS = [644667253324775454, 433385659760377856, 268690881551269888]
            
            # Comparação ultra-segura (converte ambos para String e limpa espaços)
            user_atual_id = str(interaction.user.id).strip()
            recrutador_ficha_id = str(dados_antigos['recruiter_id']).strip()
            
            eh_recrutador_original = user_atual_id == recrutador_ficha_id
            eh_staff_autorizada = interaction.user.id in IDS_AUTORIZADOS

            if not (eh_recrutador_original or eh_staff_autorizada):
                return await interaction.followup.send("❌ Você não tem permissão para editar esta ficha.")

            updates = {}
            
            # Mapeamento de alterações de texto
            if novo_recrutado: updates["recruit_roblox_name"] = novo_recrutado
            if novo_nick_conta: updates["recruit_roblox_nick"] = novo_nick_conta
            if nova_idade: updates["recruit_age"] = str(nova_idade)
            if novo_discord_user: updates["recruit_discord_nick"] = novo_discord_user
            if novo_discord_id: updates["recruit_id"] = str(novo_discord_id)
            if novo_recrutador: updates["recruiter_id"] = str(novo_recrutador.id)

            # --- LÓGICA DE NOVA IMAGEM (MESMA FUNCIONALIDADE) ---
            if editar_imagem:
                await interaction.followup.send("📸 **Por favor, envie a nova foto (arquivo) agora neste canal.**", ephemeral=True)

                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel and m.attachments

                try:
                    # Espera 60 segundos por uma mensagem com anexo
                    msg = await self.bot.wait_for("message", check=check, timeout=60.0)
                    attachment = msg.attachments[0]
                    
                    # Validação simples de tipo
                    if not any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                        return await interaction.followup.send("❌ O arquivo enviado não é uma imagem válida.", ephemeral=True)

                    # 1. Baixa a imagem enviada
                    img_data = await attachment.read()
                    file_ext = attachment.filename.split('.')[-1]
                    file_name = f"edit_{id_registro}_{int(time.time())}.{file_ext}"

                    # 2. Upload para o Supabase Storage
                    self.bot.supabase.storage.from_("recrutamentos").upload(
                        path=file_name,
                        file=img_data,
                        file_options={"content-type": attachment.content_type}
                    )

                    # 3. Pega a URL pública
                    new_url = self.bot.supabase.storage.from_("recrutamentos").get_public_url(file_name)
                    updates["recruit_image"] = new_url
                    
                    # Apaga a mensagem enviada pelo usuário para limpar o chat
                    try: await msg.delete() 
                    except: pass

                    # Remove imagem antiga se existir para não lotar o storage
                    if dados_antigos.get('recruit_image'):
                        try:
                            nome_antigo = dados_antigos['recruit_image'].split('/')[-1]
                            self.bot.supabase.storage.from_("recrutamentos").remove([nome_antigo])
                        except: pass

                except asyncio.TimeoutError:
                    return await interaction.followup.send("⏰ Tempo esgotado! A imagem não foi alterada.", ephemeral=True)

            # 2. Verifica se houve alguma mudança para não gastar API à toa
            if not updates: 
                return await interaction.followup.send("⚠️ Nada para alterar.", ephemeral=True)

            # 3. Atualiza o banco de dados
            self.bot.supabase.table("recruitments").update(updates).eq("registro_id", id_registro).execute()

            # --- LOG DE EDIÇÃO ---
            canal_log = self.bot.get_channel(ID_CANAL_LOGS)
            if canal_log:
                embed_log = discord.Embed(title=f"📝 Ficha #{id_registro} Editada", color=0x3498db, timestamp=datetime.now())
                embed_log.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
                
                alteracoes = ""
                # Mapeia os campos internos para nomes amigáveis no Log
                nomes_campos = {
                    "recruit_roblox_name": "Nome", "recruit_roblox_nick": "Nick Conta",
                    "recruit_age": "Idade", "recruit_discord_nick": "User Discord",
                    "recruit_id": "ID Discord", "recruiter_id": "Recrutador", "recruit_image": "Imagem"
                }

                for chave, novo_valor in updates.items():
                    valor_antigo = dados_antigos.get(chave, "Nenhum")
                    if chave == "recruit_image":
                        alteracoes += f"🔹 **{nomes_campos[chave]}**: Alterada (Clique na ficha para ver)\n"
                    else:
                        alteracoes += f"🔹 **{nomes_campos[chave]}**: `{valor_antigo}` ➔ `{novo_valor}`\n"
                
                embed_log.description = alteracoes
                await canal_log.send(embed=embed_log)

            # 4. Lógica de Nick MD | Nome (MESMA FUNCIONALIDADE)
            if novo_recrutado or novo_discord_id:
                guild = interaction.guild
                membro_id = int(novo_discord_id) if novo_discord_id else int(dados_antigos['recruit_id'])
                membro = guild.get_member(membro_id)
                
                if membro:
                    novo_nome_display = novo_recrutado if novo_recrutado else dados_antigos['recruit_roblox_name']
                    try:
                        await membro.edit(nick=f"ᴹᴰ | {novo_nome_display}")
                    except discord.Forbidden:
                        await interaction.followup.send("⚠️ Dados salvos, mas não pude alterar o apelido (permissão insuficiente).", ephemeral=True)

            await interaction.followup.send(f"✅ Ficha #{id_registro} atualizada com sucesso!", ephemeral=True)
            
        except Exception as e:
            print(f"Erro ao editar ficha: {e}")
            await interaction.followup.send(f"❌ Erro interno ao editar: {e}", ephemeral=True)

    @app_commands.command(name="tab", description="Mostra a tabela de recrutados")
    @app_commands.describe(
        ordem="Escolha a ordem de exibição",
        recrutador="Filtrar por um recrutador específico (opcional)",
        mes="Filtrar por mês (opcional)",
        ano="Ano do filtro (opcional, padrão: ano atual)"
    )
    @app_commands.choices(
        ordem=[
            app_commands.Choice(name="Mais recente para o mais antigo (Decrescente)", value="desc"),
            app_commands.Choice(name="Mais antigo para o mais recente (Crescente)", value="asc")
        ],
        mes=[
            app_commands.Choice(name="Janeiro", value=1),
            app_commands.Choice(name="Fevereiro", value=2),
            app_commands.Choice(name="Março", value=3),
            app_commands.Choice(name="Abril", value=4),
            app_commands.Choice(name="Maio", value=5),
            app_commands.Choice(name="Junho", value=6),
            app_commands.Choice(name="Julho", value=7),
            app_commands.Choice(name="Agosto", value=8),
            app_commands.Choice(name="Setembro", value=9),
            app_commands.Choice(name="Outubro", value=10),
            app_commands.Choice(name="Novembro", value=11),
            app_commands.Choice(name="Dezembro", value=12)
        ]
    )
    @e_moderador_ou_dono()
    async def tab(self, interaction: discord.Interaction, ordem: str = "desc", recrutador: discord.Member = None, mes: int = None, ano: int = None):
        await interaction.response.defer()
        try:
            is_desc = True if ordem == "desc" else False

            query = self.bot.supabase.table("recruitments").select("registro_id", "recruit_roblox_name", "recruiter_id", "created_at")

            if recrutador:
                query = query.eq("recruiter_id", str(recrutador.id))

            if mes:
                year = ano if ano else datetime.now().year
                start_date = f"{year}-{mes:02d}-01T00:00:00"
                if mes == 12:
                    end_date = f"{year + 1}-01-01T00:00:00"
                else:
                    end_date = f"{year}-{mes + 1:02d}-01T00:00:00"
                query = query.gte("created_at", start_date).lt("created_at", end_date)

            query = query.order("registro_id", desc=is_desc)
            res = query.execute()

            if not res.data:
                msg = "⚠️ Nenhuma ficha encontrada"
                if recrutador:
                    msg += f" para {recrutador.mention}"
                if mes:
                    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
                    msg += f" em {meses[mes - 1]}"
                    if ano:
                        msg += f" de {ano}"
                return await interaction.followup.send(msg + ".")

            dados = res.data
            total = len(dados)

            meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            titulo = "📋 Tabela de Recrutados"
            if recrutador and mes:
                titulo += f" — {recrutador.display_name} — {meses[mes - 1]}"
                if ano:
                    titulo += f"/{ano}"
            elif recrutador:
                titulo += f" — {recrutador.display_name}"
            elif mes:
                titulo += f" — {meses[mes - 1]}"
                if ano:
                    titulo += f"/{ano}"
            titulo += " (Recentes)" if is_desc else " (Antigos)"

            chunks = [dados[i:i + 15] for i in range(0, len(dados), 15)]
            embeds = []

            for idx, chunk in enumerate(chunks):
                lista_texto = ""
                for item in chunk:
                    recr_id = item.get('recruiter_id')
                    recr_nome = self.get_recruiter_name(recr_id) or item.get('recruiter_name')
                    if recr_id and recr_nome:
                        recr = f" — {recr_nome} (<@{recr_id}>)" if recr_id else ""
                    else:
                        recr = f" — <@{recr_id}>" if recr_id else ""
                    lista_texto += f"**ID #{item['registro_id']}** - {item['recruit_roblox_name']}{recr}\n"

                embed = discord.Embed(title=titulo, description=lista_texto, color=0x3498db)
                embed.set_footer(text=f"Página {idx + 1} de {len(chunks)} | Total: {total}")
                embeds.append(embed)

            view = RecentesPaginator(embeds, interaction.user.id)
            await interaction.followup.send(embed=embeds[0], view=view)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao listar: {e}", ephemeral=True)

    @app_commands.command(name="ranking", description="Mostra o Top 10 recrutadores que mais recrutaram")
    @e_moderador_ou_dono()
    async def ranking(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            # Busca todos os recruiter_id da tabela
            res = self.bot.supabase.table("recruitments").select("recruiter_id").execute()
            
            if not res.data:
                return await interaction.followup.send("📊 Ainda não há recrutamentos registrados.")

            # Contagem de ocorrências de cada recrutador
            contagem = {}
            for item in res.data:
                rid = item['recruiter_id']
                contagem[rid] = contagem.get(rid, 0) + 1

            # Ordena do maior para o menor e pega os top 10
            ranking_ordenado = sorted(contagem.items(), key=lambda x: x[1], reverse=True)[:10]

            descricao = ""
            medalhas = ["🥇", "🥈", "🥉", "👤", "👤", "👤", "👤", "👤", "👤", "👤"]

            for i, (recruiter_id, total) in enumerate(ranking_ordenado):
                medalha = medalhas[i] if i < len(medalhas) else "👤"
                descricao += f"{medalha} **{i+1}º** | <@{recruiter_id}> — `{total}` recrutados\n"

            embed = discord.Embed(
                title="🏆 Ranking de Recrutadores",
                description=descricao,
                color=0xf1c40f # Cor dourada
            )
            embed.set_footer(text="Continue o bom trabalho, Mudkip!")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao gerar ranking: {e}", ephemeral=True)

    @app_commands.command(name="excel", description="Gera uma planilha Excel com todos os recrutamentos")
    @e_moderador_ou_dono()
    async def excel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            import pandas as pd # Import interno para performance

            # 1. Busca todos os dados do banco
            res = self.bot.supabase.table("recruitments").select("*").order("registro_id", desc=False).execute()
            
            if not res.data:
                return await interaction.followup.send("⚠️ Não há dados para exportar.", ephemeral=True)

            # 2. Prepara a lista de dados formatada
            lista_exportacao = []
            for d in res.data:
                # Lógica de Classificação de Idade
                idade = int(d.get('recruit_age', 0))
                classificacao = ">18" if idade >= 18 else "<18"
                
                # Formatação da Data (Brasil)
                dt = datetime.fromisoformat(d['created_at'].replace('Z', '+00:00')) - timedelta(hours=3)
                data_formatada = dt.strftime('%d/%m/%Y %H:%M')

                # Nome do recrutador (registrado ou "Sem registro"), mantendo o ID
                recrutador_nome = d.get('recruiter_name') or self.get_recruiter_name(d.get('recruiter_id')) or "Sem registro"

                # Montagem do dicionário seguindo a ordem das colunas pedida
                item = {
                    "Recrutador": recrutador_nome,
                    "ID do discord do recrutador": d['recruiter_id'],
                    "Player": d.get('recruit_roblox_name'),
                    "Nickname": d.get('recruit_roblox_nick'),
                    "Plataforma": d.get('platform'),
                    "Data": data_formatada,
                    "Idade": idade,
                    "Classificação de Idade": classificacao,
                    "Gênero": d.get('gender'),
                    "Discord do recrutado": d.get('recruit_discord_nick'),
                    "ID do discord do recrutado": d.get('recruit_id')
                }
                lista_exportacao.append(item)

            # 3. Cria o DataFrame e o arquivo em memória
            df = pd.DataFrame(lista_exportacao)
            
            with io.BytesIO() as binary_excel:
                with pd.ExcelWriter(binary_excel, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Recrutamentos')
                
                binary_excel.seek(0)
                
                # 4. Envia o arquivo
                data_hoje = datetime.now().strftime('%d_%m_%Y')
                file = discord.File(fp=binary_excel, filename=f"Recrutamentos_{data_hoje}.xlsx")
                await interaction.followup.send("✅ Planilha gerada com sucesso!", file=file, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao gerar Excel: {e}", ephemeral=True)

    @app_commands.command(name="limpeza", description="Lista membros recrutados que saíram do servidor")
    @e_moderador_ou_dono()
    async def limpeza(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            # 1. Busca todos os recrutados registrados no Supabase
            res = self.bot.supabase.table("recruitments").select("recruit_id", "recruit_roblox_name", "registro_id").execute()
            
            if not res.data:
                return await interaction.followup.send("⚠️ Nenhuma ficha encontrada no banco de dados.")

            # 2. Filtra quem NÃO está no servidor
            fora_do_servidor = []
            guild = interaction.guild
            
            for item in res.data:
                membro_id = int(item['recruit_id'])
                # guild.get_member busca no cache do bot
                if guild.get_member(membro_id) is None:
                    fora_do_servidor.append(item)

            if not fora_do_servidor:
                return await interaction.followup.send("✅ Todos os recrutados registrados estão presentes no servidor!")

            # 3. Lógica de Paginação (chunks de 15 itens)
            chunks = [fora_do_servidor[i:i + 15] for i in range(0, len(fora_do_servidor), 15)]
            embeds = []

            for idx, chunk in enumerate(chunks):
                lista_texto = ""
                for item in chunk:
                    # Adicionado o ID de Registro e o ID do Discord logo abaixo/ao lado
                    lista_texto += f"**ID #{item['registro_id']}** - {item['recruit_roblox_name']}\n> ID Discord: `{item['recruit_id']}`\n\n"
                
                embed = discord.Embed(
                    title="🚪 Recrutados Fora do Servidor",
                    description=lista_texto,
                    color=0xe74c3c # Vermelho
                )
                embed.set_footer(text=f"Página {idx + 1} de {len(chunks)} | Total: {len(fora_do_servidor)}")
                embeds.append(embed)

            view = RecentesPaginator(embeds, interaction.user.id)
            await interaction.followup.send(embed=embeds[0], view=view)

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao realizar limpeza: {e}", ephemeral=True)

    @app_commands.command(name="delete", description="Exclui permanentemente uma ficha pelo ID de registro")
    @app_commands.describe(id_registro="O ID da ficha que deseja deletar")
    async def delete(self, interaction: discord.Interaction, id_registro: int):
        # IDs autorizados (sua whitelist)
        whitelist = [MEU_ID_DISCORD, 433385659760377856, 268690881551269888]

        if interaction.user.id not in whitelist:
            return await interaction.response.send_message("❌ Você não tem autorização especial para excluir registros.", ephemeral=True)

        # Verifica se a ficha existe
        res_check = self.bot.supabase.table("recruitments").select("recruit_roblox_name").eq("registro_id", id_registro).execute()
        
        if not res_check.data:
            return await interaction.response.send_message(f"❌ Ficha #{id_registro} não encontrada.", ephemeral=True)

        nome_recrutado = res_check.data[0]['recruit_roblox_name']

        # Envia embed de confirmação
        embed = discord.Embed(
            title="🚨 PROTOCOLO DE SEGURANÇA",
            description=f"Você está prestes a excluir a ficha **#{id_registro} ({nome_recrutado})**.\n\nClique no botão abaixo para iniciar o desbloqueio.",
            color=0xff0000
        )

        view = ConfirmDeleteView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # Espera o processo dos botões
        await view.wait()

        if view.confirmado:
            try:
                self.bot.supabase.table("recruitments").delete().eq("registro_id", id_registro).execute()
                await interaction.edit_original_response(content=f"🗑️ **Ficha #{id_registro} ({nome_recrutado}) foi removida com sucesso.**", embed=None, view=None)

                # --- LOG DE EXCLUSÃO ---
                canal_log = self.bot.get_channel(ID_CANAL_LOGS)
                if canal_log:
                    embed_log = discord.Embed(title="🗑️ Ficha Excluída", color=0xff4757, timestamp=datetime.now())
                    embed_log.add_field(name="ID da Ficha", value=f"#{id_registro}", inline=True)
                    embed_log.add_field(name="Recrutado", value=nome_recrutado, inline=True)
                    embed_log.add_field(name="Excluído por", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
                    await canal_log.send(embed=embed_log)

            except Exception as e:
                await interaction.edit_original_response(content=f"❌ Erro ao deletar: {e}", embed=None, view=None)
    
    @rec.error
    @ficha.error
    @edit.error
    @tab.error
    @ranking.error
    @excel.error
    @limpeza.error
    @delete.error
    async def global_permission_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ **Acesso Negado:** Você não tem permissão suficiente para usar este comando.", 
                ephemeral=True
            )
        else:
            print(f"Erro no comando: {error}")

async def setup(bot):
    await bot.add_cog(Recruitment(bot))