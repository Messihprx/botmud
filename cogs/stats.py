import discord
from discord.ext import commands, tasks
from changelog import VERSION
from datetime import datetime, timedelta, time
from openai import OpenAI

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configuração da IA para gerar os parabéns
        self.ai_client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="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"
        )
        self.check_birthdays.start()
    
    def cog_unload(self):
        self.check_birthdays.cancel()

    # Função auxiliar para gerar texto com IA e formatar menções
    async def gerar_texto_aniversario(self, user_id, tipo="hoje"):
        # ID do cargo que você vai definir
        ID_CARGO_MUDKIP = 1261978783498371106 

        # Busca o objeto do usuário para pegar o nome para a IA
        user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        nome_user = user.display_name if user else f"Membro"

        prompt_hoje = f"Gere um parabéns de aniversário engraçado, curto e sarcástico para {nome_user}. Use gírias brasileiras e emojis. E não considere gênero."
        prompt_amanha = f"Gere um aviso curto e fofoqueiro dizendo que amanhã é o aniversário de {nome_user}. Avise o clã MUDKIP para se preparar. E não considere gênero."
        
        system_msg = "Você é um membro zoeiro de um clã chamado MUDKIP. Seu tom é engraçado e amigável ao mesmo tempo."
        prompt_final = prompt_hoje if tipo == "hoje" else prompt_amanha

        try:
            def call_ai():
                completion = self.ai_client.chat.completions.create(
                    model="meta/llama-3.3-70b-instruct",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt_final}
                    ],
                    temperature=0.8,
                    max_tokens=200
                )
                return completion.choices[0].message.content

            texto_ia = await self.bot.loop.run_in_executor(None, call_ai)
            
            # Retorna o texto da IA + Menção do Usuário + Menção do Cargo
            return f"{texto_ia}\n\n🎈 <@{user_id}> | <@&{ID_CARGO_MUDKIP}>"

        except Exception as e:
            print(f"Erro na IA de niver: {e}")
            return f"Parabéns <@{user_id}>! 🎉 | <@&{ID_CARGO_MUDKIP}>" if tipo == "hoje" else f"Amanhã é niver de <@{user_id}>! | <@&{ID_CARGO_MUDKIP}>"

    # --- SISTEMA DE ANIVERSÁRIOS ---

    @commands.command(name="niver")
    async def niver(self, ctx, *, busca: str = None):
        # ... (Código do comando niver que você já tem)
        # (Mantive a lógica de registro e consulta @alguem intacta)
        if busca and (ctx.message.mentions or busca.isdigit() is False and "/" not in busca and " " not in busca):
            target = ctx.message.mentions[0] if ctx.message.mentions else None
            if not target: return await ctx.reply("❌ Não encontri.")
            res = self.bot.supabase.table("user_stats").select("birthday").eq("user_id", target.id).execute()
            if res.data and res.data[0].get('birthday'):
                return await ctx.reply(f"🎂 O niver de **{target.display_name}** é **{res.data[0]['birthday']}**.")
            return await ctx.reply(f"⚠️ Sem registro para **{target.display_name}**.")

        if not busca: return await ctx.reply("❓ Ex: `=niver 5 5` ou `=niver @alguem`.")
        try:
            data_limpa = busca.replace("/", " ").split()
            dia, mes = int(data_limpa[0]), int(data_limpa[1])
            niver_formatado = datetime(2024, mes, dia).strftime("%d/%m")
            self.bot.supabase.table("user_stats").upsert({"user_id": ctx.author.id, "birthday": niver_formatado}).execute()
            await ctx.reply(f"✅ Registrado: **{niver_formatado}**!")
        except: await ctx.reply("❌ Data inválida.")

    @tasks.loop(time=[time(hour=3, minute=0)]) 
    async def check_birthdays(self):
        agora = datetime.utcnow() - timedelta(hours=3)
        hoje = agora.strftime("%d/%m")
        amanha = (agora + timedelta(days=1)).strftime("%d/%m")
        
        ID_CANAL_AVISO_PREVIO = 1261978949441945620 
        ID_CANAL_PARABENS = 1261978898212851774      

        canal_previa = self.bot.get_channel(ID_CANAL_AVISO_PREVIO)
        canal_parabens = self.bot.get_channel(ID_CANAL_PARABENS)

        # 1. Busca HOJE
        res_hoje = self.bot.supabase.table("user_stats").select("user_id").eq("birthday", hoje).execute()
        for entry in res_hoje.data:
            # A função gerar_texto_aniversario agora cuida das menções
            msg = await self.gerar_texto_aniversario(int(entry['user_id']), "hoje")
            if canal_parabens:
                await canal_parabens.send(msg)

        # 2. Busca AMANHÃ
        res_amanha = self.bot.supabase.table("user_stats").select("user_id").eq("birthday", amanha).execute()
        for entry in res_amanha.data:
            msg = await self.gerar_texto_aniversario(int(entry['user_id']), "amanha")
            if canal_previa:
                await canal_previa.send(msg)

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()

    def get_status(self, xp):
        """Retorna o título baseado no XP (Versão Mudkip)"""
        if xp < 50: return "Mudkip tradutor novato"
        if xp < 150: return "Mudkip tradutor Aprendiz"
        if xp < 400: return "Mudkip Tradutor Fluente"
        if xp < 1000: return "Mudkip Mestre Poliglota"
        return "Lenda das Línguas da Mudkipédia"

    @commands.command()
    async def top(self, ctx):
        """Exibe o ranking e a posição atual do autor"""
        # 1. Busca o Top 10 para o embed
        res = self.bot.supabase.table("user_stats").select("user_id, xp").order("xp", desc=True).execute()
        
        if not res.data:
            return await ctx.reply("📊 Ranking vazio.")

        # 2. Encontrar a posição do autor no ranking geral
        user_rank = "N/A"
        user_xp = 0
        for index, entry in enumerate(res.data):
            if entry['user_id'] == ctx.author.id:
                user_rank = index + 1
                user_xp = entry['xp']
                break

        # 3. Montar a lista visual do Top 10
        top_10 = res.data[:10]
        embed = discord.Embed(
            title="🏆 Ranking de Poliglotas", 
            description="Os maiores tradutores da Mudkipédia",
            color=0xf1c40f
        )
        
        lb_text = ""
        for i, u in enumerate(top_10):
            emoji = ["🥇", "🥈", "🥉", "👤"][i] if i < 3 else "👤"
            # Destaca o autor na lista se ele estiver no top 10
            line = f"{emoji} **{i+1}.** <@{u['user_id']}> — `{u['xp']} pts`"
            if u['user_id'] == ctx.author.id:
                line = f"➡️ {line} **(VOCÊ)**"
            lb_text += line + "\n"
        
        embed.add_field(name="Top 10 Usuários", value=lb_text, inline=False)

        # 4. Adicionar campo com a posição atual do autor (Sua Posição)
        embed.add_field(
            name="📍 Sua Posição", 
            value=f"Você está em **#{user_rank}** com **{user_xp} XP**", 
            inline=False
        )

        embed.set_footer(text=f"Messi Bot | Versão {VERSION}")
        await ctx.send(embed=embed)

    @commands.command(name="perfil")
    async def perfil(self, ctx, member: discord.Member = None):
        """Exibe um card de perfil elegante do tradutor"""
        target = member or ctx.author
        res = self.bot.supabase.table("user_stats").select("xp, preferred_lang").eq("user_id", target.id).execute()
        
        if res.data:
            xp = res.data[0].get('xp', 0)
            lang = res.data[0].get('preferred_lang', 'Nenhum')
        else:
            xp = 0
            lang = "Nenhum"
        
        level = (xp // 50) + 1
        xp_pro_proximo = 50 - (xp % 50)
        
        bar_size = 10
        progress = (xp % 50) / 50
        filled_chars = int(progress * bar_size)
        bar = "🟦" * filled_chars + "⬛" * (bar_size - filled_chars)
        percent = int(progress * 100)

        embed = discord.Embed(
            title=f"✨ Registro de Tradutor",
            description=f"Informações oficiais de {target.mention}",
            color=0x7289da 
        )
        
        embed.add_field(name="🏆 Título Atual", value=f"**{self.get_status(xp)}**", inline=True)
        embed.add_field(name="⭐ Nível", value=f"` LVL {level} `", inline=True)
        embed.add_field(name="📊 Experiência Total", value=f"**{xp}** XP", inline=True)
        embed.add_field(
            name="📈 Progresso do Nível", 
            value=f"{bar} `{percent}%` \n*Faltam {xp_pro_proximo} XP para o nível {level + 1}*", 
            inline=False
        )
        embed.add_field(name="🌐 Idioma Definido", value=f"`{lang.upper()}`", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        data_entrada = target.joined_at.strftime('%d/%m/%Y') if target.joined_at else "Desconhecida"
        embed.set_footer(text=f"Membro desde {data_entrada}", icon_url=self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Stats(bot))