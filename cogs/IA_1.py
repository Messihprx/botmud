import discord
from discord import app_commands
from discord.ext import commands
from openai import OpenAI
from datetime import datetime, timezone
import re
import time

DONO_ID = 644667253324775454
TABELA_IA = "ai_config"


def mascara_chave(key: str) -> str:
    if not key:
        return "••••"
    if len(key) <= 10:
        return "•" * len(key)
    return f"{key[:6]}…{key[-4:]}"


def texto_da_resposta(completion, max_chars: int = 1800) -> str:
    """Extrai APENAS o texto final da resposta da IA.

    Nunca devolve o raciocínio interno (reasoning_content) — isso é lixo
    técnico e não deve aparecer no chat. Se o content vier nulo, logamos
    o diagnóstico e devolvemos vazio para o comando responder direitinho.
    """
    msg = completion.choices[0].message
    texto = (msg.content or "").strip()
    if texto:
        return texto[:max_chars]

    choice = completion.choices[0]
    reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
    print(
        f"[IA] Resposta veio SEM content | finish_reason={getattr(choice, 'finish_reason', '?')} "
        f"| reasoning={len(reasoning) if isinstance(reasoning, str) else 0} chars "
        f"| (raciocínio não exibido)"
    )
    return ""


def diagnostico_vazio(completion) -> str:
    """Linha curta de diagnóstico quando a IA responde sem content."""
    choice = completion.choices[0]
    msg = choice.message
    reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
    return (
        f"`finish_reason={getattr(choice, 'finish_reason', '?')}` · "
        f"`reasoning={len(reasoning) if isinstance(reasoning, str) else 0} chars`"
    )


class CadastroIAModal(discord.ui.Modal):
    """Formulário para cadastrar a IA (só o dono consegue abrir)."""

    def __init__(self, cog):
        super().__init__(title="Cadastro de IA")
        self.cog = cog

        self.base_url = discord.ui.TextInput(
            label="Base URL do provedor",
            placeholder="https://integrate.api.nvidia.com/v1",
            required=True,
            max_length=300,
        )
        self.api_key = discord.ui.TextInput(
            label="API Key",
            style=discord.TextStyle.paragraph,
            placeholder="Cole aqui a chave da API (NVIDIA, OpenAI, Groq, DeepSeek...)",
            required=True,
            max_length=500,
        )
        self.model = discord.ui.TextInput(
            label="Modelo",
            placeholder="meta/llama-3.3-70b-instruct",
            required=True,
            max_length=200,
        )
        self.add_item(self.base_url)
        self.add_item(self.api_key)
        self.add_item(self.model)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != DONO_ID:
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        base_url = str(self.base_url).strip().rstrip("/")
        api_key = str(self.api_key).strip()
        model = str(self.model).strip()

        ok, erro = self.cog.salvar_config(base_url, api_key, model)
        if not ok:
            return await interaction.followup.send(
                f"❌ Erro ao salvar no banco: `{erro}`\n\n"
                "Roda o SQL `migracao_ai_config.sql` no Supabase e tenta de novo.",
                ephemeral=True,
            )

        await interaction.followup.send(
            "✅ **IA cadastrada com sucesso!**\n\n"
            f"🧠 Modelo: `{model}`\n"
            f"🌐 Base URL: `{base_url}`\n"
            f"🔑 Chave: `{mascara_chave(api_key)}`\n\n"
            "Testa com `=ia_teste` e confere com `=ia_info`.",
            ephemeral=True,
        )


class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._cfg = None
        self._cfg_carregado = False
        self._client = None
        self._client_key = None

    # --- Cadastro da IA ---
    def carregar_config(self):
        if self._cfg_carregado:
            return self._cfg
        try:
            res = (
                self.bot.supabase.table(TABELA_IA)
                .select("base_url, api_key, model")
                .eq("id", "global")
                .execute()
            )
            self._cfg = res.data[0] if res.data else None
        except Exception as e:
            print(f"[IA] Erro ao ler '{TABELA_IA}': {e}")
            self._cfg = None
        self._cfg_carregado = True
        return self._cfg

    def salvar_config(self, base_url, api_key, model):
        payload = {
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            res = (
                self.bot.supabase.table(TABELA_IA)
                .update(payload)
                .eq("id", "global")
                .execute()
            )
            if not res.data:
                self.bot.supabase.table(TABELA_IA).insert({"id": "global", **payload}).execute()
        except Exception as e:
            print(f"[IA] Erro ao salvar '{TABELA_IA}': {e}")
            return False, str(e)

        self._cfg = {"base_url": base_url, "api_key": api_key, "model": model}
        self._cfg_carregado = True
        self._client = None
        self._client_key = None
        return True, None

    def ai(self):
        """Retorna (client, model) da IA cadastrada ou None."""
        cfg = self.carregar_config()
        if not cfg:
            return None
        chave = (cfg["base_url"], cfg["api_key"], cfg["model"])
        if self._client is None or self._client_key != chave:
            self._client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
            self._client_key = chave
        return self._client, cfg["model"]

    def sem_ia(self):
        return (
            "🤖 **Nenhuma IA cadastrada.**\n"
            "Só o dono pode cadastrar: use o comando `/ia_cadastrar`."
        )

    # --- Comandos de gestão (só o dono) ---
    @app_commands.command(name="ia_cadastrar", description="Abre o formulário para cadastrar a IA do bot (apenas o dono)")
    async def ia_cadastrar(self, interaction: discord.Interaction):
        if interaction.user.id != DONO_ID:
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        await interaction.response.send_modal(CadastroIAModal(self))

    @ia_cadastrar.error
    async def ia_cadastrar_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        else:
            print(f"[IA] Erro no /ia_cadastrar: {error}")

    @commands.command(name="ia_teste")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def ia_teste(self, ctx):
        """Testa se a IA cadastrada está respondendo (só o dono)"""
        if ctx.author.id != DONO_ID:
            return await ctx.reply("❌ Sem permissão.")

        ai = self.ai()
        if not ai:
            return await ctx.reply(self.sem_ia())

        client, model = ai
        cfg = self.carregar_config()
        await ctx.typing()
        inicio = time.time()

        def ping():
            return client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Responda apenas com a palavra: OK"}],
                temperature=0,
                max_tokens=400,
                stream=False,
            )

        try:
            resposta = await self.bot.loop.run_in_executor(None, ping)
        except Exception as e:
            detalhe = str(e)[:400]
            print(f"[IA] Erro no teste: {e}")
            return await ctx.reply(
                f"❌ **A IA não está funcionando.**\n\n"
                f"🧠 Modelo: `{model}`\n"
                f"🌐 Base URL: `{cfg['base_url']}`\n"
                f"⚠️ Erro: `{detalhe}`",
                mention_author=False,
            )

        latencia = round((time.time() - inicio) * 1000)
        texto = texto_da_resposta(resposta)

        if not texto:
            return await ctx.reply(
                f"⚠️ **A IA respondeu, mas veio VAZIA** (`content=None`).\n\n"
                f"🧠 Modelo: `{model}`\n"
                f"🌐 Base URL: `{cfg['base_url']}`\n"
                f"⚡ Latência: `{latencia}ms`\n"
                f"🔎 {diagnostico_vazio(resposta)}\n\n"
                f"Se `finish_reason=length`, o modelo gastou tudo no raciocínio — "
                f"troque por um modelo de chat normal ou um de raciocínio mais curto.",
                mention_author=False,
            )

        await ctx.reply(
            f"✅ **A IA está funcionando!**\n\n"
            f"🧠 Modelo: `{model}`\n"
            f"🌐 Base URL: `{cfg['base_url']}`\n"
            f"⚡ Latência: `{latencia}ms`",
            mention_author=False,
        )

    @commands.command(name="ia_info")
    async def ia_info(self, ctx):
        """Mostra a IA cadastrada (só o dono)"""
        if ctx.author.id != DONO_ID:
            return await ctx.reply("❌ Sem permissão.")

        cfg = self.carregar_config()
        if not cfg:
            return await ctx.reply(self.sem_ia())

        await ctx.reply(
            f"🧠 **IA cadastrada**\n\n"
            f"Modelo: `{cfg['model']}`\n"
            f"Base URL: `{cfg['base_url']}`\n"
            f"Chave: `{mascara_chave(cfg['api_key'])}`\n\n"
            f"Altere com `/ia_cadastrar`.",
            mention_author=False,
        )


    @commands.command(name="resumo")
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def resumo(self, ctx, quantidade: int = 50):
        """Resume o chat de forma engraçada (Sem Embed e com prefixo =)"""
        
        if quantidade > 100:
            return await ctx.reply("❌ O limite é de 100 mensagens para o resumo.")

        ai = self.ai()
        if not ai:
            return await ctx.reply(self.sem_ia())
        client, model = ai

        # Mostra que o bot está processando
        await ctx.typing()

        try:
            # 1. Coletar mensagens recentes
            messages_list = []
            async for msg in ctx.channel.history(limit=quantidade, before=ctx.message):
                # Ignora bots e comandos do próprio bot
                if not msg.author.bot and not msg.content.startswith(self.bot.command_prefix):
                    if msg.content.strip():
                        # Limpa menções para a IA não se confundir
                        clean_content = re.sub(r'<@!?\d+>', '', msg.content)
                        messages_list.append(f"{msg.author.display_name}: {clean_content}")

            if not messages_list:
                return await ctx.reply("⚠️ Não achei mensagens suficientes para fofocar.")

            history_text = "\n".join(reversed(messages_list))

            # 2. Lógica da IA (cadastrada via /ia_cadastrar)
            def get_ai_response():
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system", 
                            "content": (
                                "Você é um membro sarcástico, engraçado e levemente debochado de um clã no discord. "
                                "Seu objetivo é fazer um resumo curto e cômico do que as pessoas andam falando. "
                                "Use gírias, seja ácido se necessário e foque nas partes mais aleatórias. "
                                "Responda em alguns tópicos com o texto do resumo, sem introduções formais. Use emojis."
                            )
                        },
                        {"role": "user", "content": f"Resuma essas conversas de forma engraçada:\n\n{history_text}"}
                    ],
                    temperature=0.6,
                    top_p=0.7,
                    max_tokens=3000, # folga pra modelo de raciocínio terminar o texto final
                    stream=False
                )
                return texto_da_resposta(completion)

            # Executa sem travar o bot
            resumo_final = await self.bot.loop.run_in_executor(None, get_ai_response)

            if not resumo_final:
                return await ctx.reply("😵 A IA voltou em branco. Tenta de novo em alguns segundos!")

            # 3. Resposta em Texto Puro
            # Adicionei uma linha divisória para ficar organizado
            resposta = (
                f"📝 **Resumo das últimas {len(messages_list)} mensagens:**\n\n"
                f"{resumo_final}\n\n"
            )
            
            await ctx.reply(resposta, mention_author=False, delete_after=30)

        except Exception as e:
            print(f"Erro na IA: {e}")
            await ctx.reply("💥 A IA deu pau. Tenta de novo em alguns segundos ou roda `=ia_teste` pra ver o erro.")

    @commands.command(name="insulto")
    @commands.cooldown(1, 10, commands.BucketType.user) # 1 uso a cada 10s por usuário
    async def insulto(self, ctx, member: discord.Member = None):
        """Gera um insulto criativo e engraçado sobre alguém marcado"""

        if not member:
            return await ctx.reply("⚠️ Você precisa marcar alguém para eu poder esculachar! Ex: `=insulto @alguem`")

        if member.id == self.bot.user.id:
            return await ctx.reply("🤖 Tentando me insultar? Eu tenho uma IA no meu cérebro, você tem o quê? Um mouse de 10 reais?")

        res = self.bot.supabase.table("protected_users").select("user_id").eq("user_id", member.id).execute()

        # Verificação de segurança: Se o ID está na lista ou é o próprio bot
        if res.data:
            return await ctx.reply(f"Não tenho coragem para insultar o **{member.display_name}** 😅")

        ai = self.ai()
        if not ai:
            return await ctx.reply(self.sem_ia())
        client, model = ai

        await ctx.typing()

        try:
            def get_insult():
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system", 
                            "content": (
                                "Você é um mestre de insultos criativos, abstratos e extremamente engraçados. Compare mas não faça só isso "
                                "Seu objetivo é humilhar de forma cômica, sem usar palavrões ou ofensas pesadas. "
                                "Fuja de clichês (lento, burro, feio). Use comparações bizarras e específicas. "
                                "Exemplos de estilo: 'Você tem a presença de um pimentão cozido', 'Sua aura é de quem come pizza com colher', "
                                "'Você é o motivo pelo qual o shampoo vem com instruções'. "
                                "Seja curto, ácido e use gírias brasileiras modernas. "
                                "Seja criativo e não use os mesmos insultos genéricos que todo mundo já ouviu."
                                "Responda apenas com o texto do insulto."
                            )
                        },
                        {"role": "user", "content": f"Crie um insulto engraçado para o usuário chamado {member.display_name}"}
                    ],
                    temperature=0.9, # Mais alto para ser mais criativo nos xingamentos
                    max_tokens=2500, # folga pra modelo de raciocínio terminar o texto final
                    stream=False
                )
                return texto_da_resposta(completion)

            insulto_final = await self.bot.loop.run_in_executor(None, get_insult)

            if not insulto_final:
                return await ctx.reply("😵 Voltei semIdeia do que falar. Tenta de novo!")

            # Responde mencionando a pessoa para ela ver o esculacho
            await ctx.send(f"🔥 {member.mention}, {insulto_final}")

        except Exception as e:
            print(f"Erro no comando insulto: {e}")
            await ctx.reply("Minha criatividade deu curto-circuito. Sorte a sua!")
    
    @commands.command(name="proteger")
    async def proteger(self, ctx, member: discord.Member = None):
        DONO_ID = 644667253324775454
        if ctx.author.id != DONO_ID:
            return await ctx.reply("❌ Sem permissão.")

        target = member or ctx.author
        print(f" tentando proteger: {target.display_name} ({target.id})")

        try:
            # Usando insert em vez de upsert para testar, e garantindo que o ID é int
            data = {"user_id": int(target.id)}
            self.bot.supabase.table("protected_users").insert(data).execute()
            
            await ctx.reply(f"🛡️ **{target.display_name}** protegido!")
            print(f"✅ Sucesso ao proteger {target.id}")

        except Exception as e:
            # Se der erro de "Duplicate", o insert falha, então tentamos update
            try:
                self.bot.supabase.table("protected_users").update(data).eq("user_id", int(target.id)).execute()
                await ctx.reply(f"🛡️ **{target.display_name}** já estava protegido (atualizado)!")
            except Exception as e2:
                print(f"❌ ERRO CRÍTICO NO SUPABASE: {e2}")
                await ctx.reply(f"❌ Erro no banco de dados. Verifique se a tabela 'protected_users' existe.")

    @commands.command(name="desproteger")
    async def desproteger(self, ctx, member: discord.Member = None):
        DONO_ID = 644667253324775454
        if ctx.author.id != DONO_ID:
            return await ctx.reply("❌ Acesso negado.")

        target = member or ctx.author
        print(f" removendo proteção: {target.id}")

        try:
            self.bot.supabase.table("protected_users").delete().eq("user_id", int(target.id)).execute()
            await ctx.reply(f"🔓 **{target.display_name}** desprotegido!")
        except Exception as e:
            print(f"❌ Erro ao desproteger: {e}")
            await ctx.reply("❌ Erro ao remover do banco.")

    @commands.command(name="gay")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def gay_transform(self, ctx, *, texto: str = None):
        """Transforma um texto comum em algo fabuloso"""
        
        target_text = texto

        # Se não enviou texto, verifica se está respondendo a alguém
        if not target_text and ctx.message.reference:
            referenced_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            target_text = referenced_msg.content

        # Se ainda assim não tiver texto, dá o aviso
        if not target_text:
            return await ctx.reply("⚠️ Mona, eu preciso de um texto ou que você responda a alguma mensagem para eu dar um close nela! ✨")

        ai = self.ai()
        if not ai:
            return await ctx.reply(self.sem_ia())
        client, model = ai

        await ctx.typing()

        try:
            def get_fabulous_response():
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system", 
                            "content": (
                                "Você é uma diva absoluta, mestre das gírias LGBTQIA+ brasileiras (estilo 'pajubá' moderno). "
                                "Seu objetivo é reescrever a mensagem do usuário para deixá-la extremamente 'fabulosa', 'gay' e expressiva. "
                                "Use termos como: 'juro', 'migah', 'ai que tudo', 'babado', 'mona', 'grito', 'passada', 'poc', 'arrasou', 'belíssima'. "
                                "Abuse de emojis brilhantes e expressões de choque. "
                                "Mantenha o sentido original da mensagem, mas transforme o tom completamente. "
                                "Responda apenas com o texto transformado."
                            )
                        },
                        {"role": "user", "content": f"Deixe essa mensagem fabulosa: {target_text}"}
                    ],
                    temperature=0.9,
                    max_tokens=2500, # folga pra modelo de raciocínio terminar o texto final
                    stream=False
                )
                return texto_da_resposta(completion)

            texto_fabuloso = await self.bot.loop.run_in_executor(None, get_fabulous_response)

            if not texto_fabuloso:
                return await ctx.reply("Ai migah, a IA veio vazia. Tenta de novo!")

            # Resposta em texto puro conforme sua preferência anterior
            await ctx.reply(f"✨ **Versão Arrasadora:**\n\n{texto_fabuloso}", mention_author=False)

        except Exception as e:
            print(f"Erro no comando gay: {e}")
            await ctx.reply("Ai migah, desculpa, deu um tilt aqui e perdi meu brilho. Tenta de novo!")

async def setup(bot):
    await bot.add_cog(AI(bot))