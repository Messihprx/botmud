import discord
from discord.ext import commands
import asyncio
import os
import sys
import io
from supabase import create_client, Client
from changelog import VERSION
from dotenv import load_dotenv
import time

# 1. Carrega as variáveis do arquivo .env
load_dotenv()

# Configuração de Encoding para evitar erros de caracteres no console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
print("🌐 [LOGS] Console configurado para UTF-8 com line_buffering")

# 2. Resgata as variáveis de ambiente
TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- CONFIGURAÇÃO SUPABASE ---
try:
    supabase: Client = create_client(SUPABASE_URL or "", SUPABASE_KEY or "")
except Exception as e:
    supabase = None

class MessiBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.invites = True
        self.active_channels = set() # OBRIGATÓRIO
        self.user_languages = {}     # OBRIGATÓRIO
        # Inicializa o bot com o prefixo e intents, remove o help padrão
        super().__init__(command_prefix='=', intents=intents, help_command=None)
        
        # Compartilha a conexão do banco e caches com todos os Cogs
        self.supabase = supabase
        self.active_channels = set()
        self.user_languages = {}
        self.start_time = time.time()

    async def setup_hook(self):
        print("📂 Carregando módulos...")
        # Percorre a pasta cogs e carrega os arquivos .py
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Módulo carregado: {filename}')
                except Exception as e:
                    print(f'❌ Falha ao carregar {filename}: {e}')
        
        # Sincroniza os comandos de barra (/) com o Discord
        print("🔄 Sincronizando Slash Commands...")
        await self.tree.sync()

    async def on_ready(self):
        print(f'---')
        print(f'[SUCCESS] {self.user.name} está online!')
        print(f'[INFO] Versão: {VERSION}')
        print(f'---')
        
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening, name="=help"
        ))

    async def on_disconnect(self):
        print("⚠️ [CONEXÃO] Bot desconectou do Discord. Tentando reconectar...")

    async def on_resumed(self):
        print("✅ [CONEXÃO] Sessão retomada com sucesso!")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("🚫 Você não tem permissão para usar este comando.", delete_after=10)
        elif isinstance(error, commands.CommandNotFound):
            pass 
        else:
            print(f"Erro: {error}")

async def main():
    if not TOKEN:
        print("❌ [ERRO CRÍTICO] Variável DISCORD_TOKEN não encontrada. Verifique os Secrets do Hugging Face!")
        return
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ [ERRO CRÍTICO] Variáveis SUPABASE_URL ou SUPABASE_KEY não encontradas. Verifique os Secrets do Hugging Face!")
        return

    backoff = 5  # Começa esperando 5 segundos
    max_backoff = 60  # Máximo de 60 segundos entre tentativas

    while True:
        bot = MessiBot() # Recria o bot a cada tentativa para limpar sessões antigas
        try:
            async with bot:
                # reconnect=True = discord.py reconecta sozinho em quedas de WebSocket
                await bot.start(TOKEN, reconnect=True)
        except KeyboardInterrupt:
            print("Desligando o bot...")
            break
        except Exception as e:
            print(f"💥 [CRASH] Bot caiu com erro: {e}")
            print(f"🔄 Reconectando em {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)  # Backoff exponencial
        else:
            # bot.start() retornou sem erro (logout manual)
            print("Bot encerrado normalmente.")
            break

if __name__ == "__main__":
    asyncio.run(main())