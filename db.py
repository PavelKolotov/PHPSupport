import sqlite3

from globals import USER_NOT_FOUND, ACCESS_DENIED, ACCESS_ALLOWED


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


con = sqlite3.connect("database.db", check_same_thread=False)
con.row_factory = dict_factory


def check_access_by_user_id(user_id):
    cur: sqlite3.Cursor = con.execute(f'select access, user_group from users where user_id="{user_id}"')
    row = cur.fetchone()
    cur.close()
    if not row:
        return (USER_NOT_FOUND, row['user_group'])
    elif row['access']:
        return (ACCESS_ALLOWED, row['user_group'])
    else:
        return (ACCESS_DENIED, row['user_group'])


def check_user_access(tg_name=None, user_id=None, chat_id=None):
    '''проверяет наличие доступа к системе у пользователя с указанным именем.
    (имеется ввиду имя пользователя в Telegram)
    Возвращает кортеж (а, б), где а=-1 - пользователя нет в БД.
    а=0 - пользователь есть в БД, но нет доступа
    а=1 - пользователь есть в БД и обладает доступом
    б - код группы пользователя (0-админы, 1-клиенты, 2-подрядчики)
    '''
    cur: sqlite3.Cursor = con.execute(f"select access, user_group "
                                      f"from users where tg_name='{tg_name if tg_name else 0}' or "
                                      f"tg_user_id={user_id if user_id else 0} or "
                                      f"chat_id={chat_id if chat_id else 0}")
    row = cur.fetchone()
    cur.close()
    if not row:
        return (USER_NOT_FOUND, None)
    elif row['access']:
        return (ACCESS_ALLOWED, row['user_group'])
    else:
        return (ACCESS_DENIED, row['user_group'])


def get_user_data_by_tgname(tg_name, fields=()):
    """
    Retrieve information for user with given Telegram name.
    :param tg_name: Telegram name of the user
    :param fields: tuple, containing field names (str) of the user table.
    if ommited function return all fields
    :return: dictionary where each key correponds to the field name
    """
    cur: sqlite3.Cursor
    if fields:
        cur = con.execute(f'select {", ".join(fields)}  from users')
    else:
        cur = con.execute('select *  from users')
    rows = cur.fetchall()
    cur.close()
    return rows


def get_user_by_chat_id(chat_id):
    cur: sqlite3.Cursor = con.execute(f'select *  from users where chat_id={chat_id}')
    row = cur.fetchone()
    cur.close()
    return row


def update_user_data(tg_name, fields=(), values=()):
    """
    Update data in the datebase for the user with specified name (Telegram)
    :return: affected rows
    """
    if fields:
        assigments = []
        for i, field in enumerate(fields):
            value = values[i]
            if type(value) is str:
                assigments.append(f"{field}='{value}'")
            else:
                assigments.append(f"{field}={value}")
        assigments = ", ".join(assigments)
        cur: sqlite3.Cursor = con.execute(
            f"Update users set {assigments} where tg_name='{tg_name}'"
        )
        con.commit()
        cur.close()
        return cur.rowcount
    else:
        return 0


def update_order_data(order_id, fields=[], values=[]):
    """
    Update order with specified order_id
    :return: affected rows
    """
    if fields:
        assigments = []
        for i, field in enumerate(fields):
            value = values[i]
            if type(value) is str:
                assigments.append(f"{field}='{value}'")
            else:
                assigments.append(f"{field}={value}")
        assigments = ", ".join(assigments)
        cur: sqlite3.Cursor = con.execute(
            f"Update orders set {assigments} where order_id='{order_id}'"
        )
        con.commit()
        cur.close()
        return cur.rowcount
    else:
        return 0


def get_free_orders():
    """retrieve orders wich can be taken
    by executor"""
    cur: sqlite3.Cursor = con.execute(
        f'select * from orders where status=0 order by date_reg'
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_client_active_orders(chat_id):
    cur: sqlite3.Cursor = con.execute(
        f'select * from orders where client_chat_id={chat_id}'
        f' and status<6 order by status'
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_client_orders_done(chat_id):
    cur: sqlite3.Cursor = con.execute(
        f'select * from orders where client_chat_id={chat_id} and status=6'
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_executor_orders(chat_id, status=()):
    if status:
        status_seq = f'({", ".join(map(str,status))})'
        sql = f'select * from orders where ex_chat_id={chat_id}' \
              f' and status in {status_seq} order by date_reg'
    else:
        sql = f'select * from orders where ex_chat_id={chat_id} order by date_reg'
    cur: sqlite3.Cursor = con.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return rows


def add_client_order(chat_id, description, credentials, date):
    """
    register a new client application
    :param chat_id: of the client
    :param description: of the application
    :param credentials: of the sever admin site
    :return: id of the new order
    """
    data = (chat_id, description, credentials, date)
    cur = con.execute(
        'insert into orders '
        '(client_chat_id, description, credentials, date_reg) '
        'values(?, ?, ?, ?)', data)
    con.commit()
    cur.close()
    return cur.lastrowid


def get_order_by_id(order_id):
    cur: sqlite3.Cursor = con.execute(
        f'select * from orders where order_id={order_id}'
    )
    row = cur.fetchone()
    cur.close()
    return row


def get_order_status(order_id):
    cur: sqlite3.Cursor = con.execute(
        f'select status from orders where order_id={order_id}'
    )
    row = cur.fetchone()
    cur.close()
    return row['status']


def get_order_questions(order_id):
    cur: sqlite3.Cursor = con.execute(
        f'select questions from orders where order_id={order_id}'
    )
    row = cur.fetchone()
    cur.close()
    return row['questions']


def get_order_client_chat(order_id):
    cur: sqlite3.Cursor = con.execute(
        f'select client_chat_id from orders where order_id={order_id}'
    )
    row = cur.fetchone()
    cur.close()
    return row['client_chat_id']


def get_order_exec_chat(order_id):
    cur: sqlite3.Cursor = con.execute(
        f'select ex_chat_id from orders where order_id={order_id}'
    )
    row = cur.fetchone()
    cur.close()
    return row['ex_chat_id']


def get_list_users(user_group):
    """retrieve all executors/clients"""
    cur: sqlite3.Cursor = con.execute(
        f'select * from users where user_group={user_group}'
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_all_users():
    cur: sqlite3.Cursor = con.execute(
        f'select * from users'
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_all_orders():
    cur: sqlite3.Cursor = con.execute(
        f'select * from orders'
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def change_user_access(tg_name, access):
    cur = con.execute(f'UPDATE users SET access = {access} WHERE tg_name LIKE "{tg_name}"')
    con.commit()
    cur.close()
    return cur.lastrowid


def change_user_id(tg_name, chat_id):
    cur = con.execute(f'UPDATE users SET chat_id = {chat_id} WHERE tg_name LIKE "{tg_name}"')
    con.commit()
    cur.close()
    return cur.lastrowid


def add_new_user(tg_name, user_group, subscription_time, access=1):
    data = (tg_name, user_group, subscription_time, access)
    cur = con.execute(
        'insert into users '
        '(tg_name, user_group, subscription_time, access) '
        'values( ?, ?, ?, ?)', data)
    con.commit()
    cur.close()
    return cur.lastrowid


def get_exec_stat(request_date, date_now):
    cur: sqlite3.Cursor = con.execute(
         f'''SELECT users.tg_name, users.chat_id, orders.date_accepted, count(users.tg_name) as cnt
            FROM orders INNER JOIN
            users ON orders.ex_chat_id = users.chat_id
            WHERE  orders.date_accepted BETWEEN "{request_date}" AND "{date_now}"
            GROUP BY users.tg_name'''
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_clients_stat(request_date, date_now):
    cur: sqlite3.Cursor = con.execute(
         f'''SELECT users.tg_name, users.chat_id, count(users.tg_name) as cnt
            FROM orders INNER JOIN
            users ON orders.client_chat_id = users.chat_id
            WHERE  orders.date_reg BETWEEN "{request_date}" AND "{date_now}"
            GROUP BY users.tg_name'''
    )
    rows = cur.fetchall()
    cur.close()
    return rows


if __name__ == '__main__':
    pass