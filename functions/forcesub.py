import asyncio
from pyrogram import Client
from pyrogram.types import Message
from datetime import datetime, timedelta
from pyrogram.enums import ChatMemberStatus
from config import AUTH_CHANNEL, START_TXT, BUTTON_TEXT
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)


async def handle_force_subscribe(c: Client, m: Message):
    user_id = m.from_user.id
    start_time = datetime.now()
    try:
        user = await c.get_chat_member(AUTH_CHANNEL, user_id)
        if user.status == ChatMemberStatus.BANNED:
            await c.delete_messages(
                chat_id=m.chat.id,
                message_ids=m.id,
                revoke=True
            )
            return 400
    except UserNotParticipant:
        date = start_time + timedelta(seconds=120)
        invite_link = await c.create_chat_invite_link(AUTH_CHANNEL, expire_date=date, member_limit=1)
        await c.send_message(
            chat_id=user_id,
            text=START_TXT,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(BUTTON_TEXT, url=invite_link.invite_link)
                    ]
                ]
            ),
            reply_to_message_id=m.id,
        )
        return 400
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return 400
    except Exception as e:
        await c.send_message(
            chat_id=user_id,
            text="Bir şeyler ters gitti.",
            disable_web_page_preview=True,
            reply_to_message_id=m.id,
        )
        LOGGER.info(e)
        return 400
