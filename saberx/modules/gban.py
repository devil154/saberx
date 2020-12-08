import html, time
from io import BytesIO

from telegram import ParseMode, ChatAction, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import ElitesOfRobot.modules.sql.antispam_sql as sql
from ElitesOfRobot import (
    dispatcher,
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    STRICT_GBAN,
    GBAN_DUMP,
    ERROR_DUMP,
    DEV_USERS,
    WHITELIST_USERS,
    spamwtc,
    SUPPORT_CHAT,
)
from saberx.modules.helper_funcs.chat_status import user_admin, is_user_admin, support_plus
from saberx.modules.helper_funcs.extraction import extract_user, extract_user_and_text, get_user
from saberx.modules.helper_funcs.filters import CustomFilters
from saberx.modules.helper_funcs.alternate import typing_action, send_action
from saberx.modules.sql.users_sql import get_all_chats

from saberx import oko
from telethon import events

from html_telegraph_poster import TelegraphPoster
from html_telegraph_poster.upload_images import upload_image

Saberx_Gban = TelegraphPoster(use_api=True)
Saberx_Gban.create_api_token('saberx gban', 'saberx') 


GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "Bots can't add new chat members",
    "Channel_private",
    "Chat not found",
    "Can't demote chat creator",
    "Chat_admin_required",
    "Group chat was deactivated",
    "Method is available for supergroup and channel chats only",
    "Method is available only for supergroups",
    "Need to be inviter of a user to kick it from a basic group",
    "Not enough rights to restrict/unrestrict chat member",
    "Not in the chat",
    "Only the creator of a basic group can kick group administrators",
    "Peer_id_invalid",
    "User is an administrator of the chat",
    "User_not_participant",
    "Reply message not found",
    "Can't remove chat owner",
}

UNGBAN_ERRORS = {
    "Bots can't add new chat members",
    "Channel_private",
    "Chat not found",
    "Can't demote chat creator",
    "Chat_admin_required",
    "Group chat was deactivated",
    "Method is available for supergroup and channel chats only",
    "Method is available only for supergroups",
    "Need to be inviter of a user to kick it from a basic group",
    "Not enough rights to restrict/unrestrict chat member",
    "Not in the chat",
    "Only the creator of a basic group can kick group administrators",
    "Peer_id_invalid",
    "User is an administrator of the chat",
    "User_not_participant",
    "Reply message not found",
    "User not found",
}



@run_async
@support_plus
@typing_action
def gban(update, context):
    message = update.effective_message
    chat = update.effective_chat
    args = context.args
    user_id, reason = extract_user_and_text(message, args)
    if message.reply_to_message.photo:
        photo = context.bot.get_file(update.message.reply_to_message.photo[-1].file_id)
        evidence_img = photo.download(f'{str(update.message.from_user.id)}.jpg')
        evidence_img = upload_image(evidence_img)
    else:
        evidence = message.reply_to_message.text
        
    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return

    if user_id == OWNER_ID: 
        return

    if int(user_id) in DEV_USERS: 
        return

    if int(user_id) in SUDO_USERS: 
        return
    
    if int(user_id) in SUPPORT_USERS: 
        return

    if int(user_id) in WHITELIST_USERS:
        return

    if user_id == context.bot.id: 
        return

    try:
        user_chat = context.bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != "private":
        message.reply_text("That's not a user!")
        return

    if user_chat.first_name == "":
        message.reply_text("This is a deleted account! no point to gban them...")
        return
    
    if not reason:
        message.reply_text("Global Ban requires a reason to do so, why not send me one?")
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            message.reply_text(
                "This user is already gbanned; I'd change the reason, but you haven't given me one..."
            )
            return

        old_reason = sql.update_gban_reason(
            user_id, user_chat.username or user_chat.first_name, reason
        )
        user_id, new_reason = extract_user_and_text(message, args)

        if old_reason:
            banner = update.effective_user  # type: Optional[User]
            bannerid = banner.id
            bannername = banner.first_name
            new_reason = (
                f"{new_reason}"
            )

            context.bot.sendMessage(
                GBAN_DUMP,
                "<b>Global Ban Reason Update</b>"
                "\n<b>Officer:</b> {}"
                "\n\n<b>User:</b> {}"
                "\n<b>ID:</b> <code>{}</code>"
                "\n<b>Previous Reason:</b> {}"
                "\n<b>New Reason:</b> {}".format(
                    mention_html(banner.id, banner.first_name),
                    mention_html(
                        user_chat.id, user_chat.first_name or "Deleted Account"
                    ),
                    user_chat.id,
                    old_reason,
                    new_reason,
                ),
                parse_mode=ParseMode.HTML,
            )

            message.reply_text(
                "This user is already gbanned, for the following reason:\n"
                "<code>{}</code>\n"
                "I've gone and updated it with your new reason!".format(
                    html.escape(old_reason)
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            message.reply_text(
                "This user is already gbanned, but had no reason set; I've gone and updated it!"
            )

        return
    
    banner = update.effective_user
    bannerid = banner.id
    bannername = banner.first_name
    reason = f"{reason}"
    officer = f"{bannername}"
    officerid =f"{bannerid}"
    

    if chat.type != 'private':
            chat_origin = "<b>{} ({})</b>".format(
            html.escape(chat.title), chat.id)
    else:
        chat_origin = "<b>{}</b>".format(chat.id)
        
    if message.reply_to_message.photo:
        evidence = f"<img src='{evidence_img}'>"
    else:
         evidence = evidence  
    EVIDENSE_NEW_GBAN = f"<strong>New Global Ban</strong> \
                        \n<strong>Originated from:</strong> <code>{chat_origin}</code> \
                        \n<strong>Officer:</strong> {mention_html(banner.id, banner.first_name)} \n\
                        \n<strong>User:</strong> {mention_html(user_chat.id, user_chat.first_name)} \
                        \n<strong>ID:</strong> <code>{user_chat.id}</code> \
                        \n<strong>Reason:</strong> {reason} \
                        \n\n<strong>Evidence:</strong> <br>\n{evidence}"
    
    page = Saberx_Gban.post(title=f"Saberx-Gban-{user_chat.id}", author=f"{banner.first_name} ({banner.id})", text=EVIDENSE_NEW_GBAN)
    evidence_link = page.get('url')
    evidence_link = "<a href='{}'>{}</a>".format(evidence_link, f"Saberx Evidence")
    
    message.reply_text(
        f"<b>Beginning of Global Ban For</b> {mention_html(user_chat.id, user_chat.first_name)}"
        f"\n<b>With ID</b>: <code>{user_chat.id}</code>"
        f"\n\n<b>Officer</b>: {banner.first_name}"
        f"\n<b>Officer ID</b>: <code>{banner.id}</code>"
        f"\n\n<b>Reason</b>: <code>{reason}</code>"
        f"\n<b>Evidence:</b> {evidence_link}",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
    starting_usermsg = f"""#Event\n<b>You've Been Globally Banned</b>\n<b>Reason:</b> {reason}\n<b>Global Ban Log:</b> <a href="https://t.me/ElitesOfLogs">LOGS</a>\n<b>Appeal:</b> @{SUPPORT_CHAT}"""
    
   
    try:
        if chat.type != 'private':
            chat_origin = "<b>{} ({})</b>".format(
            html.escape(chat.title), chat.id)
        else:
            chat_origin = "<b>{}</b>".format(chat.id)
        context.bot.sendMessage(
            GBAN_DUMP,  
            "#GBANNED"
            f"\n<b>Originated from:</b> <code>{chat_origin}</code>"
            "\n<b>Officer:</b> {}"
            "\n\n<b>User:</b> {}"
            "\n<b>ID:</b> <code>{}</code>"
            "\n<b>Reason:</b> {}"
            "\n<b>Evidence:</b> {}".format(
                mention_html(banner.id, banner.first_name),
                mention_html(user_chat.id, user_chat.first_name),
                user_chat.id,
                reason,
                evidence_link,
            ),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        
        
        
    except Exception:
        context.bot.send_message(ERROR_DUMP, "<b>[Error]</b>"
                                    "\nFailed to Log gban user."
                                    )
    
    try:
        context.bot.send_message(user_chat.id, starting_usermsg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception:
        context.bot.send_message(ERROR_DUMP,
                                   f"<b>[Error]</b>\n"
                                   f"Failed to send Gban message to this user."
                                   f"\nID: <code>{user_chat.id}</code>",
                         parse_mode=ParseMode.HTML
                         )    

    try:
        context.bot.kick_chat_member(chat.id, user_chat.id)
    except BadRequest as excp:
        if excp.message in GBAN_ERRORS:
            pass
        
    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)
    
    

@run_async
@support_plus
@typing_action
def ungban(update, context):
    message = update.effective_message
    bot = context.bot
    args = context.args
    user_id, reason = extract_user_and_text(message, args)
    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return

    user_chat = context.bot.get_chat(user_id)
    if user_chat.type != "private":
        message.reply_text("That's not a user!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("This user is not gbanned!")
        return
    
    if not reason:
        message.reply_text(
            "Removal of Global Ban requires a reason."
        )
        return
    
    unbanner = update.effective_user  # type: Optional[User]
    full_reason = html.escape(
        f"{reason}")
    officer = "{unbanner.first_name}"
    officerid = "{unbanner.id}"


    message.reply_text(
        "\n<b>Regression Of Global Ban</b>"
        "\n<b>Officer:</b> {}"
        "\n\n<b>User:</b> {}"
        "\n<b>Reason:</b> {}".format(
            mention_html(unbanner.id, unbanner.first_name),
            mention_html(user_chat.id, user_chat.first_name),
            full_reason,
        ),
        parse_mode=ParseMode.HTML,
    )
    try:
        context.bot.sendMessage(
            GBAN_DUMP,
            "#UNGBANNED" 
            "\n<b>Officer:</b> {}"
            "\n\n<b>User:</b> {}"
            "\n<b>ID:</b> <code>{}</code>"
            "\n<b>Reason:</b> {}".format(
                mention_html(unbanner.id, unbanner.first_name),
                mention_html(user_chat.id, user_chat.first_name),
                user_chat.id, full_reason,
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        bot.send_message(GBAN_DUMP, 
                         "<b>[Error]</b>"
                         "\nFailed to Log un-gban user."
                         )
    try:
        ungban_strating_user = f"#Event\n<b>You've Been Globally Unbanned</b>\n<b>Reason:</b> {full_reason}"
        
        bot.send_message(user_chat.id, ungban_strating_user, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
        bot.send_message(user_chat.id,
                         "This user have been ungbanned succesfully, they might have to ask 'admins' of chats they were banned to unban manually due to global ban." \
                        "\n\nPlease forward this message to them or let them know about this.",
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                        )
    except Exception:
        bot.send_message(ERROR_DUMP,
                         f"<b>[Error]</b>\n"
                         f"Failed to send Un-Gban message to this user."
                         f"\nID: <code>{user_chat.id}</code>",
                         parse_mode=ParseMode.HTML
                         )
        
        message.reply_text("This user have been ungbanned succesfully, they might have to ask 'admins' of chats they were banned to unban manually due to global ban." \
                       "\n\nPlease forward this message to them or let them know about this.")
 
    sql.ungban_user(user_id)
    
    

@run_async
@support_plus
@send_action(ChatAction.UPLOAD_DOCUMENT)
def gbanlist(update, context):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text(
            "There aren't any gbanned users! You're kinder than I expected..."
        )
        return

    banfile = "List of retards.\n"
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(
            document=output,
            filename="gbanlist.txt",
            caption="Here is the list of currently gbanned users.",
        )


def check_and_ban(update, user_id, should_message=True):

    try:
        spmban = spamwtc.get_ban(int(user_id))
        if spmban:
            update.effective_chat.kick_member(user_id)
            if should_message:
                update.effective_message.reply_text(
                    f"This User Has Been Detected As Spammer By @SpamWatch And Has Been Removed!\nReason: <code>{spmban.reason}</code>",
                    parse_mode=ParseMode.HTML,
                )
                return
            else:
                return
    except Exception:
        pass

    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            usr = sql.get_gbanned_user(user_id)
            greason = usr.reason
            if not greason:
                greason = "No reason given"

            update.effective_message.reply_text(
                f"*Alert! This User Was GBanned And Have Been Removed!*\n*Reason*: {greason}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return


@run_async
def enforce_gban(update, context):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if (
        sql.does_chat_gban(update.effective_chat.id)
        and update.effective_chat.get_member(context.bot.id).can_restrict_members
    ):
        user = update.effective_user
        chat = update.effective_chat
        msg = update.effective_message

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)

@run_async
@user_admin
@typing_action
def gbanstat(update, context):
    args = context.args
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "I've enabled antispam in this group. This will help protect you "
                "from spammers, unsavoury characters, and the biggest trolls."
            )
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "I've disabled antispam in this group. GBans wont affect your users "
                "anymore. You'll be less protected from any trolls and spammers "
                "though!"
            )
    else:
        update.effective_message.reply_text(
            "Give me some arguments to choose a setting! on/off, yes/no!\n\n"
            "Your current setting is: {}\n"
            "When True, any gbans that happen will also happen in your group. "
            "When False, they won't, leaving you at the possible mercy of "
            "spammers.".format(sql.does_chat_gban(update.effective_chat.id))
        )


def __stats__():
    return "┣⊸ Gbanned Users - {}".format(sql.num_gbanned_users())


def __USER_INFO__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)
    text = "<b>Globally Banned : </b>{}"
    if user_id in [777000, 1087968824]:
        return ""
    if user_id == dispatcher.bot.id:
        return ""
    if int(user_id) in SUDO_USERS + DEV_USERS:
        text="<b>Globally Banned : </b>❓"
        return text
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += f"\n<b>Reason:</b> {html.escape(user.reason)}\n"
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "This chat is enforcing *gbans*: `{}`.".format(sql.does_chat_gban(chat_id))







GBAN_HANDLER = CommandHandler(
    "gban",
    gban,
    pass_args=True
)
UNGBAN_HANDLER = CommandHandler(
    "ungban",
    ungban,
    pass_args=True
)
GBAN_LIST = CommandHandler(
    "gbanlist",
    gbanlist
)
GBAN_STATUS = CommandHandler(
    "antispam", gbanstat, pass_args=True, filters=Filters.group
)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
