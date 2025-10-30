import discord
from discord.ext import commands
import asyncio
import config

intents = discord.Intents.default()

class GitHubBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(command_prefix="!", *args, **kwargs)

    async def on_ready(self):
        print(f'¡Conectado como {self.user} (ID: {self.user.id})!')
        print('------')
        
    async def setup_hook(self):
        """Carga los cogs antes de que el bot se conecte a Discord."""
        print("Cargando cogs...")
        await self.load_extension("cogs.github_webhooks")
        print("Cogs cargados.")


async def main():
    bot = GitHubBot(intents=intents)
    async with bot:
        await bot.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot detenido manualmente.")