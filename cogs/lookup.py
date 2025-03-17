import discord
from discord.ext import commands
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from database.connection import get_session
from database.models import User, WordleData
from util.util import send_no_games_embed

class Lookup(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def decode_grid(wordle_grid: str) -> str:
        return wordle_grid.replace('W', '⬜').replace('B', '⬛').replace('Y', '🟨').replace('G', '🟩')

    @commands.command()
    async def lookup(self, ctx: commands.Context, message: str) -> None:
        session = get_session()
        try:
            user = ctx.author
            if ctx.message.mentions:
                user = ctx.message.mentions[0]
            user_data = session.query(User).filter(User.user_id == user.id).first()
            if user_data is None:
                await send_no_games_embed(ctx, user)
                return

            lookup_date = None
            if '/' in message:
                parts = message.split('/')
                try:
                    if len(parts[2]) == 2:
                        lookup_date = datetime.strptime(message, '%m/%d/%y').date()
                    else:
                        lookup_date = datetime.strptime(message, '%m/%d/%Y').date()
                except (ValueError, IndexError):
                    lookup_date = None
            elif '-' in message:
                parts = message.split('-')
                try:
                    if len(parts[2]) == 2:
                        lookup_date = datetime.strptime(message, '%m-%d-%y').date()
                    else:
                        lookup_date = datetime.strptime(message, '%m-%d-%Y').date()
                except (ValueError, IndexError):
                    lookup_date = None
            else:
                message = f'{int(message):,}'

            if lookup_date:
                wordle_data = session.query(WordleData).filter(
                    WordleData.user_id == user.id,
                    WordleData.wordle_date == lookup_date
                ).first()
            else:
                wordle_data = session.query(WordleData).filter(
                    WordleData.user_id == user.id,
                    WordleData.wordle_id == message
                ).first()

            if wordle_data is None:
                error_embed = discord.Embed(color = discord.Color.red())
                if lookup_date:
                    error_embed.set_author(name = f'{user.display_name} has not played Wordle on {lookup_date}', icon_url = user.avatar)
                else:
                    error_embed.set_author(name = f'{user.display_name} has not played Wordle {message}', icon_url = user.avatar)
                await ctx.send(embed = error_embed)
                return

            wordle_id = wordle_data.wordle_id
            wordle_score = wordle_data.wordle_score
            wordle_grid = self.decode_grid(wordle_data.wordle_grid)
            formatted_date = wordle_data.wordle_date.strftime('%m/%d/%Y')

            embed = discord.Embed(
                color = discord.Color.green(),
                title = f'Wordle {wordle_id} {wordle_score}/6',
                description = f'{wordle_grid}'
            )
            embed.set_author(name = user.display_name, icon_url = user.avatar)
            embed.set_footer(text = formatted_date)

            await ctx.send(embed = embed)

        except SQLAlchemyError as e:
            print(f'Database error: {e}')
        finally:
            session.close()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Lookup(bot))
