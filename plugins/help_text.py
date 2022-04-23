from config import AUTH_CHANNEL
from pyrogram.types import Message
from translation import Translation
from pyrogram import Client, filters
from database.add import add_user_to_database
from plugins.settings.settings import Settings
from functions.forcesub import handle_force_subscribe


@Client.on_message(filters.incoming & filters.command(["start", "help"]))
async def start(bot: Client, event: Message):
    if not event.from_user:
        return await event.reply_text("Seni tanımıyorum ahbap.")
    await add_user_to_database(bot, event)
    if AUTH_CHANNEL:
        fsub = await handle_force_subscribe(bot, event)
        if fsub == 400:
            return
    await event.reply_text(
        text=Translation.START_TEXT.format(event.from_user.mention),
        disable_web_page_preview=True,
        reply_to_message_id=event.message_id,
        reply_markup=Translation.START_BUTTONS
    )

@Client.on_message(filters.incoming & filters.command(["ayarlar", "settings"]))
async def delete_thumb_handler(bot: Client, event: Message):
    if not event.from_user:
        return await event.reply_text("Seni tanımıyorum ahbap.")
    await add_user_to_database(bot, event)
    if AUTH_CHANNEL:
        fsub = await handle_force_subscribe(bot, event)
        if fsub == 400:
            return
    await Settings(event)
