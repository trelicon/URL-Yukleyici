import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

import os, time, asyncio, json

from PIL import Image
from translation import Translation
from pyrogram import Client, filters
from config import AUTH_CHANNEL, LOG_CHANNEL, DOWNLOAD_LOCATION, CHUNK_SIZE, DEF_THUMB_NAIL_VID_S, HTTP_PROXY

from database.add import add_user_to_database
from functions.display_progress import humanbytes
from functions.help_uploadbot import DownLoadFile
from functions.forcesub import handle_force_subscribe
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@Client.on_message(filters.private & filters.regex(pattern=".*http.*"))
async def echo(bot, update):
    if AUTH_CHANNEL:
        try:
            log_message = await update.copy(LOG_CHANNEL)
            log_info = "Gönderen Bilgileri:\n"
            log_info += "\nAd: " + update.from_user.first_name
            log_info += "\nID: " + str(update.from_user.id)
            log_info += "\nKullanıcı Adı: @" + update.from_user.username if update.from_user.username else ""
            log_info += "\nLink: " + update.from_user.mention
            await log_message.reply_text(
                text=log_info,
                disable_web_page_preview=True,
                quote=True
            )
        except Exception as error:
            print(error)
    if not update.from_user:
        return await update.reply_text("Seni tanımıyorum ahbap.")
    if AUTH_CHANNEL:
        fsub = await handle_force_subscribe(bot, update)
        if fsub == 400:
            return
    await add_user_to_database(bot, update)
    await bot.send_chat_action(
        chat_id=update.chat.id,
        action="typing"
    )
    logger.info(update.from_user)
    url = update.text
    yt_dlp_username = None
    yt_dlp_password = None
    file_name = None

    print(url)
    if "|" in url:
        url_parts = url.split("|")
        if len(url_parts) == 2:
            url = url_parts[0]
            file_name = url_parts[1]
        elif len(url_parts) == 4:
            url = url_parts[0]
            file_name = url_parts[1]
            yt_dlp_username = url_parts[2]
            yt_dlp_password = url_parts[3]
        else:
            for entity in update.entities:
                if entity.type == "text_link":
                    url = entity.url
                elif entity.type == "url":
                    o = entity.offset
                    l = entity.length
                    url = url[o:o + l]
        if url is not None:
            url = url.strip()
        if file_name is not None:
            file_name = file_name.strip()
        if yt_dlp_username is not None:
            yt_dlp_username = yt_dlp_username.strip()
        if yt_dlp_password is not None:
            yt_dlp_password = yt_dlp_password.strip()
        logger.info(url)
        logger.info(file_name)
    else:
        for entity in update.entities:
            if entity.type == "text_link":
                url = entity.url
            elif entity.type == "url":
                o = entity.offset
                l = entity.length
                url = url[o:o + l]
    if HTTP_PROXY != "":
        command_to_exec = [
            "yt-dlp",
            "--no-warnings",
            "--youtube-skip-dash-manifest",
            "--no-check-certificate",
            "-j",
            url,
            "--proxy", HTTP_PROXY
        ]
    else:
        command_to_exec = [
            "yt-dlp",
            "--no-warnings",
            "--youtube-skip-dash-manifest",
            "--no-check-certificate",
            "-j",
            url
        ]
    if "moly.cloud" in url:
        command_to_exec.append("--referer")
        command_to_exec.append("https://vidmoly.to/")
    if "closeload" in url:
        command_to_exec.append("--referer")
        command_to_exec.append("https://closeload.com/")
    if "mail.ru" in url:
        command_to_exec.append("--referer")
        command_to_exec.append("https://my.mail.ru/")
    if yt_dlp_username is not None:
        command_to_exec.append("--username")
        command_to_exec.append(yt_dlp_username)
    if yt_dlp_password is not None:
        command_to_exec.append("--password")
        command_to_exec.append(yt_dlp_password)
    logger.info(command_to_exec)
    send_message = await bot.send_message(
        chat_id=update.chat.id,
        text=f"İşleniyor...⏳",
        disable_web_page_preview=True,
        reply_to_message_id=update.message_id
    )
    process = await asyncio.create_subprocess_exec(
        *command_to_exec,
        # stdout must a pipe to be accessible as process.stdout
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    # logger.info(e_response)
    t_response = stdout.decode().strip()
    # logger.info(t_response)
    if e_response and "nonnumeric port" not in e_response:
        # logger.warn("Status : FAIL", exc.returncode, exc.output)
        error_message = e_response.replace("please report this issue on https://yt-dl.org/bug . Make sure you are using the latest version; see  https://yt-dl.org/update  on how to update. Be sure to call youtube-dl with the --verbose flag and include its complete output.", "")
        if "This video is only available for registered users." in error_message:
            error_message += Translation.SET_CUSTOM_USERNAME_PASSWORD
        time.sleep(1)
        await send_message.edit_text(
            text=Translation.NO_VOID_FORMAT_FOUND.format(str(error_message)),
            parse_mode="html",
            disable_web_page_preview=True
        )
        return False
    if t_response:
        await send_message.edit_text("Formatlar Ayıklanıyor...")
        # logger.info(t_response)
        x_reponse = t_response
        response_json = []
        if "\n" in x_reponse:
            for yu_r in x_reponse.split("\n"):
                response_json.append(json.loads(yu_r))
        else:
            response_json.append(json.loads(x_reponse))
        # response_json = json.loads(x_reponse)
        random = str(time.time())
        save_ytdl_json_path = os.path.join(
            DOWNLOAD_LOCATION,
            str(update.from_user.id) + random + ".json"
        )
        with open(save_ytdl_json_path, "w", encoding="utf8") as outfile:
            json.dump(response_json, outfile, ensure_ascii=False)
        # logger.info(response_json)
        inline_keyboard = []
        for current_r_json in response_json:

            duration = None
            if "duration" in current_r_json:
                duration = current_r_json["duration"]
            if "formats" in current_r_json:
                for formats in current_r_json["formats"]:
                    format_id = formats.get("format_id")
                    format_string = formats.get("format_note")
                    if format_string is None:
                        format_string = formats.get("format")
                    format_ext = formats.get("ext")
                    approx_file_size = ""
                    if "filesize" in formats:
                        approx_file_size = humanbytes(formats["filesize"])
                    dipslay_str_uon = (
                            "🎬 "
                            + format_string
                            + " - "
                            + approx_file_size
                            + " "
                            + format_ext
                            + " "
                    )
                    cb_string_video = "{}|{}|{}|{}".format("video", format_id, format_ext, random)
                    if format_string is not None and not "audio only" in format_string:
                        ikeyboard = [
                            InlineKeyboardButton(
                                dipslay_str_uon,
                                callback_data=(cb_string_video).encode("UTF-8")
                            )
                        ]
                        """if duration is not None:
                            cb_string_video_message = "{}|{}|{}".format(
                                "vm", format_id, format_ext)
                            ikeyboard.append(
                                InlineKeyboardButton(
                                    "VM",
                                    callback_data=(
                                        cb_string_video_message).encode("UTF-8")
                                )
                            )"""
                    else:
                        ikeyboard = [
                                InlineKeyboardButton(
                                    dipslay_str_uon,
                                    callback_data=(cb_string_video).encode("UTF-8"),
                                )
                            ]
                    inline_keyboard.append(ikeyboard)
                if duration is not None:
                    cb_string_64 = "{}|{}|{}|{}".format("audio", "64k", "mp3", random)
                    cb_string_128 = "{}|{}|{}|{}".format("audio", "128k", "mp3", random)
                    cb_string = "{}|{}|{}|{}".format("audio", "320k", "mp3", random)
                    inline_keyboard.append(
                        [
                            InlineKeyboardButton(
                                "🎵 MP3 " + "(" + "64 kbps" + ")",
                                callback_data=cb_string_64.encode("UTF-8"),
                            ),
                            InlineKeyboardButton(
                                "🎵 MP3 " + "(" + "128 kbps" + ")",
                                callback_data=cb_string_128.encode("UTF-8"),
                            ),
                        ]
                    )
                    inline_keyboard.append(
                        [
                            InlineKeyboardButton(
                                "🎵 MP3 " + "(" + "320 kbps" + ")",
                                callback_data=cb_string.encode("UTF-8"),
                            )
                        ]
                    )
            else:
                format_id = current_r_json["format_id"]
                format_ext = current_r_json["ext"]
                cb_string_video = "{}|{}|{}|{}".format("video", format_id, format_ext, random)
                inline_keyboard.append(
                    [
                        InlineKeyboardButton(
                            "🎞️ SVideo", callback_data=(cb_string_video).encode("UTF-8")
                        )
                    ]
                )
            break
        inline_keyboard.append([InlineKeyboardButton("✖️ Kapat", callback_data='close')])
        reply_markup = InlineKeyboardMarkup(inline_keyboard)
        # logger.info(reply_markup)
        thumbnail = DEF_THUMB_NAIL_VID_S
        thumbnail_image = DEF_THUMB_NAIL_VID_S

        if "thumbnail" in current_r_json:
            if current_r_json["thumbnail"] is not None:
                thumbnail = current_r_json["thumbnail"]
                thumbnail_image = current_r_json["thumbnail"]
        thumb_image_path = DownLoadFile(
            thumbnail_image,
            DOWNLOAD_LOCATION + "/" +
            str(update.from_user.id) + random + ".webp",
            CHUNK_SIZE,
            None,  # bot,
            Translation.DOWNLOAD_START,
            update.message_id,
            update.chat.id
        )

        if os.path.exists(thumb_image_path):
            im = Image.open(thumb_image_path).convert("RGB")
            im.save(thumb_image_path.replace(".webp", ".jpg"), "jpeg")
        else:
            thumb_image_path = None

        await send_message.edit_text(
            text=Translation.FORMAT_SELECTION.format(thumbnail) + "\n" + Translation.SET_CUSTOM_USERNAME_PASSWORD,
            reply_markup=reply_markup,
            parse_mode="html",
            disable_web_page_preview=True
        )
