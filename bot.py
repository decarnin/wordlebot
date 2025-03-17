import asyncio
import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord import Message
import config
from database.connection import get_session
from database.models import ServerData

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

async def get_prefix(bot: Bot, message: Message):
    session = get_session()
    server = session.query(ServerData).filter(ServerData.server_id == message.guild.id).first()
    session.close()
    return server.prefix if server else '!'

bot = commands.Bot(command_prefix = get_prefix, intents = intents)

initial_extensions = [
    'cogs.setup',
    'cogs.store_wordle',
    'cogs.stats',
    'cogs.leaderboard',
    'cogs.lookup',
    'cogs.misc'
]

@bot.event
async def on_ready() -> None:
    print(f'LOGGED IN AS {bot.user} (ID: {bot.user.id})')

async def main() -> None:
    bot.remove_command('help')
    async with bot:
        for extension in initial_extensions:
            await bot.load_extension(extension)
        await bot.start(config.DISCORD_BOT_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
