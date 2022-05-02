from config import AUTH_CHANNEL
from translation import Translation
from pyrogram import Client, filters, types
from database.add import add_user_to_database
from plugins.settings.settings import Settings
from functions.forcesub import handle_force_subscribe


@Client.on_message(filters.private & filters.command(["start", "help"]))
async def start_handler(c: Client, m: "types.Message"):
    if not m.from_user:
        return await m.reply_text("Seni tanımıyorum ahbap.")
    await add_user_to_database(c, m)
    if AUTH_CHANNEL:
        fsub = await handle_force_subscribe(c, m)
        if fsub == 400:
            return
    await m.reply_text(
        text=Translation.START_TEXT.format(m.from_user.mention),
        disable_web_page_preview=True,
        reply_to_message_id=m.id,
        reply_markup=Translation.START_BUTTONS
    )


@Client.on_message(filters.private & filters.command(["ayarlar", "settings"]))
async def delete_thumb_handler(c: Client, m: "types.Message"):
    if not m.from_user:
        return await m.reply_text("Seni tanımıyorum ahbap.")
    await add_user_to_database(c, m)
    if AUTH_CHANNEL:
        fsub = await handle_force_subscribe(c, m)
        if fsub == 400:
            return
    await Settings(m)
