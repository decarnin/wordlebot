import discord
from discord.ext import commands
from sqlalchemy.exc import SQLAlchemyError
from database.connection import get_session
from database.models import User, ServerData, ServerMembership, WordleData, WordleServerMembership

def add_user(user: discord.User) -> None:
    session = get_session()
    try:
        existing_user = session.query(User).filter(User.user_id == user.id).first()
        if not existing_user:
            new_user = User(user_id = user.id, user_name = user.name, avatar = user.display_avatar.replace(format = 'png').url)
            session.add(new_user)
        else:
            existing_user.user_name = user.name
            existing_user.avatar = user.display_avatar.replace(format = 'png').url
        session.commit()

    except SQLAlchemyError as e:
        print(f'Database error in add_user: {e}')
        session.rollback()

    finally:
        session.close()

async def add_server(server_id: int) -> None:
    session = get_session()
    try:
        existing_server = session.query(ServerData).filter(ServerData.server_id == server_id).first()
        if not existing_server:
            new_server = ServerData(server_id = server_id, prefix = '!')
            session.add(new_server)
            session.commit()

    except SQLAlchemyError as e:
        print(f'Database error in add_server: {e}')
        session.rollback()

    finally:
        session.close()

def add_server_membership(user_id: int, server_id: int, display_name: str) -> None:
    session = get_session()
    try:
        existing_membership = session.query(ServerMembership).filter(
            ServerMembership.user_id == user_id,
            ServerMembership.server_id == server_id
            ).first()
        if not existing_membership:
            new_membership = ServerMembership(user_id = user_id, server_id = server_id, display_name = display_name)
            session.add(new_membership)
        else:
            existing_membership.display_name = display_name
        session.commit()

    except SQLAlchemyError as e:
        print(f'Database error in add_server_membership: {e}')
        session.rollback()
    
    finally:
        session.close()

def add_wordle(user_id: int, wordle_id: str, wordle_score: str, wordle_grid: str, wordle_date) -> None:
    session = get_session()
    try:
        existing_wordle = session.query(WordleData).filter(WordleData.user_id == user_id, WordleData.wordle_id == wordle_id).first()
        
        if not existing_wordle:
            new_wordle = WordleData(
                user_id = user_id,
                wordle_id = wordle_id,
                wordle_score = wordle_score,
                wordle_grid = wordle_grid,
                wordle_date = wordle_date
            )
            session.add(new_wordle)
            session.commit()

    except SQLAlchemyError as e:
        print(f"Database error in add_wordle: {e}")
        session.rollback()

    finally:
        session.close()

def add_wordle_server_membership(user_id: int, server_id: int, wordle_id: int) -> None:
    session = get_session()
    try:
        existing_membership = session.query(WordleServerMembership).filter(
            WordleServerMembership.user_id == user_id,
            WordleServerMembership.server_id == server_id,
            WordleServerMembership.wordle_id == wordle_id
            ).first()
        if not existing_membership:
            new_membership = WordleServerMembership(user_id = user_id, server_id = server_id, wordle_id = wordle_id)
            session.add(new_membership)
            session.commit()

    except SQLAlchemyError as e:
        print(f'Database error in add_wordle_server_membership: {e}')
        session.rollback()
    
    finally:
        session.close()

async def send_no_games_embed(ctx: commands.Context, user: discord.User) -> None:
    no_games_embed = discord.Embed(color = discord.Color.red())
    no_games_embed.set_author(name = f'{user.display_name} has not played any games yet', icon_url = user.avatar)
    await ctx.send(embed = no_games_embed)