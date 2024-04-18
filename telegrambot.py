import logging
import requests
from typing import Final
from hashlib import sha256
from pymongo import MongoClient
from telegram import (InlineQueryResultArticle, InlineQueryResultPhoto, InputTextMessageContent, Update,
                      InlineKeyboardMarkup, InlineKeyboardButton)
from telegram.ext import (ApplicationBuilder, ContextTypes, InlineQueryHandler, CommandHandler, filters, MessageHandler,
                          ConversationHandler, CallbackQueryHandler)
from uuid import uuid4

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


CHANNEL_ID: Final = -1001760329506
TOKEN: Final = '6777553545:AAE_b9T8vcPbpGkm1pHKzsHqhfkrzfKTtAU'
# Connect to database
client = MongoClient('localhost', 27017)
db = client['TelegramBot']
users_collection = db['users']
logged_in_collection = db['logged_in']


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = '\n\nبه بات تلگرامی شیخیه باقری خوش آمدید، برای ادامه لطفا یکی از آپشن های زیر را انتخاب کنید.\n\n'
    options = ['/login برای ورود به اکانت', '/ticket برای درخواست پشتیبانی']
    text += '\n'.join(options)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Option 1", callback_data="1")],
        [
            InlineKeyboardButton("Option 2", callback_data="2"),
            InlineKeyboardButton("Option 3", callback_data="3")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Hey', reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.edit_message_text(text=f'you choose: {query.data}')

USERNAME, PASSWORD = range(2)
REGISTER = 0


def is_authorized(chat_id):
    if logged_in_collection.find_one({'chat_id': chat_id}):
        return True
    return False
async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_authorized(update.effective_user.id):
        text = 'شما قبلا وارد شدید و میتوانید از امکانات استفاده کنید.'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                       reply_to_message_id=update.effective_message.message_id)
        return ConversationHandler.END
    text = 'لظفا نام کاربری خودرا وارد کنید، اگر نام کاربری ندارید با پشتیبانی ارتباط بگیرید.'
    text += '\n\n'
    text += 'ضمنا در هر مرحله برای لغو عملیات ورود دستور /cancel را وارد کنید.'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                   reply_to_message_id=update.effective_message.message_id)
    return USERNAME


async def login_password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    user = users_collection.find_one({'username': username})
    if user:
        context.user_data['username'] = username
        text = 'لطفا کلمه عبور خود را وارد کنید.'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                       reply_to_message_id=update.effective_message.message_id)
        return PASSWORD
    text = 'کاربر با این مشخصات یافت نشد، مجددا با /login وارد شوید.'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                       reply_to_message_id=update.effective_message.message_id)
    return ConversationHandler.END


async def login_check_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    password = sha256(password.encode('utf-8')).hexdigest()
    user = users_collection.find_one({'username': context.user_data['username'], "password": password})
    if user:
        text = 'شما با موفقیت وارد شدید'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                       reply_to_message_id=update.effective_message.message_id)
        logged_in_collection.insert_one({'chat_id': update.effective_chat.id})
        return ConversationHandler.END
    text = 'رمز عبور اشتباه است مجددا با دستور /login وارد شوید'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                   reply_to_message_id=update.effective_message.message_id)
    return ConversationHandler.END


async def login_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = 'عملیات ورود لغو شد!'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                   reply_to_message_id=update.effective_message.message_id)
    return ConversationHandler.END


async def logout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_authorized(update.effective_user.id):
        logged_in_collection.delete_one({'chat_id': update.effective_chat.id})
        await context.bot.send_message(chat_id=update.effective_chat.id, text='خارج شدید',
                                       reply_to_message_id=update.effective_message.id)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text='شما اصلا وارد نشده اید!',
                                       reply_to_message_id=update.effective_message.id)

async def register_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = context.args[0]
    if code == '48022125':  # should save to file or environment variable
        text = '\n\nلطفا با فرم زیر نام کاربری و رمز عبور خودرا وارد کنید\n\n'
        text += 'username_example:password_example\n\n'
        text += '\n\nمثلا اگر نام کاربری ali و رمز عبور 123 میباشد باید مانند زیر عمل کنید\n\n'
        text += 'ali:123'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        return REGISTER
    await context.bot.send_message(chat_id=update.effective_chat.id, text='شما مجاز به ثبت نام نیستید')


async def register_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(update.message.text.split(':')) != 2:
            raise Exception('Error - Check your input format')
        username, password = update.message.text.split(':')
        password = sha256(password.encode('utf-8')).hexdigest()
        if users_collection.find_one({'username': username}):
            raise Exception('User already exists')
        users_collection.insert_one({'username': username, 'password': password})
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    return ConversationHandler.END


TICKET = 0
async def ticket_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text='لطفا مشکل خودرا در یک پیام با جزئبات توضیح دهید')
    return TICKET


async def ticket_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    chat_id = update.effective_chat.id
    username = update.effective_chat.username
    text = f'{chat_id=}, {username=}, \n{message=}'
    await context.bot.send_message(chat_id=110908059, text=text)
    await context.bot.send_message(chat_id=chat_id, text='پیام شما برای پشتیبان ارسال شد!')
    return ConversationHandler.END


async def forward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_chat.forward_from(from_chat_id=-1001760329506, message_id=5)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))

    login = ConversationHandler(
        entry_points=[CommandHandler('login', login_handler)],
        states={USERNAME: [MessageHandler(filters.TEXT & ~ filters.COMMAND, login_password_handler)],
                PASSWORD: [MessageHandler(filters.TEXT & ~ filters.COMMAND, login_check_user_handler)]},
        fallbacks=[CommandHandler('cancel', login_cancel_handler)]
    )

    register = ConversationHandler(
        entry_points=[CommandHandler('register', register_handler)],
        states={REGISTER: [MessageHandler(filters.TEXT & ~ filters.COMMAND, register_info_handler)]},
        fallbacks=[CommandHandler('cancel', login_cancel_handler)]
    )

    ticket = ConversationHandler(
        entry_points=[CommandHandler('ticket', ticket_handler)],
        states={TICKET: [MessageHandler(filters.TEXT & ~ filters.COMMAND, ticket_info_handler)]},
        fallbacks=[CommandHandler('cancel', login_cancel_handler)]
    )
    application.add_handler(login)
    application.add_handler(register)
    application.add_handler(ticket)
    application.add_handler(CommandHandler('logout', logout_handler))
    application.add_handler(CommandHandler('forward', forward_handler))
    application.add_handler(CommandHandler('test', test))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()
