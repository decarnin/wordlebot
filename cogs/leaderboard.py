import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, case, cast, Integer
from database.connection import get_session
from database.models import User, WordleData, ServerMembership

class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def get_user_rank(self, period: str, user_id: int, filter_server_id: int | None = None, display_server_id: int | None = None) -> tuple | None:
        session = get_session()
        try:
            pst_time: datetime = datetime.now(ZoneInfo('America/Los_Angeles'))
            today_date = pst_time.date()
            week = int(today_date.strftime('%U'))
            month = today_date.month
            year = today_date.year

            if period == 'daily':
                score_expr = case(
                    (WordleData.wordle_score == 'X', 10),
                    else_ = cast(WordleData.wordle_score, Integer)
                )
                base_query = session.query(
                    User.user_id,
                    func.max(score_expr).label('score')
                ).join(WordleData, User.user_id == WordleData.user_id)
                if filter_server_id is not None:
                    base_query = base_query.join(
                        ServerMembership,
                        (ServerMembership.user_id == User.user_id) & (ServerMembership.server_id == filter_server_id)
                    )
                elif display_server_id is not None:
                    base_query = base_query.outerjoin(
                        ServerMembership,
                        (ServerMembership.user_id == User.user_id) & (ServerMembership.server_id == display_server_id)
                    )
                base_query = base_query.filter(WordleData.wordle_date == today_date)
                base_query = base_query.group_by(User.user_id)
                user_score = base_query.filter(User.user_id == user_id).with_entities(func.max(score_expr)).scalar()
                if user_score is None:
                    return None
                count_better = base_query.filter(func.max(score_expr) < user_score).count()
                rank = count_better + 1
                user_obj = session.query(User).filter(User.user_id == user_id).first()
                display_name = user_obj.user_name if user_obj else ''
                avatar = user_obj.avatar if user_obj else ''
                return (rank, user_score, display_name, avatar)
            else:
                base_query = session.query(
                    User.user_id,
                    func.avg(
                        case(
                            (WordleData.wordle_score == 'X', 10),
                            else_ = cast(WordleData.wordle_score, Integer)
                        )
                    ).label('average_score'),
                    func.count(WordleData.wordle_id).label('games_played'),
                    func.coalesce(ServerMembership.display_name, User.user_name).label('display_name'),
                    User.avatar
                ).join(WordleData, User.user_id == WordleData.user_id)
                if filter_server_id is not None:
                    base_query = base_query.join(
                        ServerMembership,
                        (ServerMembership.user_id == User.user_id) & (ServerMembership.server_id == filter_server_id)
                    )
                elif display_server_id is not None:
                    base_query = base_query.outerjoin(
                        ServerMembership,
                        (ServerMembership.user_id == User.user_id) & (ServerMembership.server_id == display_server_id)
                    )
                if period == 'weekly':
                    base_query = base_query.filter(
                        func.WEEK(WordleData.wordle_date, 0) == int(week),
                        func.YEAR(WordleData.wordle_date) == year
                    )
                elif period == 'monthly':
                    base_query = base_query.filter(
                        func.MONTH(WordleData.wordle_date) == month,
                        func.YEAR(WordleData.wordle_date) == year
                    )
                elif period == 'yearly':
                    base_query = base_query.filter(func.YEAR(WordleData.wordle_date) == year)
                base_query = base_query.group_by(User.user_id, User.user_name, User.avatar, ServerMembership.display_name)
                user_record = base_query.filter(User.user_id == user_id).first()
                if not user_record:
                    return None
                user_avg = user_record.average_score
                subq = base_query.subquery()
                count_query = session.query(func.count()).select_from(subq).filter(subq.c.average_score < user_avg)
                count_better = count_query.scalar() or 0
                rank = count_better + 1
                return (rank, user_avg, user_record.games_played, user_record.display_name, user_record.avatar)
        finally:
            session.close()

    @staticmethod
    def get_leaderboard(period: str, filter_server_id: int | None = None, display_server_id: int | None = None) -> list:
        session = get_session()
        try:
            pst_time: datetime = datetime.now(ZoneInfo('America/Los_Angeles'))
            today_date = pst_time.date()
            week = int(today_date.strftime('%U'))
            month = today_date.month
            year = today_date.year

            if period == 'daily':
                score_expr = case(
                    (WordleData.wordle_score == 'X', 10),
                    else_ = cast(WordleData.wordle_score, Integer)
                )
                query = session.query(
                    User.user_id,
                    func.coalesce(ServerMembership.display_name, User.user_name).label('display_name'),
                    User.avatar,
                    func.max(score_expr).label('score')
                ).join(WordleData, User.user_id == WordleData.user_id)
                if filter_server_id is not None:
                    query = query.join(
                        ServerMembership,
                        (ServerMembership.user_id == User.user_id) & (ServerMembership.server_id == filter_server_id)
                    )
                elif display_server_id is not None:
                    query = query.outerjoin(
                        ServerMembership,
                        (ServerMembership.user_id == User.user_id) & (ServerMembership.server_id == display_server_id)
                    )
                query = query.filter(WordleData.wordle_date == today_date)
                query = query.group_by(User.user_id, User.user_name, User.avatar, ServerMembership.display_name)
                query = query.order_by('score')
                all_data = query.all()
                return all_data[:100]
            else:
                query = session.query(
                    User.user_id,
                    func.coalesce(ServerMembership.display_name, User.user_name).label('display_name'),
                    User.avatar,
                    func.avg(
                        case(
                            (WordleData.wordle_score == 'X', 10),
                            else_ = cast(WordleData.wordle_score, Integer)
                        )
                    ).label('average_score'),
                    func.count(WordleData.wordle_id).label('games_played')
                ).join(WordleData, User.user_id == WordleData.user_id)
                if filter_server_id is not None:
                    query = query.join(
                        ServerMembership,
                        (ServerMembership.user_id == User.user_id) & (ServerMembership.server_id == filter_server_id)
                    )
                elif display_server_id is not None:
                    query = query.outerjoin(
                        ServerMembership,
                        (ServerMembership.user_id == User.user_id) & (ServerMembership.server_id == display_server_id)
                    )
                if period == 'weekly':
                    query = query.filter(
                        func.WEEK(WordleData.wordle_date, 0) == int(week),
                        func.YEAR(WordleData.wordle_date) == year
                    )
                elif period == 'monthly':
                    query = query.filter(
                        func.MONTH(WordleData.wordle_date) == month,
                        func.YEAR(WordleData.wordle_date) == year
                    )
                elif period == 'yearly':
                    query = query.filter(func.YEAR(WordleData.wordle_date) == year)
                query = query.group_by(User.user_id, User.user_name, User.avatar, ServerMembership.display_name)
                query = query.order_by('average_score')
                all_data = query.all()
                return all_data[:100]
        except SQLAlchemyError as e:
            print(f'Database error: {e}')
            return []
        finally:
            session.close()

    @commands.command()
    async def leaderboard(self, ctx: commands.Context, *, message: str = 'all time') -> None:
        period = message.lower()
        server = ctx.guild
        server_id = server.id
        server_name = server.name

        raw_data = self.get_leaderboard(period, filter_server_id = server_id, display_server_id = server_id)
        if period == 'daily':
            ranked_data = [(i + 1, row[0], row[3], row[1], row[2]) for i, row in enumerate(raw_data)]
        else:
            ranked_data = [(i + 1, row[0], row[3], row[4], row[1], row[2]) for i, row in enumerate(raw_data)]

        user_record = next((r for r in ranked_data if r[1] == ctx.author.id), None)
        if not user_record:
            user_record = self.get_user_rank(period, ctx.author.id, filter_server_id = server_id, display_server_id = server_id)

        forcibly_append = False
        if user_record and isinstance(user_record, tuple) and user_record[0] <= 100:
            if user_record[0] > 10:
                forcibly_append = True

        display_period = period.capitalize()
        embed = discord.Embed(
            color = discord.Color.green(),
            title = f'{display_period} leaderboard in {server_name}'
        )

        image_file = await self.leaderboard_image(ctx, ranked_data, display_period, page = 0, forcibly_append = forcibly_append)
        embed.set_image(url = f'attachment://leaderboard_0.png')

        if user_record:
            if period == 'daily':
                rank, _, score, display_name, u_avatar = user_record
                embed.set_footer(
                    text = f'Your rank: {rank}  |  Score: {score}',
                    icon_url = u_avatar
                )
            else:
                rank, _, u_avg, u_games, display_name, u_avatar = user_record
                embed.set_footer(
                    text = f'Your rank: {rank}  |  Average: {u_avg:.2f}  |  Games: {u_games}',
                    icon_url = u_avatar
                )

        view = self.LeaderboardView(ranked_data, display_period, ctx.author, self, forcibly_append)
        await ctx.send(file = image_file, embed = embed, view = view)

    @commands.command()
    async def gleaderboard(self, ctx: commands.Context, *, message: str = 'all time') -> None:
        period = message.lower()
        raw_data = self.get_leaderboard(period, filter_server_id = None, display_server_id = ctx.guild.id)
        if period == 'daily':
            ranked_data = [(i + 1, row[0], row[3], row[1], row[2]) for i, row in enumerate(raw_data)]
        else:
            ranked_data = [(i + 1, row[0], row[3], row[4], row[1], row[2]) for i, row in enumerate(raw_data)]

        user_record = next((r for r in ranked_data if r[1] == ctx.author.id), None)
        if not user_record:
            user_record = self.get_user_rank(period, ctx.author.id, filter_server_id = None, display_server_id = ctx.guild.id)

        forcibly_append = False
        if user_record and isinstance(user_record, tuple) and user_record[0] <= 100:
            if user_record[0] > 10:
                forcibly_append = True

        display_period = period.capitalize()
        embed = discord.Embed(
            color = discord.Color.green(),
            title = f'{display_period} leaderboard globally'
        )

        image_file = await self.leaderboard_image(ctx, ranked_data, display_period, page = 0, forcibly_append = forcibly_append)
        embed.set_image(url = f'attachment://leaderboard_0.png')

        if user_record:
            if period == 'daily':
                rank, _, score, display_name, u_avatar = user_record
                embed.set_footer(
                    text = f'Your rank: {rank}  |  Score: {score}',
                    icon_url = u_avatar
                )
            else:
                rank, _, u_avg, u_games, display_name, u_avatar = user_record
                embed.set_footer(
                    text = f'Your rank: {rank}  |  Average: {u_avg:.2f}  |  Games: {u_games}',
                    icon_url = u_avatar
                )

        view = self.LeaderboardView(ranked_data, display_period, ctx.author, self, forcibly_append)
        await ctx.send(file = image_file, embed = embed, view = view)

    def shorten_text(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
        if draw.textlength(text, font = font) <= max_width:
            return text
        ellipsis = '...'
        ellipsis_width = draw.textlength(ellipsis, font = font)
        available_width = max_width - ellipsis_width
        for i in range(len(text), 0, -1):
            if draw.textlength(text[:i], font = font) <= available_width:
                return text[:i] + ellipsis
        return ellipsis

    async def leaderboard_image(self, ctx_or_interaction, leaderboard_data: list, period: str, page: int = 0, forcibly_append: bool = False) -> discord.File:
        if isinstance(ctx_or_interaction, discord.Interaction):
            current_user = ctx_or_interaction.user
        else:
            current_user = ctx_or_interaction.author

        is_daily = (period.lower() == 'daily')
        user_in_top = next((r for r in leaderboard_data if r[1] == current_user.id), None)

        max_rows = 10
        if forcibly_append and user_in_top and user_in_top[0] > 10 and page == 0:
            page_entries = leaderboard_data[:max_rows - 1] + [user_in_top]
        else:
            start_index = page * max_rows
            page_entries = leaderboard_data[start_index:start_index + max_rows]

        row_height = 110
        header_height = 70
        total_rows = len(page_entries)
        large_width = 1600
        large_height = header_height + 20 + row_height * total_rows + 20

        white = (255, 255, 255)
        transparent = (0, 0, 0, 0)
        img = Image.new('RGBA', (large_width, large_height), transparent)
        draw = ImageDraw.Draw(img)

        top_margin = 0
        if is_daily:
            col_rank_x = 40
            col_avatar_x = 180
            avatar_size = 100
            col_name_x = 300
            name_column_width = 1070
            col_score_x = 1370
            score_column_width = 200

            bold_font = ImageFont.truetype('assets/whitneybold.otf', 60)
            regular_font = ImageFont.truetype('assets/whitneymedium.otf', 60)
            rank_header_text = 'Rank'
            rank_header_w = draw.textlength(rank_header_text, font = bold_font)
            rank_header_x = col_rank_x + ((col_avatar_x - col_rank_x) - rank_header_w) / 2
            draw.text((rank_header_x, top_margin), rank_header_text, font = bold_font, fill = white)

            draw.text((col_name_x, top_margin), 'Player', font = bold_font, fill = white)

            score_header_text = 'Score'
            score_header_w = draw.textlength(score_header_text, font = bold_font)
            score_header_x = col_score_x + (score_column_width - score_header_w) / 2
            draw.text((score_header_x, top_margin), score_header_text, font = bold_font, fill = white)
        else:
            col_rank_x = 40
            col_avatar_x = 180
            avatar_size = 100
            col_name_x = 300
            name_column_width = 800
            col_average_x = 1100
            average_column_width = 180
            col_games_x = 1370
            games_column_width = 200

            bold_font = ImageFont.truetype('assets/whitneybold.otf', 60)
            regular_font = ImageFont.truetype('assets/whitneymedium.otf', 60)
            rank_header_text = 'Rank'
            rank_header_w = draw.textlength(rank_header_text, font = bold_font)
            rank_header_x = col_rank_x + ((col_avatar_x - col_rank_x) - rank_header_w) / 2
            draw.text((rank_header_x, top_margin), rank_header_text, font = bold_font, fill = white)

            draw.text((col_name_x, top_margin), 'Player', font = bold_font, fill = white)

            avg_header_text = 'Average'
            avg_header_w = draw.textlength(avg_header_text, font = bold_font)
            avg_header_x = col_average_x + (average_column_width - avg_header_w) / 2
            draw.text((avg_header_x, top_margin), avg_header_text, font = bold_font, fill = white)

            games_header_text = 'Games'
            games_header_w = draw.textlength(games_header_text, font = bold_font)
            games_header_x = col_games_x + (games_column_width - games_header_w) / 2
            draw.text((games_header_x, top_margin), games_header_text, font = bold_font, fill = white)

        line_y = header_height
        draw.line([(40, line_y), (large_width - 40, line_y)], fill = white, width = 4)

        if is_daily:
            bold_font = ImageFont.truetype('assets/whitneybold.otf', 60)
            regular_font = ImageFont.truetype('assets/whitneymedium.otf', 60)
            rank_texts = [f'{entry[0]}.' for entry in page_entries]
            max_rank_width = max(draw.textlength(text, font = bold_font) for text in rank_texts) if rank_texts else 0
            rank_column_width = col_avatar_x - 40
            rank_left_x = 40 + (rank_column_width - max_rank_width) / 2

            y_offset = line_y + 20
            for entry in page_entries:
                rank, user_id, score, display_name, avatar_url = entry
                rank_text = f'{rank}.'
                draw.text((rank_left_x, y_offset + 20), rank_text, font = bold_font, fill = white)
                try:
                    if avatar_url:
                        response = requests.get(avatar_url)
                        avatar_img = Image.open(BytesIO(response.content)).convert('RGBA')
                    else:
                        raise ValueError('No stored avatar URL.')
                    avatar_img = avatar_img.resize((avatar_size, avatar_size))
                    mask = Image.new('L', (avatar_size, avatar_size), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill = 255)
                    img.paste(avatar_img, (col_avatar_x, y_offset + 5), mask)
                except Exception:
                    user_obj = self.bot.get_user(user_id)
                    if user_obj:
                        fallback_avatar_url = user_obj.display_avatar.replace(format = 'png').url
                        try:
                            response = requests.get(fallback_avatar_url)
                            avatar_img = Image.open(BytesIO(response.content)).convert('RGBA')
                            avatar_img = avatar_img.resize((avatar_size, avatar_size))
                            mask = Image.new('L', (avatar_size, avatar_size), 0)
                            mask_draw = ImageDraw.Draw(mask)
                            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill = 255)
                            img.paste(avatar_img, (col_avatar_x, y_offset + 5), mask)
                        except Exception:
                            default_avatar = Image.open('assets/default_avatar.png').convert('RGBA')
                            default_avatar = default_avatar.resize((avatar_size, avatar_size))
                            mask = Image.new('L', (avatar_size, avatar_size), 0)
                            mask_draw = ImageDraw.Draw(mask)
                            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill = 255)
                            img.paste(default_avatar, (col_avatar_x, y_offset + 5), mask)
                    else:
                        default_avatar = Image.open('assets/default_avatar.png').convert('RGBA')
                        default_avatar = default_avatar.resize((avatar_size, avatar_size))
                        mask = Image.new('L', (avatar_size, avatar_size), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill = 255)
                        img.paste(default_avatar, (col_avatar_x, y_offset + 5), mask)

                if user_id == current_user.id:
                    name_font = bold_font
                    stats_font = bold_font
                else:
                    name_font = regular_font
                    stats_font = regular_font

                if len(display_name) > 32:
                    display_name = display_name[:32]
                name_max_width = name_column_width - 20
                display_name = self.shorten_text(draw, display_name, name_font, name_max_width)
                draw.text((col_name_x, y_offset + 25), display_name, font = name_font, fill = white)

                score_str = str(score)
                score_w = draw.textlength(score_str, font = stats_font)
                score_x = col_score_x + (score_column_width - score_w) / 2
                draw.text((score_x, y_offset + 25), score_str, font = stats_font, fill = white)
                y_offset += row_height
        else:
            bold_font = ImageFont.truetype('assets/whitneybold.otf', 60)
            regular_font = ImageFont.truetype('assets/whitneymedium.otf', 60)
            rank_texts = [f'{entry[0]}.' for entry in page_entries]
            max_rank_width = max(draw.textlength(text, font = bold_font) for text in rank_texts) if rank_texts else 0
            rank_column_width = col_avatar_x - 40
            rank_left_x = 40 + (rank_column_width - max_rank_width) / 2

            games_texts = [str(entry[3]) for entry in page_entries]
            max_games_width = max(draw.textlength(text, font = regular_font) for text in games_texts) if games_texts else 0
            games_left_x = col_games_x + (games_column_width - max_games_width) / 2

            y_offset = line_y + 20
            for entry in page_entries:
                rank, user_id, avg_score, games_played, display_name, avatar_url = entry
                rank_text = f'{rank}.'
                draw.text((rank_left_x, y_offset + 20), rank_text, font = bold_font, fill = white)
                try:
                    if avatar_url:
                        response = requests.get(avatar_url)
                        avatar_img = Image.open(BytesIO(response.content)).convert('RGBA')
                    else:
                        raise ValueError('No stored avatar URL.')
                    avatar_img = avatar_img.resize((avatar_size, avatar_size))
                    mask = Image.new('L', (avatar_size, avatar_size), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill = 255)
                    img.paste(avatar_img, (col_avatar_x, y_offset + 5), mask)
                except Exception:
                    user_obj = self.bot.get_user(user_id)
                    if user_obj:
                        fallback_avatar_url = user_obj.display_avatar.replace(format = 'png').url
                        try:
                            response = requests.get(fallback_avatar_url)
                            avatar_img = Image.open(BytesIO(response.content)).convert('RGBA')
                            avatar_img = avatar_img.resize((avatar_size, avatar_size))
                            mask = Image.new('L', (avatar_size, avatar_size), 0)
                            mask_draw = ImageDraw.Draw(mask)
                            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill = 255)
                            img.paste(avatar_img, (col_avatar_x, y_offset + 5), mask)
                        except Exception:
                            default_avatar = Image.open('assets/default_avatar.png').convert('RGBA')
                            default_avatar = default_avatar.resize((avatar_size, avatar_size))
                            mask = Image.new('L', (avatar_size, avatar_size), 0)
                            mask_draw = ImageDraw.Draw(mask)
                            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill = 255)
                            img.paste(default_avatar, (col_avatar_x, y_offset + 5), mask)
                    else:
                        default_avatar = Image.open('assets/default_avatar.png').convert('RGBA')
                        default_avatar = default_avatar.resize((avatar_size, avatar_size))
                        mask = Image.new('L', (avatar_size, avatar_size), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill = 255)
                        img.paste(default_avatar, (col_avatar_x, y_offset + 5), mask)

                if user_id == current_user.id:
                    name_font = bold_font
                    stats_font = bold_font
                else:
                    name_font = regular_font
                    stats_font = regular_font

                if len(display_name) > 32:
                    display_name = display_name[:32]
                name_max_width = name_column_width - 20
                display_name = self.shorten_text(draw, display_name, name_font, name_max_width)
                draw.text((col_name_x, y_offset + 25), display_name, font = name_font, fill = white)

                avg_str = f'{avg_score:.2f}'
                avg_w = draw.textlength(avg_str, font = stats_font)
                avg_x = col_average_x + (average_column_width - avg_w) / 2
                draw.text((avg_x, y_offset + 25), avg_str, font = stats_font, fill = white)

                games_str = str(games_played)
                draw.text((games_left_x, y_offset + 25), games_str, font = regular_font, fill = white)
                y_offset += row_height

        buf = BytesIO()
        img.save(buf, format = 'PNG', optimize = True)
        buf.seek(0)
        return discord.File(fp = buf, filename = f'leaderboard_{page}.png')

    class LeaderboardView(discord.ui.View):
        def __init__(self, leaderboard_data: list, period: str, author: discord.User, cog_instance, forcibly_append: bool, current_page: int = 0):
            super().__init__(timeout = 180)
            self.leaderboard_data = leaderboard_data
            self.period = period
            self.author = author
            self.cog_instance = cog_instance
            self.forcibly_append = forcibly_append
            self.current_page = current_page

        @discord.ui.button(label = '←', style = discord.ButtonStyle.gray)
        async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.current_page > 0:
                self.current_page -= 1
                await self.update_leaderboard(interaction)
            else:
                await interaction.response.defer()

        @discord.ui.button(label = '→', style = discord.ButtonStyle.gray)
        async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
            total_entries = len(self.leaderboard_data) + (1 if self.forcibly_append and any(r for r in self.leaderboard_data if r[1] == self.author.id) else 0)
            max_pages = (total_entries - 1) // 10
            if self.current_page < max_pages:
                self.current_page += 1
                await self.update_leaderboard(interaction)
            else:
                await interaction.response.defer()

        async def update_leaderboard(self, interaction: discord.Interaction):
            total_entries = len(self.leaderboard_data) + (1 if self.forcibly_append and any(r for r in self.leaderboard_data if r[1] == self.author.id) else 0)
            max_pages = (total_entries - 1) // 10
            self.left.disabled = (self.current_page == 0)
            self.right.disabled = (self.current_page >= max_pages)

            new_image = await self.cog_instance.leaderboard_image(interaction, self.leaderboard_data, self.period, page = self.current_page, forcibly_append = self.forcibly_append)
            embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed(title = self.period)
            embed.set_image(url = f'attachment://leaderboard_{self.current_page}.png')

            new_view = type(self)(self.leaderboard_data, self.period, self.author, self.cog_instance, self.forcibly_append, self.current_page)
            new_view.left.disabled = self.left.disabled
            new_view.right.disabled = self.right.disabled

            await interaction.response.edit_message(attachments = [new_image], embed = embed, view = new_view)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leaderboard(bot))
    print('LEADERBOARD COG LOADED')
