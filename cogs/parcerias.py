import discord
from discord import app_commands
from discord.ext import commands
import asyncio

class ParceriaModal(discord.ui.Modal, title='Configurar Nova Parceria'):
    clan_name = discord.ui.TextInput(label='Nome do Clã Parceiro', placeholder='Ex: MUDKIPS', max_length=23)
    tag = discord.ui.TextInput(label='Tag do Clã', placeholder='Ex: MD', max_length=6)

    def __init__(self, bot, role):
        super().__init__()
        self.bot = bot
        self.role = role

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Gerar Link Permanente
        invite = await interaction.channel.create_invite(
            max_age=0, # Nunca expira
            max_uses=0, # Usos ilimitados
            unique=True,
            reason=f"Parceria: {self.clan_name.value}"
        )

        # 2. Salvar no Supabase
        data = {
            "invite_code": invite.code,
            "role_id": self.role.id,
            "tag": self.tag.value,
            "clan_name": self.clan_name.value
        }
        
        try:
            self.bot.supabase.table("parcerias").insert(data).execute()
            
            embed = discord.Embed(title="🤝 Parceria Registrada!", color=discord.Color.green())
            embed.add_field(name="Clã", value=self.clan_name.value)
            embed.add_field(name="Tag", value=f"`{self.tag.value}`")
            embed.add_field(name="Cargo", value=self.role.mention)
            embed.add_field(name="Link", value=invite.url)
            
            await interaction.response.send_message(f"Link gerado com sucesso para {self.clan_name.value}!", embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao salvar no banco: {e}", ephemeral=True)

class ConfirmarRemocao(discord.ui.View):
    def __init__(self, invite_code):
        super().__init__(timeout=30)
        self.value = None
        self.invite_code = invite_code

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()

class Parcerias(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    # Evento para carregar convites assim que o bot estiver pronto
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                self.invites[guild.id] = await guild.invites()
                print(f"✅ Convites carregados para: {guild.name}")
            except:
                print(f"❌ Sem permissão de convites em: {guild.name}")

    @app_commands.command(name="addparceria", description="Cria um link de parceria")
    @app_commands.describe(cargo="Cargo que o membro receberá")
    @commands.has_permissions(administrator=True)
    async def addparceria(self, interaction: discord.Interaction, cargo: discord.Role):
        # Atualiza o cache antes de abrir o modal para garantir que o link novo seja notado dps
        self.invites[interaction.guild.id] = await interaction.guild.invites()
        await interaction.response.send_modal(ParceriaModal(self.bot, cargo))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # 1. Tenta identificar o convite usado
        invites_before = self.invites.get(member.guild.id, [])
        try:
            invites_after = await member.guild.invites()
        except:
            return # Bot sem permissão

        # Atualiza o cache para a próxima entrada
        self.invites[member.guild.id] = invites_after

        used_invite = None
        for inv in invites_before:
            for af in invites_after:
                if inv.code == af.code and af.uses > inv.uses:
                    used_invite = af
                    break
        
        if not used_invite:
            return

        # 2. Busca no Supabase
        res = self.bot.supabase.table("parcerias").select("*").eq("invite_code", used_invite.code).execute()
        
        if res.data:
            config = res.data[0]
            tag = config['tag']
            role_id = int(config['role_id']) # Garantir que é int
            ID_CANAL_LOGS = 1348395276754227241

            # 3. Execução das ações
            try:
                # Remove o cargo de "esperando set" se ele existir
                # Substitua pelo ID real do seu cargo de restrição
                ID_CARGO_RESTRITO = 1261978807917875251
                cargo_restrito = member.guild.get_role(ID_CARGO_RESTRITO)
                if cargo_restrito in member.roles:
                    await member.remove_roles(cargo_restrito)

                # Adiciona o cargo da parceria
                role = member.guild.get_role(role_id)
                if role:
                    await member.add_roles(role)

                # Muda o Nick
                novo_nome = f"{tag} | {member.display_name}"
                await member.edit(nick=novo_nome[:32])

                canal_log = member.guild.get_channel(ID_CANAL_LOGS)
                if canal_log:
                    embed = discord.Embed(title="📥 Nova Entrada via Parceria", color=discord.Color.green())
                    embed.add_field(name="Membro", value=f"{member.mention} (`{member.id}`)", inline=True)
                    embed.add_field(name="Parceria", value=f"**{config['clan_name']}**", inline=True)
                    embed.add_field(name="Tag Aplicada", value=f"`{tag}`", inline=True)
                    await canal_log.send(embed=embed)
                
            except Exception as e:
                print(f"Erro ao processar entrada de parceria: {e}")

    # --- COMANDO SLASH PARA LISTAR PARCERIAS ---
    @app_commands.command(name="listarparcerias", description="Lista todas as parcerias registradas e estatísticas")
    @commands.has_permissions(administrator=True)
    async def listarparcerias(self, interaction: discord.Interaction):
        await interaction.response.defer() # Defer pois a busca no banco + contagem pode demorar

        try:
            # 1. Busca todas as parcerias no Supabase
            res = self.bot.supabase.table("parcerias").select("*").execute()
            
            if not res.data:
                return await interaction.followup.send("⚠️ Nenhuma parceria registrada no banco de dados.")

            embed = discord.Embed(
                title="🤝 Relatório de Parcerias Ativas",
                color=discord.Color.blue(),
                timestamp=interaction.created_at
            )

            for p in res.data:
                invite_code = p['invite_code']
                tag = p['tag']
                clan_name = p['clan_name']
                role_id = int(p['role_id'])
                
                # 2. Busca o cargo e conta os membros
                role = interaction.guild.get_role(role_id)
                qtd_membros = len(role.members) if role else 0
                mencion_cargo = role.mention if role else "⚠️ Cargo Excluído"
                
                # 3. Monta o link completo
                link_url = f"https://discord.gg/{invite_code}"

                # Adiciona o campo no embed
                embed.add_field(
                    name=f"🏰 {clan_name} [{tag}]",
                    value=(
                        f"🔗 **Link:** {link_url}\n"
                        f"🏷️ **Cargo:** {mencion_cargo}\n"
                        f"👥 **Membros atuais:** `{qtd_membros}`"
                    ),
                    inline=False
                )

            embed.set_footer(text=f"Total de {len(res.data)} parcerias registradas")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Erro ao listar parcerias: {e}")
            await interaction.followup.send(f"❌ Ocorreu um erro ao buscar os dados: {e}")

    @app_commands.command(name="removerparceria", description="Apaga uma parceria do sistema com confirmação")
    @app_commands.describe(codigo="O código final do link (ex: gx4vR29)")
    @commands.has_permissions(administrator=True)
    async def removerparceria(self, interaction: discord.Interaction, codigo: str):
        codigo_limpo = codigo.split("/")[-1]

        # Cria a interface de botões
        view = ConfirmarRemocao(codigo_limpo)
        
        await interaction.response.send_message(
            f"⚠️ Você tem certeza que deseja remover a parceria `{codigo_limpo}`? \nIsso apagará o registro no banco e o link no Discord.",
            view=view,
            ephemeral=True # Apenas você vê a confirmação
        )

        # Espera o usuário clicar em um botão
        await view.wait()

        if view.value is None:
            await interaction.edit_original_response(content="⏳ Tempo esgotado. A remoção foi cancelada.", view=None)
        elif view.value:
            try:
                # 1. Deleta no Supabase
                res = self.bot.supabase.table("parcerias").delete().eq("invite_code", codigo_limpo).execute()
                
                if res.data:
                    # 2. Tenta deletar o convite no Discord
                    invites = await interaction.guild.invites()
                    for inv in invites:
                        if inv.code == codigo_limpo:
                            await inv.delete(reason="Parceria removida via comando.")
                    
                    # Atualiza o cache do bot
                    self.invites[interaction.guild.id] = await interaction.guild.invites()
                    
                    await interaction.edit_original_response(content=f"✅ Parceria `{codigo_limpo}` removida com sucesso!", view=None)
                else:
                    await interaction.edit_original_response(content="❌ Código não encontrado no banco de dados.", view=None)
            except Exception as e:
                await interaction.edit_original_response(content=f"❌ Erro ao remover: {e}", view=None)
        else:
            await interaction.edit_original_response(content="❌ Remoção cancelada pelo usuário.", view=None)

async def setup(bot):
    await bot.add_cog(Parcerias(bot))