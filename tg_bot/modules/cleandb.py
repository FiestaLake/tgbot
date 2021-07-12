from logging import Logger
from time import sleep

from tg_bot import OWNER_ID, dispatcher
import tg_bot.modules.sql.users_sql as user_sql

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, Filters


def get_invalid_chats(update: Update, context: CallbackContext, remove: bool = False):
    bot = context.bot
    chat_id = update.effective_chat.id
    chats = user_sql.get_all_chats()
    kicked_chats, progress = 0, 0
    chat_list = []
    progress_message = None

    for chat in chats:

        if ((100 * chats.index(chat)) / len(chats)) > progress:
            progress_bar = f"{progress}% completed in getting invalid chats."
            if progress_message:
                try:
                    bot.editMessageText(
                        progress_bar, chat_id, progress_message.message_id
                    )
                except:
                    pass
            else:
                progress_message = bot.sendMessage(chat_id, progress_bar)
            progress += 5

        cid = chat.chat_id
        sleep(0.1)
        try:
            bot.get_chat(cid, timeout=60)
        except (BadRequest, Unauthorized):
            kicked_chats += 1
            chat_list.append(cid)
        except:
            pass

    try:
        progress_message.delete()
    except:
        pass

    if not remove:
        return kicked_chats
    else:
        for muted_chat in chat_list:
            sleep(0.1)
            user_sql.del_chat(muted_chat)
        return kicked_chats


def cleandb(update: Update, context: CallbackContext):
    msg = update.effective_message

    msg.reply_text("Getting invalid chat count ...")
    invalid_chat_count = get_invalid_chats(update, context)

    reply = f"Total invalid chats - {invalid_chat_count}"

    buttons = [[InlineKeyboardButton("Clean DB now", callback_data="db_cleanup")]]

    update.effective_message.reply_text(
        reply, reply_markup=InlineKeyboardMarkup(buttons)
    )


def callback_button(update: Update, context: CallbackContext):
    bot = context.bot
    query = update.callback_query
    message = query.message
    chat_id = update.effective_chat.id
    query_type = query.data

    bot.answer_callback_query(query.id)

    if query_type == "db_cleanup":
        bot.editMessageText("Cleaning up DB ...", chat_id, message.message_id)
        invalid_chat_count = get_invalid_chats(update, context, True)
        reply = "Cleaned up {} chats from DB!".format(invalid_chat_count)
        bot.sendMessage(chat_id, reply)

    else:
        Logger.warning("Unknown callback occured in cleandb! Type={}".format(query.type))


__mod_name__ = "Clean DB"

DB_CLEANUP_HANDLER = CommandHandler("cleandb", 
                                    cleandb,
                                    filters=Filters.chat(OWNER_ID),
                                    run_async=True)
BUTTON_HANDLER = CallbackQueryHandler(callback_button, pattern="db_.*", run_async=True)

dispatcher.add_handler(DB_CLEANUP_HANDLER)
dispatcher.add_handler(BUTTON_HANDLER)

