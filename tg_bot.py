from io import BytesIO

import redis
from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from moltin_api import MoltinApiClient

_database = None
_moltin = None


def start(update: Update, context: CallbackContext, moltin: MoltinApiClient):
    all_products = moltin.get_all_products()['data']
    keyboard = [
        [InlineKeyboardButton(product['attributes']['name'], callback_data=product['id'])]
        for product in all_products
    ]
    keyboard_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Добро пожаловать в Fish-shop!',
        reply_markup=keyboard_markup
    )
    return 'HANDLE_MENU'


def handle_menu(update: Update, context: CallbackContext, moltin: MoltinApiClient):
    query = update.callback_query
    context.bot.answer_callback_query(callback_query_id=query.id)
    product = moltin.get_product(product_id=query.data)['data']
    image = moltin.fetch_image(product_id=query.data)
    text = f'{product["attributes"]["name"]}\n\n{product["attributes"]["description"]}'
    keyboard = [
        [InlineKeyboardButton(f'{kg} кг', callback_data=f'buy_{product["id"]}_{kg}')
         for kg in [1, 5, 10]],
        [InlineKeyboardButton('Назад', callback_data='menu')]
    ]
    keyboard_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=BytesIO(image),
        caption=text,
        reply_markup=keyboard_markup
    )
    context.bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
    )
    return 'HANDLE_DESCRIPTION'


def handle_description(update: Update, context: CallbackContext, moltin: MoltinApiClient):
    query = update.callback_query
    if query.data == 'menu':
        return start(update, context, moltin)
    elif query.data.startswith('buy_'):
        _, product_id, quantity = query.data.split('_')

        return


def handle_users_reply(update, context):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode('utf-8')

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description
    }

    state_handler = states_functions.get(user_state, start)
    next_state = state_handler(
        update=update,
        context=context,
        moltin=get_moltin_client()
    ) or user_state
    db.set(chat_id, next_state)


def get_database_connection():
    global _database
    if not _database:
        database_password = env('REDIS_PASSWORD')
        database_host = env('REDIS_URL')
        database_port = env('REDIS_PORT')
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


def get_moltin_client():
    global _moltin
    if not _moltin:
        _moltin = MoltinApiClient(
            client_id=env('CLIENT_ID'),
            client_secret=env('CLIENT_SECRET')
        )
    return _moltin


def main():
    token = env('TG_TOKEN')
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    env = Env()
    env.read_env()
    main()
