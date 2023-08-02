from socket import socket, AF_INET, SOCK_STREAM  # Обращаться к LUA скриптам QuikSharp будем через соединения
from threading import current_thread, Thread  # Результат работы функций обратного вызова будем получать в отдельном потоке
from json import loads  # Принимать данные в QUIK будем через JSON
from json.decoder import JSONDecodeError  # Ошибка декодирования JSON


# class Singleton(type):
#     """Метакласс для создания Singleton классов"""
#     def __init__(cls, *args, **kwargs):
#         """Инициализация класса"""
#         super(Singleton, cls).__init__(*args, **kwargs)  # то создаем зкземпляр класса
#         cls._singleton = None  # Экземпляра класса еще нет
#
#     def __call__(cls, *args, **kwargs):
#         """Вызов класса"""
#         if cls._singleton is None:  # Если класса нет в экземплярах класса
#             cls._singleton = super(Singleton, cls).__call__(*args, **kwargs)
#         return cls._singleton  # Возвращаем экземпляр класса
#
#
# class QuikPy(metaclass=Singleton):  # Singleton класс
class QuikPy:
    """Работа с Quik из Python через LUA скрипты QuikSharp https://github.com/finsight/QUIKSharp/tree/master/src/QuikSharp/lua
     На основе Документации по языку LUA в QUIK из https://arqatech.com/ru/support/files/
     """
    buffer_size = 1048576  # Размер буфера приема в байтах (1 МБайт)
    socket_requests = None  # Соединение для запросов
    callback_thread = None  # Поток обработки функций обратного вызова

    def DefaultHandler(self, data):
        """Пустой обработчик события по умолчанию. Его можно заменить на пользовательский"""
        pass

    def callback_handler(self):
        """Поток обработки результатов функций обратного вызова"""
        callbacks = socket(AF_INET, SOCK_STREAM)  # Соединение для функций обратного вызова
        callbacks.connect((self.Host, self.CallbacksPort))  # Открываем соединение для функций обратного вызова
        thread = current_thread()  # Получаем текущий поток
        fragments = []  # Будем получать ответ в виде списка фрагментов. Они могут быть разной длины. Ответ может состоять из нескольких фрагментов
        while getattr(thread, 'process', True):  # Пока поток нужен
            while True:  # Пока есть что-то в буфере ответов
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
                    break  # т.к. неполной может быть только последняя строка, то выходим из разбора функций обратного выходва

                # Разбираем функцию обратного вызова QUIK LUA
                if data['cmd'] == 'OnFirm':  # 1. Новая фирма
                    self.OnFirm(data)
                elif data['cmd'] == 'OnAllTrade':  # 2. Получение обезличенной сделки
                    self.OnAllTrade(data)
                elif data['cmd'] == 'OnTrade':  # 3. Получение новой / изменение существующей сделки
                    self.OnTrade(data)
                elif data['cmd'] == 'OnOrder':  # 4. Получение новой / изменение существующей заявки
                    self.OnOrder(data)
                elif data['cmd'] == 'OnAccountBalance':  # 5. Изменение позиций по счету
                    self.OnAccountBalance(data)
                elif data['cmd'] == 'OnFuturesLimitChange':  # 6. Изменение ограничений по срочному рынку
                    self.OnFuturesLimitChange(data)
                elif data['cmd'] == 'OnFuturesLimitDelete':  # 7. Удаление ограничений по срочному рынку
                    self.OnFuturesLimitDelete(data)
                elif data['cmd'] == 'OnFuturesClientHolding':  # 8. Изменение позиции по срочному рынку
                    self.OnFuturesClientHolding(data)
                elif data['cmd'] == 'OnMoneyLimit':  # 9. Изменение денежной позиции
                    self.OnMoneyLimit(data)
                elif data['cmd'] == 'OnMoneyLimitDelete':  # 10. Удаление денежной позиции
                    self.OnMoneyLimitDelete(data)
                elif data['cmd'] == 'OnDepoLimit':  # 11. Изменение позиций по инструментам
                    self.OnDepoLimit(data)
                elif data['cmd'] == 'OnDepoLimitDelete':  # 12. Удаление позиции по инструментам
                    self.OnDepoLimitDelete(data)
                elif data['cmd'] == 'OnAccountPosition':  # 13. Изменение денежных средств
                    self.OnAccountPosition(data)
                # OnNegDeal - 14. Получение новой / изменение существующей внебиржевой заявки
                # OnNegTrade - 15. Получение новой / изменение существующей сделки для исполнения
                elif data['cmd'] == 'OnStopOrder':  # 16. Получение новой / изменение существующей стоп-заявки
                    self.OnStopOrder(data)
                elif data['cmd'] == 'OnTransReply':  # 17. Ответ на транзакцию пользователя
                    self.OnTransReply(data)
                elif data['cmd'] == 'OnParam':  # 18. Изменение текущих параметров
                    self.OnParam(data)
                elif data['cmd'] == 'OnQuote':  # 19. Изменение стакана котировок
                    self.OnQuote(data)
                elif data['cmd'] == 'OnDisconnected':  # 20. Отключение терминала от сервера QUIK
                    self.OnDisconnected(data)
                elif data['cmd'] == 'OnConnected':  # 21. Соединение терминала с сервером QUIK
                    self.OnConnected(data)
                # OnCleanUp - 22. Смена сервера QUIK / Пользователя / Сессии
                elif data['cmd'] == 'OnClose':  # 23. Закрытие терминала QUIK
                    self.OnClose(data)
                elif data['cmd'] == 'OnStop':  # 24. Остановка LUA скрипта в терминале QUIK / закрытие терминала QUIK
                    self.OnStop(data)
                elif data['cmd'] == 'OnInit':  # 25. Запуск LUA скрипта в терминале QUIK
                    self.OnInit(data)
                # Разбираем функции обратного вызова QuikSharp
                elif data['cmd'] == 'NewCandle':  # Получение новой свечки
                    self.OnNewCandle(data)
                elif data['cmd'] == 'OnError':  # Получено сообщение об ошибке
                    self.OnError(data)
        callbacks.close()  # Закрываем соединение для ответов

    def process_request(self, request):
        """Отправляем запрос в QUIK, получаем ответ из QUIK"""
        # Issue 13. В QUIK некорректно отображаются русские буквы UTF8
        raw_data = f'{request}\r\n'.replace("'", '"').encode('cp1251')  # Переводим в кодировку Windows 1251
        self.socket_requests.sendall(raw_data)  # Отправляем запрос в QUIK
        fragments = []  # Гораздо быстрее получать ответ в виде списка фрагментов
        while True:  # Пока фрагменты есть в буфере
            fragment = self.socket_requests.recv(self.buffer_size)  # Читаем фрагмент из буфера
            fragments.append(fragment.decode('cp1251'))  # Переводим фрагмент в Windows кодировку 1251, добавляем в список
            if len(fragment) < self.buffer_size:  # Если в принятом фрагменте данных меньше чем размер буфера
                data = ''.join(fragments)  # Собираем список фрагментов в строку
                try:  # Бывает ситуация, когда данных приходит меньше, но это еще не конец данных
                    return loads(data)  # Попробуем вернуть ответ в формате JSON в Windows кодировке 1251
                except JSONDecodeError:  # Если это еще не конец данных
                    pass  # то ждем фрагментов в буфере дальше

    # Инициализация и вход

    def __init__(self, host='127.0.0.1', requests_port=34130, callbacks_port=34131):
        """Инициализация"""
        # 2.2. Функции обратного вызова
        self.OnFirm = self.DefaultHandler  # 1. Новая фирма
        self.OnAllTrade = self.DefaultHandler  # 2. Получение обезличенной сделки
        self.OnTrade = self.DefaultHandler  # 3. Получение новой / изменение существующей сделки
        self.OnOrder = self.DefaultHandler  # 4. Получение новой / изменение существующей заявки
        self.OnAccountBalance = self.DefaultHandler  # 5. Изменение позиций
        self.OnFuturesLimitChange = self.DefaultHandler  # 6. Изменение ограничений по срочному рынку
        self.OnFuturesLimitDelete = self.DefaultHandler  # 7. Удаление ограничений по срочному рынку
        self.OnFuturesClientHolding = self.DefaultHandler  # 8. Изменение позиции по срочному рынку
        self.OnMoneyLimit = self.DefaultHandler  # 9. Изменение денежной позиции
        self.OnMoneyLimitDelete = self.DefaultHandler  # 10. Удаление денежной позиции
        self.OnDepoLimit = self.DefaultHandler  # 11. Изменение позиций по инструментам
        self.OnDepoLimitDelete = self.DefaultHandler  # 12. Удаление позиции по инструментам
        self.OnAccountPosition = self.DefaultHandler  # 13. Изменение денежных средств
        # OnNegDeal - 14. Получение новой / изменение существующей внебиржевой заявки
        # OnNegTrade - 15. Получение новой / изменение существующей сделки для исполнения
        self.OnStopOrder = self.DefaultHandler  # 16. Получение новой / изменение существующей стоп-заявки
        self.OnTransReply = self.DefaultHandler  # 17. Ответ на транзакцию пользователя
        self.OnParam = self.DefaultHandler  # 18. Изменение текущих параметров
        self.OnQuote = self.DefaultHandler  # 19. Изменение стакана котировок
        self.OnDisconnected = self.DefaultHandler  # 20. Отключение терминала от сервера QUIK
        self.OnConnected = self.DefaultHandler  # 21. Соединение терминала с сервером QUIK
        # OnCleanUp - 22. Смена сервера QUIK / Пользователя / Сессии
        self.OnClose = self.DefaultHandler  # 23. Закрытие терминала QUIK
        self.OnStop = self.DefaultHandler  # 24. Остановка LUA скрипта в терминале QUIK / закрытие терминала QUIK
        self.OnInit = self.DefaultHandler  # 25. Запуск LUA скрипта в терминале QUIK

        # Функции обратного вызова QuikSharp
        self.OnNewCandle = self.DefaultHandler  # Получение новой свечки
        self.OnError = self.DefaultHandler  # Получено сообщение об ошибке

        self.Host = host  # IP адрес или название хоста
        self.RequestsPort = requests_port  # Порт для отправки запросов и получения ответов
        self.CallbacksPort = callbacks_port  # Порт для функций обратного вызова
        self.socket_requests = socket(AF_INET, SOCK_STREAM)  # Создаем соединение для запросов
        self.socket_requests.connect((self.Host, self.RequestsPort))  # Открываем соединение для запросов

        self.callback_thread = Thread(target=self.callback_handler, name='CallbackThread')  # Создаем поток обработки функций обратного вызова
        self.callback_thread.start()  # Запускаем поток

    def __enter__(self):
        """Вход в класс, например, с with"""
        return self

    # Фукнции связи с QuikSharp
    
    def Ping(self, trans_id=0):
        """Проверка соединения. Отправка ping. Получение pong"""
        return self.process_request({'data': 'Ping', 'id': trans_id, 'cmd': 'ping', 't': ''})

    def Echo(self, message, trans_id=0):
        """Эхо. Отправка и получение одного и того же сообщения"""
        return self.process_request({'data': message, 'id': trans_id, 'cmd': 'echo', 't': ''})

    def DivideStringByZero(self, trans_id=0):
        """Тест обработки ошибок. Выполняется деление на 0 с выдачей ошибки"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'divide_string_by_zero', 't': ''})

    def IsQuik(self, trans_id=0):
        """Скрипт запущен в Квике"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'is_quik', 't': ''})

    # 2.1 Сервисные функции

    def IsConnected(self, trans_id=0):  # 1
        """Состояние подключения терминала к серверу QUIK. Возвращает 1 - подключено / 0 - не подключено"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'isConnected', 't': ''})

    def GetScriptPath(self, trans_id=0):  # 2
        """Путь скрипта без завершающего обратного слэша"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getScriptPath', 't': ''})

    def GetInfoParam(self, params, trans_id=0):  # 3
        """Значения параметров информационного окна"""
        return self.process_request({'data': params, 'id': trans_id, 'cmd': 'getInfoParam', 't': ''})

    # message - 4. Сообщение в терминале QUIK. Реализовано в виде 3-х отдельных функций в QuikSharp

    def Sleep(self, time, trans_id=0):  # 5
        """Приостановка скрипта. Время в миллисекундах"""
        return self.process_request({'data': time, 'id': trans_id, 'cmd': 'sleep', 't': ''})

    def GetWorkingFolder(self, trans_id=0):  # 6
        """Путь к info.exe, исполняющего скрипт без завершающего обратного слэша"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getWorkingFolder', 't': ''})

    def PrintDbgStr(self, message, trans_id=0):  # 7
        """Вывод отладочной информации. Можно посмотреть с помощью DebugView"""
        return self.process_request({'data': message, 'id': trans_id, 'cmd': 'PrintDbgStr', 't': ''})

    # sysdate - 8. Системные дата и время
    # isDarkTheme - 9. Тема оформления. true - тёмная, false - светлая

    # Сервисные функции QuikSharp
    
    def MessageInfo(self, message, trans_id=0):  # В QUIK LUA message icon_type=1
        """Отправка информационного сообщения в терминал QUIK"""
        return self.process_request({'data': message, 'id': trans_id, 'cmd': 'message', 't': ''})

    def MessageWarning(self, message, trans_id=0):  # В QUIK LUA message icon_type=2
        """Отправка сообщения с предупреждением в терминал QUIK"""
        return self.process_request({'data': message, 'id': trans_id, 'cmd': 'warning_message', 't': ''})

    def MessageError(self, message, trans_id=0):  # В QUIK LUA message icon_type=3
        """Отправка сообщения об ошибке в терминал QUIK"""
        return self.process_request({'data': message, 'id': trans_id, 'cmd': 'error_message', 't': ''})

    # 3.1. Функции для обращения к строкам произвольных таблиц

    # getItem - 1. Строка таблицы
    # getOrderByNumber - 2. Заявка
    # getNumberOf - 3. Кол-во записей в таблице
    # SearchItems - 4. Быстрый поиск по таблице заданной функцией поиска

    # Функции для обращения к строкам произвольных таблиц QuikSharp

    def GetTradeAccounts(self, trans_id=0):
        """Торговые счета, у которых указаны поддерживаемые классы инструментов"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getTradeAccounts', 't': ''})

    def GetTradeAccount(self, class_code, trans_id=0):
        """Торговый счет для запрашиваемого кода класса"""
        return self.process_request({'data': class_code, 'id': trans_id, 'cmd': 'getTradeAccount', 't': ''})
        
    def GetAllOrders(self, trans_id=0):
        """Таблица заявок (вся)"""
        return self.process_request({'data': f'', 'id': trans_id, 'cmd': 'get_orders', 't': ''})

    def GetOrders(self, class_code, sec_code, trans_id=0):
        """Таблица заявок (по инструменту)"""
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'get_orders', 't': ''})

    def GetOrderByNumber(self, order_id, trans_id=0):
        """Заявка по номеру"""
        return self.process_request({'data': order_id, 'id': trans_id, 'cmd': 'getOrder_by_Number', 't': ''})

    def GetOrderById(self, class_code, sec_code, order_trans_id, trans_id=0):
        """Заявка по инструменту и Id транзакции"""
        return self.process_request({'data': f'{class_code}|{sec_code}|{order_trans_id}', 'id': trans_id, 'cmd': 'getOrder_by_ID', 't': ''})

    def GetOrderByClassNumber(self, class_code, order_id, trans_id=0):
        """Заявка по классу инструмента и номеру"""
        return self.process_request({'data': f'{class_code}|{order_id}', 'id': trans_id, 'cmd': 'getOrder_by_Number', 't': ''})

    def GetMoneyLimits(self, trans_id=0):
        """Все денежные лимиты"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getMoneyLimits', 't': ''})

    def GetClientCode(self, trans_id=0):
        """Основной (первый) код клиента"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getClientCode', 't': ''})

    def GetClientCodes(self, trans_id=0):
        """Все коды клиента"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getClientCodes', 't': ''})

    def GetAllDepoLimits(self, trans_id=0):
        """Лимиты по бумагам (всем)"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'get_depo_limits', 't': ''})

    def GetDepoLimits(self, sec_code, trans_id=0):
        """Лимиты по бумагам (по инструменту)"""
        return self.process_request({'data': sec_code, 'id': trans_id, 'cmd': 'get_depo_limits', 't': ''})

    def GetAllTrades(self, trans_id=0):
        """Таблица сделок (вся)"""
        return self.process_request({'data': f'', 'id': trans_id, 'cmd': 'get_trades', 't': ''})

    def GetTrades(self, class_code, sec_code, trans_id=0):
        """Таблица сделок (по инструменту)"""
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'get_trades', 't': ''})

    def GetTradesByOrderNumber(self, order_num, trans_id=0):
        """Таблица сделок по номеру заявки"""
        return self.process_request({'data': order_num, 'id': trans_id, 'cmd': 'get_Trades_by_OrderNumber', 't': ''})

    def GetAllStopOrders(self, trans_id=0):
        """Стоп заявки (все)"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'get_stop_orders', 't': ''})

    def GetStopOrders(self, class_code, sec_code, trans_id=0):
        """Стоп заявки (по инструменту)"""
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'get_stop_orders', 't': ''})

    def GetAllTrade(self, trans_id=0):
        """Таблица обезличенных сделок (вся)"""
        return self.process_request({'data': f'', 'id': trans_id, 'cmd': 'get_all_trades', 't': ''})

    def GetTrade(self, class_code, sec_code, trans_id=0):
        """Таблица обезличенных сделок (по инструменту)"""
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'get_all_trades', 't': ''})

    # 3.2 Функции для обращения к спискам доступных параметров

    def GetClassesList(self, trans_id=0):  # 1
        """Список классов"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getClassesList', 't': ''})

    def GetClassInfo(self, class_code, trans_id=0):  # 2
        """Информация о классе"""
        return self.process_request({'data': class_code, 'id': trans_id, 'cmd': 'getClassInfo', 't': ''})

    def GetClassSecurities(self, class_code, trans_id=0):  # 3
        """Список инструментов класса"""
        return self.process_request({'data': class_code, 'id': trans_id, 'cmd': 'getClassSecurities', 't': ''})
    
    # Функции для обращения к спискам доступных параметров QuikSharp

    def GetOptionBoard(self, class_code, sec_code, trans_id=0):
        """Доска опционов"""
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'getOptionBoard', 't': ''})

    # 3.3 Функции для получения информации по денежным средствам

    def GetMoney(self, client_code, firm_id, tag, curr_code, trans_id=0):  # 1
        """Денежные позиции"""
        return self.process_request({'data': f'{client_code}|{firm_id}|{tag}|{curr_code}', 'id': trans_id, 'cmd': 'getMoney', 't': ''})

    def GetMoneyEx(self, firm_id, client_code, tag, curr_code, limit_kind, trans_id=0):  # 2
        """Денежные позиции указанного типа"""
        return self.process_request({'data': f'{firm_id}|{client_code}|{tag}|{curr_code}|{limit_kind}', 'id': trans_id, 'cmd': 'getMoneyEx', 't': ''})

    # 3.4 Функции для получения позиций по инструментам

    def GetDepo(self, client_code, firm_id, sec_code, account, trans_id=0):  # 1
        """Позиции по инструментам"""
        return self.process_request({'data': f'{client_code}|{firm_id}|{sec_code}|{account}', 'id': trans_id, 'cmd': 'getDepo', 't': ''})

    def GetDepoEx(self, firm_id, client_code, sec_code, account, limit_kind, trans_id=0):  # 2
        """Позиции по инструментам указанного типа"""
        return self.process_request({'data': f'{firm_id}|{client_code}|{sec_code}|{account}|{limit_kind}', 'id': trans_id, 'cmd': 'getDepoEx', 't': ''})

    # 3.5 Функция для получения информации по фьючерсным лимитам

    def GetFuturesLimit(self, firm_id, account_id, limit_type, curr_code, trans_id=0):  # 1
        """Фьючерсные лимиты"""
        return self.process_request({'data': f'{firm_id}|{account_id}|{limit_type}|{curr_code}', 'id': trans_id, 'cmd': 'getFuturesLimit', 't': ''})

    # Функция для получения информации по фьючерсным лимитам QuikSharp

    def GetFuturesClientLimits(self, trans_id=0):
        """Все фьючерсные лимиты"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getFuturesClientLimits', 't': ''})

    # 3.6 Функция для получения информации по фьючерсным позициям

    def GetFuturesHolding(self, firm_id, account_id, sec_code, position_type, trans_id=0):  # 1
        """Фьючерсные позиции"""
        return self.process_request({'data': f'{firm_id}|{account_id}|{sec_code}|{position_type}', 'id': trans_id, 'cmd': 'getFuturesHolding', 't': ''})

    # Функция для получения информации по фьючерсным позициям QuikSharp

    def GetFuturesHoldings(self, trans_id=0):
        """Все фьючерсные позиции"""
        return self.process_request({'data': '', 'id': trans_id, 'cmd': 'getFuturesClientHoldings', 't': ''})

    # 3.7 Функция для получения информации по инструменту

    def GetSecurityInfo(self, class_code, sec_code, trans_id=0):  # 1
        """Информация по инструменту"""
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'getSecurityInfo', 't': ''})

    # Функция для получения информации по инструменту QuikSharp

    def GetSecurityInfoBulk(self, class_codes, sec_codes, trans_id=0):
        """Информация по инструментам"""
        return self.process_request({'data': f'{class_codes}|{sec_codes}', 'id': trans_id, 'cmd': 'getSecurityInfoBulk', 't': ''})

    def GetSecurityClass(self, classes_list, sec_code, trans_id=0):
        """Класс по коду инструмента из заданных классов"""
        return self.process_request({'data': f'{classes_list}|{sec_code}', 'id': trans_id, 'cmd': 'getSecurityClass', 't': ''})

    # 3.8 Функция для получения даты торговой сессии

    # getTradeDate - 1. Дата текущей торговой сессии

    # 3.9 Функция для получения стакана по указанному классу и инструменту

    def GetQuoteLevel2(self, class_code, sec_code, trans_id=0):  # 1
        """Стакан по классу и инструменту"""
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'GetQuoteLevel2', 't': ''})

    # 3.10 Функции для работы с графиками

    # getLinesCount - 1. Кол-во линий в графике

    def GetNumCandles(self, tag, trans_id=0):  # 2
        """Кол-во свечей по тэгу"""
        return self.process_request({'data': tag, 'id': trans_id, 'cmd': 'get_num_candles', 't': ''})

    # getCandlesByIndex - 3. Информация о свечках (реализовано в get_candles)
    # CreateDataSource - 4. Создание источника данных c функциями: (реализовано в get_candles_from_data_source)
    # - SetUpdateCallback - Привязка функции обратного вызова на изменение свечи
    # - O, H, L, C, V, T - Функции получения цен, объемов и времени
    # - Size - Функция кол-ва свечек в источнике данных
    # - Close - Функция закрытия источника данных. Терминал прекращает получать данные с сервера
    # - SetEmptyCallback - Функция сброса функции обратного вызова на изменение свечи

    # Функции для работы с графиками QuikSharp

    def GetCandles(self, tag, line, first_candle, count, trans_id=0):
        """Свечки по идентификатору графика"""
        return self.process_request({'data': f'{tag}|{line}|{first_candle}|{count}', 'id': trans_id, 'cmd': 'get_candles', 't': ''})

    def GetCandlesFromDataSource(self, class_code, sec_code, interval, count):  # ichechet - Добавлен выход по таймауту
        """Свечки"""
        return self.process_request({'data': f'{class_code}|{sec_code}|{interval}|{count}', 'id': '1', 'cmd': 'get_candles_from_data_source', 't': ''})

    def SubscribeToCandles(self, class_code, sec_code, interval, trans_id=0):
        """Подписка на свечки"""
        return self.process_request({'data': f'{class_code}|{sec_code}|{interval}', 'id': trans_id, 'cmd': 'subscribe_to_candles', 't': ''})

    def IsSubscribed(self, class_code, sec_code, interval, trans_id=0):
        """Есть ли подписка на свечки"""
        return self.process_request({'data': f'{class_code}|{sec_code}|{interval}', 'id': trans_id, 'cmd': 'is_subscribed', 't': ''})

    def UnsubscribeFromCandles(self, class_code, sec_code, interval, trans_id=0):
        """Отмена подписки на свечки"""
        return self.process_request({'data': f'{class_code}|{sec_code}|{interval}', 'id': trans_id, 'cmd': 'unsubscribe_from_candles', 't': ''})

    # 3.11 Функции для работы с заявками

    def SendTransaction(self, transaction, trans_id=0):  # 1
        """Отправка транзакции в торговую систему"""
        return self.process_request({'data': transaction, 'id': trans_id, 'cmd': 'sendTransaction', 't': ''})

    # CalcBuySell - 2. Максимальное кол-во лотов в заявке

    # 3.12 Функции для получения значений таблицы "Текущие торги"

    def GetParamEx(self, class_code, sec_code, param_name, trans_id=0):  # 1
        """Таблица текущих торгов"""
        return self.process_request({'data': f'{class_code}|{sec_code}|{param_name}', 'id': trans_id, 'cmd': 'getParamEx', 't': ''})

    def GetParamEx2(self, class_code, sec_code, param_name, trans_id=0):  # 2
        """Таблица текущих торгов по инструменту с возможностью отказа от получения"""
        return self.process_request({'data': f'{class_code}|{sec_code}|{param_name}', 'id': trans_id, 'cmd': 'getParamEx2', 't': ''})

    # Функция для получения значений таблицы "Текущие торги" QuikSharp

    def GetParamEx2Bulk(self, class_codes, sec_codes, param_names, trans_id=0):
        """Таблица текущих торгов по инструментам с возможностью отказа от получения"""
        return self.process_request({'data': f'{class_codes}|{sec_codes}|{param_names}', 'id': trans_id, 'cmd': 'getParamEx2Bulk', 't': ''})

    # 3.13 Функции для получения параметров таблицы "Клиентский портфель"

    def GetPortfolioInfo(self, firm_id, client_code, trans_id=0):  # 1
        """Клиентский портфель"""
        return self.process_request({'data': f'{firm_id}|{client_code}', 'id': trans_id, 'cmd': 'getPortfolioInfo', 't': ''})

    def GetPortfolioInfoEx(self, firm_id, client_code, limit_kind, trans_id=0):  # 2
        """Клиентский портфель по сроку расчетов"""
        return self.process_request({'data': f'{firm_id}|{client_code}|{limit_kind}', 'id': trans_id, 'cmd': 'getPortfolioInfoEx', 't': ''})

    # 3.14 Функции для получения параметров таблицы "Купить/Продать"

    # getBuySellInfo - 1. Параметры таблицы купить/продать
    # getBuySellInfoEx - 2. Параметры таблицы купить/продать с дополнительными полями вывода

    # 3.15 Функции для работы с таблицами Рабочего места QUIK

    # AddColumn - 1. Добавление колонки в таблицу
    # AllocTable - 2. Структура, описывающая таблицу
    # Clear - 3. Удаление содержимого таблицы
    # CreateWindow - 4. Создание окна таблицы
    # DeleteRow - 5. Удаление строки из таблицы
    # DestroyTable - 6. Закрытие окна таблицы
    # InsertRow - 7. Добавление строки в таблицу
    # IsWindowClosed - 8. Закрыто ли окно с таблицей
    # GetCell - 9. Данные ячейки таблицы
    # GetTableSize - 10. Кол-во строк и столбцов таблицы
    # GetWindowCaption - 11. Заголовок окна таблицы
    # GetWindowRect - 12. Координаты верхнего левого и правого нижнего углов таблицы
    # SetCell - 13. Установка значения ячейки таблицы
    # SetWindowCaption - 14. Установка заголовка окна таблицы
    # SetWindowPos - 15. Установка верхнего левого угла, и размеры таблицы
    # SetTableNotificationCallback - 16. Установка функции обратного вызова для обработки событий в таблице
    # RGB - 17. Преобразование каждого цвета в одно число для функци SetColor
    # SetColor - 18. Установка цвета ячейки, столбца или строки таблицы
    # Highlight - 19. Подсветка диапазона ячеек цветом фона и цветом текста на заданное время с плавным затуханием
    # SetSelectedRow - 20. Выделение строки таблицы

    # 3.16 Функции для работы с метками

    def AddLabel(self, price, cur_date, cur_time, qty, path, label_id, alignment, background, trans_id=0):  # 1
        """Добавление метки на график"""
        return self.process_request({'data': f'{price}|{cur_date}|{cur_time}|{qty}|{path}|{label_id}|{alignment}|{background}', 'id': trans_id, 'cmd': 'AddLabel', 't': ''})

    def DelLabel(self, chart_tag, label_id, trans_id=0):  # 2
        """Удаление метки с графика"""
        return self.process_request({'data': f'{chart_tag}|{label_id}', 'id': trans_id, 'cmd': 'DelLabel', 't': ''})

    def DelAllLabels(self, chart_tag, trans_id=0):  # 3
        """Удаление всех меток с графика"""
        return self.process_request({'data': chart_tag, 'id': trans_id, 'cmd': 'DelAllLabels', 't': ''})

    def GetLabelParams(self, chart_tag, label_id, trans_id=0):  # 4
        """Получение параметров метки"""
        return self.process_request({'data': f'{chart_tag}|{label_id}', 'id': trans_id, 'cmd': 'GetLabelParams', 't': ''})

    # SetLabelParams - 5. Установка параметров метки

    # 3.17 Функции для заказа стакана котировок

    def SubscribeLevel2Quotes(self, class_code, sec_code, trans_id=0):  # 1
        """Подписка на стакан по Классу|Коду бумаги"""
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'Subscribe_Level_II_Quotes', 't': ''})

    def UnsubscribeLevel2Quotes(self, class_code, sec_code, trans_id=0):  # 2
        """Отмена подписки на стакан по Классу|Коду бумаги"""
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'Unsubscribe_Level_II_Quotes', 't': ''})

    def IsSubscribedLevel2Quotes(self, class_code, sec_code, trans_id=0):  # 3
        """Есть ли подписка на стакан по Классу|Коду бумаги"""
        return self.process_request({'data': f'{class_code}|{sec_code}', 'id': trans_id, 'cmd': 'IsSubscribed_Level_II_Quotes', 't': ''})

    # 3.18 Функции для заказа параметров Таблицы текущих торгов

    def ParamRequest(self, class_code, sec_code, param_name, trans_id=0):  # 1
        """Заказ получения таблицы текущих торгов по инструменту"""
        return self.process_request({'data': f'{class_code}|{sec_code}|{param_name}', 'id': trans_id, 'cmd': 'paramRequest', 't': ''})

    def CancelParamRequest(self, class_code, sec_code, param_name, trans_id=0):  # 2
        """Отмена заказа получения таблицы текущих торгов по инструменту"""
        return self.process_request({'data': f'{class_code}|{sec_code}|{param_name}', 'id': trans_id, 'cmd': 'cancelParamRequest', 't': ''})

    # Функции для заказа параметров Таблицы текущих торгов QuikSharp

    def ParamRequestBulk(self, class_codes, sec_codes, param_names, trans_id=0):
        """Заказ получения таблицы текущих торгов по инструментам"""
        return self.process_request({'data': f'{class_codes}|{sec_codes}|{param_names}', 'id': trans_id, 'cmd': 'paramRequestBulk', 't': ''})

    def CancelParamRequestBulk(self, class_codes, sec_codes, param_names, trans_id=0):
        """Отмена заказа получения таблицы текущих торгов по инструментам"""
        return self.process_request({'data': f'{class_codes}|{sec_codes}|{param_names}', 'id': trans_id, 'cmd': 'cancelParamRequestBulk', 't': ''})

    # 3.19 Функции для получения информации по единой денежной позиции

    def GetTrdAccByClientCode(self, firm_id, client_code, trans_id=0):  # 1
        """Торговый счет срочного рынка по коду клиента фондового рынка"""
        return self.process_request({'data': f'{firm_id}|{client_code}', 'id': trans_id, 'cmd': 'getTrdAccByClientCode', 't': ''})

    def GetClientCodeByTrdAcc(self, firm_id, trade_account_id, trans_id=0):  # 2
        """Код клиента фондового рынка с единой денежной позицией по торговому счету срочного рынка"""
        return self.process_request({'data': f'{firm_id}|{trade_account_id}', 'id': trans_id, 'cmd': 'getClientCodeByTrdAcc', 't': ''})

    def IsUcpClient(self, firm_id, client, trans_id=0):  # 3
        """Имеет ли клиент единую денежную позицию"""
        return self.process_request({'data': f'{firm_id}|{client}', 'id': trans_id, 'cmd': 'IsUcpClient', 't': ''})

    # Выход и закрытие

    def CloseConnectionAndThread(self):
        """Закрытие соединения для запросов и потока обработки функций обратного вызова"""
        self.socket_requests.close()  # Закрываем соединение для запросов
        self.callback_thread.process = False  # Поток обработки функций обратного вызова больше не нужен

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из класса, например, с with"""
        self.CloseConnectionAndThread()  # Закрываем соединение для запросов и поток обработки функций обратного вызова

    def __del__(self):
        self.CloseConnectionAndThread()  # Закрываем соединение для запросов и поток обработки функций обратного вызова
