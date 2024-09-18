from typing import Union  # Объединение типов
from socket import socket, AF_INET, SOCK_STREAM  # Обращаться к LUA скриптам QUIK# будем через соединения
from threading import Thread, Event, Lock  # Поток/событие выхода для обратного вызова. Блокировка process_request для многопоточных приложений
from json import loads  # Принимать данные в QUIK будем через JSON
from json.decoder import JSONDecodeError  # Ошибка декодирования JSON
import logging  # Будем вести лог

from pytz import timezone  # Работаем с временнОй зоной


class QuikPy:
    """Работа с QUIK из Python через LUA скрипты QUIK# https://github.com/finsight/QUIKSharp/tree/master/src/QuikSharp/lua
     На основе Документации по языку LUA в QUIK из https://arqatech.com/ru/support/files/
     Маркировка функций по пунктам документа: Документация по языку LUA в QUIK и примеры - Интерпретатор языка Lua - Версия 11.2
     """
    buffer_size = 1048576  # Размер буфера приема в байтах (1 МБайт)
    tz_msk = timezone('Europe/Moscow')  # QUIK работает по московскому времени
    currency = 'SUR'  # Суммы будем получать в рублях
    limit_kind = 1  # Основной режим торгов T1
    futures_firm_id = 'SPBFUT'  # Код фирмы для срочного рынка. Если ваш брокер поставил другую фирму для срочного рынка, то измените ее
    logger = logging.getLogger('QuikPy')  # Будем вести лог

    def __init__(self, host='127.0.0.1', requests_port=34130, callbacks_port=34131):
        """Инициализация

        :param str host: IP адрес или название хоста
        :param int requests_port: Порт для отправки запросов и получения ответов
        :param int callbacks_port: Порт для функций обратного вызова
        """
        # 2.2 Функции обратного вызова
        self.on_firm = self.default_handler  # 2.2.1 Новая фирма
        self.on_all_trade = self.default_handler  # 2.2.2 Новая обезличенная сделка
        self.on_trade = self.default_handler  # 2.2.3 Новая сделка / Изменение существующей сделки
        self.on_order = self.default_handler  # 2.2.4 Новая заявка / Изменение существующей заявки
        self.on_account_balance = self.default_handler  # 2.2.5 Изменение текущей позиции по счету
        self.on_futures_limit_change = self.default_handler  # 2.2.6 Изменение ограничений по срочному рынку
        self.on_futures_limit_delete = self.default_handler  # 2.2.7 Удаление ограничений по срочному рынку
        self.on_futures_client_holding = self.default_handler  # 2.2.8 Изменение позиции по срочному рынку
        self.on_money_limit = self.default_handler  # 2.2.9 Изменение денежной позиции
        self.on_money_limit_delete = self.default_handler  # 2.2.10 Удаление денежной позиции
        self.on_depo_limit = self.default_handler  # 2.2.11 Изменение позиций по инструментам
        self.on_depo_limit_delete = self.default_handler  # 2.2.12 Удаление позиции по инструментам
        self.on_account_position = self.default_handler  # 2.2.13 Изменение денежных средств
        # on_neg_deal - 2.2.14 Новая внебиржевая заявка / Изменение существующей внебиржевой заявки
        # on_neg_trade - 2.2.15 Новая внебиржевая сделка / Изменение существующей внебиржевой сделки
        self.on_stop_order = self.default_handler  # 2.2.16 Новая стоп заявка / Изменение существующей стоп заявки
        self.on_trans_reply = self.default_handler  # 2.2.17 Ответ на транзакцию пользователя
        self.on_param = self.default_handler  # 2.2.18 Изменение текущих параметров
        self.on_quote = self.default_handler  # 2.2.19 Изменение стакана котировок
        self.on_disconnected = self.default_handler  # 2.2.20 Отключение терминала от сервера QUIK
        self.on_connected = self.default_handler  # 2.2.21 Соединение терминала с сервером QUIK
        # on_clean_up - 2.2.22 Смена сервера QUIK / Пользователя / Сессии
        self.on_close = self.default_handler  # 2.2.23 Закрытие терминала QUIK
        self.on_stop = self.default_handler  # 2.2.24 Остановка LUA скрипта в терминале QUIK / закрытие терминала QUIK
        self.on_init = self.default_handler  # 2.2.25 Запуск LUA скрипта в терминале QUIK
        # on_main - 2.2.26 Функция, реализующая основной поток выполнения в скрипте

        # Функции обратного вызова QUIK#
        self.on_new_candle = self.default_handler  # Новая свечка
        self.on_error = self.default_handler  # Сообщение об ошибке

        self.host = host  # IP адрес или название хоста
        self.requests_port = requests_port  # Порт для отправки запросов и получения ответов
        self.callbacks_port = callbacks_port  # Порт для функций обратного вызова
        self.socket_requests = socket(AF_INET, SOCK_STREAM)  # Создаем соединение для запросов
        self.socket_requests.connect((self.host, self.requests_port))  # Открываем соединение для запросов

        self.callback_exit_event = Event()  # Определяем событие выхода из потока
        self.callback_thread = Thread(target=self.callback_handler, name='CallbackThread').start()  # Создаем и запускаем поток обработки функций обратного вызова
        self.lock = Lock()  # Блокировка process_request для многопоточных приложений

        self.accounts = list()  # Счета
        money_limits = self.get_money_limits()['data']  # Все денежные лимиты (остатки на счетах)
        i = 0  # Начальный номер счета
        for account in self.get_trade_accounts()['data']:  # Пробегаемся по всем торговым счетам
            firm_id = account['firmid']  # Фирма
            client_code = next((moneyLimit['client_code'] for moneyLimit in money_limits if moneyLimit['firmid'] == firm_id), '')  # Код клиента
            class_codes: list[str] = account['class_codes'][1:-1].split('|')  # Список режимов торгов счета. Убираем первую и последнюю вертикальную черту, разбиваем по вертикальной черте
            self.accounts.append(dict(  # Добавляем торговый счет
                account_id=i, client_code=client_code, firm_id=firm_id, trade_account_id=account['trdaccid'],  # Номер счета / Код клиента / Фирма / Счет
                class_codes=class_codes, futures=(firm_id == self.futures_firm_id)))  # Режимы торгов / Счет срочного рынка
            i += 1  # Смещаем на следующий номер счета
        self.subscriptions = []  # Список подписок. Для возобновления всех подписок после повторного подключения к серверу QUIK
        self.symbols = {}  # Справочник тикеров

    def __enter__(self):
        """Вход в класс, например, с with"""
        return self

    # Фукнции отладки QUIK#

    def ping(self, trans_id=0):
        """Проверка соединения. Отправка строки 'ping'. Получение строки 'pong'

        :param int trans_id: Код транзакции
        :return: Строка 'pong'
        """
        return self.process_request({'data': 'Ping', 'id': trans_id, 'cmd': 'ping', 't': ''})

    def echo(self, message, trans_id=0):
        """Отправка и получение одного и того же сообщения (эхо)

        :param str message: Сообщение
        :param int trans_id: Код транзакции
        :return: Это же сообщение
        """
        return self.process_request({'data': message, 'id': trans_id, 'cmd': 'echo', 't': ''})

    def divide_string_by_zero(self, trans_id=0):
        """Тест обработки ошибок. Выполняется деление строки на 0 с выдачей ошибки

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'divide_string_by_zero', 't': ''})

    def is_quik(self, trans_id=0):
        """Скрипт запущен в QUIK

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'is_quik', 't': ''})

    # 2.1 Сервисные функции

    def is_connected(self, trans_id=0):  # 2.1.1 Функция предназначена для определения состояния подключения клиентского места к серверу
        """Состояние подключения терминала к серверу QUIK

        :param int trans_id: Код транзакции
        :return: 1 - подключено / 0 - не подключено
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'isConnected', 't': ''})

    def get_script_path(self, trans_id=0):  # 2.1.2 Функция возвращает путь, по которому находится запускаемый скрипт, без завершающего обратного слеша (\). Например, C:\QuikFront\Scripts
        """Путь скрипта

        :param int trans_id: Код транзакции
        :return: Путь скрипта без завершающего обратного слэша
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getScriptPath', 't': ''})

    def get_info_param(self, params, trans_id=0):  # 2.1.3 Функция возвращает значения параметров информационного окна (пункт меню Система / О программе / Информационное окно…)
        """Значения параметров информационного окна

        :param str params: Параметр. Список возможных параметров на стр. 8
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': params, 'id': trans_id, 'cmd': 'getInfoParam', 't': ''})

    # message - 2.1.4. Сообщение в терминале QUIK. Реализовано в виде 3-х отдельных функций message_info/message_warning/message_error в QUIK# ниже

    def sleep(self, time, trans_id=0):  # 2.1.5 Функция приостанавливает выполнение скрипта
        """Приостановка скрипта. Время в миллисекундах

        :param int time: Время в миллисекундах
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': time, 'id': trans_id, 'cmd': 'sleep', 't': ''})

    def get_working_folder(self, trans_id=0):  # 2.1.6 Функция возвращает путь, по которому находится файл info.exe, исполняющий данный скрипт, без завершающего обратного слеша (\). Например, c:\QuikFront
        """Путь к info.exe, исполняющего скрипт

        :param int trans_id: Код транзакции
        :return: Путь к info.exe, исполняющего скрипта, без завершающего обратного слэша
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getWorkingFolder', 't': ''})

    def print_dbg_str(self, message, trans_id=0):  # 2.1.7 Функция для вывода отладочной информации
        """Вывод отладочной информации. Можно посмотреть с помощью DebugView

        :param str message: Отладочная информация
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': message, 'id': trans_id, 'cmd': 'PrintDbgStr', 't': ''})

    # sysdate - 2.1.8. Системные дата и время
    # isDarkTheme - 2.1.9. Тема оформления. true - тёмная, false - светлая

    # Сервисные функции QUIK#

    def message_info(self, message, trans_id=0):  # В QUIK LUA message icon_type=1
        """Отправка информационного сообщения в терминал QUIK

        :param str message: Информационное сообщение
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': message, 'id': trans_id, 'cmd': 'message', 't': ''})

    def message_warning(self, message, trans_id=0):  # В QUIK LUA message icon_type=2
        """Отправка сообщения с предупреждением в терминал QUIK

        :param str message: Сообщение с предупреждением
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': message, 'id': trans_id, 'cmd': 'warning_message', 't': ''})

    def message_error(self, message, trans_id=0):  # В QUIK LUA message icon_type=3
        """Отправка сообщения об ошибке в терминал QUIK

        :param str message: Сообщение об ошибке
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': message, 'id': trans_id, 'cmd': 'error_message', 't': ''})

    # 3.1. Функции для обращения к строкам произвольных таблиц

    # getItem - 3.1.1. Строка таблицы
    # getOrderByNumber - 3.1.2. Заявка
    # getNumberOf - 3.1.3. Кол-во записей в таблице
    # SearchItems - 3.1.4. Быстрый поиск по таблице заданной функцией поиска

    def get_trade_accounts(self, trans_id=0):  # QUIK#
        """Торговые счета, у которых указаны поддерживаемые классы инструментов

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getTradeAccounts', 't': ''})

    def get_trade_account(self, class_code, trans_id=0):  # QUIK#
        """Торговый счет для режима торгов

        :param str class_code: Код режима торгов
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': class_code, 'id': trans_id, 'cmd': 'getTradeAccount', 't': ''})

    def get_all_orders(self, trans_id=0):  # QUIK#
        """Все заявки

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'', 'id': trans_id, 'cmd': 'get_orders', 't': ''})

    def get_orders(self, class_code, sec_code, trans_id=0):  # QUIK#
        """Заявки по тикеру

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'get_orders', 't': ''})

    def get_order_by_number(self, order_id, trans_id=0):  # QUIK#
        """Заявка по номеру

        :param str order_id: Номер заявки
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': order_id, 'id': trans_id, 'cmd': 'getOrder_by_Number', 't': ''})

    def get_order_by_id(self, class_code, sec_code, order_trans_id, trans_id=0):  # QUIK#
        """Заявка по тикеру и коду транзакции заявки

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param str order_trans_id: Код транзакции заявки
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}|{order_trans_id}', 'id': trans_id, 'cmd': 'getOrder_by_ID', 't': ''})

    def get_order_by_class_number(self, class_code, order_id, trans_id=0):  # QUIK#
        """Заявка по режиму торгов и номеру

        :param str class_code: Код режима торгов
        :param str order_id: Номер заявки
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{order_id}', 'id': trans_id, 'cmd': 'getOrder_by_Number', 't': ''})

    def get_money_limits(self, trans_id=0):  # QUIK#
        """Все позиции по деньгам

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getMoneyLimits', 't': ''})

    def get_client_code(self, trans_id=0):  # QUIK#
        """Основной (первый) код клиента

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getClientCode', 't': ''})

    def get_client_codes(self, trans_id=0):  # QUIK#
        """Все коды клиента

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getClientCodes', 't': ''})

    def get_all_depo_limits(self, trans_id=0):  # QUIK#
        """Лимиты по всем инструментам

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'get_depo_limits', 't': ''})

    def get_depo_limits(self, sec_code, trans_id=0):  # QUIK#
        """Лимиты по инструменту

        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': sec_code, 'id': trans_id, 'cmd': 'get_depo_limits', 't': ''})

    def get_all_trades(self, trans_id=0):  # QUIK#
        """Все сделки

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'', 'id': trans_id, 'cmd': 'get_trades', 't': ''})

    def get_trades(self, class_code, sec_code, trans_id=0):  # QUIK#
        """Сделки по инструменту

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'get_trades', 't': ''})

    def get_trades_by_order_number(self, order_num, trans_id=0):  # QUIK#
        """Сделки по номеру заявки

        :param str order_num: Номер заявки
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': order_num, 'id': trans_id, 'cmd': 'get_Trades_by_OrderNumber', 't': ''})

    def get_all_stop_orders(self, trans_id=0):  # QUIK#
        """Все стоп заявки

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'get_stop_orders', 't': ''})

    def get_stop_orders(self, class_code, sec_code, trans_id=0):  # QUIK#
        """Стоп заявки по инструменту

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'get_stop_orders', 't': ''})

    def get_all_trade(self, trans_id=0):  # QUIK#
        """Все обезличенные сделки

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'', 'id': trans_id, 'cmd': 'get_all_trades', 't': ''})

    def get_trade(self, class_code, sec_code, trans_id=0):  # QUIK#
        """Обезличенные сделки по инструменту

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'get_all_trades', 't': ''})

    # 3.2 Функции для обращения к спискам доступных параметров

    def get_classes_list(self, trans_id=0):  # 3.2.1 Функция предназначена для получения списка режимов торгов, переданных с сервера в ходе сеанса связи
        """Все режимы торгов

        :param int trans_id: Код транзакции
        :return: Все режимы торгов разделенные запятыми. В конце также запятая
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getClassesList', 't': ''})

    def get_class_info(self, class_code, trans_id=0):  # 3.2.2 Функция предназначена для получения информации о режиме торгов
        """Информация о режиме торгов

        :param str class_code: Код режима торгов
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': class_code, 'id': trans_id, 'cmd': 'getClassInfo', 't': ''})

    def get_class_securities(self, class_code, trans_id=0):  # 3.2.3 Функция предназначена для получения списка кодов инструментов для списка режимов торгов, заданного списком кодов
        """Тикеры режима торгов

        :param str class_code: Код режима торгов
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': class_code, 'id': trans_id, 'cmd': 'getClassSecurities', 't': ''})

    def get_option_board(self, class_code, sec_code, trans_id=0):  # QUIK#
        """Доска опционов

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'getOptionBoard', 't': ''})

    # 3.3 Функции для получения информации по денежным средствам

    def get_money(self, client_code, firm_id, tag, curr_code, trans_id=0):  # 3.3.1 Функция предназначена для получения информации по денежным позициям
        """Денежные позиции

        :param str client_code: Код клиента
        :param str firm_id: Код фирмы
        :param str tag: Идентификатор денежного лимита
        :param str curr_code: Код валюты. SUR для рублей
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{client_code}|{firm_id}|{tag}|{curr_code}', 'id': trans_id, 'cmd': 'getMoney', 't': ''})

    def get_money_ex(self, firm_id, client_code, tag, curr_code, limit_kind, trans_id=0):  # 3.3.2 Функция предназначена для получения информации по денежным позициям указанного типа
        """Денежные позиции указанного типа

        :param str firm_id: Код фирмы
        :param str client_code: Код клиента
        :param str tag: Идентификатор денежного лимита
        :param str curr_code: Код валюты. SUR для рублей
        :param int limit_kind: Срок расчетов
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{firm_id}|{client_code}|{tag}|{curr_code}|{limit_kind}', 'id': trans_id, 'cmd': 'getMoneyEx', 't': ''})

    # 3.4 Функции для получения позиций по инструментам

    def get_depo(self, client_code, firm_id, sec_code, account, trans_id=0):  # 3.4.1 Функция предназначена для получения позиций по инструментам
        """Позиции по инструментам

        :param str client_code: Код клиента
        :param str firm_id: Код фирмы
        :param str sec_code: Тикер
        :param str account: Счет
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{client_code}|{firm_id}|{sec_code}|{account}', 'id': trans_id, 'cmd': 'getDepo', 't': ''})

    def get_depo_ex(self, firm_id, client_code, sec_code, account, limit_kind, trans_id=0):  # 3.4.2 Функция предназначена для получения позиций по инструментам указанного типа
        """Позиции по инструментам указанного типа

        :param str firm_id: Код фирмы
        :param str client_code: Код клиента
        :param str sec_code: Тикер
        :param str account: Счет
        :param int limit_kind: Срок расчетов
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{firm_id}|{client_code}|{sec_code}|{account}|{limit_kind}', 'id': trans_id, 'cmd': 'getDepoEx', 't': ''})

    # 3.5 Функция для получения информации по фьючерсным лимитам

    def get_futures_limit(self, firm_id, account_id, limit_type, curr_code, trans_id=0):  # 3.5.1 Функция предназначена для получения информации по фьючерсным лимитам
        """Фьючерсные лимиты

        :param str firm_id: Код фирмы
        :param str account_id: Счет
        :param int limit_type: Срок расчетов (limit_kind)
        :param str curr_code: Код валюты. SUR для рублей
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{firm_id}|{account_id}|{limit_type}|{curr_code}', 'id': trans_id, 'cmd': 'getFuturesLimit', 't': ''})

    def get_futures_client_limits(self, trans_id=0):  # QUIK#
        """Все фьючерсные лимиты

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getFuturesClientLimits', 't': ''})

    # 3.6 Функция для получения информации по фьючерсным позициям

    def get_futures_holding(self, firm_id, account_id, sec_code, position_type, trans_id=0):  # 3.6.1 Функция предназначена для получения информации по фьючерсным позициям
        """Фьючерсные позиции

        :param str firm_id: Код фирмы
        :param str account_id: Счет
        :param str sec_code: Тикер
        :param str position_type: Тип лимита. Возможные значения: 0 – не определён; 1 – основной счет; 2 – клиентские и дополнительные счета; 4 – все счета торг. членов
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{firm_id}|{account_id}|{sec_code}|{position_type}', 'id': trans_id, 'cmd': 'getFuturesHolding', 't': ''})

    def get_futures_holdings(self, trans_id=0):  # QUIK#
        """Все фьючерсные позиции

        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getFuturesClientHoldings', 't': ''})

    # 3.7 Функция для получения информации по инструменту

    def get_security_info(self, class_code, sec_code, trans_id=0):  # 3.7.1 Функция предназначена для получения информации по инструменту
        """Информация по инструменту

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'getSecurityInfo', 't': ''})

    def get_security_info_bulk(self, class_sec_codes, trans_id=0):  # QUIK#
        """Информация по инструментам

        :param set[str] class_sec_codes: Список кодов режимов торгов и тикеров. Например: {'TQBR|SBER', 'SPBFUT|CNYRUBF'}
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': class_sec_codes, 'id': trans_id, 'cmd': 'getSecurityInfoBulk', 't': ''})

    def get_security_class(self, classes_list, sec_code, trans_id=0):  # QUIK#
        """Режим торгов по коду инструмента из заданных режимов торгов

        :param str classes_list: Режимы торгов через запятую, по которым будет поиск
        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{classes_list}|{sec_code}', 'id': trans_id, 'cmd': 'getSecurityClass', 't': ''})

    # 3.8 Функция для получения даты торговой сессии

    # getTradeDate - 3.8.1. Дата текущей торговой сессии

    # 3.9 Функция для получения стакана по указанному классу и инструменту

    def get_quote_level2(self, class_code, sec_code, trans_id=0):  # 3.9.1 Функция предназначена для получения стакана по указанному режиму торгов и инструменту
        """Стакан по классу и инструменту

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'GetQuoteLevel2', 't': ''})

    # 3.10 Функции для работы с графиками

    # getLinesCount - 3.10.1. Кол-во линий в графике

    def get_num_candles(self, tag, trans_id=0):  # 3.10.2 Функция предназначена для получения информации о количестве свечек по выбранному идентификатору
        """Кол-во свечей по идентификатору

        :param str tag: Строковый идентификатор графика или индикатора
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': tag, 'id': trans_id, 'cmd': 'get_num_candles', 't': ''})

    # getCandlesByIndex - 3.10.3. Информация о свечках (реализовано в get_candles)
    # CreateDataSource - 3.10.4. Создание источника данных c функциями: (реализовано в get_candles_from_data_source)
    # - SetUpdateCallback - Привязка функции обратного вызова на изменение свечи
    # - O, H, L, C, V, T - Функции получения цен, объемов и времени
    # - Size - Функция кол-ва свечек в источнике данных
    # - Close - Функция закрытия источника данных. Терминал прекращает получать данные с сервера
    # - SetEmptyCallback - Функция сброса функции обратного вызова на изменение свечи

    def get_candles(self, tag, line, first_candle, count, trans_id=0):  # QUIK#
        """Свечи по идентификатору графика

        :param str tag: Строковый идентификатор графика или индикатора
        :param int line: Номер линии графика или индикатора
        :param int first_candle: Номер первой свечи
        :param int count: Кол-во свечей. 0 - все
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{tag}|{line}|{first_candle}|{count}', 'id': trans_id, 'cmd': 'get_candles', 't': ''})

    def get_candles_from_data_source(self, class_code, sec_code, interval, param='-', count=0):  # QUIK#
        """Свечи

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int interval: Кол-во в минутах: 0 (тик), 1, 2, 3, 4, 5, 6, 10, 15, 20, 30, 60 (1 час), 120 (2 часа), 240 (4 часа), 1440 (день), 10080 (неделя), 23200 (месяц)
        :param str param: Если параметр не задан, то заказываются данные на основании Таблицы обезличенных сделок, если задан – данные по этому параметру
        :param int count: Кол-во свечей. 0 - все
        """
        return self.process_request({'data': f'{class_code}|{sec_code}|{interval}|{param}|{count}', 'id': '1', 'cmd': 'get_candles_from_data_source', 't': ''})

    def subscribe_to_candles(self, class_code, sec_code, interval, param='-', trans_id=0):  # QUIK#
        """Подписка на свечи

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int interval: Кол-во в минутах: 0 (тик), 1, 2, 3, 4, 5, 6, 10, 15, 20, 30, 60 (1 час), 120 (2 часа), 240 (4 часа), 1440 (день), 10080 (неделя), 23200 (месяц)
        :param str param: Если параметр не задан, то заказываются данные на основании Таблицы обезличенных сделок, если задан – данные по этому параметру
        :param int trans_id: Код транзакции
        """
        result = self.process_request({'data': f'{class_code}|{sec_code}|{interval}|{param}', 'id': trans_id, 'cmd': 'subscribe_to_candles', 't': ''})
        subscription = {'subscription': 'candles', 'class_code': class_code, 'sec_code': sec_code, 'interval': interval, 'param': param}  # Подписка
        if self.is_subscribed(class_code, sec_code, interval, param) and subscription not in self.subscriptions:  # Если есть подписка на свечи, но ее нет в списке подписок
            self.subscriptions.append(subscription)  # то добавляем подписку
        return result

    def unsubscribe_from_candles(self, class_code, sec_code, interval, param='-', trans_id=0):  # QUIK#
        """Отмена подписки на свечи

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int interval: Кол-во в минутах: 0 (тик), 1, 2, 3, 4, 5, 6, 10, 15, 20, 30, 60 (1 час), 120 (2 часа), 240 (4 часа), 1440 (день), 10080 (неделя), 23200 (месяц)
        :param str param: Если параметр не задан, то заказываются данные на основании Таблицы обезличенных сделок, если задан – данные по этому параметру
        :param int trans_id: Код транзакции
        """
        result = self.process_request({'data': f'{class_code}|{sec_code}|{interval}|{param}', 'id': trans_id, 'cmd': 'unsubscribe_from_candles', 't': ''})
        subscription = {'subscription': 'candles', 'class_code': class_code, 'sec_code': sec_code, 'interval': interval, 'param': param}  # Подписка
        if not self.is_subscribed(class_code, sec_code, interval, param) and subscription in self.subscriptions:  # Если нет подписки на свечи, но она есть в списке подписок
            self.subscriptions.remove(subscription)  # то удаляемподписку
        return result

    def is_subscribed(self, class_code, sec_code, interval, param='-', trans_id=0):  # QUIK#
        """Есть ли подписка на свечи

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int interval: Кол-во в минутах: 0 (тик), 1, 2, 3, 4, 5, 6, 10, 15, 20, 30, 60 (1 час), 120 (2 часа), 240 (4 часа), 1440 (день), 10080 (неделя), 23200 (месяц)
        :param str param: Если параметр не задан, то заказываются данные на основании Таблицы обезличенных сделок, если задан – данные по этому параметру
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}|{interval}|{param}', 'id': trans_id, 'cmd': 'is_subscribed', 't': ''})

    # 3.11 Функции для работы с заявками

    def send_transaction(self, transaction, trans_id=0):  # 3.11.1 Функция предназначена для отправки транзакций в торговую систему
        """Отправка транзакции в торговую систему

        :param dict transaction: Транзакция в виде словаря. Формат и правила формирования описаны в Руководстве пользователя QUIK https://arqatech.com/ru/support/files/ Файл 6. Совместная работа с другими приложениями. Пункт 6.9.2
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': transaction, 'id': trans_id, 'cmd': 'sendTransaction', 't': ''})

    # CalcBuySell - 3.11.2. Максимальное кол-во лотов в заявке

    # 3.12 Функции для получения значений таблицы "Текущие торги"

    def get_param_ex(self, class_code, sec_code, param_name, trans_id=0):  # 3.12.1 Функция предназначена для получения значений всех параметров биржевой информации из таблицы Текущие торги. С помощью этой функции можно получить любое из значений Таблицы текущих торгов для заданных кодов класса и инструмента
        """Таблица текущих торгов

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param str param_name: Параметр
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}|{param_name}', 'id': trans_id, 'cmd': 'getParamEx', 't': ''})

    def get_param_ex2(self, class_code, sec_code, param_name, trans_id=0):  # 3.12.2 Функция предназначена для получения значений всех параметров биржевой информации из Таблицы текущих торгов с возможностью в дальнейшем отказаться от получения определенных параметров, заказанных с помощью функции ParamRequest
        """Таблица текущих торгов по инструменту с возможностью отказа от получения

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param str param_name: Параметр
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}|{param_name}', 'id': trans_id, 'cmd': 'getParamEx2', 't': ''})

    def get_param_ex2_bulk(self, class_sec_codes_params, trans_id=0):  # QUIK#
        """Таблица текущих торгов по инструментам с возможностью отказа от получения

        :param set[str] class_sec_codes_params: Список кодов режимов торгов, тикеров, параметров. Например: {'TQBR|SBER|SEC_SCALE', 'SPBFUT|CNYRUBF|SEC_PRICE_STEP'}
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': class_sec_codes_params, 'id': trans_id, 'cmd': 'getParamEx2Bulk', 't': ''})

    # 3.13 Функции для получения параметров таблицы "Клиентский портфель"

    def get_portfolio_info(self, firm_id, client_code, trans_id=0):  # 3.13.1 Функция предназначена для получения значений параметров таблицы Клиентский портфель, соответствующих идентификатору участника торгов firmid, коду клиента client_code и сроку расчетов limit_kind со значением 0
        """Клиентский портфель

        :param str firm_id: Код фирмы
        :param str client_code: Код клиента
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{firm_id}|{client_code}', 'id': trans_id, 'cmd': 'getPortfolioInfo', 't': ''})

    def get_portfolio_info_ex(self, firm_id, client_code, limit_kind, trans_id=0):  # 3.13.2 Функция предназначена для получения значений параметров таблицы Клиентский портфель, соответствующих идентификатору участника торгов firmid, коду клиента client_code и сроку расчетов limit_kind со значением, заданным пользователем.
        """Клиентский портфель по сроку расчетов

        :param str firm_id: Код фирмы
        :param str client_code: Код клиента
        :param int limit_kind: Срок расчетов
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{firm_id}|{client_code}|{limit_kind}', 'id': trans_id, 'cmd': 'getPortfolioInfoEx', 't': ''})

    # 3.14 Функции для получения параметров таблицы "Купить/Продать"

    # getBuySellInfo - 3.14.1. Параметры таблицы купить/продать
    # getBuySellInfoEx - 3.14.2. Параметры таблицы купить/продать с дополнительными полями вывода

    # 3.15 Функции для работы с таблицами Рабочего места QUIK

    # AddColumn - 3.15.1. Добавление колонки в таблицу
    # AllocTable - 3.15.2. Структура, описывающая таблицу
    # Clear - 3.15.3. Удаление содержимого таблицы
    # CreateWindow - 3.15.4. Создание окна таблицы
    # DeleteRow - 3.15.5. Удаление строки из таблицы
    # DestroyTable - 3.15.6. Закрытие окна таблицы
    # InsertRow - 3.15.7. Добавление строки в таблицу
    # IsWindowClosed - 3.15.8. Закрыто ли окно с таблицей
    # GetCell - 3.15.9. Данные ячейки таблицы
    # GetTableSize - 3.15.10. Кол-во строк и столбцов таблицы
    # GetWindowCaption - 3.15.11. Заголовок окна таблицы
    # GetWindowRect - 3.15.12. Координаты верхнего левого и правого нижнего углов таблицы
    # SetCell - 3.15.13. Установка значения ячейки таблицы
    # SetWindowCaption - 3.15.14. Установка заголовка окна таблицы
    # SetWindowPos - 3.15.15. Установка верхнего левого угла, и размеры таблицы
    # SetTableNotificationCallback - 3.15.16. Установка функции обратного вызова для обработки событий в таблице
    # RGB - 3.15.17. Преобразование каждого цвета в одно число для функци SetColor
    # SetColor - 3.15.18. Установка цвета ячейки, столбца или строки таблицы
    # Highlight - 3.15.19. Подсветка диапазона ячеек цветом фона и цветом текста на заданное время с плавным затуханием
    # SetSelectedRow - 3.15.20. Выделение строки таблицы

    # 3.16 Функции для работы с метками

    def add_label(self, price, cur_date, cur_time, qty, path, chart_tag, alignment, background, trans_id=0):  # 3.16.1 Добавляет метку с заданными параметрами
        """Добавление метки на график"""
        return self.process_request({'data': f'{price}|{cur_date}|{cur_time}|{qty}|{path}|{chart_tag}|{alignment}|{background}', 'id': trans_id, 'cmd': 'AddLabel', 't': ''})

    def del_label(self, chart_tag, label_id, trans_id=0):  # 3.16.2 Удаляет метку с заданными параметрами
        """Удаление метки с графика"""
        return self.process_request({'data': f'{chart_tag}|{label_id}', 'id': trans_id, 'cmd': 'DelLabel', 't': ''})

    def del_all_labels(self, chart_tag, trans_id=0):  # 3.16.3 Команда удаляет все метки на диаграмме с указанным графиком
        """Удаление всех меток с графика"""
        return self.process_request({'data': chart_tag, 'id': trans_id, 'cmd': 'DelAllLabels', 't': ''})

    def get_label_params(self, chart_tag, label_id, trans_id=0):  # 3.16.4 Команда позволяет получить параметры метки
        """Получение параметров метки"""
        return self.process_request({'data': f'{chart_tag}|{label_id}', 'id': trans_id, 'cmd': 'GetLabelParams', 't': ''})

    # SetLabelParams - 3.16.5. Установка параметров метки

    # 3.17 Функции для заказа стакана котировок

    def subscribe_level2_quotes(self, class_code, sec_code, trans_id=0):  # 3.17.1 Функция заказывает на сервер получение стакана по указанному классу и инструменту
        """Подписка на стакан

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        result = self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'Subscribe_Level_II_Quotes', 't': ''})
        subscription = {'subscription': 'quotes', 'class_code': class_code, 'sec_code': sec_code}  # Подписка
        if self.is_subscribed_level2_quotes(class_code, sec_code)['data'] and subscription not in self.subscriptions:  # Если есть подписка на стакан, но ее нет в списке подписок
            self.subscriptions.append(subscription)  # то добавляем подписку
        return result

    def unsubscribe_level2_quotes(self, class_code, sec_code, trans_id=0):  # 3.17.2 Функция отменяет заказ на получение с сервера стакана по указанному классу и инструменту
        """Отмена подписки на стакан

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        result = self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'Unsubscribe_Level_II_Quotes', 't': ''})
        subscription = {'subscription': 'quotes', 'class_code': class_code, 'sec_code': sec_code}  # Подписка
        if not self.is_subscribed_level2_quotes(class_code, sec_code)['data'] and subscription in self.subscriptions:  # Если нет подписки на стакан, но она есть в списке подписок
            self.subscriptions.remove(subscription)  # то удаляем подписку
        return result

    def is_subscribed_level2_quotes(self, class_code, sec_code, trans_id=0):  # 3.17.3 Функция позволяет узнать, заказан ли с сервера стакан по указанному классу и инструменту
        """Есть ли подписка на стакан

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'IsSubscribed_Level_II_Quotes', 't': ''})

    # 3.18 Функции для заказа параметров Таблицы текущих торгов

    def param_request(self, class_code, sec_code, param_name, trans_id=0):  # 3.18.1 Функция заказывает получение параметров Таблицы текущих торгов
        """Заказ получения таблицы текущих торгов по инструменту

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param str param_name: Параметр
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}|{param_name}', 'id': trans_id, 'cmd': 'paramRequest', 't': ''})

    def cancel_param_request(self, class_code, sec_code, param_name, trans_id=0):  # 3.18.2 Функция отменяет заказ на получение параметров Таблицы текущих торгов
        """Отмена заказа получения таблицы текущих торгов по инструменту

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param str param_name: Параметр
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{class_code}|{sec_code}|{param_name}', 'id': trans_id, 'cmd': 'cancelParamRequest', 't': ''})

    def param_request_bulk(self, class_sec_codes_params, trans_id=0):  # QUIK#
        """Заказ получения таблицы текущих торгов по инструментам

        :param set[str] class_sec_codes_params: Список кодов режимов торгов, тикеров, параметров. Например: {'TQBR|SBER|SEC_SCALE', 'SPBFUT|CNYRUBF|SEC_PRICE_STEP'}
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': class_sec_codes_params, 'id': trans_id, 'cmd': 'paramRequestBulk', 't': ''})

    def cancel_param_request_bulk(self, class_sec_codes_params, trans_id=0):  # QUIK#
        """Отмена заказа получения таблицы текущих торгов по инструментам

        :param set[str] class_sec_codes_params: Список кодов режимов торгов, тикеров, параметров. Например: {'TQBR|SBER|SEC_SCALE', 'SPBFUT|CNYRUBF|SEC_PRICE_STEP'}
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': class_sec_codes_params, 'id': trans_id, 'cmd': 'cancelParamRequestBulk', 't': ''})

    # 3.19 Функции для получения информации по единой денежной позиции

    def get_trd_acc_by_client_code(self, firm_id, client_code, trans_id=0):  # 3.19.1 Функция возвращает торговый счет срочного рынка, соответствующий коду клиента фондового рынка с единой денежной позицией
        """Торговый счет срочного рынка по коду клиента фондового рынка

        :param str firm_id: Код фирмы
        :param str client_code: Код клиента
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{firm_id}|{client_code}', 'id': trans_id, 'cmd': 'getTrdAccByClientCode', 't': ''})

    def get_client_code_by_trd_acc(self, firm_id, trade_account_id, trans_id=0):  # 3.19.2 Функция возвращает код клиента фондового рынка с единой денежной позицией, соответствующий торговому счету срочного рынка
        """Код клиента фондового рынка с единой денежной позицией по торговому счету срочного рынка

        :param str firm_id: Код фирмы
        :param str trade_account_id: Счет
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{firm_id}|{trade_account_id}', 'id': trans_id, 'cmd': 'getClientCodeByTrdAcc', 't': ''})

    def is_ucp_client(self, firm_id, client, trans_id=0):  # 3.19.3 Функция предназначена для получения признака, указывающего имеет ли клиент единую денежную позицию
        """Имеет ли клиент единую денежную позицию

        :param str firm_id: Код фирмы
        :param str client: Код клиента фондового рынка или торговый счет срочного рынка
        :param int trans_id: Код транзакции
        """
        return self.process_request({'data': f'{firm_id}|{client}', 'id': trans_id, 'cmd': 'IsUcpClient', 't': ''})

    # Запросы

    def process_request(self, request):
        """Отправка запроса в виде словаря и получение ответа в виде JSON из QUIK
        :param dict request: Запрос в виде словаря
        :returns: Ответ JSON
        """
        self.lock.acquire()  # Ставим блокировку. Если во время выполнения process_request к нему будет обращение из другого потока, то будем здесь ожидать, пока блокировка не будет снята
        raw_data = f'{request}\r\n'.replace("'", '"').encode('cp1251')  # Переводим: словарь -> строка, одинарные кавычки -> двойные, кодировка UTF8 -> Windows 1251
        self.socket_requests.sendall(raw_data)  # Отправляем запрос в QUIK
        fragments = []  # Гораздо быстрее получать ответ в виде списка фрагментов
        while True:  # Пока фрагменты есть в буфере
            fragment = self.socket_requests.recv(self.buffer_size)  # Читаем фрагмент из буфера
            fragments.append(fragment.decode('cp1251'))  # Переводим фрагмент в Windows кодировку 1251, добавляем в список
            if len(fragment) < self.buffer_size:  # Если в принятом фрагменте данных меньше чем размер буфера
                data = ''.join(fragments)  # Собираем список фрагментов в строку
                try:  # Бывает ситуация, когда данных приходит меньше, но это еще не конец данных
                    result = loads(data)  # Пробуем перевести ответ в формат JSON в кодировке Windows 1251
                    # self.logger.debug(f'process_request: Запрос: {raw_data} Ответ: {result}')  # Для отладки
                    self.lock.release()  # Снимаем блокировку с process_request
                    return result
                except JSONDecodeError:  # Если это еще не конец данных
                    pass  # то ждем фрагментов в буфере дальше

    # Подписки (функции обратного вызова)

    def default_handler(self, data):
        """Пустой обработчик события по умолчанию. Его можно заменить на пользовательский"""
        pass

    def callback_handler(self):
        """Поток обработки результатов функций обратного вызова"""
        callbacks = socket(AF_INET, SOCK_STREAM)  # Соединение для функций обратного вызова
        callbacks.connect((self.host, self.callbacks_port))  # Открываем соединение для функций обратного вызова
        fragments = []  # Будем получать ответ в виде списка фрагментов. Они могут быть разной длины. Ответ может состоять из нескольких фрагментов
        while True:  # Пока поток нужен
            while True:  # Пока есть что-то в буфере ответов
                if self.callback_exit_event.is_set():  # Если установлено событие выхода из потока
                    callbacks.close()  # то закрываем соединение для функций обратного вызова
                    return  # Выходим, дальше не продолжаем
                fragment = callbacks.recv(self.buffer_size)  # Читаем фрагмент из буфера
                fragments.append(fragment.decode('cp1251'))  # Переводим фрагмент в Windows кодировку 1251, добавляем в список
                if len(fragment) < self.buffer_size:  # Если в принятом фрагменте данных меньше чем размер буфера
                    break  # то, возможно, это был последний фрагмент, выходим из чтения буфера
            data = ''.join(fragments)  # Собираем список фрагментов в строку
            data_list = data.split('\n')  # Одновременно могут прийти несколько функций обратного вызова, разбираем их по одной
            fragments = []  # Сбрасываем фрагменты. Если последнюю строку не сможем разобрать, то занесем ее сюда
            for data in data_list:  # Пробегаемся по всем функциям обратного вызова
                if data == '':  # Если функция обратного вызова пустая
                    continue  # то ее не разбираем, переходим на следующую функцию, дальше не продолжаем
                try:  # Пробуем разобрать функцию обратного вызова
                    data = loads(data)  # Возвращаем полученный ответ в формате JSON
                except JSONDecodeError:  # Если разобрать не смогли (пришла не вся строка)
                    fragments.append(data)  # то, что не разобрали ставим в список фрагментов
                    break  # т.к. неполной может быть только последняя строка, то выходим из разбора функций обратного вызова
                # self.logger.debug(f'callback_handler: Пришли данные подписки {data["cmd"]} {data}')  # Для отладки
                # Разбираем функцию обратного вызова QUIK LUA
                if data['cmd'] == 'OnFirm':  # 1. Новая фирма
                    self.on_firm(data)
                elif data['cmd'] == 'OnAllTrade':  # 2. Получение обезличенной сделки
                    self.on_all_trade(data)
                elif data['cmd'] == 'OnTrade':  # 3. Получение новой / изменение существующей сделки
                    self.on_trade(data)
                elif data['cmd'] == 'OnOrder':  # 4. Получение новой / изменение существующей заявки
                    self.on_order(data)
                elif data['cmd'] == 'OnAccountBalance':  # 5. Изменение позиций по счету
                    self.on_account_balance(data)
                elif data['cmd'] == 'OnFuturesLimitChange':  # 6. Изменение ограничений по срочному рынку
                    self.on_futures_limit_change(data)
                elif data['cmd'] == 'OnFuturesLimitDelete':  # 7. Удаление ограничений по срочному рынку
                    self.on_futures_limit_delete(data)
                elif data['cmd'] == 'OnFuturesClientHolding':  # 8. Изменение позиции по срочному рынку
                    self.on_futures_client_holding(data)
                elif data['cmd'] == 'OnMoneyLimit':  # 9. Изменение денежной позиции
                    self.on_money_limit(data)
                elif data['cmd'] == 'OnMoneyLimitDelete':  # 10. Удаление денежной позиции
                    self.on_money_limit_delete(data)
                elif data['cmd'] == 'OnDepoLimit':  # 11. Изменение позиций по инструментам
                    self.on_depo_limit(data)
                elif data['cmd'] == 'OnDepoLimitDelete':  # 12. Удаление позиции по инструментам
                    self.on_depo_limit_delete(data)
                elif data['cmd'] == 'OnAccountPosition':  # 13. Изменение денежных средств
                    self.on_account_position(data)
                # on_neg_deal - 14. Получение новой / изменение существующей внебиржевой заявки
                # on_neg_trade - 15. Получение новой / изменение существующей сделки для исполнения
                elif data['cmd'] == 'OnStopOrder':  # 16. Получение новой / изменение существующей стоп заявки
                    self.on_stop_order(data)
                elif data['cmd'] == 'OnTransReply':  # 17. Ответ на транзакцию пользователя
                    self.on_trans_reply(data)
                elif data['cmd'] == 'OnParam':  # 18. Изменение текущих параметров
                    self.on_param(data)
                elif data['cmd'] == 'OnQuote':  # 19. Изменение стакана котировок
                    self.on_quote(data)
                elif data['cmd'] == 'OnDisconnected':  # 20. Отключение терминала от сервера QUIK
                    self.on_disconnected(data)
                elif data['cmd'] == 'OnConnected':  # 21. Соединение терминала с сервером QUIK
                    for subscription in self.subscriptions:  # Пробегаемся по всем подпискам
                        class_code = subscription['class_code']  # Код режима торгов
                        sec_code = subscription['sec_code']  # Тикер
                        if subscription['subscription'] == 'quotes' and not self.is_subscribed_level2_quotes(class_code, sec_code)['data']:  # Если подписка на стакан и ее нет в QUIK
                            self.subscribe_level2_quotes(class_code, sec_code)  # то переподписываемся на стакан
                            self.logger.debug(f'Повторная подписка на стакан: {class_code}.{sec_code}')
                        elif subscription['subscription'] == 'candles':  # Если подписка на свечки
                            interval = subscription['interval']  # Кол-во в минутах
                            param = subscription['param']  # Необязательный параметр
                            if not self.is_subscribed(class_code, sec_code, interval, param)['data']:  # и ее нет в QUIK'
                                self.subscribe_to_candles(class_code, sec_code, interval, param)  # то подписываемся на свечки
                                self.logger.debug(f'Повторная подписка на бары: {class_code}.{sec_code} {interval} {param}')
                    self.on_connected(data)
                # on_clean_up - 22. Смена сервера QUIK / Пользователя / Сессии
                elif data['cmd'] == 'OnClose':  # 23. Закрытие терминала QUIK
                    self.on_close(data)
                elif data['cmd'] == 'OnStop':  # 24. Остановка LUA скрипта в терминале QUIK / закрытие терминала QUIK
                    self.on_stop(data)
                elif data['cmd'] == 'OnInit':  # 25. Запуск LUA скрипта в терминале QUIK
                    self.on_init(data)
                # Разбираем функции обратного вызова QUIK#
                elif data['cmd'] == 'NewCandle':  # Получение новой свечки
                    self.on_new_candle(data)
                elif data['cmd'] == 'lua_error':  # Получено сообщение об ошибке
                    self.on_error(data)

    # Выход и закрытие

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из класса, например, с with"""
        self.close_connection_and_thread()  # Закрываем соединение для запросов и поток обработки функций обратного вызова

    def __del__(self):
        self.close_connection_and_thread()  # Закрываем соединение для запросов и поток обработки функций обратного вызова

    def close_connection_and_thread(self):
        """Закрытие соединения для запросов и потока обработки функций обратного вызова"""
        self.socket_requests.close()  # Закрываем соединение для запросов
        self.callback_exit_event.set()  # Останавливаем поток обработки функций обратного вызова

    # Функции конвертации

    def dataname_to_class_sec_codes(self, dataname) -> Union[tuple[str, str], None]:
        """Код режима торгов и тикер из названия тикера

        :param str dataname: Название тикера
        :return: Код режима торгов и тикер
        """
        symbol_parts = dataname.split('.')  # По разделителю пытаемся разбить тикер на части
        if len(symbol_parts) >= 2:  # Если тикер задан в формате <Код режима торгов>.<Код тикера>
            class_code = symbol_parts[0]  # Код режима торгов
            sec_code = '.'.join(symbol_parts[1:])  # Код тикера
        else:  # Если тикер задан без кода режима торгов
            sec_code = dataname  # Код тикера
            class_codes = self.get_classes_list()['data']  # Все режимы торгов через запятую
            class_code = self.get_security_class(class_codes, sec_code)['data']  # Код режима торгов из всех режимов по тикеру
        return class_code, sec_code

    @staticmethod
    def class_sec_codes_to_dataname(class_code, sec_code):
        """Название тикера из кода режима торгов и кода тикера

        :param str class_code: Код режима торгов
        :param str sec_code: Код тикера
        :return: Название тикера
        """
        return f'{class_code}.{sec_code}'

    def get_symbol_info(self, class_code, sec_code, reload=False):
        """Спецификация тикера

        :param str class_code: Код режима торгов
        :param str sec_code: Код тикера
        :param bool reload: Получить информацию из QUIK
        :return: Значение из кэша/QUIK или None, если тикер не найден
        """
        if reload or (class_code, sec_code) not in self.symbols:  # Если нужно получить информацию из QUIK или нет информации о тикере в справочнике
            symbol_info = self.get_security_info(class_code, sec_code)  # Получаем информацию о тикере из QUIK
            if 'data' not in symbol_info:  # Если ответ не пришел (возникла ошибка). Например, для опциона
                self.logger.error(f'Информация о {self.class_sec_codes_to_dataname(class_code, sec_code)} не найдена')
                return None  # то возвращаем пустое значение
            self.symbols[(class_code, sec_code)] = symbol_info['data']  # Заносим информацию о тикере в справочник
        return self.symbols[(class_code, sec_code)]  # Возвращаем значение из справочника

    @staticmethod
    def timeframe_to_quik_timeframe(tf) -> tuple[int, bool]:
        """Перевод временнОго интервала во временной интервал QUIK

        :param str tf: Временной интервал https://ru.wikipedia.org/wiki/Таймфрейм
        :return: Временной интервал QUIK, внутридневной интервал
        """
        if 'MN' in tf:  # Месячный временной интервал
            return 23200, False
        if tf[0:1] == 'W':  # Недельный временной интервал
            return 10080, False
        if tf[0:1] == 'D':  # Дневной временной интервал
            return 1440, False
        if tf[0:1] == 'M':  # Минутный временной интервал
            minutes = int(tf[1:])  # Кол-во минут
            if minutes in (1, 2, 3, 4, 5, 6, 10, 15, 20, 30, 60, 120, 240):  # Разрешенные временнЫе интервалы в QUIK
                return minutes, True
        raise NotImplementedError  # С остальными временнЫми интервалами не работаем, в т.ч. и с тиками (интервал = 0)

    @staticmethod
    def quik_timeframe_to_timeframe(tf) -> tuple[str, bool]:
        """Перевод временнОго интервала QUIK во временной интервал

        :param int tf: Временной интервал QUIK
        :return: Временной интервал https://ru.wikipedia.org/wiki/Таймфрейм, внутридневной интервал
        """
        if tf == 23200:  # Месячный временной интервал
            return 'MN1', False
        if tf == 10080:  # Недельный временной интервал
            return 'W1', False
        if tf == 1440:  # Дневной временной интервал
            return 'D1', False
        if tf in (1, 2, 3, 4, 5, 6, 10, 15, 20, 30, 60, 120, 240):  # Минутный временной интервал
            return f'M{tf}', True
        raise NotImplementedError  # С остальными временнЫми интервалами не работаем , в т.ч. и с тиками (интервал = 0)

    def price_to_valid_price(self, class_code, sec_code, quik_price) -> Union[int, float]:
        """Перевод цены в цену, которую примет QUIK в заявке

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param float quik_price: Цена в QUIK
        :return: Цена, которую примет QUIK в зявке
        """
        si = self.get_symbol_info(class_code, sec_code)  # Спецификация тикера
        min_price_step = si['min_price_step']  # Шаг цены
        valid_price = quik_price // min_price_step * min_price_step  # Цена должна быть кратна шагу цены
        scale = si['scale']  # Кол-во десятичных знаков
        if scale > 0:  # Если задано кол-во десятичных знаков
            return round(valid_price, scale)  # то округляем цену кратно шага цены, возвращаем ее
        return int(valid_price)  # Если кол-во десятичных знаков = 0, то переводим цену в целое число

    def price_to_quik_price(self, class_code, sec_code, price) -> Union[int, float]:
        """Перевод цены в рублях за штуку в цену QUIK

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param float price: Цена в рублях за штуку
        :return: Цена в QUIK
        """
        si = self.get_symbol_info(class_code, sec_code)  # Спецификация тикера
        if not si:  # Если тикер не найден
            return price  # то цена не изменяется
        min_price_step = si['min_price_step']  # Шаг цены
        quik_price = price  # Изначально считаем, что цена не изменится
        if class_code in ('TQOB', 'TQCB', 'TQRD', 'TQIR'):  # Для облигаций (Т+ Гособлигации, Т+ Облигации, Т+ Облигации Д, Т+ Облигации ПИР)
            quik_price = price * 100 / si['face_value']  # Пункты цены для котировок облигаций представляют собой проценты номинала облигации
        elif class_code == 'SPBFUT':  # Для рынка фьючерсов
            lot_size = si['lot_size']  # Лот
            step_price = float(self.get_param_ex(class_code, sec_code, 'STEPPRICE')['data']['param_value'])  # Стоимость шага цены
            if lot_size > 1 and step_price:  # Если есть лот и стоимость шага цены
                lot_price = price * lot_size  # Цена в рублях за лот
                quik_price = lot_price * min_price_step / step_price  # Цена в рублях за штуку
        return self.price_to_valid_price(class_code, sec_code, quik_price)  # Возращаем цену, которую примет QUIK в заявке

    def quik_price_to_price(self, class_code, sec_code, quik_price) -> float:
        """Перевод цены QUIK в цену в рублях за штуку

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param float quik_price: Цена в QUIK
        :return: Цена в рублях за штуку
        """
        si = self.get_symbol_info(class_code, sec_code)  # Спецификация тикера
        if not si:  # Если тикер не найден
            return quik_price  # то цена не изменяется
        if class_code in ('TQOB', 'TQCB', 'TQRD', 'TQIR'):  # Для облигаций (Т+ Гособлигации, Т+ Облигации, Т+ Облигации Д, Т+ Облигации ПИР)
            return quik_price / 100 * si['face_value']  # Пункты цены для котировок облигаций представляют собой проценты номинала облигации
        elif class_code == 'SPBFUT':  # Для рынка фьючерсов
            lot_size = si['lot_size']  # Лот
            step_price = float(self.get_param_ex(class_code, sec_code, 'STEPPRICE')['data']['param_value'])  # Стоимость шага цены
            if lot_size > 1 and step_price:  # Если есть лот и стоимость шага цены
                min_price_step = si['min_price_step']  # Шаг цены
                lot_price = quik_price // min_price_step * step_price  # Цена за лот
                return lot_price / lot_size  # Цена за штуку
        return quik_price  # В остальных случаях цена не изменяется

    def lots_to_size(self, class_code, sec_code, lots) -> int:
        """Перевод лотов в штуки

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int lots: Кол-во лотов
        :return: Кол-во штук
        """
        si = self.get_symbol_info(class_code, sec_code)  # Спецификация тикера
        if si:  # Если тикер найден
            lot_size = si['lot_size']  # Кол-во штук в лоте
            if lot_size:  # Если задано кол-во штук в лоте
                return int(lots * lot_size)  # то возвращаем кол-во в штуках
        return lots  # В остальных случаях возвращаем кол-во в лотах

    def size_to_lots(self, class_code, sec_code, size) -> int:
        """Перевод штуки в лоты

        :param str class_code: Код режима торгов
        :param str sec_code: Тикер
        :param int size: Кол-во штук
        :return: Кол-во лотов
        """
        si = self.get_symbol_info(class_code, sec_code)  # Спецификация тикера
        if si:  # Если тикер найден
            lot_size = int(si['lot_size'])  # Кол-во штук в лоте
            if lot_size:  # Если задано кол-во штук
                return size // lot_size  # то возвращаем кол-во в лотах
        return size  # В остальных случаях возвращаем кол-во в штуках
