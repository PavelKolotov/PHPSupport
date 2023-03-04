import telebot

from environs import Env
from telebot.util import quick_markup

env = Env()
env.read_env()
tg_bot_token = env('TG_CLIENTS_TOKEN')
bot = telebot.TeleBot(token=tg_bot_token)


# user groups
UG_ADMIN = 0      # Admimnistrators
UG_CLIENT = 1     # clients
UG_EXECUTOR = 2   # executors

# help strings for different user groups
help_messages = {
    UG_ADMIN: 'Подсказки для Админа',
    UG_CLIENT: 'Подсказки для клиента',
    UG_EXECUTOR: 'Подсказки для исполнителя',
}

# others
INPUT_DUE_TIME = 60     # time (sec) to wait for user text input
BUTTONS_DUE_TIME = 30   # time (sec) to wait for user clicks button
ACCESS_DUE_TIME = 300   # if more time has passed since last show_main_menu() we should check access again

# user access status
USER_NOT_FOUND = -1     # user not found in DB
ACCESS_DENIED = 0       # user is found but access is forbidden
ACCESS_ALLOWED = 1      # user is found and access is allowed

# main menu callback buttons
markup_client = quick_markup({
    'Активные заявки': {'callback_data': 'apps_to_client'},
    'Выполненные заявки': {'callback_data': 'apps_to_client_done'},
    'Подать заявку': {'callback_data': 'apply'},
})

markup_executor = quick_markup({
    'Заявки от заказчиков': {'callback_data': 'apps_to_exec'},
    'Заявки в работе': {'callback_data': 'apps_in_work'},
    'Завершенные заказы': {'callback_data': 'apps_to_exec_done'},
    'Условия оплаты': {'callback_data': 'salary'},
})

markup_admin = quick_markup({
    'Регистрация': {'callback_data': 'add_user'},
    'Управление доступом': {'callback_data': 'access_control'},
    'Статистика заявок': {'callback_data': 'apps_stat'},
    'Статистика оплат': {'callback_data': 'salary_stat'}
})

markup_cancel_step = quick_markup({
    'Отмена': {'callback_data': 'cancel_step'},
  })

markup_group_uuser = quick_markup({
    'Заказчик': {'callback_data': 'add_client'},
    'Исполнитель': {'callback_data': 'add_executor'},
})

markup_group_users = quick_markup({
    'Заказчики': {'callback_data': 'get_clients'},
    'Исполнители': {'callback_data': 'get_executors'},
  })

# cancel button to exit current input step for all user groups
# if clicked, main menu for the appropriate user group is shown
# and current input step is canceled

# cache for temporary saving context-specific info
# for each user, communicating with the bot.
# Each chat in the dict (and it means particular user in fact) is accessed by chat_id
# see start_bot() in bot_functions.py for understanding content of chats{}
chats = {}