import discord
from discord.ext import commands
from sqlalchemy.exc import SQLAlchemyError
from database.connection import get_session
from database.models import ServerData, ServerMembership
from util.util import add_user, add_server_membership

class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def relay_message(self, ctx: commands.Context, *, message: str) -> None:
        await ctx.send(message)

    @commands.command()
    async def update(self, ctx: commands.Context) -> None:
        user = ctx.author
        
        add_user(user)
        add_server_membership(user.id, ctx.guild.id, user.display_name)

        updated_user_embed = discord.Embed(color = discord.Color.blue())
        updated_user_embed.set_author(name = f'{user.display_name}\'s name and avatar has been updated', icon_url = user.avatar)
        await ctx.send(embed = updated_user_embed)

    @commands.has_permissions(administrator = True)
    @commands.command()
    async def updateserver(self, ctx: commands.Context) -> None:
        session = get_session()
        try:
            user_list = session.query(ServerMembership).filter(ServerMembership.server_id == ctx.guild.id).all()

            for user in user_list:
                if user.user_id not in [member.id for member in ctx.guild.members]:
                    session.delete(user)

            for member in ctx.guild.members:
                add_user(member)
                add_server_membership(member.id, ctx.guild.id, member.display_name)

            session.commit()

            update_server_embed = discord.Embed(color = discord.Color.blue())
            update_server_embed.set_author(name = f'{ctx.guild.name}\'s member list has been updated', icon_url = ctx.guild.icon)
            await ctx.send(embed = update_server_embed)

        except SQLAlchemyError as e:
            print(f'Database error: {e}')
            session.rollback()

        finally:
            session.close()

    @commands.command()
    async def help(self, ctx: commands.Context) -> None:

        session = get_session()
        try:
            server = session.query(ServerData).filter(ServerData.server_id == ctx.guild.id).first()
            prefix = server.prefix

        except SQLAlchemyError as e:
            print(f'Database error: {e}')
            session.rollback()

        finally:
            session.close()

        help_embed = discord.Embed(
            color = discord.Color.blue(),
            title = 'Command overview',
            description = (
                f'`{prefix}stats [@user]` - Display your Wordle stats (mention a user to see theirs)\n'
                f'`{prefix}leaderboard [daily|weekly|monthly|yearly|all time]` - Display the server leaderboard for a specific period (defaults to all time)\n'
                f'`{prefix}gleaderboard [daily|weekly|monthly|yearly|all time]` - Display the global leaderboard for a specific period (defaults to all time)\n'
                f'`{prefix}lookup <wordle_id|date(MM/DD/YY)> [@user]` - Lookup a specific Wordle (mention a user to look up their Wordle)\n'
                f'`{prefix}update` - Update your Discord username and avatar, and add yourself to the server database (this also happens automatically when submitting a Wordle)\n'
                f'`{prefix}manualreview` - Reply to a Wordle submission with this command to request a manual review\n'
                
                '\n**Admin commands**\n'
                f'`{prefix}updateserver` - Update the server member list\n'
                f'`{prefix}setprefix <new_prefix>` - Set a new command prefix (max 5 characters)\n'
                f'`{prefix}setchannel` - Set the designated Wordle channel (Wordles will only be accepted here)\n'

                f'\n`<>` = Required, `[]` = Optional, `|` = Or\n'

                '\n**Wordle submission info**\n'
                'When submitting a Wordle, a ✅ reaction indicates it was accepted and added to the database. A ❌ means it was rejected. '
                'Rejections occur if the Wordle is invalid or if you have already submitted it in this server.'
            )
        )
        await ctx.send(embed = help_embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Misc(bot))
    print('MISC COG LOADED')
