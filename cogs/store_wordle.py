import discord
from discord.ext import commands
from util.util import add_user, add_server_membership, add_wordle, add_wordle_server_membership
from zoneinfo import ZoneInfo
from sqlalchemy.exc import SQLAlchemyError
from database.connection import get_session
from database.models import WordleData, ServerData, WordleServerMembership
import re
import random


class StoreWordle(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        session = get_session()
        try:
            server = session.query(ServerData).filter(ServerData.server_id == message.guild.id).first()
            wordle_channel_id = server.wordle_channel_id if server else None
        finally:
            session.close()

        if not wordle_channel_id or message.channel.id != wordle_channel_id:
            return

        await self.store_wordle_info(message)

    @commands.command()
    async def manualreview(self, ctx: commands.Context) -> None:
        original_message = ctx.message.reference.resolved
        wordle_info = self.extract_wordle_info(original_message.content)

        if wordle_info:
            if self.verify_wordle_info(wordle_info[1], wordle_info[2]):
            
                emojis = ('⚠️', '🚨', '🚩')
                emoji = random.choice(emojis)
                embed = discord.Embed(
                    color = discord.Color.red(),
                    title = f'{emoji} MANUAL REVIEW REQUESTED {emoji}',
                    description = (
                    f'USER: {original_message.author.mention}\n'
                    f'REQUESTED BY: {ctx.author.mention}\n')
                )
                await original_message.reply(embed = embed)

    async def check_for_suspicious_wordle(self, message: discord.Message, wordle_score: str, wordle_grid: str) -> None:
        # If it's 4 or above, consider them safe
        if wordle_score in ['4', '5', '6', 'X']:
            return

        if wordle_score == '1':
            await self.system_flag(message, 'cheater')
            return

        cols = [wordle_grid[i:i+5] for i in range(0, len(wordle_grid), 5)]
        suspicion_score = 0

        if wordle_score == '2':
            suspicion_score += 2
        else: # wordle_score == '3':
            suspicion_score += 1
        if cols[0].count('G') + cols[0].count('Y') >= 4:
            suspicion_score += 2
        if len(cols) > 1:
            if cols[1].count('G') + cols[1].count('Y') >= 4:
                suspicion_score += 1

        suspicion_score += random.choice([-1, 0, 0, 1])

        if suspicion_score <= 1:
            return
        elif suspicion_score == 2:
            if random.random() < 0.5:
                await self.system_flag(message, 'flag')
                return
        elif suspicion_score == 3:
            if random.random() < 0.75:
                await self.system_flag(message, 'flag')
                return
        elif suspicion_score == 4:
            await self.system_flag(message, 'flag')
            return
        else: # suspicion_score >= 5
            await self.system_flag(message, 'cheater')

    async def system_flag(self, message: discord.Message, type: str) -> None:
        emojis = ('⚠️', '🚨', '🚩')
        emoji = emojis[random.randint(0, len(emojis) - 1)]

        if type == 'flag':
            embed_title = f'{emoji} ALERT: SYSTEM FLAG DETECTED {emoji}'
            embed_description = (
                f'USER: {message.author.mention}\n'
                'YOU HAVE BEEN FLAGGED FOR A MANUAL REVIEW\n')
        elif type == 'cheater':
            embed_title = f'{emoji} ALERT: WAC HAS DETECTED A CHEATER {emoji}'
            embed_description = (
                f'USER: {message.author.mention}\n'
                'YOU HAVE BEEN FLAGGED FOR A MANUAL REVIEW\n')
        system_flag_embed = discord.Embed(
            color = discord.Color.red(),
            title = embed_title,
            description = embed_description
        )
        await message.reply(embed = system_flag_embed)

    @staticmethod
    def extract_wordle_info(text: str) -> tuple | None:
        regex_pattern = r'^Wordle\s+(\d{1,3}(?:,\d{3})*)\s+([1-6X])\/6\s*\r?\n\r?\n((?:[⬜⬛🟨🟩]{5}\r?\n){0,5}[⬜⬛🟨🟩]{5})(?:\r?\n.*)?$'
        match = re.search(regex_pattern, text)
        if match:
            wordle_id, wordle_score, wordle_grid = match.groups()
            wordle_grid = wordle_grid.replace('⬜', 'W').replace('⬛', 'B').replace('🟨', 'Y').replace('🟩', 'G')
            return wordle_id, wordle_score, wordle_grid
        return None

    @staticmethod
    def verify_wordle_info(wordle_score: str, wordle_grid: str) -> bool:
        lines = wordle_grid.strip().splitlines()
        rows = len(lines)
        allowed = {'W', 'B', 'Y', 'G'}
        for line in lines:
            if len(line) != 5 or any(char not in allowed for char in line):
                return False
        if wordle_score == 'X':
            if rows != 6 or lines[-1] == 'G' * 5:
                return False
        else:
            expected_rows = int(wordle_score)
            if rows != expected_rows or lines[-1] != 'G' * 5:
                return False
        return True

    async def store_wordle_info(self, message: discord.Message) -> None:
        wordle_info = self.extract_wordle_info(message.content)
        if wordle_info is None:
            return

        user = message.author
        user_id = user.id
        server_id = message.guild.id
        wordle_id, wordle_score, wordle_grid = wordle_info
        pst_time = message.created_at.astimezone(ZoneInfo('America/Los_Angeles'))
        wordle_date = f'{pst_time.year}/{pst_time.month}/{pst_time.day}'

        if not self.verify_wordle_info(wordle_score, wordle_grid):
            await message.add_reaction('❌')
            return
        
        session = get_session()
        try:
            existing_wordle = session.query(WordleData).filter(WordleData.user_id == user_id, WordleData.wordle_id == wordle_id).first()
            if existing_wordle:
                server_submission = session.query(WordleServerMembership).filter(
                    WordleServerMembership.user_id == user_id,
                    WordleServerMembership.server_id == server_id,
                    WordleServerMembership.wordle_id == wordle_id).first()
                
                if server_submission:
                    await message.add_reaction('❌')
                else:
                    if wordle_grid != existing_wordle.wordle_grid:
                        await message.add_reaction('❌')
                    else:
                        add_wordle_server_membership(user_id, server_id, wordle_id)
                        await message.add_reaction('✅')
                        await self.check_for_suspicious_wordle(message, wordle_score, wordle_grid)
            else:
                add_user(user)
                add_server_membership(user_id, server_id, user.display_name)
                add_wordle(user_id, wordle_id, wordle_score, wordle_grid, wordle_date)
                add_wordle_server_membership(user_id, server_id, wordle_id)

                session.commit()
                await message.add_reaction('✅')
                await self.check_for_suspicious_wordle(message, wordle_score, wordle_grid)

        except SQLAlchemyError as e:
            print(f"Database error: {e}")
            session.rollback()
            
        finally:
            session.close()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StoreWordle(bot))
    print('STORE WORDLE COG LOADED')
