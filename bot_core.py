import datetime as dt


import bot_functions as calls
from globals import *

# general callback functions mapping to callback buttons
# all of these buttons are from main user menus
calls_map = {
    'apps_to_client': calls.apps_to_client,
    'apps_to_client_done': calls.apps_to_client_done,
    'apply': calls.apply,
    'apps_to_exec': calls.apps_to_exec,
    'apps_to_exec_done': calls.apps_to_exec_done,
    'salary': calls.salary,
    'apps_in_work': calls.apps_in_work,
    'add_user': calls.add_user,
    'access_control': calls.access_control,
    'apps_stat': calls.apps_stat,
    'salary_stat': calls.get_salary_stat,
}

# callback functions mapping to callback buttons
# for handling particular entity by ID
# all of these buttons are attached to particular messages
calls_id_map = {
    'take_order_id': calls.take_order_id,
    'ask_question_id': calls.ask_question_id,
    'edit_question_id': calls.edit_question_id,
    'work_done_id': calls.work_done_id,
    'see_client_answer_id': calls.see_client_answer_id,
    'accept_answer_id': calls.accept_answer_id,
    'reject_answer_id': calls.reject_answer_id,
    'answer_id': calls.answer_id,
    'edit_answer_id': calls.edit_answer_id,
    'client_see_questions_id': calls.client_see_questions_id,
    'exec_see_questions_id': calls.exec_see_questions_id,
    'accept_work_id': calls.accept_work_id,
    'reject_work_id': calls.reject_work_id,
    'send_comments_id': calls.send_comments_id,
    'allow_access_id': calls.allow_access_id,
    'deny_access_id': calls.deny_access_id,
}

# callback buttons display names to mention them in handling functions
# todo - доработать или избавиться от этого
buttons_names = {
    'apps_to_client': 'Мои заявки',
    'apply': 'Подать заявку',
    'apps_to_exec': 'Список заявок',
    'salary': 'Оплата',
    'ask_question_id': 'Задать вопрос',
    'active_task': 'Заявка в работе',
    'work_done_id': 'Сдать работу',
}


@bot.message_handler(commands=['start'])
def command_start(message: telebot.types.Message):
    calls.start_bot(message)


@bot.message_handler(commands=['menu'])
def command_menu(message: telebot.types.Message):
    user = calls.check_user_in_cache(message)
    if not user:
        return
    else:
        calls.show_main_menu(message.chat.id, user['group'])


@bot.message_handler()
def get_text(message):
    if calls.check_user_in_cache(message):
        bot.send_message(message.chat.id, 'Для работы с ботом пользуйтесь кнопками')



@bot.callback_query_handler(func=lambda call: call.data)
def handle_buttons(call):
    user = calls.check_user_in_cache(call.message)
    if not user:
        return
    source = user['callback_source']
    if source and not call.message.id in user['callback_source']:
        bot.send_message(call.message.chat.id, 'Кнопка не актуальна\n'
                                               '/menu - показать основное меню')
        return
    elif (dt.datetime.now()-dt.timedelta(0, 180)) > dt.datetime.fromtimestamp(call.message.date):
        bot.send_message(call.message.chat.id, 'Срок действия кнопки истек')
        calls.show_main_menu(call.message.chat.id, chats[call.message.chat.id]['group'])
        return
    btn_command: str = call.data
    current_command = user['callback']
    if btn_command == 'cancel_step':
        if current_command:
            calls.cancel_step(call.message)
        return
    if user['callback']:
        bot.send_message(call.message.chat.id,
                         f'Вы находитесь в режиме '
                         f'ввода данных другой команды: "{buttons_names[current_command]}".\n'
                         f'Сначала завершите ее или отмените')
        return
    if 'id' in btn_command:
        parts = btn_command.split(':')
        key_func = parts[-1]
        func_name = parts[0]
        calls_id_map[func_name](call.message, key_func)
        return
    else:
        calls_map[call.data](call.message)


bot.polling(none_stop=True, interval=0)