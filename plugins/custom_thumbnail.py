import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from pyrogram import Client

logging.getLogger("pyrogram").setLevel(logging.WARNING)
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from functions.forcesub import handle_force_subscribe
from config import AUTH_CHANNEL
from database.add import add_user_to_database
from plugins.settings.settings import *
from translation import Translation


@Client.on_message(filters.incoming & filters.photo)
async def photo_handler(bot: Client, event: Message):
    if not event.from_user:
        return await event.reply_text("Seni tanımıyorum ahbap.")
    await add_user_to_database(bot, event)
    if AUTH_CHANNEL:
        fsub = await handle_force_subscribe(bot, event)
        if fsub == 400:
            return
    editable = await event.reply_text("**👀 İşleniyor...**")
    await db.set_thumbnail(event.from_user.id, thumbnail=event.photo.file_id)
    await editable.edit(Translation.SAVED_CUSTOM_THUMB_NAIL)


@Client.on_message(filters.incoming & filters.command(["delthumb", "deletethumb"]))
async def delete_thumb_handler(bot: Client, event: Message):
    if not event.from_user:
        return await event.reply_text("Seni tanımıyorum ahbap.")
    await add_user_to_database(bot, event)
    if AUTH_CHANNEL:
        fsub = await handle_force_subscribe(bot, event)
        if fsub == 400:
            return

    await db.set_thumbnail(event.from_user.id, thumbnail=None)
    await event.reply_text(
        Translation.DEL_ETED_CUSTOM_THUMB_NAIL,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙ Ayarlar", callback_data="Settings")]
        ])
    )


@Client.on_message(filters.incoming & filters.command("showthumb"))
async def viewthumbnail(bot, update):
    if not update.from_user:
        return await update.reply_text("Seni tanımıyorum ahbap.")
    await add_user_to_database(bot, update)
    if AUTH_CHANNEL:
        fsub = await handle_force_subscribe(bot, update)
        if fsub == 400:
            return
    thumbnail = await db.get_thumbnail(update.from_user.id)
    if thumbnail is not None:
        await bot.send_photo(
            chat_id=update.chat.id,
            photo=thumbnail,
            caption=f"Ayarlı Thumbnail",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🗑️ Sil", callback_data="deleteThumbnail")]]
            ),
            reply_to_message_id=update.id)
    else:
        await update.reply_text(text=f"Thumbnail Bulunamadı.")
