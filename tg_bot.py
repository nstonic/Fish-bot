import logging
from io import BytesIO

from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from helpers import parse_cart
from logger import TGLoggerHandler
from moltin_api import MoltinApiClient
from redis_client import RedisClient

tg_logger = logging.getLogger('TG_logger')


def show_cart(update: Update, context: CallbackContext):
    moltin = MoltinApiClient()
    db = RedisClient()
    query = update.callback_query
    customer_id = db.client.get(f'customer_{query.from_user.id}')
    cart = None
    keyboard = [
        [InlineKeyboardButton('Оплатить', callback_data='make_order')],
        [InlineKeyboardButton('В меню', callback_data='menu')]
    ]
    if customer_id:
        customer = moltin.get_customer(customer_id=customer_id.decode('utf-8'))
        cart = moltin.get_current_cart(customer['data']['email'])
        for product in cart['data']:
            button = InlineKeyboardButton(
                f'Убрать из корзины {product["name"]}',
                callback_data=f'del_{product["id"]}'
            )
            keyboard.insert(0, [button])

    context.bot.answer_callback_query(
        callback_query_id=query.id
    )
    keyboard_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=parse_cart(cart),
        parse_mode='HTML',
        reply_markup=keyboard_markup
    )
    context.bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
    )
    return 'HANDLE_CART'


def show_product(update: Update, context: CallbackContext):
    moltin = MoltinApiClient()
    query = update.callback_query
    product = moltin.get_product_with_price(product_id=query.data)['data']
    image = moltin.fetch_image(product_id=query.data)
    text = f'{product["attributes"]["name"]} - {product["price"]}₽\n\n{product["attributes"]["description"]}'

    context.bot.answer_callback_query(
        callback_query_id=query.id
    )

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


def add_product_to_cart(update: Update, context: CallbackContext):
    moltin = MoltinApiClient()
    db = RedisClient()
    query = update.callback_query
    user_id = query.from_user.id
    customer_id = db.client.get(f'customer_{user_id}')
    if not customer_id:
        context.bot.send_message(
            chat_id=user_id,
            text='Похоже вы еще ничего не покупали в Fish-shop. Для создания первого заказа пришлите ваш email.'
        )
        return 'HANDLE_EMAIL'
    else:
        customer = moltin.get_customer(customer_id=customer_id.decode('utf-8'))

    _, product_id, quantity = query.data.split('_')
    moltin.add_product_to_cart(
        product_id=product_id,
        quantity=int(quantity),
        customer_email=customer['data']['email']
    )
    context.bot.answer_callback_query(
        callback_query_id=query.id,
        text='Добавлено в корзину'
    )
    context.bot.delete_message(
        chat_id=user_id,
        message_id=query.message.message_id,
    )
    return show_cart(update, context)


def delete_product_from_cart(update: Update, context: CallbackContext):
    moltin = MoltinApiClient()
    db = RedisClient()
    query = update.callback_query
    _, product_id = query.data.split('_')
    customer_id = db.client.get(f'customer_{query.from_user.id}')
    customer = moltin.get_customer(customer_id=customer_id.decode('utf-8'))
    cart_id = moltin.get_current_cart_id(customer['data']['email'])
    moltin.delete_product_from_cart(
        cart_id=cart_id,
        product_id=product_id
    )
    return show_cart(update, context)


def make_order(update: Update, context: CallbackContext):
    return start(update, context)


def start(update: Update, context: CallbackContext):
    moltin = MoltinApiClient()
    all_products = moltin.get_all_products()['data']
    if update.callback_query:
        context.bot.answer_callback_query(
            callback_query_id=update.callback_query.id
        )
        message_id = update.callback_query.message.message_id
    elif update.message:
        message_id = update.message.message_id
    else:
        return

    keyboard = [
        [InlineKeyboardButton(product['attributes']['name'], callback_data=product['id'])]
        for product in all_products
    ]
    keyboard.append(
        [InlineKeyboardButton('Корзина', callback_data='cart')]
    )
    keyboard_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Добро пожаловать в Fish-shop!',
        reply_markup=keyboard_markup
    )
    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=message_id
    )
    return 'HANDLE_MENU'


def handle_menu(update: Update, context: CallbackContext):
    if update.callback_query.data == 'cart':
        return show_cart(update, context)
    else:
        return show_product(update, context)


def handle_cart(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'menu':
        return start(update, context)
    elif query.data == 'make_order':
        return make_order(update, context)
    elif query.data.startswith('del_'):
        return delete_product_from_cart(update, context)


def handle_description(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'menu':
        return start(update, context)
    elif query.data.startswith('buy_'):
        return add_product_to_cart(update, context)


def waiting_email(update: Update, context: CallbackContext):
    moltin = MoltinApiClient()
    db = RedisClient()
    if not update.message:
        return
    user_email = update.message.text.strip()
    customer = moltin.create_customer(user_email)
    user_id = update.message.from_user.id
    db.client.set(f'customer_{user_id}', customer['data']['id'])
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'Ваша почта {user_email} сохранена\nГотово! Теперь можете сделать первый заказ'
    )
    return 'HANDLE_DESCRIPTION'


def handle_users_reply(update: Update, context: CallbackContext):
    db = RedisClient()

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
        user_state = db.client.get(chat_id).decode('utf-8')
    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'WAITING_EMAIL': waiting_email,
        'HANDLE_CART': handle_cart
    }

    state_handler = states_functions.get(user_state, start)
    next_state = state_handler(
        update=update,
        context=context
    ) or user_state
    db.client.set(chat_id, next_state)


def error_handler(update: Update, context: CallbackContext):
    if 'Message to delete not found' not in context.error:
        tg_logger.error(msg="Исключение при обработке сообщения в боте DVMNFishBot:", exc_info=context.error)


def main():
    env = Env()
    env.read_env()
    token = env('TG_TOKEN')
    RedisClient(
        password=env('REDIS_PASSWORD'),
        host=env('REDIS_URL'),
        port=env('REDIS_PORT')
    )
    MoltinApiClient(
        client_id=env('CLIENT_ID'),
        client_secret=env('CLIENT_SECRET'),
        price_book_id=env('PRICE_BOOK_ID')
    )

    tg_logger.setLevel(logging.WARNING)
    tg_logger.addHandler(TGLoggerHandler(
        tg_token=env('TG_ADMIN_TOKEN'),
        chat_id=env('TG_ADMIN_ID'),
    ))

    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    dispatcher.add_error_handler(error_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
