from io import BytesIO
from pprint import pprint

from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from moltin_api import MoltinApiClient
from redis_client import RedisClient


def start(update: Update, context: CallbackContext):
    moltin = MoltinApiClient()
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


def handle_menu(update: Update, context: CallbackContext):
    moltin = MoltinApiClient()
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


def handle_description(update: Update, context: CallbackContext):
    moltin = MoltinApiClient()
    db = RedisClient()
    query = update.callback_query
    if query.data == 'menu':
        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
        return start(update, context)
    elif query.data.startswith('buy_'):
        _, product_id, quantity = query.data.split('_')
        user_id = query.from_user.id
        customer_id = db.client.get(f'customer_{user_id}').decode('utf-8')
        if not customer_id:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Похоже вы еще ничего не покупали в Fish-shop. Для создания первого заказа пришлите ваш email.'
            )
            return 'HANDLE_EMAIL'
        else:
            customer = moltin.get_customer(customer_id=customer_id)
        cart_id = moltin.add_product_to_cart(
            product_id=product_id,
            quantity=int(quantity),
            customer_email=customer['data']['email']
        )
        pprint(moltin.get_cart_items(cart_id))
        return


def handle_email(update: Update, context: CallbackContext):
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
        text='Готово! Теперь можете сделать первый заказ'
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
        'HANDLE_EMAIL': handle_email
    }

    state_handler = states_functions.get(user_state, start)
    next_state = state_handler(
        update=update,
        context=context
    ) or user_state
    db.client.set(chat_id, next_state)


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
        client_secret=env('CLIENT_SECRET')
    )
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
