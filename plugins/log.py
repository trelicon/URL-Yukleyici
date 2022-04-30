from config import OWNER_ID
from pyrogram import Client, filters

import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
                    level=logging.INFO)
LOGGER = logging.getLogger(__name__)


@Client.on_message(filters.command('log') & filters.user(OWNER_ID))
async def sendLogs(client, message):
    with open('log.txt', 'rb') as f:
        try:
            await client.send_document(document=f,
                                       file_name=f.name, reply_to_message_id=message.id,
                                       chat_id=message.chat.id, caption=f.name)
        except Exception as e:
            await message.reply_text(str(e))
