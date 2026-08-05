import discord
from discord.ext import commands
from deep_translator import GoogleTranslator
import time

class Translator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cache = {}  # Cache local para XP dos usuários
        self.global_buffer = 0  # Buffer para contagem global de traduções, reduzindo chamadas ao banco
        self.load_db_cache()
        self.flags = {
            "🇧🇷": "pt", "🇵🇹": "pt",
            "🇺🇸": "en", "🇬🇧": "en",
            "🇺🇲": "en",
            "🇪🇸": "es", "🇲🇽": "es",
            "🇪🇦": "es",
            "🇫🇷": "fr", "🇩🇪": "de",
            "🇮🇹": "it", "🇯🇵": "ja",
            "🇰🇷": "ko", "🇨🇳": "zh-CN",
            "🇵🇭": "tl", "🇷🇺": "ru"
        }
        

    def load_db_cache(self):
        """Carrega canais ativos e idiomas dos usuários para a memória"""
        try:
            # Canais
            c_res = self.bot.supabase.table("active_channels").select("channel_id").execute()
            self.bot.active_channels = {item['channel_id'] for item in c_res.data}
            
            # Idiomas
            u_res = self.bot.supabase.table("user_stats").select("user_id, preferred_lang").execute()
            for item in u_res.data:
                lang = item.get('preferred_lang')
                if lang and lang != "Nenhum":
                    self.bot.user_languages[item['user_id']] = lang
            print(f"✅ Cache carregado: {len(self.bot.active_channels)} canais e {len(self.bot.user_languages)} usuários.")
        except Exception as e:
            print(f"❌ Erro ao carregar cache: {e}")

    def add_xp(self, user_id, username):
        """Adiciona XP com sistema de buffer para evitar sobrecarga"""
        try:
            import time
            current_time = time.time()
            
            # 1. Inicializa o cache do usuário se não existir
            if user_id not in self.xp_cache:
                self.xp_cache[user_id] = {'xp': 0, 'username': username, 'last_update': current_time}
            
            # 2. Incrementa localmente (rápido, não usa internet)
            self.xp_cache[user_id]['xp'] += 1
            self.global_buffer += 1
            
            # 3. SÓ envia para o banco se passaram 30 segundos DESDE O ÚLTIMO UPDATE do usuário
            # Isso agrupa várias mensagens em uma única viagem ao banco
            if current_time - self.xp_cache[user_id]['last_update'] > 30:
                xp_ganho = self.xp_cache[user_id]['xp']
                
                # Busca o XP atual no banco
                res = self.bot.supabase.table("user_stats").select("xp").eq("user_id", str(user_id)).execute()
                
                if res.data:
                    total_xp = res.data[0]['xp'] + xp_ganho
                    self.bot.supabase.table("user_stats").update({
                        "xp": total_xp, 
                        "username": username
                    }).eq("user_id", str(user_id)).execute()
                else:
                    self.bot.supabase.table("user_stats").insert({
                        "user_id": str(user_id), 
                        "xp": xp_ganho, 
                        "username": username
                    }).execute()
                
                # Limpa o buffer do usuário
                self.xp_cache[user_id]['xp'] = 0
                self.xp_cache[user_id]['last_update'] = current_time

                # 4. Aproveita a "viagem" ao banco para atualizar o global se houver acúmulo
                if self.global_buffer > 0:
                    # Usamos uma query SQL direta (RPC) ou pegamos o atual e somamos tudo de uma vez
                    s_res = self.bot.supabase.table("stats").select("total_translations").eq("id", "global").single().execute()
                    if s_res.data:
                        novo_total = s_res.data['total_translations'] + self.global_buffer
                        self.bot.supabase.table("stats").update({"total_translations": novo_total}).eq("id", "global").execute()
                        self.global_buffer = 0

        except Exception as e:
            print(f"Erro ao processar XP (Cache Mode): {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith(self.bot.command_prefix):
            return

        if message.stickers or (not message.content.strip() and message.attachments):
            return

        if message.channel.id in self.bot.active_channels and message.author.id in self.bot.user_languages:
            user_langs = self.bot.user_languages[message.author.id]
            
            if not user_langs or str(user_langs).lower() in ["off", "nenhum", "não definido", "none"]:
                return

            text_to_translate = message.content.strip()

            import re
            text_to_translate = re.sub(r'http[s]?://\S+', '', text_to_translate).strip()
            text_clean = re.sub(r'<a?:\w+:\d+>|<@!?\d+>|<#\d+>', '', text_to_translate).strip()

            if not text_clean or len(text_clean) < 2:
                return

            # Limpa a lista e remove termos inválidos
            langs_to_translate = [l.strip().lower() for l in str(user_langs).split(",") if l.strip()]
            
            translated_any = False
            for lang in langs_to_translate:
                if lang in ["off", "nenhum", "não definido", "none", "nan", "on"]:
                    continue

                try:
                    translated = GoogleTranslator(source='auto', target=lang).translate(text_to_translate)
                    
                    if translated and translated.lower() != text_to_translate.lower():
                        content = f"**Tradução ({lang.upper()}):** {translated}"
                        await message.reply(content, mention_author=False, delete_after=60)
                        translated_any = True # AGORA o XP será contado
                except Exception as e:
                    if "No support" not in str(e):
                        print(f"Erro ao traduzir automático: {e}")

            if translated_any:
                self.add_xp(message.author.id, message.author.name)
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """REGRA 2: Tradução por reação (Backup sob demanda)"""
        # Ignora se for o próprio bot reagindo
        if payload.user_id == self.bot.user.id:
            return

        emoji = str(payload.emoji)
        if emoji not in self.flags:
            return

        target_lang = self.flags[emoji]
        channel = self.bot.get_channel(payload.channel_id)
        try:
            message = await channel.fetch_message(payload.message_id)
            if not message.content or len(message.content) < 2:
                return

            translated = GoogleTranslator(source='auto', target=target_lang).translate(message.content)
            
            if translated:
                no_ping = discord.AllowedMentions(users=False, roles=False, everyone=False)

                await message.reply(
                    f"🌍 **Tradução solicitada ({target_lang.upper()}):**\n{translated}",
                    mention_author=False, # Não marca o dono da mensagem original
                    allowed_mentions=no_ping,
                    delete_after=60       # Apaga após 1 minuto
                )
        except Exception as e:
            print(f"Erro na tradução por reação: {e}")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def activate(self, ctx):
        self.bot.active_channels.add(ctx.channel.id)
        self.bot.supabase.table("active_channels").upsert({"channel_id": ctx.channel.id}).execute()
        await ctx.reply("✅ Tradução automática ativada neste canal!")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def deactivate(self, ctx):
        if ctx.channel.id in self.bot.active_channels:
            self.bot.active_channels.remove(ctx.channel.id)
            self.bot.supabase.table("active_channels").delete().eq("channel_id", ctx.channel.id).execute()
            await ctx.reply("❌ Tradução automática desativada neste canal.")

    @commands.command(name="setlang")
    async def setlang(self, ctx, lang: str, member: discord.Member = None):
        """Define o idioma do usuário ou de outro membro (se for ADM)"""
        # Define quem é o alvo: o membro marcado ou quem digitou o comando
        target = member or ctx.author
        
        # Se tentou marcar alguém e não é ADM, barra a execução
        if member and member != ctx.author:
            if not ctx.author.guild_permissions.manage_guild:
                return await ctx.reply("🚫 Você precisa da permissão `Gerenciar Servidor` para alterar o idioma de outros membros.")

        lang = lang.lower()

        if lang == "off":
            if target.id in self.bot.user_languages:
                del self.bot.user_languages[target.id]
            
            self.bot.supabase.table("user_stats").update({
                "preferred_lang": "Nenhum"
            }).eq("user_id", target.id).execute()
            
            await ctx.reply(f"❌ Tradução automática desligada para **{target.display_name}**.")
        
        else:
            # Atualiza o cache local e o Banco de Dados usando o ID do TARGET
            self.bot.user_languages[target.id] = lang
            
            self.bot.supabase.table("user_stats").upsert({
                "user_id": target.id, 
                "preferred_lang": lang, 
                "username": target.name
            }).execute()
            
            await ctx.reply(f"✅ Idioma de **{target.display_name}** definido para `{lang.upper()}`.")

    @commands.command(name="translate")
    async def translate(self, ctx, lang: str, *, text: str = None):
        """Traduz um texto direto ou uma mensagem respondida (Prioriza o texto digitado)"""
        
        text_to_translate = None

        # 1. Verifica se o usuário digitou um texto após o idioma
        if text:
            text_to_translate = text
        
        # 2. Se não digitou texto, verifica se ele respondeu a uma mensagem
        elif ctx.message.reference:
            referenced_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            text_to_translate = referenced_msg.content

        # 3. Se nenhum dos dois existir, avisa o erro
        if not text_to_translate or text_to_translate.strip() == "":
            return await ctx.reply("❌ Use `=translate <idioma> <texto>` ou responda a uma mensagem.")

        try:
            translated = GoogleTranslator(source='auto', target=lang.lower()).translate(text_to_translate)
            
            embed = discord.Embed(color=0x3498db)
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.add_field(name=f"🌍 Tradução ({lang.upper()})", value=translated, inline=False)
            
            await ctx.reply(embed=embed, mention_author=False)
            self.add_xp(ctx.author.id, ctx.author.name)
            
        except Exception as e:
            await ctx.reply(f"❌ Erro ao traduzir: Verifique se o código do idioma `{lang}` está correto (ex: pt, en, es).")
           

    @commands.command(name="languages")
    async def languages_command(self, ctx):
        """Lista os idiomas suportados mais comuns"""
        langs = {
            "Português": "pt", "Inglês": "en", "Espanhol": "es", 
            "Francês": "fr", "Alemão": "de", "Italiano": "it", 
            "Japonês": "ja", "Coreano": "ko", "Chinês": "zh-CN",
            "Russo": "ru", "Árabe": "ar", "Holandês": "nl"
        }
        
        embed = discord.Embed(
            title="🌍 Idiomas Suportados",
            description="Use o código com `=setlang`.\nExemplo: `=setlang en`",
            color=0x3498db
        )

        texto_langs = "\n".join([f"**{n}:** `{s}`" for n, s in langs.items()])
        embed.add_field(name="Principais", value=texto_langs, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="addlang")
    async def addlang(self, ctx, lang: str):
        """Adiciona um segundo idioma para tradução automática"""
        user_id = ctx.author.id
        lang = lang.lower().strip()

        # Pega o que o usuário já tem no cache
        current_langs = self.bot.user_languages.get(user_id, "")

        if not current_langs or current_langs.lower() == "nenhum":
            return await ctx.reply("❌ Você ainda não tem um idioma principal definido. Use `=setlang <idioma>` primeiro.")

        # Transforma em lista para manipular
        lang_list = [l.strip() for l in current_langs.split(",") if l.strip()]

        if lang in lang_list:
            return await ctx.reply(f"❌ O idioma `{lang.upper()}` já está na sua lista.")

        if len(lang_list) >= 2:
            return await ctx.reply("🚫 Limite atingido! Você só pode ter no máximo **2 idiomas** simultâneos.")

        # Adiciona o novo idioma
        lang_list.append(lang)
        new_lang_string = ",".join(lang_list)

        # Atualiza Cache e Banco
        self.bot.user_languages[user_id] = new_lang_string
        self.bot.supabase.table("user_stats").update({
            "preferred_lang": new_lang_string,
            "username": ctx.author.name
        }).eq("user_id", user_id).execute()

        await ctx.reply(f"✅ `{lang.upper()}` adicionado! Agora traduzirei suas mensagens para: `{new_lang_string.upper()}`.")

    @commands.command(name="removelang")
    async def removelang(self, ctx, lang: str):
        """Remove um idioma da sua lista de traduções"""
        user_id = ctx.author.id
        lang = lang.lower().strip()

        current_langs = self.bot.user_languages.get(user_id, "")
        
        if not current_langs or current_langs.lower() == "nenhum":
            return await ctx.reply("❌ Você não tem idiomas configurados.")

        lang_list = [l.strip() for l in current_langs.split(",") if l.strip()]

        if lang not in lang_list:
            return await ctx.reply(f"❌ O idioma `{lang.upper()}` não está na sua lista.")

        # Remove da lista
        lang_list.remove(lang)
        
        if len(lang_list) == 0:
            new_lang_string = "Nenhum"
            if user_id in self.bot.user_languages:
                del self.bot.user_languages[user_id]
        else:
            new_lang_string = ",".join(lang_list)
            self.bot.user_languages[user_id] = new_lang_string

        # Atualiza Banco
        self.bot.supabase.table("user_stats").update({
            "preferred_lang": new_lang_string
        }).eq("user_id", user_id).execute()

        await ctx.reply(f"🗑️ `{lang.upper()}` removido. Idiomas restantes: `{new_lang_string.upper()}`.") 

    @commands.command(name="langs")
    async def list_languages(self, ctx):
        """Mostra os idiomas suportados em embeds organizados"""
        try:
            # Obtém os idiomas da API
            supported_languages = GoogleTranslator().get_supported_languages(as_dict=True)
            
            # Ordena por nome para facilitar a busca
            sorted_langs = dict(sorted(supported_languages.items()))
            
            # Criamos uma lista de strings formatadas
            all_langs = [f"**{name.title()}**: `{code}`" for name, code in sorted_langs.items()]
            
            # Dividimos em blocos de 30 idiomas para cada Embed
            chunk_size = 30
            chunks = [all_langs[i:i + chunk_size] for i in range(0, len(all_langs), chunk_size)]
            
            await ctx.send("## 🌍 Lista de Idiomas Suportados")

            for i, chunk in enumerate(chunks):
                embed = discord.Embed(
                    description="\n".join(chunk),
                    color=0x3498db
                )
                embed.set_footer(text=f"Página {i+1} de {len(chunks)} | Use o código para traduzir")
                await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Erro ao gerar lista: {e}")

async def setup(bot):
    await bot.add_cog(Translator(bot))