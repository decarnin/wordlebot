import discord
from discord.ext import commands
from sqlalchemy.exc import SQLAlchemyError
from database.connection import get_session
from database.models import ServerData
from util.util import add_user, add_server, add_server_membership


class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, server: discord.Guild) -> None:
        await add_server(server.id)

        for user in server.members:
            add_user(user)
            add_server_membership(user.id, server.id, user.display_name)

    @commands.has_permissions(administrator = True)
    @commands.command()
    async def setprefix(self, ctx: commands.Context, new_prefix: str) -> None:
        session = get_session()

        if len(new_prefix) > 5:
            prefix_error_embed = discord.Embed(
                color = discord.Color.red(),
                description = 'The new prefix must be 5 characters or less'
            )
            await ctx.send(embed = prefix_error_embed)
            return
        
        try:
            server = session.query(ServerData).filter(ServerData.server_id == ctx.guild.id).first()
            old_prefix = server.prefix
            server.prefix = new_prefix
            session.commit()

            set_prefix_embed = discord.Embed(
                color = discord.Color.blue(),
                title = 'New prefix set',
                description = f'Old prefix `{old_prefix}` -> New prefix `{new_prefix}`'
            )
            await ctx.send(embed = set_prefix_embed)

        except SQLAlchemyError as e:
            print(f'Database error: {e}')
            session.rollback()
            
        finally:
            session.close()

    @commands.has_permissions(administrator = True)
    @commands.command()
    async def setchannel(self, ctx: commands.Context) -> None:

        channel = ctx.channel
        session = get_session()
        try:
            server_data = session.query(ServerData).filter(ServerData.server_id == ctx.guild.id).first()

            server_data.wordle_channel_id = channel.id
            session.commit()

            set_channel_embed = discord.Embed(color = discord.Color.blue(), title = f'Wordle channel set to {channel.mention}')
            set_channel_embed.set_footer(text = 'Wordle\'s will only be accepted in this channel')

            await ctx.send(embed = set_channel_embed)

        except SQLAlchemyError as e:
            print(f'Database error: {e}')
            session.rollback()

        finally:
            session.close()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Setup(bot))
    print('SETUP COG LOADED')
