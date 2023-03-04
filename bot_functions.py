import datetime as dt
import telebot

from telebot.util import quick_markup
from datetime import timedelta

import db
from globals import (
    bot, USER_NOT_FOUND, ACCESS_DENIED, UG_CLIENT, ACCESS_DUE_TIME, ACCESS_ALLOWED,
    chats, help_messages, markup_client, markup_admin, markup_executor,
    markup_cancel_step, UG_EXECUTOR, UG_ADMIN, INPUT_DUE_TIME
)


# COMMON FUNCTIONS

def cache_user(chat_id):
    user = db.get_user_by_chat_id(chat_id)
    access_due = dt.datetime.now() + dt.timedelta(0, ACCESS_DUE_TIME)
    chats[chat_id] = {
        'name': None,
        'callback': None,               # current callback button
        'last_msg': [],                 # последние отправленные за один раз сообщения,в которых нужно удалить кнопки
        'callback_source': [],          # если задан, колбэк кнопки будут обрабатываться только с этих сообщений
        'group': user['user_group'],    # группа, к которой принадлежит пользователь
        'access_due': access_due,       # дата и время актуальности кэшированного статуса
        'access': user['access'],       # код доступа
        'text': None,                   # для разных целей - перспектива
        'number': None,                 # для разных целей - перспектива
        'step_due': None,               # срок  ожидания ввода данных (используем в callback функциях)
    }
    return chats[chat_id]


def start_bot(message: telebot.types.Message):
    user_name = message.from_user.username
    bot.send_message(message.chat.id, f'Здравствуйте, {message.from_user.username}.')
    access_due = dt.datetime.now() + dt.timedelta(0, ACCESS_DUE_TIME)
    access, group = db.check_user_access(tg_name=user_name)
    if access == USER_NOT_FOUND:
        bot.send_message(message.chat.id, 'Вы не зарегистрированы в системе.')
        return
    elif access == ACCESS_DENIED and group == UG_CLIENT:

        bot.send_message(message.chat.id, 'Ваша подписка окончилась, новые заявки создать нельзя.'
                                          'Однако можно отслеживать ранее поданные заявки')

    db.update_user_data(
        user_name,
        ('tg_user_id', 'chat_id'),
        (message.from_user.id, message.chat.id)
    )
    chats[message.chat.id] = {
        'callback': None,  # current callback button
        'last_msg': [],  # последние отправленные за один раз сообщения (для подчистки кнопок) -- перспектива
        'callback_source': [],  # если задан, колбэк кнопки будут обрабатываться только с этих сообщений
        'group': group,  # группа, к которой принадлежит пользователь
        'access_due': access_due,  # дата и время актуальности кэшированного статуса
        'access': access,  # код доступа
        'text': None,  # для разных целей - перспектива
        'number': None,  # для разных целей - перспектива
        'step_due': None,  # срок актуальности ожидания ввода данных (используем в callback функциях)
    }
    show_main_menu(message.chat.id, group)


def check_user_in_cache(msg: telebot.types.Message):
    """проверят наличие user в кэше
    это на случай, если вдруг случился сбой/перезапуск скрипта на сервере
    и кэш приказал долго жить. В этом случае нужно отправлять пользователя в начало
    пути, чтобы избежать ошибок """
    user = chats.get(msg.chat.id)
    if not user:
        bot.send_message(msg.chat.id, 'Упс. Что то пошло не так.\n'
                                      'Начнем с главного меню')
        start_bot(msg)
        return None
    else:
        return user


def send_help_msg(chat_id, group):
    """
    Send  help message to chat_id depending on user group
    :param chat_id: chat_id of the user
    :param group: user group (see UT_* constants in db.py)
    :return:None
    """
    bot.send_message(chat_id, help_messages[group])


def show_main_menu(chat_id, group):
    user = chats[chat_id]
    if user['access_due'] < dt.datetime.now():
        access, group = db.check_user_access(chat_id=chat_id)
        user['access_due'] = dt.datetime.now() + dt.timedelta(0, ACCESS_DUE_TIME)
        user['access'] = access
        user['group'] = group
    """
    show main menu (the set of callback buttons depending on user group)
    :param chat_id: chat_id of the user
    :param group: user group (see UT_* constants in db.py)
    :return:
    """
    markup = None
    if group == UG_CLIENT:
        markup = markup_client
    elif group == UG_EXECUTOR:
        markup = markup_executor
    elif group == UG_ADMIN:
        markup = markup_admin
    msg = bot.send_message(chat_id, 'Варианты действий', reply_markup=markup)
    chats[chat_id]['callback_source'] = [msg.id, ]
    chats[chat_id]['callback'] = None


# CALLBACK FUNCTIONS FOR ALL USER GROUPS
def remove_last_buttons(chat_id):
    """Remove buttons in all messages cached in user['last_msg']
    This function is intended for future improvements
    """
    return
    user = chats[chat_id]
    msg: telebot.types.Message
    for msg in user['last_msg']:
        bot.edit_message_reply_markup(chat_id, msg.message_id, reply_markup=None)


def cancel_step(message: telebot.types.Message):
    """cancel current input process and show main menu"""
    remove_last_buttons(message.chat.id)
    bot.clear_step_handler(message)
    bot.send_message(message.chat.id, 'Действие отменено')
    show_main_menu(message.chat.id, chats[message.chat.id]['group'])
    chats[message.chat.id]['callback'] = None


# CALLBACK FUNCTIONS FOR CLIENT
def apply(message: telebot.types.Message, step=0):
    """
    provide input of application description and server credentials from client
    and putting the given info to DB
    """
    user = chats[message.chat.id]
    if user['access'] != ACCESS_ALLOWED:
        bot.send_message(message.chat.id, 'Ваша подписка окончилась, новые заявки создать нельзя.'
                                          'Однако можно отслеживать ранее поданные заявки')
        return
    if step == 0:
        user['callback'] = 'apply'
        msg = bot.send_message(message.chat.id, '''
                Сформулируйте содержание задачи
                *Примеры*:
                - Нужно добавить в интернет-магазин фильтр товаров по цвету
                - Нужно выгрузить товары с сайта в Excel-таблице
                - Нужно загрузить 450 SKU на сайт из Execel таблицы
                - Хочу провести на сайте акцию, хочу разместить баннер и добавить функционал, чтобы впридачу к акционным товарам выдавался приз
                ''', parse_mode='Markdown', reply_markup=markup_cancel_step)
        user['callback_source'].append(msg.id)
        bot.register_next_step_handler(message, apply, 1)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    elif step == 1:
        user['text'] = message.text
        msg = bot.send_message(
            message.chat.id,
            'Пожалуйста введите учетные данные для входа на сервер:\n'
            'URL:, логин, пароль', reply_markup=markup_cancel_step
        )
        user['callback_source'] = [msg.id, ]
        bot.register_next_step_handler(message, apply, 2)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif step == 2:
        date_reg = dt.date.today()
        credentials = message.text
        order_id = db.add_client_order(message.chat.id, user['text'], credentials, date_reg)
        bot.send_message(message.chat.id, f'Заявка #{order_id} принята.'
                                          f' Вам помогут в течение 24 часов')
        user['callback'] = None
        user['callback_source'] = []


def apps_to_client(msg: telebot.types.Message):
    """
    callback function to handle 'Мои заявки' button click
    Public all applications for the msg.chat.id
    :param msg: message
    :return:None
    """
    orders = db.get_client_active_orders(msg.chat.id)
    client_calls: list = chats[msg.chat.id]['callback_source']
    if not orders:
        bot.send_message(msg.chat.id, 'У вас нет зарегистрированных заявок')
    for order in orders:
        buttons = {}
        status = order['status']
        date_text = [f'Дата регистрации:  {order["date_reg"]}']
        if status == 0:
            status_text = '*--ПОИСК ИСПОЛНИТЕЛЯ--*\n'
        elif status == 1:
            status_text = '*--В РАБОТЕ--*\n'
            date_text.append(f'Взято в работу:  {order["date_appoint"]}')
            buttons['Комментарий исполнителю'] = {
                'callback_data': f'send_comments_id:{order["order_id"]}'
            }
        elif status == 2:
            status_text = '*--ЕСТЬ ВОПРОСЫ--*\n'
            buttons['Смотреть вопросы'] = {'callback_data': f'client_see_questions_id:{order["order_id"]}'}
        elif status == 3:
            status_text = '*--ВЫ ОТВЕТИЛИ--*\n'
            buttons['Редактировать ответ'] = {'callback_data': f'edit_answer_id:{order["order_id"]}'}
        elif status == 4:
            status_text = '*--ВЫПОЛНЕНА И ЖДЕТ ВАШЕЙ ПРИЕМКИ--*\n'
            buttons['Принять'] = {'callback_data': f'accept_work_id:{order["order_id"]}'}
            buttons['Отклонить'] = {'callback_data': f'reject_work_id:{order["order_id"]}'}
        elif status == 5:
            status_text = '*--НА ДОРАБОТКЕ--*\n'
        elif status == 6:
            status_text = '*--ПРИНЯТА ВАМИ--*\n'
            date_text.append(f'Дата приемки:  {order["date_accepted"]}')
        date_text = '\n'.join(date_text)
        comments = order['comments']
        if not comments:
            msg_text = f'{status_text}Заявка #{order["order_id"]}\n---\n{order["description"]}\n---\n{date_text}'
        else:
            msg_text = f'{status_text}Заявка #{order["order_id"]}\n---\n{order["description"]}\n---\n' \
                       f'Ваши комментарии:\n{comments}\n---\n{date_text}'
        if buttons:
            msg = bot.send_message(msg.chat.id, msg_text,
                                   parse_mode='Markdown',
                                   reply_markup=quick_markup(buttons))
            client_calls.append(msg.id)
        else:
            bot.send_message(msg.chat.id, msg_text, parse_mode='Markdown')


def apps_to_client_done(msg: telebot.types.Message):
    orders = db.get_client_orders_done(msg.chat.id)
    if not orders:
        bot.send_message(msg.chat.id, 'У вас нет завершенных заявок')
        return
    for order in orders:
        msg_text = f'*Заявка #{order["order_id"]}*\n---\n' \
                   f'{order["description"]}\n---\n' \
                   f'Дата регистрации: {order["date_reg"]}' \
                   f'Дата приемки в работу: {order["date_appoint"]}' \
                   f'Работа принята вами: {order["date_accepted"]}'
        bot.send_message(msg.chat.id, msg_text, parse_mode='Markdown')


def answer_id(msg: telebot.types.Message, order_id, step=0, end_text=None):
    user = chats[msg.chat.id]
    if step == 0:
        user['callback'] = 'answer_id'
        msg = bot.send_message(msg.chat.id, 'Отправьте в чат ответы на вопросы исполнителя',
                               reply_markup=markup_cancel_step)
        bot.register_next_step_handler(msg, answer_id, order_id, 1, end_text)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
        user['callback_source'] = [msg.id, ]
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(msg.chat.id, 'Время ввода данных истекло')
        cancel_step(msg)
        return
    elif step == 1:
        answer = msg.text
        db.update_order_data(order_id, ['answer', 'status'], [answer, 3])
        exec_chat_id = db.get_order_exec_chat(order_id)
        buttons = quick_markup({
            'Принять': {'callback_data': f'accept_answer_id:{order_id}'},
            'Остались вопросы': {'callback_data': f'reject_answer_id:{order_id}'}
        })
        if end_text:
            msg_text = f'По заявке *#{order_id}* {end_text}\n' \
                       f'{answer}'
        else:
            msg_text = f'По заявке *#{order_id}* заказчик ответил на Ваши вопросы\n' \
                       f'{answer}'
        msg_to_exec = bot.send_message(exec_chat_id, msg_text, parse_mode='Markdown', reply_markup=buttons)
        exec = chats.get(exec_chat_id)
        if not exec:
            exec = cache_user(exec_chat_id)
        exec['callback_source'].append(msg_to_exec.id)
        bot.send_message(msg.chat.id, f'Уведомление о Ваших ответах по *заявке #{order_id}* направлены исполнителю',
                         parse_mode='Markdown')
        user['callback'] = None
        user['callback_source'] = []


def send_comments_id(msg: telebot.types.Message, order_id, step=0):
    user = chats[msg.chat.id]
    if step == 0:
        user['callback'] = 'send_comments_id'
        msg = bot.send_message(msg.chat.id, 'Напишите Ваш комментарий',
                               reply_markup=markup_cancel_step)
        user['callback_source'] = [msg.id, ]
        bot.register_next_step_handler(msg, send_comments_id, order_id, 1)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(msg.chat.id, 'Время ввода данных истекло')
        cancel_step(msg)
        return
    elif step == 1:
        comments = msg.text
        db.update_order_data(order_id, ['comments'], [comments])
        exec_chat_id = db.get_order_exec_chat(order_id)
        buttons = quick_markup({
            'Задать вопрос': {'callback_data': f'ask_question_id:{order_id}'}
        })
        msg_text = f'*Комментарий от заказчика по заявке #{order_id}*\n' \
                   f'{comments}'
        exec = chats.get(exec_chat_id)
        if not exec:
            exec = cache_user(exec_chat_id)
        msg_to_exec = bot.send_message(exec_chat_id, msg_text, parse_mode='Markdown', reply_markup=buttons)
        bot.send_message(msg.chat.id, f'Комментарий отправлен исполнителю')
        exec['callback_source'].append(msg_to_exec.id)
        user['callback'] = None
        user['callback_source'] = []


def edit_answer_id(msg: telebot.types.Message, order_id):
    order = db.get_order_by_id(order_id)
    bot.send_message(msg.chat.id, f'*Вопросы исполнителя* к заявке #*{order_id}*\n'
                                  f'{order["questions"]}\n'
                                  f'*Ранее вы ответили*\n'
                                  f'{order["answer"]}')
    answer_id(msg, order_id, end_text='заказчик откорректировал ответы на вопросы')


def client_see_questions_id(msg: telebot.types.Message, order_id):
    order = db.get_order_by_id(order_id)
    buttons = quick_markup({
        'Ответить на вопросы': {'callback_data': f'answer_id:{order_id}'}
    })
    msg = bot.send_message(msg.chat.id, f'Вопросы исполнителя по заявке *#{order_id}*\n\n'
                                        f'{order["questions"]}', reply_markup=buttons,
                           parse_mode='Markdown')
    chats[msg.chat.id]['callback_source'].append(msg.id)


def accept_work_id(msg: telebot.types.Message, order_id):
    db.update_order_data(order_id, ['status', 'date_accepted'], [6, str(dt.date.today())])
    exec_chat = db.get_order_exec_chat(order_id)
    bot.send_message(exec_chat, f'Работа по заявке #{order_id} принята заказчиком.')
    bot.send_message(msg.chat.id, f'Вы приняли работу по заявке #{order_id}.')


def reject_work_id(msg: telebot.types.Message, order_id, step=0):
    user = chats[msg.chat.id]
    if step == 0:
        user['callback'] = 'reject_work_id'
        msg = bot.send_message(msg.chat.id, 'Напишите обоснование, почему не принимаете работу',
                               reply_markup=markup_cancel_step)
        user['callback_source'] = [msg.id, ]
        bot.register_next_step_handler(msg, reject_work_id, order_id, 1)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(msg.chat.id, 'Время ввода данных истекло')
        cancel_step(msg)
        return
    elif step == 1:
        comments = msg.text
        db.update_order_data(order_id, ['comments', 'status'], [comments, 5])
        exec_chat_id = db.get_order_exec_chat(order_id)
        buttons = quick_markup({'Встречный вопрос': {'callback_data': f'ask_question_id:{order_id}'}})
        msg_text = f'По заявке *#{order_id}* Заказчик не принимает работу.\n' \
                   f'*Обоснование:*\n{comments}'
        exec = chats.get(exec_chat_id)
        if not exec:
            exec = cache_user(exec_chat_id)
        msg_to_exec = bot.send_message(exec_chat_id, msg_text, parse_mode='Markdown', reply_markup=buttons)
        bot.send_message(msg.chat.id, f'Оповещение о неприемке работы по  заявке'
                                      f' *#{order_id}* направлено исполнителю', parse_mode='Markdown')
        exec['callback_source'].append(msg_to_exec.id)
        user['callback'] = None
        user['callback_source'] = []


# CALLBACK FUNCTIONS FOR EXECUTOR

def apps_to_exec(msg: telebot.types.Message):
    exec_orders = db.get_executor_orders(msg.chat.id, (1, 2, 3, 4, 5))
    if exec_orders:
        # на самом деле код позволяет принять в работу сколько угодно
        # заявок и потом взаимодействовать по каждой из них с клиентом в режиме вопрос-ответ
        # здесь пока намеренно поставлено ограничение только на одну заявку
        bot.send_message(msg.chat.id, 'У вас есть активная заявка в работе\n'
                                      'Сначала завершите ее')
        return
    orders = db.get_free_orders()
    actual_messages = chats[msg.chat.id]['callback_source']
    if orders:
        for order in orders:
            id = order['order_id']
            markup = quick_markup({'Взять в работу': {'callback_data': f'take_order_id:{id}'}})
            text_out = f'*Заявка #{id}*\n\n*Описание:*\n {order["description"]}\n'
            msg = bot.send_message(msg.chat.id, text_out, reply_markup=markup, parse_mode='Markdown')
            actual_messages.append(msg.id)
    else:
        bot.send_message(msg.chat.id, 'Пока нет свободных заявок')


def apps_in_work(msg: telebot.types.Message):
    orders = db.get_executor_orders(msg.chat.id, (1, 2, 3, 4, 5))
    if not orders:
        bot.send_message(msg.chat.id, 'У вас нет заявок в работе')
    actual_messages = []
    for order in orders:
        buttons = {'Сдать работу': {'callback_data': f'work_done_id:{order["order_id"]}'}}
        status = order['status']
        date_text = [f'Дата регистрации:  {order["date_reg"]}']
        if status == 1:
            status_text = '*--В РАБОТЕ--*\n'
            date_text.append(f'Взято в работу:  {order["date_appoint"]}')
            buttons['Задать вопросы'] = {'callback_data': f'ask_question_id:{order["order_id"]}'}
        elif status == 2:
            status_text = '*--ЗАДАНЫ ВОПРОСЫ--*\n'
            buttons['Редактировать вопросы'] = {'callback_data': f'edit_question_id:{order["order_id"]}'}
        elif status == 3:
            status_text = '*--ЗАКАЗЧИК ОТВЕТИЛ--*\n'
            buttons['Смотреть ответ'] = {'callback_data': f'see_client_answer_id:{order["order_id"]}'}
        elif status == 4:
            status_text = '*--ОЖИДАНИЕ ПРИЕМКИ ЗАКАЗЧИКОМ--*\n'
            buttons = None
        elif status == 5:
            status_text = '*--НА ДОАРБОТКУ--*\n'
            buttons['Задать вопросы'] = {'callback_data': f'ask_question_id:{order["order_id"]}'}
        date_text = '\n'.join(date_text)
        comments = order['comments']
        if comments:
            msg_text = f'{status_text}Заявка *#{order["order_id"]}*\n' \
                       f'{order["description"]}\n' \
                       f'*Данные для входы на сервер*\n' \
                       f'{order["credentials"]}' \
                       f'*Комментарии заказчика*\n{comments}\n{date_text}'
        else:
            msg_text = f'{status_text}Заявка *#{order["order_id"]}*\n' \
                       f'{order["description"]}\n' \
                       f'*Данные для входы на сервер*\n' \
                       f'{order["credentials"]}\n' \
                       f'{date_text}'
        if buttons:
            msg = bot.send_message(msg.chat.id, msg_text,
                                   parse_mode='Markdown',
                                   reply_markup=quick_markup(buttons))
            actual_messages.append(msg.id)
        else:
            bot.send_message(msg.chat.id, msg_text, parse_mode='Markdown')
    chats[msg.chat.id]['callback_source'] = actual_messages


def apps_to_exec_done(msg: telebot.types.Message):
    orders = db.get_executor_orders(msg.chat.id, (6,))
    if not orders:
        bot.send_message(msg.chat.id, 'У вас нет завершенных заявок')
        return
    for order in orders:
        msg_text = f'*Заявка #{order["order_id"]}*\n---\n' \
                   f'{order["description"]}\n---\n' \
                   f'Дата регистрации: {order["date_reg"]}\n' \
                   f'Дата приемки в работу: {order["date_appoint"]}\n' \
                   f'Принято заказчиком: {order["date_accepted"]}'
        bot.send_message(msg.chat.id, msg_text, parse_mode='Markdown')


def salary(msg: telebot.types.Message):
    bot.send_message(msg.chat.id, 'Ставка оплаты - 1000 руб за заявку')


def ask_question_id(msg: telebot.types.Message, order_id, step=0, end_text=None):
    executor = chats[msg.chat.id]
    if step == 0:
        executor['callback'] = 'ask_question_id'
        msg = bot.send_message(msg.chat.id, 'Введите вопросы, каждый вопрос с новой строки',
                               reply_markup=markup_cancel_step)
        executor['callback_source'] = [msg.id, ]
        bot.register_next_step_handler(msg, ask_question_id, order_id, 1, end_text)
        executor['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif executor['step_due'] < dt.datetime.now():
        bot.send_message(msg.chat.id, 'Время ввода данных истекло')
        cancel_step(msg)
        return
    elif step == 1:
        questions = msg.text
        db.update_order_data(order_id, ['questions', 'status'], [questions, 2])
        client_chat_id = db.get_order_client_chat(order_id)
        client = chats.get(client_chat_id)
        buttons = quick_markup({'Ответить': {'callback_data': f'answer_id:{order_id}'}})
        if end_text:
            msg_text = f'По заявке *#{order_id}* {end_text}\n\n' \
                       f'{questions}'
        else:
            msg_text = f'По заявке *#{order_id}* у исполнителя есть вопросы:\n\n' \
                       f'{questions}'
        msg_to_client = bot.send_message(client_chat_id, msg_text, parse_mode='Markdown', reply_markup=buttons)
        if not client:
            client = cache_user(client_chat_id)
        client['callback_source'].append(msg_to_client.id)
        bot.send_message(msg.chat.id, f'Вопросы по заявке *#{order_id}* направлены клиенту',
                         parse_mode='Markdown')
        executor['callback'] = None
        executor['callback_source'] = []


def edit_question_id(msg: telebot.types.Message, order_id, step=0):
    questions = db.get_order_questions(order_id)
    bot.send_message(msg.chat.id, f'Ваши вопросы к заявке #{order_id}\n\n'
                                  f'{questions}')
    ask_question_id(msg, order_id, end_text='исполнитель скорректировал вопросы')


def see_client_answer_id(msg: telebot.types.Message, order_id):
    order = db.get_order_by_id(order_id)
    user = chats[msg.chat.id]
    buttons = quick_markup({
        'Принять ответ': {'callback_data': f'accept_answer_id:{order_id}'},
        'Остались вопросы': {'callback_data': f'reject_answer_id:{order_id}'}
    })
    msg = bot.send_message(msg.chat.id, f'Ответы Заказчика по  заявке #*{order_id}*\n\n'
                                        f'{order["answer"]}', reply_markup=buttons,
                           parse_mode='Markdown')
    user['callback_source'] = [msg.id, ]


def exec_see_questions_id(msg: telebot.types.Message, order_id):
    user = chats[msg.chat.id]
    order = db.get_order_by_id(order_id)
    buttons = quick_markup({
        'Изменить': {'callback_data': f'edit_question_id:{order_id}'},
    })
    msg = bot.send_message(msg.chat.id, f'*Ваши вопросы по заявке #{order_id}*\n\n'
                                        f'{order["questions"]}', reply_markup=buttons,
                           parse_mode='Markdown')
    user['callback_source'] = [msg.id, ]


def take_order_id(msg: telebot.types.Message, order_id, step=0):
    user = chats[msg.chat.id]
    if step == 0:
        user['callback'] = 'take_order_id'
        msg = bot.send_message(msg.chat.id, 'Введите оценку сроков выполнения в свободной форме',
                               reply_markup=markup_cancel_step)
        bot.register_next_step_handler(msg, take_order_id, order_id, 1)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
        user['callback_source'] = [msg.id, ]
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(msg.chat.id, 'Время ввода данных истекло')
        cancel_step(msg)
        return
    elif step == 1:
        if db.get_order_status(order_id):
            print(db.get_order_status(order_id))
            bot.send_message(msg.chat.id, f'К сожалению эта заявка уже взята'
                                          f' в работу другим исполнителем')
        else:
            estimation = msg.text
            date_appoint = dt.date.today()
            db.update_order_data(order_id,
                                 ['estimation', 'date_appoint', 'status', 'ex_chat_id'],
                                 [estimation, str(date_appoint), 1, msg.chat.id])
            client_chat = db.get_order_client_chat(order_id)
            order = db.get_order_by_id(order_id)
            bot.send_message(msg.chat.id, f'Заявка *#{order_id}* принята Вами в работу',
                             parse_mode='Markdown')
            bot.send_message(client_chat, f'Ваша заявка #{order_id} принята в работу\n'
                                          f'*Оценка времени выполнения от исполнителя*\n {order["estimation"]}',
                             parse_mode='Markdown')
            bot.send_message(msg.chat.id, f'*Данные для входа на сервер:*\n'
                                          f'{order["credentials"]}', parse_mode='Markdown')
        user['callback'] = None
        user['callback_source'] = []


def work_done_id(msg: telebot.types.Message, order_id):
    db.update_order_data(order_id, ['status'], [4])
    client_chat = db.get_order_client_chat(order_id)
    client = chats.get(client_chat)
    buttons = quick_markup({
        'Принять': {'callback_data': f'accept_work_id:{order_id}'},
        'Отклонить': {'callback_data': f'reject_work_id:{order_id}'}
    })
    msg_to_client = bot.send_message(client_chat, f'Работа по *заявке #{order_id}* выполнена',
                                     reply_markup=buttons, parse_mode='Markdown')
    if not client:
        client = cache_user(client_chat)
    client['callback_source'].append(msg_to_client.id)
    bot.send_message(msg.chat.id, f'*Заявка #{order_id}* переведена в статус "Выполнена"\n'
                                  f'Заказчику направлено уведомление', parse_mode='Markdown')


def accept_answer_id(msg: telebot.types.Message, order_id):
    db.update_order_data(order_id, ['status'], [1])
    client_chat = db.get_order_client_chat(order_id)
    bot.send_message(client_chat, f'Ваши ответы на вопросы по *заявке #{order_id}*'
                                  f' приняты исполнителем', parse_mode='Markdown')
    bot.send_message(msg.chat.id, f'Вы приняли ответ заказчика по заявке #{order_id}')


def reject_answer_id(msg: telebot.types.Message, order_id):
    ask_question_id(msg, order_id, end_text='у исполнителя остались вопросы')


# CALLBACK FUNCTIONS FOR ADMIN

def add_user(message: telebot.types.Message, step=0):
    user = chats[message.chat.id]
    user['callback'] = 'add_user'
    if step == 0:
        msg = bot.send_message(message.chat.id, '''
                Введите имя пользователя для регистации без учета @
                ''', parse_mode='Markdown', reply_markup=markup_cancel_step)
        user['callback_source'] = [msg.id]
        bot.register_next_step_handler(message, add_user, 1)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    elif step == 1:
        user['name'] = message.text
        msg = bot.send_message(
            message.chat.id,
            'Введите группу пользователя:\n'
            '1 - заказчик, 2 - исполнитель', reply_markup=markup_cancel_step
        )
        user['callback_source'] = [msg.id]
        bot.register_next_step_handler(message, add_user, 2)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif step == 2:
        if message.text in ['1', '2']:
            date_reg = dt.date.today()
            user_group = message.text
            user_id = db.add_new_user(user['name'], user_group, date_reg)
            bot.send_message(message.chat.id, f'Пользователь #{user_id} - {user["name"]} зарегистрирован.',
                             reply_markup=markup_admin)
        else:
            bot.send_message(message.chat.id, 'Введенная группа некорректна')
            cancel_step(message)


def access_control(message: telebot.types.Message, step=0):
    user = chats[message.chat.id]
    user['callback'] = 'access_control'
    if step == 0:
        msg = bot.send_message(message.chat.id,
                               'Введите группу пользователя:\n'
                               '1 - заказчик, 2 - исполнитель', reply_markup=markup_cancel_step)
        user['callback_source'] = [msg.id]
        bot.register_next_step_handler(msg, access_control, 1)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    elif step == 1:
        user_group = message.text
        actual_messages = chats[message.chat.id]['callback_source']
        if user_group in ['1', '2']:
            user['callback'] = None
            users = db.get_list_users(int(message.text))
            for us in users:
                tg_name = us['tg_name']
                sub_time = us['subscription_time']
                access = us['access']
                if access == ACCESS_DENIED:
                    markup = quick_markup({'Открыть доступ': {'callback_data': f'allow_access_id:{tg_name}'}})
                    user_access = 'Доступ закрыт'
                elif access == ACCESS_ALLOWED:
                    markup = quick_markup({'Закрыть доступ': {'callback_data': f'deny_access_id:{tg_name}'}})
                    user_access = 'Доступ открыт'
                if user_group == '1':
                    text_out = f'Заказчик  {tg_name}\n\nОплата подписки: {sub_time}\n' \
                               f'{user_access}'
                    msg = bot.send_message(message.chat.id, text_out, reply_markup=markup)
                    actual_messages.append(msg.id)
                elif user_group == '2':
                    text_out = f'Исполнитель *{tg_name}*\n\nЗарегистрирован: {sub_time}\n' \
                               f'{user_access}'
                    msg = bot.send_message(message.chat.id, text_out, reply_markup=markup,
                                           parse_mode="Markdown")
                    actual_messages.append(msg.id)
        else:
            msg = bot.send_message(message.chat.id, 'Введенная группа некорректна')
            cancel_step(message)


def allow_access_id(message: telebot.types.Message, tg_name):
    callback_source: list =  chats[message.chat.id]['callback_source']
    db.change_user_access(tg_name, ACCESS_ALLOWED)
    bot.send_message(message.chat.id, 'Доступ открыт')
    callback_source.remove(message.id)


def deny_access_id(message: telebot.types.Message, tg_name):
    callback_source: list =  chats[message.chat.id]['callback_source']
    db.change_user_access(tg_name, ACCESS_DENIED)
    bot.send_message(message.chat.id, 'Доступ закрыт')
    callback_source.remove(message.id)


def apps_stat(message: telebot.types.Message, step=0):
    user = chats[message.chat.id]
    user['callback'] = 'apps_stat'

    if step == 0:
        msg = bot.send_message(message.chat.id, '''
                        Введите количество дней за которые нужно сформировать статистику:
                        ''', parse_mode='Markdown', reply_markup=markup_cancel_step)
        user['callback_source'] = [msg.id]
        bot.register_next_step_handler(message, apps_stat, 1)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    if step == 1:
        user['callback'] = []
        try:
            all_orders = 0
            days = int(message.text)
            delta = timedelta(days=days)
            date_now = dt.date.today()
            request_date = date_now - delta
            db_clients = db.get_clients_stat(request_date, date_now)
            for db_client in db_clients:
                count = int(db_client['cnt'])
                chat_id = db_client['chat_id']
                tg_name = db_client['tg_name']
                all_orders += count
                bot.send_message(message.chat.id, f'Заказчик {tg_name} \n'
                                                  f'Chat_id {chat_id} \n'
                                                  f'Создано заявок {count} \n')
            bot.send_message(message.chat.id, f'Общее количество заявок за период {all_orders}')
        except:
            bot.send_message(message.chat.id, 'Введенное количество дней некорректно')
            cancel_step(message)
            return


def get_salary_stat(message: telebot.types.Message, step=0):
    user = chats[message.chat.id]
    user['callback'] = 'salary_stat'

    if step == 0:
        msg = bot.send_message(message.chat.id, '''
                    Введите количество дней за которые нужно сформировать статистику:
                    ''', parse_mode='Markdown', reply_markup=markup_cancel_step)
        user['callback_source'] = [msg.id]
        bot.register_next_step_handler(message, get_salary_stat, 1)
        user['step_due'] = dt.datetime.now() + dt.timedelta(0, INPUT_DUE_TIME)
    elif user['step_due'] < dt.datetime.now():
        bot.send_message(message.chat.id, 'Время ввода данных истекло')
        cancel_step(message)
        return
    if step == 1:
        user['callback'] = []
        try:
            days = int(message.text)
            delta = timedelta(days=days)
            date_now = dt.date.today()
            request_date = date_now - delta
            db_execs = db.get_exec_stat(request_date, date_now)
            wage_rate = 1000
            for db_exec in db_execs:
                count = int(db_exec['cnt'])
                chat_id = db_exec['chat_id']
                tg_name = db_exec['tg_name']
                salary = count * wage_rate
                bot.send_message(message.chat.id, f'Исполитель {tg_name} \n'
                                                  f'Chat_id {chat_id} \n'
                                                  f'Выполнено заявок {count} \n'
                                                  f'К оплате {salary}  \n')
        except:
            bot.send_message(message.chat.id, 'Введенное количество дней некорректно')
            cancel_step(message)
            return