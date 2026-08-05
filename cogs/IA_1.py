import discord
from discord.ext import commands
from openai import OpenAI
import re

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configuração da NVIDIA
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="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"
        )
        self.model = "meta/llama-3.3-70b-instruct"

    @commands.command(name="resumo")
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def resumo(self, ctx, quantidade: int = 50):
        """Resume o chat de forma engraçada (Sem Embed e com prefixo =)"""
        
        if quantidade > 100:
            return await ctx.reply("❌ O limite é de 100 mensagens para o resumo.")

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

            # 2. Lógica da IA (NVIDIA Llama 3.3)
            def get_ai_response():
                completion = self.client.chat.completions.create(
                    model=self.model,
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
                    max_tokens=800,
                    stream=False
                )
                return completion.choices[0].message.content

            # Executa sem travar o bot
            resumo_final = await self.bot.loop.run_in_executor(None, get_ai_response)

            # 3. Resposta em Texto Puro
            # Adicionei uma linha divisória para ficar organizado
            resposta = (
                f"📝 **Resumo das últimas {len(messages_list)} mensagens:**\n\n"
                f"{resumo_final}\n\n"
            )
            
            await ctx.reply(resposta, mention_author=False, delete_after=30)

        except Exception as e:
            print(f"Erro na IA (NVIDIA): {e}")
            await ctx.reply("💥 Minhas engrenagens da NVIDIA travaram. Tente de novo em alguns segundos.")

    @commands.command(name="insulto")
    @commands.cooldown(1, 10, commands.BucketType.user) # 1 uso a cada 10s por usuário
    async def insulto(self, ctx, member: discord.Member = None):
        """Gera um insulto criativo e engraçado sobre alguém marcado"""

        res = self.bot.supabase.table("protected_users").select("user_id").eq("user_id", member.id).execute()

        # Verificação de segurança: Se o ID estiver na lista ou for o próprio bot
        if res.data or member.id == self.bot.user.id:
            return await ctx.reply(f"Não tenho coragem para insultar o **{member.display_name}** 😅")
        
        if not member:
            return await ctx.reply("⚠️ Você precisa marcar alguém para eu poder esculachar! Ex: `=insulto @alguem`")

        if member.id == self.bot.user.id:
            return await ctx.reply("🤖 Tentando me insultar? Eu tenho o Llama 3.3 no meu cérebro, você tem o quê? Um mouse de 10 reais?")

        await ctx.typing()

        try:
            def get_insult():
                completion = self.client.chat.completions.create(
                    model=self.model,
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
                    max_tokens=200,
                    stream=False
                )
                return completion.choices[0].message.content

            insulto_final = await self.bot.loop.run_in_executor(None, get_insult)
            
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

        await ctx.typing()

        try:
            def get_fabulous_response():
                completion = self.client.chat.completions.create(
                    model=self.model,
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
                    max_tokens=500,
                    stream=False
                )
                return completion.choices[0].message.content

            texto_fabuloso = await self.bot.loop.run_in_executor(None, get_fabulous_response)
            
            # Resposta em texto puro conforme sua preferência anterior
            await ctx.reply(f"✨ **Versão Arrasadora:**\n\n{texto_fabuloso}", mention_author=False)

        except Exception as e:
            print(f"Erro no comando gay: {e}")
            await ctx.reply("Ai migah, desculpa, deu um tilt aqui e perdi meu brilho. Tenta de novo!")

async def setup(bot):
    await bot.add_cog(AI(bot))