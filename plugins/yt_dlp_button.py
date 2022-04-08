import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
LOGGER = logging.getLogger(__name__)

import asyncio
import json
import os
import shutil
import time
from datetime import datetime

from config import DOWNLOAD_LOCATION, LOG_CHANNEL, HTTP_PROXY, TG_MAX_FILE_SIZE, DEF_WATER_MARK_FILE
from database.database import db
from translation import Translation

from pyrogram.types import InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
from functions.display_progress import progress_for_pyrogram, humanbytes
from functions.help_Nekmo_ffmpeg import generate_screen_shots, VideoThumb, VideoMetaData, VMMetaData, DocumentThumb, \
    AudioMetaData
from functions.utils import remove_urls, remove_emoji


async def yt_dlp_call_back(bot, update):
    cb_data = update.data
    tg_send_type, yt_dlp_format, yt_dlp_ext, random = cb_data.split("|")

    dtime = str(time.time())

    current_user_id = update.message.reply_to_message.from_user.id
    current_touched_user_id = update.from_user.id
    if current_user_id != current_touched_user_id:
        await bot.answer_callback_query(
            callback_query_id=update.id,
            text="Seni tanımıyorum ahbap.",
            show_alert=True,
            cache_time=0,
        )
        return False, None

    thumb_image_path = DOWNLOAD_LOCATION + \
                       "/" + str(update.from_user.id) + f'{random}' + ".jpg"
    save_ytdl_json_path = DOWNLOAD_LOCATION + \
                          "/" + str(update.from_user.id) + f'{random}' + ".json"
    LOGGER.info(save_ytdl_json_path)

    try:
        with open(save_ytdl_json_path, "r", encoding="utf8") as f:
            response_json = json.load(f)
    except (FileNotFoundError) as e:
        await bot.delete_messages(
            chat_id=update.message.chat.id,
            message_ids=update.message.message_id,
            revoke=True
        )
        return False
    #
    response_json = response_json[0]
    # TODO: temporary limitations
    # LOGGER.info(response_json)
    #
    yt_dlp_url = update.message.reply_to_message.text
    LOGGER.info(yt_dlp_url)
    #

    name = str(response_json.get("title")[:100]) + \
           "." + yt_dlp_ext

    custom_file_name = remove_emoji(remove_urls(name))
    LOGGER.info(custom_file_name)
    #
    yt_dlp_username = None
    yt_dlp_password = None
    if "|" in yt_dlp_url:
        url_parts = yt_dlp_url.split("|")
        if len(url_parts) == 2:
            yt_dlp_url = url_parts[0]
            custom_file_name = url_parts[1]
        elif len(url_parts) == 4:
            yt_dlp_url = url_parts[0]
            custom_file_name = url_parts[1]
            yt_dlp_username = url_parts[2]
            yt_dlp_password = url_parts[3]
        else:
            for entity in update.message.reply_to_message.entities:
                if entity.type == "text_link":
                    yt_dlp_url = entity.url
                elif entity.type == "url":
                    o = entity.offset
                    l = entity.length
                    yt_dlp_url = yt_dlp_url[o:o + l]
        if yt_dlp_url is not None:
            yt_dlp_url = yt_dlp_url.strip()
        if custom_file_name is not None:
            custom_file_name = custom_file_name.strip()
        if yt_dlp_username is not None:
            yt_dlp_username = yt_dlp_username.strip()
        if yt_dlp_password is not None:
            yt_dlp_password = yt_dlp_password.strip()

    else:
        for entity in update.message.reply_to_message.entities:
            if entity.type == "text_link":
                yt_dlp_url = entity.url
            elif entity.type == "url":
                o = entity.offset
                l = entity.length
                yt_dlp_url = yt_dlp_url[o:o + l]

    await bot.edit_message_text(
        text=Translation.DOWNLOAD_START.format(custom_file_name),
        chat_id=update.message.chat.id,
        parse_mode="html",
        message_id=update.message.message_id
    )

    if "fulltitle" in response_json:
        description = response_json["fulltitle"][0:1021]

    tmp_directory_for_each_user = os.path.join(
        DOWNLOAD_LOCATION,
        str(update.from_user.id),
        dtime
    )
    if not os.path.isdir(tmp_directory_for_each_user):
        os.makedirs(tmp_directory_for_each_user)
    download_directory = tmp_directory_for_each_user
    download_directory = os.path.join(tmp_directory_for_each_user, custom_file_name)
    command_to_exec = []
    if tg_send_type == "audio":
        command_to_exec = [
            "yt-dlp",
            "-c",
            "--max-filesize", str(TG_MAX_FILE_SIZE),
            "--prefer-ffmpeg",
            "--extract-audio",
            "--audio-format", yt_dlp_ext,
            "--audio-quality", yt_dlp_format,
            yt_dlp_url,
            "-o", download_directory,
            "--external-downloader",
            "aria2c",
            "--external-downloader-args",
            "-x 16 -s 16 -k 1M"
        ]
    else:
        try:
            for for_mat in response_json["formats"]:
                format_id = for_mat.get("format_id")
                if format_id == yt_dlp_format:
                    acodec = for_mat.get("acodec")
                    if acodec == "none":
                        yt_dlp_format += "+bestaudio"
                    break

            command_to_exec = [
                "yt-dlp",
                "-c",
                "--max-filesize", str(TG_MAX_FILE_SIZE),
                "--embed-subs",
                "-f", yt_dlp_format,
                "--hls-prefer-ffmpeg", yt_dlp_url,
                "-o", download_directory,
                "--external-downloader",
                "aria2c",
                "--external-downloader-args",
                "-x 16 -s 16 -k 1M"
            ]
        except KeyError:
            command_to_exec = [
                "yt-dlp",
                "-c",
                "--max-filesize", str(TG_MAX_FILE_SIZE),
                yt_dlp_url, "-o", download_directory
            ]

    #
    command_to_exec.append("--no-warnings")
    # command_to_exec.append("--quiet")
    command_to_exec.append("--restrict-filenames")
    #
    if HTTP_PROXY != "":
        command_to_exec.append("--proxy")
        command_to_exec.append(HTTP_PROXY)
    if "moly.cloud" in yt_dlp_url:
        command_to_exec.append("--referer")
        command_to_exec.append("https://vidmoly.to/")
    if "closeload" in yt_dlp_url:
        command_to_exec.append("--referer")
        command_to_exec.append("https://closeload.com/")
    if yt_dlp_username is not None:
        command_to_exec.append("--username")
        command_to_exec.append(yt_dlp_username)
    if yt_dlp_password is not None:
        command_to_exec.append("--password")
        command_to_exec.append(yt_dlp_password)
    LOGGER.info(command_to_exec)
    start = datetime.now()
    process = await asyncio.create_subprocess_exec(
        *command_to_exec,
        # stdout must a pipe to be accessible as process.stdout
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    # LOGGER.info(e_response)
    # LOGGER.info(t_response)
    ad_string_to_replace = "please report this issue on https://yt-dl.org/bug . Make sure you are using the latest version; see  https://yt-dl.org/update  on how to update. Be sure to call youtube-dl with the --verbose flag and include its complete output."
    if e_response and ad_string_to_replace in e_response:
        error_message = e_response.replace(ad_string_to_replace, "")
        await update.message.edit_caption(caption=error_message)
        return False, None
    if t_response:
        # LOGGER.info(t_response)
        try:
            os.remove(save_ytdl_json_path)
        except FileNotFoundError as exc:
            pass

        end_one = datetime.now()
        time_taken_for_download = (end_one - start).seconds

        user_id = update.from_user.id
        #
        file_size = TG_MAX_FILE_SIZE + 1
        #
        LOGGER.info(tmp_directory_for_each_user)

        try:
            file_size = os.stat(download_directory).st_size
        except FileNotFoundError as exc:
            download_directory = os.path.splitext(download_directory)[0] + "." + "mkv"
            # https://stackoverflow.com/a/678242/4723940
            file_size = os.stat(download_directory).st_size
        try:
            if tg_send_type == 'video' and 'webm' in download_directory:
                ownload_directory = download_directory.rsplit('.', 1)[0] + '.mkv'
                os.rename(download_directory, ownload_directory)
                download_directory = ownload_directory
        except:
            pass

        if file_size > TG_MAX_FILE_SIZE:
            await bot.edit_message_text(
                chat_id=update.message.chat.id,
                text=Translation.RCHD_TG_API_LIMIT.format(time_taken_for_download, humanbytes(file_size)),
                message_id=update.message.message_id
            )
        else:
            is_w_f = False
            images = await generate_screen_shots(
                download_directory,
                tmp_directory_for_each_user,
                is_w_f,
                DEF_WATER_MARK_FILE,
                300,
                9
            )
            try:
                await bot.edit_message_text(
                    text=Translation.UPLOAD_START,
                    chat_id=update.message.chat.id,
                    message_id=update.message.message_id
                )
            except:
                pass

            start_time = time.time()
            btn = [[
                InlineKeyboardButton(f"Upload By {update.from_user.id}", url=f"tg://user?id={update.from_user.id}")
            ]]
            reply_markup = InlineKeyboardMarkup(btn)

            if (await db.get_upload_as_doc(update.from_user.id)) is True:
                thumbnail = await DocumentThumb(bot, update)
                await update.message.reply_to_message.reply_chat_action("upload_document")
                document = await bot.send_document(
                    chat_id=update.message.chat.id,
                    document=download_directory,
                    thumb=thumbnail,
                    caption=custom_file_name,
                    reply_to_message_id=update.message.reply_to_message.message_id,
                    # reply_markup=reply_markup,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
                if LOG_CHANNEL:
                    await document.copy(LOG_CHANNEL)
            else:
                width, height, duration = await VideoMetaData(download_directory)
                thumb_image_path = await VideoThumb(bot, update, duration, download_directory)
                await update.message.reply_to_message.reply_chat_action("upload_video")
                video = await bot.send_video(
                    chat_id=update.message.chat.id,
                    video=download_directory,
                    caption=custom_file_name,
                    duration=duration,
                    width=width,
                    height=height,
                    supports_streaming=True,
                    # reply_markup=reply_markup,
                    thumb=thumb_image_path,
                    reply_to_message_id=update.message.reply_to_message.message_id,
                    progress=progress_for_pyrogram,
                    parse_mode='html',
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
                if LOG_CHANNEL:
                    await video.copy(LOG_CHANNEL)

            if tg_send_type == "audio":
                duration = await AudioMetaData(download_directory)
                thumbnail = await DocumentThumb(bot, update)
                await update.message.reply_to_message.reply_chat_action("upload_audio")
                audio = await bot.send_audio(
                    chat_id=update.message.chat.id,
                    audio=download_directory,
                    caption=custom_file_name,
                    parse_mode="HTML",
                    duration=duration,
                    thumb=thumbnail,
                    reply_to_message_id=update.message.reply_to_message.message_id,
                    # reply_markup=reply_markup,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
                if LOG_CHANNEL:
                    await audio.copy(LOG_CHANNEL)
            elif tg_send_type == "vm":
                width, duration = await VMMetaData(download_directory)
                thumbnail = await VideoThumb(bot, update, duration, download_directory)
                await update.message.reply_to_message.reply_chat_action("upload_video_note")
                video_note = await bot.send_video_note(
                    chat_id=update.message.chat.id,
                    video_note=download_directory,
                    duration=duration,
                    length=width,
                    thumb=thumbnail,
                    reply_to_message_id=update.message.reply_to_message.message_id,
                    # reply_markup=reply_markup,
                    progress=progress_for_pyrogram,
                    progress_args=(
                        Translation.UPLOAD_START,
                        update.message,
                        start_time
                    )
                )
                if LOG_CHANNEL:
                    await video_note.copy(LOG_CHANNEL)

            end_two = datetime.now()
            time_taken_for_upload = (end_two - end_one).seconds
            media_album_p = []
            if (await db.get_generate_ss(update.from_user.id)) is True:
                if images is not None:
                    i = 0
                    uname = (await bot.get_me())['username']
                    caption = f'@{str(uname)}'
                    for image in images:
                        if os.path.exists(str(image)):
                            if i == 0:
                                media_album_p.append(
                                    InputMediaPhoto(
                                        media=image,
                                        caption=caption,
                                        parse_mode="html"
                                    )
                                )
                            else:
                                media_album_p.append(
                                    InputMediaPhoto(
                                        media=image
                                    )
                                )
                            i = i + 1
                await bot.send_media_group(
                    chat_id=update.message.chat.id,
                    disable_notification=True,
                    reply_to_message_id=update.message.message_id,
                    media=media_album_p
                )
            #
            try:
                shutil.rmtree(tmp_directory_for_each_user)
            except:
                pass
            try:
                os.remove(download_directory)
            except:
                pass
            try:
                os.remove(thumb_image_path)
            except:
                pass
            try:
                await bot.edit_message_text(
                    text=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(time_taken_for_download,
                                                                                time_taken_for_upload),
                    chat_id=update.message.chat.id,
                    message_id=update.message.message_id,
                    disable_web_page_preview=True
                )
            except MessageNotModified:
                pass
