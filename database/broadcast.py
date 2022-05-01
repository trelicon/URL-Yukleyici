import asyncio
import datetime
import time

from pyrogram import Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
from pyrogram.errors import UserNotParticipant
from pyrogram.types import Message

from config import BROADCAST_AS_COPY, LOGGER, AUTH_CHANNEL
from database.database import db


async def broadcast_messages(bot, user_id, message):
    if AUTH_CHANNEL:
        try:
            user = await bot.get_chat_member(AUTH_CHANNEL, user_id)
        except UserNotParticipant:
            return False, "Blocked"
        except Exception as e:
            LOGGER.exception(e)
        else:
            if user.status == ChatMemberStatus.BANNED:
                return False, "Blocked"
    try:
        if BROADCAST_AS_COPY is False:
            await message.forward(chat_id=user_id)
        elif BROADCAST_AS_COPY is True:
            await message.copy(chat_id=user_id, protect_content=True)
        return True, "Succes"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(bot, user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        LOGGER.info(f"{user_id} - Hesap silindiği için veritabanından kaldırıldı.")
        return False, "Deleted"
    except UserIsBlocked:
        LOGGER.info(f"{user_id} - Bot'u engelledi.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        LOGGER.info(f"{user_id} - Kimliği geçersiz")
        return False, "Error"
    except Exception as e:
        return False, "Error"


async def broadcast_handler(bot: Client, m: Message):
    users = await db.get_all_notif_user()
    b_msg = m.reply_to_message
    sts = await m.reply_text(
        text='Mesajı yayınlıyorum...'
    )
    start_time = time.time()
    total_users = await db.total_users_count()
    done = 0
    blocked = 0
    deleted = 0
    failed = 0
    success = 0
    async for user in users:
        pti, sh = await broadcast_messages(bot, int(user['id']), b_msg)
        if pti:
            success += 1
        elif not pti:
            if sh == "Blocked":
                blocked += 1
            elif sh == "Deleted":
                deleted += 1
            elif sh == "Error":
                failed += 1
        done += 1
        await asyncio.sleep(2)
        if not done % 20:
            await sts.edit(f"Yayın devam ediyor:\n\n"
                           f"Toplam Kullanıcılar {total_users}\n"
                           f"Tamamlanan: {done} / {total_users}\n"
                           f"Başarılı: {success}\n"
                           f"Engellemiş: {blocked}\n"
                           f"Silmiş: {deleted}")
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit(f"Yayın Tamamlandı:\n"
                   f"{time_taken} saniye içinde tamamlandı.\n\n"
                   f"Toplam Kullanıcılar {total_users}\n"
                   f"Tamamlanan: {done} / {total_users}\n"
                   f"Başarılı: {success}\nEngellemiş: {blocked}\n"
                   f"Silmiş: {deleted}"
                   )
