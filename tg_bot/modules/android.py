import re, html, time
from bs4 import BeautifulSoup
from requests import get
from yaml import load, Loader
from telegram import Message, Update, Bot, User, Chat, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import run_async
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher, updater, CallbackContext
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.github import getphh

GITHUB = 'https://github.com'
DEVICES_DATA = 'https://raw.githubusercontent.com/androidtrackers/certified-android-devices/master/by_device.json'


def phh(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    index = int(args[0]) if len(args) > 0 and args[0].isdigit() else 0
    text = getphh(index)
    update.effective_message.reply_text(text,
                                        parse_mode=ParseMode.HTML,
                                        disable_web_page_preview=True)
    return


def magisk(update: Update, context: CallbackContext):
    bot = context.bot
    url = 'https://raw.githubusercontent.com/topjohnwu/magisk-files/'
    releases = ""
    for type, branch in {
            "Stable": "master/stable",
            "Beta": "master/beta", 
            "Canary": "master/canary"
    }.items():
        data = get(url + branch + '.json').json()
        notes = "https://topjohnwu.github.io/Magisk/releases/" + data[
                "magisk"]["versionCode"] + ".html"
        if str(type) == "Canary":
            notes = "https://github.com/topjohnwu/magisk-files/blob/canary/notes.md"
        releases += f'*• {type}* - `{data["magisk"]["version"]}-{data["magisk"]["versionCode"]}` → ' \
                    f'[Notes]({notes}) / ' \
                    f'[Magisk]({data["magisk"]["link"]}) \n'

    del_msg = update.message.reply_text(
        "*Latest Magisk Releases:*\n{} \n" \
        "*Install/uninstall instructions*:\nhttps://topjohnwu.github.io/Magisk/install.html".format(releases),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True)
    time.sleep(300)
    try:
        del_msg.delete()
        update.effective_message.delete()
    except BadRequest as err:
        if (err.message == "Message to delete not found") or (
                err.message == "Message can't be deleted"):
            return


def device(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    if len(args) == 0:
        reply = f'No codename provided, write a codename for fetching informations.'
        del_msg = update.effective_message.reply_text(
            "{}".format(reply),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
            return
        except BadRequest as err:
            if (err.message == "Message to delete not found") or (
                    err.message == "Message can't be deleted"):
                return
    device = " ".join(args)
    db = get(DEVICES_DATA).json()
    newdevice = device.strip('lte') if device.startswith('beyond') else device
    try:
        reply = f'Search results for {device}:\n\n'
        brand = db[newdevice][0]['brand']
        name = db[newdevice][0]['name']
        model = db[newdevice][0]['model']
        codename = newdevice
        reply += f'<b>{brand} {name}</b>\n' \
            f'Model: <code>{model}</code>\n' \
            f'Codename: <code>{codename}</code>\n\n'
    except KeyError as err:
        reply = f"Couldn't find info about {device}!\n"
        del_msg = update.effective_message.reply_text(
            "{}".format(reply),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
        except BadRequest as err:
            if (err.message == "Message to delete not found") or (
                    err.message == "Message can't be deleted"):
                return
    update.message.reply_text("{}".format(reply),
                              parse_mode=ParseMode.HTML,
                              disable_web_page_preview=True)


def getfw(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    if len(args) == 1:
        msg = update.effective_message
        codename = args[0]

        URL = "https://raw.githubusercontent.com/XiaomiFirmwareUpdater/miui-updates-tracker/master/data/latest.yml"

        yaml_data = load(get(URL).content, Loader=Loader)
        data = [i for i in yaml_data if codename in i['codename']]

        if len(data) < 1:
            del_msg = msg.reply_text("Provide a valid codename (and csc)!")
            time.sleep(5)
            try:
                del_msg.delete()
                update.effective_message.delete()
                return
            except BadRequest as err:
                if (err.message == "Message to delete not found") or (
                        err.message == "Message can't be deleted"):
                        return

        markup = []
        for fw in data:
            av = fw['android']
            branch = fw['branch']
            method = fw['method']
            link = fw['link']
            fname = fw['name']
            version = fw['version']

            btn = fname + ' | ' + branch + ' | ' + method + ' | ' + version
            markup.append([InlineKeyboardButton(text=btn, url=link)])

        device = fname.split(" ")
        device.pop()
        device = " ".join(device)
        del_msg = msg.reply_text(f"The latest firmwares for *{device}* are:",
                        reply_markup=InlineKeyboardMarkup(markup),
                        parse_mode=ParseMode.MARKDOWN)
        time.sleep(60)
        try:
            del_msg.delete()
            update.effective_message.delete()
            return
        except BadRequest as err:
            if (err.message == "Message to delete not found") or (
                err.message == "Message can't be deleted"):
                    return

    if len(args) == 2:
        temp, csc = args
        model = f'sm-' + temp if not temp.upper().startswith('SM-') else temp
        fota = get(
            f'http://fota-cloud-dn.ospserver.net/firmware/{csc.upper()}/{model.upper()}/version.xml'
        )
        test = get(
            f'http://fota-cloud-dn.ospserver.net/firmware/{csc.upper()}/{model.upper()}/version.test.xml'
        )
        if test.status_code != 200:
            del_msg = update.effective_message.reply_text("Provide a valid codename and csc!")
            time.sleep(5)
            try:
                del_msg.delete()
                update.effective_message.delete()
            except BadRequest as err:
                if (err.message == "Message to delete not found") or (
                        err.message == "Message can't be deleted"):
                    return

        url1 = f'https://samfrew.com/model/{model.upper()}/region/{csc.upper()}/'
        url2 = f'https://www.sammobile.com/samsung/firmware/{model.upper()}/{csc.upper()}/'
        url3 = f'https://sfirmware.com/samsung-{model.lower()}/#tab=firmwares'
        url4 = f'https://samfw.com/firmware/{model.upper()}/{csc.upper()}/'

        page1 = BeautifulSoup(fota.content, 'lxml')
        page2 = BeautifulSoup(test.content, 'lxml')
        os1 = page1.find("latest").get("o")
        os2 = page2.find("latest").get("o")
        reply = ""
        if page1.find("latest").text.strip():
            pda1, csc1, phone1 = page1.find("latest").text.strip().split('/')
            reply += f'*Latest firmware for {model.upper()} and {csc.upper()} is:*\n'
            reply += f'• PDA: `{pda1}`\n• CSC: `{csc1}`\n'
            if phone1:
                reply += f'• Phone: `{phone1}`\n'
            if os1:
                reply += f'• Android: `{os1}`\n'
                reply += f'\n'
        else:
            reply += f'*No public release found for {model.upper()} and {csc.upper()}.*\n\n'
        if len(page2.find("latest").text.strip().split('/')) == 3:
            reply += f'*Latest test firmware for {model.upper()} and {csc.upper()} is:*\n'
            pda2, csc2, phone2 = page2.find("latest").text.strip().split('/')
            reply += f'• PDA: `{pda2}`\n• CSC: `{csc2}`\n'
            if phone2:
                reply += f'• Phone: `{phone2}`\n'
            if os2:
                reply += f'• Android: `{os2}`\n'
            reply += f'\n'
        elif not os2 == None:
            reply += f'*Latest test firmware for {model.upper()} and {csc.upper()} is:*\n'
            md5 = page2.find("latest").text.strip()
            reply += f'• Hash: `{md5}`\n• Android: `{os2}`\n\n'
        else:
            reply += f'*No test release found for {model.upper()} and {csc.upper()}.*\n\n'
        reply += f'*Downloads for {model.upper()} and {csc.upper()}*\n'
        reply += f'• [samfrew.com]({url1})\n'
        reply += f'• [sammobile.com]({url2})\n'
        reply += f'• [sfirmware.com]({url3})\n'
        reply += f'• [samfw.com]({url4})\n'
        del_msg = update.message.reply_text("{}".format(reply),
                                parse_mode=ParseMode.MARKDOWN,
                                disable_web_page_preview=True)
        
        time.sleep(60)
        try:
            del_msg.delete()
            update.effective_message.delete()
            return
        except BadRequest as err:
            if (err.message == "Message to delete not found") or (
                err.message == "Message can't be deleted"):
                    return

    else:
        msg = update.effective_message
        msg.reply_text("Provide a valid codename (and csc)!")
        return


def twrp(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    if len(args) == 0:
        reply = 'No codename provided, write a codename for fetching informations.'
        del_msg = update.effective_message.reply_text(
            "{}".format(reply),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
            return
        except BadRequest as err:
            if (err.message == "Message to delete not found") or (
                    err.message == "Message can't be deleted"):
                return

    device = " ".join(args)
    url = get(f'https://eu.dl.twrp.me/{device}/')
    if url.status_code == 404:
        reply = f"Couldn't find twrp downloads for {device}!\n"
        del_msg = update.effective_message.reply_text(
            "{}".format(reply),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
        except BadRequest as err:
            if (err.message == "Message to delete not found") or (
                    err.message == "Message can't be deleted"):
                return
    else:
        reply = f'*Latest Official TWRP for {device}*\n'
        db = get(DEVICES_DATA).json()
        newdevice = device.strip('lte') if device.startswith(
            'beyond') else device
        try:
            brand = db[newdevice][0]['brand']
            name = db[newdevice][0]['name']
            reply += f'*{brand} - {name}*\n'
        except KeyError as err:
            pass
        page = BeautifulSoup(url.content, 'lxml')
        date = page.find("em").text.strip()
        reply += f'*Updated:* {date}\n'
        trs = page.find('table').find_all('tr')
        row = 2 if trs[0].find('a').text.endswith('tar') else 1
        for i in range(row):
            download = trs[i].find('a')
            dl_link = f"https://eu.dl.twrp.me{download['href']}"
            dl_file = download.text
            size = trs[i].find("span", {"class": "filesize"}).text
            reply += f'[{dl_file}]({dl_link}) - {size}\n'

        update.message.reply_text("{}".format(reply),
                                  parse_mode=ParseMode.MARKDOWN,
                                  disable_web_page_preview=True)


__help__ = """
If you are searching stuffs related to Android, then here you are.

 - /magisk - gets the latest magisk release for Stable/Beta/Canary
 - /device <codename> - gets android device basic info from its codename
 - /twrp <codename> -  gets latest twrp for the android device using the codename
 - /getfw <model> <csc> - Samsung
   /getfw <codename> - Miui
   : gets firmware info & download links for the given device
 
 *Examples:*
  /device greatlte
  /twrp a5y17lte
  /checkfw SM-A305F INS
  /getfw SM-M205FN SER
  /getfw whyred
 
"""

__mod_name__ = "Android"

PHH_HANDLER = DisableAbleCommandHandler("phh", phh, run_async=True)
MAGISK_HANDLER = DisableAbleCommandHandler("magisk", magisk, run_async=True)
DEVICE_HANDLER = DisableAbleCommandHandler("device", device, run_async=True)
TWRP_HANDLER = DisableAbleCommandHandler("twrp", twrp, run_async=True)
GETFW_HANDLER = DisableAbleCommandHandler("getfw", getfw, run_async=True)

dispatcher.add_handler(PHH_HANDLER)
dispatcher.add_handler(MAGISK_HANDLER)
dispatcher.add_handler(DEVICE_HANDLER)
dispatcher.add_handler(TWRP_HANDLER)
dispatcher.add_handler(GETFW_HANDLER)
