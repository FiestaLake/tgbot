import html
from telegram.constants import PARSEMODE_HTML

from telegram.error import BadRequest, Unauthorized
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from typing import Optional

from telegram import Message, Chat, Update, User, ParseMode
from telegram.ext import CommandHandler, RegexHandler, Filters
from telegram.utils.helpers import mention_html

from tg_bot import LOGGER, dispatcher, CallbackContext
from tg_bot.modules.helper_funcs.chat_status import user_not_admin, user_admin
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import reporting_sql as sql

REPORT_GROUPS = 5


@user_admin
def report_setting(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if chat.type == chat.PRIVATE:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text(
                    "Turned on reporting! You'll be notified whenever anyone reports something."
                )

            elif args[0] in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("Turned off reporting! You wont get any reports.")
        else:
            msg.reply_text(
                "Your current report preference is: `{}`".format(
                    sql.user_should_report(chat.id)
                ),
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_chat_setting(chat.id, True)
                msg.reply_text(
                    "Turned on reporting! Admins who have turned on reports will be notified when /report "
                    "or @admin are called."
                )

            elif args[0] in ("no", "off"):
                sql.set_chat_setting(chat.id, False)
                msg.reply_text(
                    "Turned off reporting! No admins will be notified on /report or @admin."
                )
        else:
            msg.reply_text(
                "This chat's current setting is: `{}`".format(
                    sql.chat_should_report(chat.id)
                ),
                parse_mode=ParseMode.MARKDOWN,
            )


@user_not_admin
@loggable
def report(update: Update, context: CallbackContext) -> str:
    bot, args = context.bot, context.args
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if chat and sql.chat_should_report(chat.id):
        user_id, reason = extract_user_and_text(message, args)
        chat_name = chat.title or chat.first or chat.username

        if message.reply_to_message:
            reported_user = message.reply_to_message.from_user  # type: Optional[User]
        elif user_id:
            reported_user = bot.getChatMember(
                chat.id, user_id
            ).user  # type: Optional[User]
        else:
            message.reply_text("I can't guess the person you want to report.")
            return (
                "<b>{}:</b>"
                "\n#REPORTED FAILED"
                "\n<b>Reporter:</b> {} (<code>{}</code>)".format(
                    html.escape(chat_name),
                    mention_html(user.id, user.first_name),
                    user.id,
                )
            )

        if reported_user.id == bot.id:
            message.reply_text("Haha nope, not gonna report myself.")
            return ""

        log = (
            "<b>{}:</b>"
            "\n#REPORTED"
            "\n<b>Reporter:</b> {}"
            "\n<b>Whom:</b> {} (<code>{}</code>)".format(
                html.escape(chat_name),
                mention_html(user.id, user.first_name),
                mention_html(reported_user.id, reported_user.first_name),
                reported_user.id,
            )
        )
        if reason:
            log += "\n<b>Reason:</b> {}".format(reason)

        admin_msg = log
        if chat.type == chat.SUPERGROUP and chat.username:
            admin_msg += (
                "\n<b>Link:</b> "
                + '<a href="http://telegram.me/{}/{}">click here</a>'.format(
                    chat.username, message.message_id
                )
            )

        for admin in chat.get_administrators():
            if admin.user.is_bot:  # can't message bots
                continue
            if admin.user.id == user.id:  # don't have to get notifications
                continue
            if admin.user.id == reported_user.id:  # don't have to get notifications
                continue
            if sql.user_should_report(admin.user.id):
                try:
                    bot.send_message(
                        admin.user.id, admin_msg, parse_mode=ParseMode.HTML
                    )
                except Unauthorized:
                    pass
                except BadRequest:  # TODO: cleanup exceptions
                    LOGGER.exception("Exception while reporting user")

        message.reply_text(
            "Successfully reported "
            + '<a href="tg://user?id={id}">{name}</a> (<code>{id}</code>)!'.format(
                id=reported_user.id,
                name=reported_user.first_name,
            ),
            parse_mode=ParseMode.HTML,
        )

        return log

    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "This chat is setup to send user reports to admins, via /report and @admin: `{}`".format(
        sql.chat_should_report(chat_id)
    )


def __user_settings__(user_id):
    return "You receive reports from chats you're admin in: `{}`.\nToggle this with /reports in PM.".format(
        sql.user_should_report(user_id)
    )


__mod_name__ = "Reporting"

__help__ = """
We're all busy people who don't have time to monitor our groups 24/7. But how do you \
react if someone in your group is spamming?

Presenting reports; if someone in your group thinks someone needs reporting, they now have \
an easy way to call all admins.

 - /report <reason>: reply to a message to report it to admins.
 - @admin: reply to a message to report it to admins.
NOTE: neither of these will get triggered if used by admins

*Admin only:*
 - /reports <on/off>: change report setting, or view current status.
   - If done in pm, toggles your status.
   - If in chat, toggles that chat's status.

To report a user, simply reply to user's message with @admin or /report. \
This message tags all the chat admins; same as if they had been @'ed.
You MUST reply to a message to report a user; you can't just use @admin to tag admins for no reason!

Note that the report commands do not work when admins use them; or when used to report an admin. Bot assumes that \
admins don't need to report, or be reported!
"""

REPORT_HANDLER = CommandHandler(
    "report", report, filters=Filters.chat_type.groups, run_async=True
)
SETTING_HANDLER = CommandHandler("reports", report_setting, run_async=True)
ADMIN_REPORT_HANDLER = RegexHandler("(?i)@admin(s)?", report, run_async=True)

dispatcher.add_handler(REPORT_HANDLER, group=REPORT_GROUPS)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, group=REPORT_GROUPS)
dispatcher.add_handler(SETTING_HANDLER)
