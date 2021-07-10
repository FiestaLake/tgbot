import subprocess

import tg_bot.modules.helper_funcs.cas_api as cas
import tg_bot.modules.helper_funcs.git_api as git

from platform import python_version
from telegram import Update, ParseMode
from telegram.ext import CommandHandler

from tg_bot import dispatcher, CallbackContext
from tg_bot.modules.helper_funcs.filters import CustomFilters


def status(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    reply = "*System Status:* `operational`\n\n"
    reply += "*Python version:* `" + python_version() + "`\n"
    reply += "*python-telegram-bot:* `" + str(
        subprocess.check_output(
            "pip show python-telegram-bot | grep Version\:",
            shell=True).decode()).split()[1] + "`\n"
    reply += "*CAS API version:* `" + str(cas.vercheck()) + "`\n"
    reply += "*GitHub API version:* `" + str(git.vercheck()) + "`\n"
    update.effective_message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)


STATUS_HANDLER = CommandHandler("status",
                                status,
                                filters=CustomFilters.sudo_filter,
                                run_async=True)

dispatcher.add_handler(STATUS_HANDLER)
