import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from database.connection import get_session
from database.models import User, WordleData
from util.util import send_no_games_embed

class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def format_decimals(num: float) -> str:
        return str(int(num))

    @staticmethod
    def calculate_stats(user_id: int) -> tuple | None:
        session = get_session()
        try:
            user_data = session.query(User).filter(User.user_id == user_id).first()
            if user_data is None:
                return None
            wordle_data = session.query(WordleData).filter(WordleData.user_id == user_id).first()
            if wordle_data is None:
                return None

            score_count_map = session.query(
                WordleData.wordle_score,
                func.count(WordleData.wordle_score)
            ).filter(
                WordleData.user_id == user_id
            ).group_by(
                WordleData.wordle_score
            ).all()

            score_counts = {score: 0 for score in ['1', '2', '3', '4', '5', '6', 'X']}
            total_games = 0
            total_score = 0

            for score, count in score_count_map:
                score_counts[score] = count
                total_games += count
                total_score += (10 * count) if score == 'X' else (int(score) * count)

            win_percentage = ((total_games - score_counts['X']) / total_games * 100)
            average_score = total_score / total_games

            return total_games, win_percentage, average_score, score_counts
        except SQLAlchemyError as e:
            print(f'Database error: {e}')
        finally:
            session.close()

    @staticmethod
    def calculate_streaks(user_id: int) -> tuple | None:
        session = get_session()
        try:
            results = session.query(WordleData.wordle_id).filter(WordleData.user_id == user_id).order_by(WordleData.wordle_id.asc()).all()
            ids = [int(result[0].replace(',', '')) for result in results]
            if not ids:
                return None

            longest_streak = 1
            current_streak = 1
            temp_streak = 1
            for i in range(1, len(ids)):
                if (ids[i] - ids[i - 1]) == 1:
                    temp_streak += 1
                else:
                    if temp_streak > longest_streak:
                        longest_streak = temp_streak
                    temp_streak = 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak

            for i in range(len(ids) - 1, 0, -1):
                if (ids[i] - ids[i - 1]) == 1:
                    current_streak += 1
                else:
                    break
            return current_streak, longest_streak
        except SQLAlchemyError as e:
            print(f'Database error: {e}')
        finally:
            session.close()

    @commands.command()
    async def stats(self, ctx: commands.Context) -> None:
        user = ctx.author
        if ctx.message.mentions:
            user = ctx.message.mentions[0]

        stats_data = self.calculate_stats(user.id)
        streaks = self.calculate_streaks(user.id)

        if stats_data is None or streaks is None:
            await send_no_games_embed(ctx, user)
            return

        total_games, win_percentage, average_score, score_counts = stats_data
        current_streak, longest_streak = streaks

        white = (255, 255, 255)
        green_bar = (46, 204, 112)
        gray_bar = (100, 100, 100)

        width, height = 800, 600
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        number_size = 60
        text_size = 30
        number_font = ImageFont.truetype('assets/whitneybold.otf', number_size)
        regular_font = ImageFont.truetype('assets/whitneymedium.otf', text_size)
        bold_font = ImageFont.truetype('assets/whitneybold.otf', text_size)

        y_start = 0
        text_buffer = 10
        column_width = width / 5

        stats_list = [
            (total_games, 'Played'),
            (self.format_decimals(win_percentage), 'Win %'),
            (f'{average_score:.1f}', 'Average'),
            (current_streak, ('Current', 'Streak')),
            (longest_streak, ('Max', 'Streak'))
        ]

        for i, (stat_value, label) in enumerate(stats_list):
            center_x = (i * column_width) + (column_width / 2)
            stat_text = str(stat_value)
            stat_bbox = draw.textbbox((0, 0), stat_text, font = number_font)
            stat_width = stat_bbox[2] - stat_bbox[0]
            stat_x = center_x - (stat_width / 2)
            draw.text((stat_x, y_start), stat_text, fill = white, font = number_font)

            if isinstance(label, tuple):
                line1, line2 = label
                line1_bbox = draw.textbbox((0, 0), line1, font = regular_font)
                line2_bbox = draw.textbbox((0, 0), line2, font = regular_font)
                line1_w = line1_bbox[2] - line1_bbox[0]
                line2_w = line2_bbox[2] - line2_bbox[0]
                line1_x = center_x - (line1_w / 2)
                line2_x = center_x - (line2_w / 2)
                line1_y = y_start + number_size + text_buffer
                line2_y = line1_y + text_size
                draw.text((line1_x, line1_y), line1, fill = white, font = regular_font)
                draw.text((line2_x, line2_y), line2, fill = white, font = regular_font)
            else:
                label_bbox = draw.textbbox((0, 0), label, font = regular_font)
                label_width = label_bbox[2] - label_bbox[0]
                label_x = center_x - (label_width / 2)
                draw.text((label_x, y_start + number_size + text_buffer), label, fill = white, font = regular_font)

        graph_title = 'Guess Distribution'
        title_y = number_size + (text_size * 2) + 40
        title_x = 50
        draw.text((title_x, title_y), graph_title, fill = white, font = bold_font)

        bar_start_x = 50
        bar_start_y = title_y + 50
        max_bar_width = 700
        bar_height = 45
        bar_spacing = 10
        guesses = ['1', '2', '3', '4', '5', '6', 'X']
        largest_count = max(score_counts.values())

        for i, guess in enumerate(guesses):
            count = score_counts.get(guess, 0)
            y_pos = bar_start_y + i * (bar_height + bar_spacing)
            label_bbox = draw.textbbox((0, 0), guess, font = regular_font)
            label_height = label_bbox[3] - label_bbox[1]
            label_y = y_pos + (bar_height - label_height) / 6
            draw.text((10, label_y), guess, fill = white, font = regular_font)
            bar_fraction = (count / total_games)
            bar_width = bar_fraction * max_bar_width
            color = green_bar if (count == largest_count and count > 0) else gray_bar
            draw.rectangle([bar_start_x, y_pos, bar_start_x + bar_width, y_pos + bar_height], fill = color)
            count_str = str(count)
            count_bbox = draw.textbbox((0, 0), count_str, font = regular_font)
            text_w = count_bbox[2] - count_bbox[0]
            text_y = label_y
            margin = 5
            if bar_width >= text_w + margin:
                text_x = bar_start_x + bar_width - text_w - margin
            else:
                text_x = bar_start_x + bar_width + margin
            draw.text((text_x, text_y), count_str, fill = white, font = regular_font)

        buf = BytesIO()
        img.save(buf, format = 'PNG', optimize = True)
        buf.seek(0)
        file = discord.File(fp = buf, filename = 'stats.png')

        embed = discord.Embed(color = discord.Color.green())
        embed.set_author(name = f'{user.display_name}\'s stats:', icon_url = user.avatar)
        embed.set_image(url = 'attachment://stats.png')
        
        await ctx.send(file = file, embed = embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Stats(bot))
    print('STATS COG LOADED')
