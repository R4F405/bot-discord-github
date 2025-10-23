# main.py
import discord
from discord.ext import commands
import asyncio
import config  # Importamos nuestra configuración

# Definimos los intents necesarios.
intents = discord.Intents.default()

class GitHubBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        # <--- 3. AÑADIR command_prefix A LA LLAMADA SUPER()
        # commands.Bot requiere un prefijo de comando, incluso si no 
        # usamos comandos de texto (como !hola).
        super().__init__(command_prefix="!", *args, **kwargs)

    async def on_ready(self):
        print(f'¡Conectado como {self.user} (ID: {self.user.id})!')
        print('------')
        
    async def setup_hook(self):
        """
        Este método se llama antes de que el bot se conecte a Discord.
        Es el lugar perfecto para cargar cogs y arrancar servicios de fondo.
        """
        print("Cargando cogs...")
        # Esta línea ahora funcionará
        await self.load_extension("cogs.github_webhooks")
        print("Cogs cargados.")


async def main():
    # Pasamos 'intents' como un kwarg, que será recibido por 
    # el __init__ de commands.Bot
    bot = GitHubBot(intents=intents)
    async with bot:
        await bot.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot detenido manualmente.")