import telebot
import time
import random
import db


from telebot.util import quick_markup
from environs import Env


CLIENT_GREET = "Привет тебе, дорогой клиент!"
EXEC_GREET = "Привет тебе, дорогой исполнитель!"
ADMIN_GREET = "Привет тебе, о великий Админ!"

env = Env()
env.read_env()

tg_clients_token = env('TG_CLIENTS_TOKEN')
client_bot = telebot.TeleBot(token=tg_clients_token)

markup_client = quick_markup({
    'Мои заявки': {'callback_data': 'apps_to_client'},
    'Подать заявку': {'callback_data': 'apply'}
})
markup_executor = quick_markup({
    'Список заказов': {'callback_data': 'apps_to_exec'},
    'Условия оплаты': {'callback_data': 'salary'},
    'Что я делаю': {'callback_data': 'active_task'},
    'Задать вопрос': {'callback_data': 'ask_question'},
    'Сдать работу': {'callback_data': 'work_done'}
})

markup_accept_order = quick_markup({
    'Принять заявку': {'callback_data': 'accept_order'},
  })

orders = []
accepted_orders = []


def get_time_conv():
    return lambda x: time.strftime("%H:%M:%S %d.%m.%Y", time.localtime(x))


@client_bot.message_handler(commands=['start'])
def start(message: telebot.types.Message):
    print(message.text)
    access, type = db.check_access_by_id(message.chat.id)
    if access == -1:
        client_bot.send_message(message.chat.id, 'Вы не зарегистрированы в системе.')
    elif access == 0 and type == db.UT_CLIENT:
        client_bot.send_message(message.chat.id, 'Ваша подписка окончилась, новые заявки создать нельзя.'
                                                 'Однако можно отслеживать ранее поданные заявки')
    elif access == 1:
        if type == 0:
            client_bot.send_message(message.chat.id, ADMIN_GREET)
            client_bot.send_message(message.chat.id, "Меню админа в разработке")
        elif type == 1:
            client_bot.send_message(message.chat.id, CLIENT_GREET)
            client_bot.send_message(message.chat.id, "Основное меню:", reply_markup=markup_client)
        elif type == 2:
            client_bot.send_message(message.chat.id, EXEC_GREET)
            client_bot.send_message(message.chat.id, "Основное меню", reply_markup=markup_executor)


@client_bot.message_handler(func=lambda message: True)

def get_client_order(message):
    client_bot.send_message(message.chat.id, '''
            Примеры:
            * Здравствуйте, нужно добавить в интернет-магазин фильтр товаров по цвету
            * Здравствуйте, нужно выгрузить товары с сайта в Excel-таблице
            * Здравствуйте, нужно загрузить 450 SKU на сайт из Execel таблицы
            * Здравствуйте, хочу провести на сайте акцию, хочу разместить баннер и добавить функционал, чтобы впридачу к акционным товарам выдавался приз
            ''')
    client_bot.register_next_step_handler(message, get_order)

def get_executor_order(message):
    client_bot.register_next_step_handler(message, get_accept_order)

def get_accept_order(message):
    global accepted_orders, orders
    for order in orders:
        if str(order['order_id']) == message.text:
            orders[orders.index(order)]['step'] = 1
            orders[orders.index(order)]['executor_id'] = message.chat.id
            accepted_orders.append(orders[orders.index(order)])
            client_bot.send_message(message.chat.id, f'Заявка #{message.text} принята')
            client_bot.send_message(order['chat_id'], f'Ваша заявка #{message.text} принята к исполнению')


def get_order(message):
    global orders
    chat_id = message.chat.id
    us_name = message.from_user.first_name
    us_sname = message.from_user.last_name
    username = message.from_user.username
    order_time = get_time_conv()(message.date)
    type_id = 1
    order_id = random.randint(10000, 99999)
    text_order = message.text
    step = 0
    chats = {
        'chat_id': chat_id,
        'us_name': us_name,
        'us_sname': us_sname,
        'username': username,
        'type_id': type_id,
        'order_id': order_id,
        'time': order_time,
        'text': text_order,
        'step': step
    }
    orders.append(chats)
    print(orders)
    client_bot.send_message(message.chat.id, f'Заявка #{order_id} передана в работу, в течении дня с вами свяжется подрядчик', reply_markup=markup_client)

# сделать обработчик текстовый сообщений (ввод инфы от пользователя) c ветвлением на основании алгоритма,
# либо сделать как показано здесь: https://habr.com/ru/post/442800/ - см. раздел ветки сообщений.

@client_bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == 'apps_to_client':
        client_bot.send_message(call.message.chat.id, 'Список заказов: ')
        for order in orders:
            if order['chat_id'] == call.message.chat.id:
                client_bot.send_message(call.message.chat.id, f'Заявка #{order["order_id"]} передана в работу {order["time"]}, {order["text"]}')
        client_bot.send_message(call.message.chat.id, 'Основное меню: ', reply_markup=markup_client)
    elif call.data == 'apply':
        client_bot.send_message(call.message.chat.id, 'Я на связи. Для решения вашего вопроса, опишите его.')
        get_client_order(call.message)
    elif call.data == 'apps_to_exec':
        client_bot.send_message(call.message.chat.id, 'Список заказов: ')
        for order in orders:
            if order['step'] == 0:
                client_bot.send_message(call.message.chat.id, f'Заявка #{order["order_id"]}, {order["time"]}, {order["text"]}')
        client_bot.send_message(call.message.chat.id, 'Нажмите Принять заявку', reply_markup=markup_accept_order)
    elif call.data == 'accept_order':
        client_bot.send_message(call.message.chat.id, 'Введите номер заказа, который хотите принять')
        for accepted_order in accepted_orders:
            if accepted_order['executor_id'] == call.message.chat.id and accepted_order['step'] == 1:
                client_bot.send_message(call.message.chat.id, 'У вас уже взят заказ', reply_markup=markup_executor)
        get_executor_order(call.message)
    # elif call.data ==




    # здесь ведем обработку нажатий кнопок.
    # имеем ввиду что при ответе на кнопки некоторые сообщения
    # оснащаются другими кнопками которые также обрабатываются здесь,
    # либо для них надо сделать индивидуальные обработчики .... решить.


client_bot.polling(none_stop=True, interval=0)
