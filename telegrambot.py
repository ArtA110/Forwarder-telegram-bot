import logging
import requests
from collections import OrderedDict
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
TOKEN: Final = '6777553545:AAFmGKGc1mqUORYJh9s4fRRaB4tXd7jJj8c'
# Connect to database
client = MongoClient('localhost', 27017)
db = client['TelegramBot']
users_collection = db['users']
logged_in_collection = db['logged_in']
files_collection = db['files']


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = '\n\nبه بات تلگرامی شیخیه باقری خوش آمدید، برای ادامه لطفا یکی از آپشن های زیر را انتخاب کنید.\n\n'
    options = ['/login برای ورود به اکانت', '/ticket برای درخواست پشتیبانی']
    text += '\n'.join(options)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

USERNAME, PASSWORD = range(2)
REGISTER = 0
STATE0, STATE1, STATE2 = range(3)

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_chat.id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text='ابتدا باید /login کنید')
        return ConversationHandler.END

    all_topics = {'اصول فقه': 'osool', 'تذکره': 'tazkare', 'دره نجفیه': 'dorre', 'رجوم الشیاطین': 'rojoom',
                  'رساله غیبت': 'gheibat', 'سلطانیه': 'soltanieh', 'شرایط دعا': 'doa', 'قرآن محشی': 'mohassha',
                  'متفرقه': 'others', 'معادیه': "ma'adieh", 'معرفت سر اختیار': 'marefat', 'منطق': 'mantegh',
                  'مواعظ 1292': 'mavaez', 'میزان': 'mizan'}

    response = create_menu(name_dict=all_topics)
    reply_markup = InlineKeyboardMarkup(response)
    context.user_data['query_item'] = []
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Test', reply_markup=reply_markup)
    return STATE0


async def button1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    context.user_data['query_item'].append(query.data)
    search_result = sort_result(list(files_collection.find({"file_name": {"$regex": f"^{query.data}"}})))
    sub_menu = {}
    if len(search_result[1]['file_name'].split('-')) > 2:
        all_topics = {'سوره بقره': 'baghareh', 'سوره حمد': 'hamd', 'سوره اخلاص': 'ekhlas', 'جزء سی': 'jozv30',
                  'فخر رازی': 'FakhrRazi', 'تفتازانی': 'Taftazani', 'مقدمه': 'moghadame', 'جلد اول': '1',
                  'جلد دوم': '2', 'سال 1992': '92'}
        reverse_all_topic = {value: key for key, value in all_topics.items()}
        for result in search_result:
            if result['file_name'].split('-')[1].replace('.mp3', '') in all_topics.values():
                sub_menu[reverse_all_topic[result['file_name'].split('-')[1].replace('.mp3', '')]] = result['file_name'].split('-')[1].replace('.mp3', '')
    else:
        for result in search_result:
            sub_menu[result['title']] = result['file_name']
    reply_markup = InlineKeyboardMarkup(create_menu(name_dict=sub_menu))
    await query.edit_message_text(text=f'you choose: {query.data}', reply_markup=reply_markup)
    return STATE1


async def button2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # {"$regex": f"^{'-'.join(context.user_data['query_item'])}"}
    context.user_data['query_item'].append(query.data)
    if '.mp3' in query.data:
        search_result = sort_result(list(files_collection.find({"file_name": {"$regex": f"^{query.data}"}})))
    else:
        search_result = sort_result(
            list(files_collection.find({"file_name": {"$regex": f"^{'-'.join(context.user_data['query_item'])}"}})))
    if len(search_result) == 1:
        await update.effective_chat.forward_from(from_chat_id=CHANNEL_ID, message_id=search_result[0]['message_id'])
        await query.edit_message_text(text='File Sent Successfully')
        return ConversationHandler.END
    sub_menu = {}
    for result in search_result:
        sub_menu[result['title']] = result['file_name']
    reply_markup = InlineKeyboardMarkup(create_menu(name_dict=sub_menu))
    await query.edit_message_text(text=f'you choose: {query.data}', reply_markup=reply_markup)
    return STATE2



async def button3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    context.user_data['query_item'].append(query.data)
    search_result = sort_result(
        list(files_collection.find({"file_name": {"$regex": f"^{query.data}"}})))
    await update.effective_chat.forward_from(from_chat_id=CHANNEL_ID, message_id=search_result[0]['message_id'])
    await query.edit_message_text(text='File Sent Successfully')
    return ConversationHandler.END

def sort_result(result):
    try:
        return sorted(result, key=lambda x: int(x['file_name'].split('-')[-1].replace('.mp3', '')))
    except ValueError:
        return sorted(result, key=lambda x: x['file_name'].split('-')[-1].replace('.mp3', ''))


def create_menu(count: int=None, name_dict: dict=None):
    response = []
    i = 0
    if name_dict is not None:
        for key, value in name_dict.items():
            if i % 2 == 0:
                response.append([InlineKeyboardButton(key, callback_data=value)])
            else:
                response[i // 2].append(InlineKeyboardButton(key, callback_data=value))
            i+=1
    elif count is not None:
        for i in range(count):
            if i % 2 == 0:
                response.append([InlineKeyboardButton(str(i+1), callback_data=i)])
            else:
                response[i//2].append(InlineKeyboardButton(str(i+1), callback_data=i))
    return response


def is_authorized(chat_id: int) -> bool:
    if logged_in_collection.find_one({'chat_id': chat_id}):
        return True
    return False


async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_authorized(update.effective_chat.id):
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
    if is_authorized(update.effective_chat.id):
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

    audio = ConversationHandler(
        entry_points=[CommandHandler('test', test)],
        states={STATE0: [CallbackQueryHandler(button1)],
                STATE1: [CallbackQueryHandler(button2)],
                STATE2: [CallbackQueryHandler(button3)]},
        fallbacks=[CommandHandler('cancel', login_cancel_handler)]
    )
    application.add_handler(login)
    application.add_handler(register)
    application.add_handler(ticket)
    application.add_handler(audio)
    application.add_handler(CommandHandler('logout', logout_handler))
    application.add_handler(CommandHandler('forward', forward_handler))
    application.run_polling()
