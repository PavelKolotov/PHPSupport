import telebot
import time


from telebot import types
from environs import Env
from aiogram.utils.markdown import hlink


env = Env()
env.read_env()

tg_clients_token = env('TG_CLIENTS_TOKEN')
client_bot = telebot.TeleBot(token=tg_clients_token)

client_base = [933137433, ]
contractor_base = [9331374330, 205520898]

client_application = []
link = hlink('ПИПИ', 'https://pypi.org/project/pyTelegramBotAPI/#description')

applications = [{'key': 123, 'text': 'Test1', 'appl': link}, {'key': 1234, 'text': 'Test2', 'appl': link}]


def get_time_conv():
    return lambda x: time.strftime("%H:%M:%S %d.%m.%Y", time.localtime(x))


@client_bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Авторизация')
    markup.add(btn1)
    client_bot.send_message(message.chat.id, 'Я на связи. Нажми на кнопку Авторизация ...', reply_markup=markup)


@client_bot.message_handler(func=lambda message: message.chat.id not in client_base and message.chat.id not in contractor_base)
def get_payment_verification(message):
    client_bot.send_message(message.chat.id, 'У вас нет доступа к боту')
    print(message.chat.id)


@client_bot.message_handler(func=lambda message: message.chat.id in client_base)
def get_client_application(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Сделать заявку')
    btn2 = types.KeyboardButton('Мои заявки')
    markup.add(btn1, btn2)
    order_id = 1000

    if message.text == 'Авторизация':
        client_bot.send_message(message.chat.id, 'Для начала работы нажмите на кнопку Сделать заявку', reply_markup=markup)

        us_id = message.chat.id
        us_name = message.from_user.first_name
        us_sname = message.from_user.last_name
        username = message.from_user.username
        print(us_id)
        print(us_name)
        print(us_sname)
        print(username)

    elif message.text == 'Сделать заявку':
        client_bot.send_message(message.chat.id, '''Я на связи. Для решения вашего вопроса, опишите его.
        Примеры:
        * Здравствуйте, нужно добавить в интернет-магазин фильтр товаров по цвету
        * Здравствуйте, нужно выгрузить товары с сайта в Excel-таблице
        * Здравствуйте, нужно загрузить 450 SKU на сайт из Execel таблицы
        * Здравствуйте, хочу провести на сайте акцию, хочу разместить баннер и добавить функционал, чтобы впридачу к акционным товарам выдавался приз
        ''')

    elif message.text == 'Мои заявки':
        client_bot.send_message(message.chat.id, 'Ваши заявки:')

    else:
        client_application.append(message.text)

        application_date = get_time_conv()(message.date)
        order_id += 1
        client_bot.send_message(message.chat.id, f'Заявка #{order_id} передана в работу {application_date}, в течении дня с вами свяжется подрядчик')

        print(client_application)
        print(application_date)


@client_bot.message_handler(func=lambda message: message.chat.id in contractor_base)
def get_client_application(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Cписок заказов")
    btn2 = types.KeyboardButton("Что я делаю")
    btn3 = types.KeyboardButton("Условия оплаты")
    btn4 = types.KeyboardButton("Выполнено заказов")
    markup.add(btn1, btn2, btn3, btn4)

    if message.text == 'Авторизация':
        client_bot.send_message(message.chat.id, 'Для начала работы нажмите на кнопку Спиcок заказов', reply_markup=markup)

        us_id = message.chat.id
        us_name = message.from_user.first_name
        us_sname = message.from_user.last_name
        username = message.from_user.username
        print(us_id)
        print(us_name)
        print(us_sname)
        print(username)

    if message.text == 'Cписок заказов':
        client_bot.send_message(message.chat.id, 'Список заказов: ')
        for application in applications:
            client_bot.send_message(message.chat.id, application['text'], parse_mode='HTML')


client_bot.polling(none_stop=True, interval=0)
