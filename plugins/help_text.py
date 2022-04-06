from config import AUTH_CHANNEL
from translation import Translation
from pyrogram import Client, filters
from database.add import add_user_to_database
from functions.forcesub import handle_force_subscribe

@Client.on_message(filters.private & filters.command(["start", "help", "ayarlar", "settings"]))
async def start(bot, update):
    if not update.from_user:
        return await update.reply_text("Seni tanımıyorum ahbap.")
    await add_user_to_database(bot, update)
    if AUTH_CHANNEL:
        fsub = await handle_force_subscribe(bot, update)
        if fsub == 400:
            return
    await update.reply_text(
        text=Translation.START_TEXT.format(update.from_user.mention),
        disable_web_page_preview=True,
        reply_markup=Translation.START_BUTTONS
    )