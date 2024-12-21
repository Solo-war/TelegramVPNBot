import os
import uuid
import telebot
import datetime
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
)
from py3xui import Api, Client
from dotenv import load_dotenv

load_dotenv()

api = Api.from_env()
api.login()
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
CURRENCY = 'XTR'
Dict = {}

def keyboard_tarif():
    keyboard = InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(
        InlineKeyboardButton("Подписка на год", callback_data="subscription_year"),
        InlineKeyboardButton("Подписка на полгода", callback_data="subscription_half_year"),
        InlineKeyboardButton("Подписка на месяц", callback_data="subscription_month")
    )
    return keyboard

def get_user_connections(telegram_user_id):
    counter = 1
    connections = []
    base_email = f"{telegram_user_id}telegram.User"
    unique_email = f"{base_email}_{counter}"

    while api.client.get_by_email(unique_email) is not None:
        connections.append(unique_email)
        counter += 1
        unique_email = f"{base_email}_{counter}"

    return connections

def get_default_inbound_id():
    return 7

def generate_vless_link(inbound_id, client):
    inbound = api.inbound.get_by_id(inbound_id)
    stream_settings = inbound.stream_settings
    ip = os.environ.get("SERVER_IP", "127.0.0.1")
    port = inbound.port
    protocol = inbound.protocol
    security = stream_settings.security
    network = stream_settings.network
    pbk = stream_settings.reality_settings.get("settings", {}).get("publicKey")
    sni = stream_settings.reality_settings.get("serverNames", ["example.com"])[0]
    short_ids = stream_settings.reality_settings.get("shortIds", [""])[0]
    fp = stream_settings.reality_settings.get("settings", {}).get("fingerprint", "random")
    spx = stream_settings.reality_settings.get("short_id", "")
    inbound_name = inbound.remark
    remark = f"{client.email}"
    vless_link = (
        f"<code>vless://{client.id}@{ip}:{port}?type={network}&security={security}&pbk={pbk}&fp={fp}"
        f"&sni={sni}&sid={short_ids}&spx=%2F#{inbound_name}-{remark}</code>"
    )
    return vless_link

@bot.message_handler(commands=['start'])
def start(message):
    keyboard_tariff = keyboard_tarif()
    telegram_username = message.from_user.username
    bot.send_message(
        message.chat.id,
        f"Добро пожаловать, {telegram_username}! 🌐 Я твой персональный proxy-бот, который быстро и просто поможет тебе "
        f"обеспечить защиту данных и полный доступ к интернету. Давай подключим тебя к безопасному миру уже сейчас!"
    )
    bot.send_message(
        message.chat.id,
        "Выбери свой тариф уже сейчас и начни пользоваться быстрым и безопасным Proxy!",
        reply_markup=keyboard_tariff
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("create_subscrip"))
def create_subscrip(call):
    keyboard_tariff = keyboard_tarif()
    bot.send_message(
        call.message.chat.id,
        "Выбери свой тариф уже сейчас и начни пользоваться быстрым и безопасным Proxy!",
        reply_markup=keyboard_tariff
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("list_connections"))
def list_connections(call):
    user_id = call.from_user.id
    connections = get_user_connections(user_id)

    if not connections:
        bot.send_message(call.message.chat.id, "У вас нет активных подписок.")
        return

    keyboard = InlineKeyboardMarkup()
    for connection in connections:
        client_id = connection.split('_')[-1]
        keyboard.add(
            InlineKeyboardButton(
                text=f"Подключение {client_id}",
                callback_data=f"check_traffic_{client_id}"
            ),
        )
    keyboard.add(
        InlineKeyboardButton("Главное меню", callback_data="main_menu")
    )
    bot.send_message(call.message.chat.id, "Ваши активные подключения:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_traffic_"))
def check_traffic(call):
    inbound = api.inbound.get_by_id(7)
    for client in inbound.settings.clients:
        if client is not None:
            panel_uuid = client.id
            break

    client_info = api.client.get_traffic_by_id(panel_uuid)
    client_info_up = client_info[0]
    email = client_info_up.email
    up = client_info_up.up
    down = client_info_up.down
    up_traffic = up / (1024 * 1024)
    down_traffic = down / (1024 * 1024)
    online_users = api.client.online()
    status = "В сети" if email in online_users else "Не в сети"
    keyboard = create_keyboard(client.id)

    bot.send_message(
        call.message.chat.id,
        f"Подключение {client.id}\nВходящий трафик: {up_traffic:.2f} MB\n"
        f"Выходящий трафик: {down_traffic:.2f} MB\nСтатус: {status}",
        reply_markup=keyboard
    )

def send_welcome(message):
    try:
        telegram_user_id = message.from_user.id
        telegram_username = message.from_user.username or "unknown_user"
        email = f"{telegram_user_id}telegram.bot"
        client_id = str(uuid.uuid4())
        keyboard = create_keyboard(client_id)
        bot.send_message(
            message.chat.id,
            f"Привет, {telegram_username}!\n"
            f"Вы успешно добавлены в систему.\n\n"
            f"Ваш email: {email}\n"
            f"Ваш ID: {client_id}\n\n"
            f"Для управления своей подпиской используйте кнопки ниже:",
            reply_markup=keyboard
        )
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка при добавлении: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("support_message"))
def support_message(call):
    bot.send_message(
        call.message.chat.id,
        "Если у вас возникли какие-либо трудности или вопросы, вы всегда можете обратиться в нашу техподдержку.\n\n"
        "Напишите нам, и мы постараемся помочь вам в кратчайшие сроки - <CONTACT>"
    )

def create_keyboard(client_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(
        InlineKeyboardButton("Посмотреть трафик", callback_data=f"list_connections_{client_id}"),
        InlineKeyboardButton("Добавить соединение", callback_data="create_subscrip"),
        InlineKeyboardButton("Поддержка", callback_data="support_message")
    )
    return keyboard

@bot.callback_query_handler(func=lambda call: call.data.startswith("subscription_"))
def create_subscription(call):
    telegram_user_id = call.from_user.id
    base_email = f"{telegram_user_id}telegram.User_1"
    client_id = str(uuid.uuid4())
    inbound_id = get_default_inbound_id()

    days = {
        "subscription_year": 365,
        "subscription_half_year": 182.5,
        "subscription_month": 31
    }.get(call.data)

    if days is None:
        bot.send_message(call.message.chat.id, "Неизвестный тип подписки.")
        return

    expiry_time = int((datetime.datetime.now() + datetime.timedelta(days=days)).timestamp()) * 1000
    expiry_datetime = datetime.datetime.fromtimestamp(expiry_time / 1000)
    duration_text = expiry_datetime.strftime("%d %b %Y")

    counter = 2
    unique_email = base_email
    while api.client.get_by_email(unique_email) is not None:
        unique_email = f"{telegram_user_id}telegram.User_{counter}"
        counter += 1

    new_client = Client(
        id=client_id,
        email=unique_email,
        enable=True,
        expiry_time=expiry_time
    )
    api.client.add(inbound_id, [new_client])
    vless_link = generate_vless_link(inbound_id, new_client)
    keyboard = create_keyboard(client_id)

    bot.send_message(
        call.message.chat.id,
        f"🎉 Подписка успешно активирована!\n\n"
        f"Ваши данные:\n"
        f"Email: {unique_email}\n"
        f"ID клиента: {client_id}\n"
        f"Срок действия до: {duration_text}\n\n"
        f"Для подключения используйте следующую ссылку:\n"
        f"{vless_link}",
        reply_markup=keyboard, parse_mode='HTML'
    )

def create_keyboard_traffic(client_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(
        InlineKeyboardButton("Посмотреть трафик пользователя", callback_data=f"list_connections_{client_id}"),
        InlineKeyboardButton("Добавить соединение", callback_data="create_subscrip"),
        InlineKeyboardButton("Поддержка", callback_data="support_message")
    )
    return keyboard

@bot.callback_query_handler(func=lambda call: call.data.startswith("main_menu"))
def main_menu(call):
    bot.answer_callback_query(call.id)

    inbound = api.inbound.get_by_id(7)
    for client in inbound.settings.clients:
        if client is not None:
            client_id = client.id
            break

    keyboard = create_keyboard_traffic(client_id)
    bot.send_message(
        chat_id=call.message.chat.id,
        text="🌐 Я твой персональный proxy-бот, который быстро и просто поможет тебе обеспечить защиту данных "
             "и полный доступ к интернету. Давай подключим тебя к безопасному миру уже сейчас!",
        reply_markup=keyboard
    )

if __name__ == "__main__":
    print("Бот запущен!")
    bot.polling()
