import socket  # Обращаться к LUA скриптам QuikSharp будем через соединения
import threading  # Результат работы функций обратного вызова будем получать в отдельном потоке
import json  # Передавать и принимать данные в QUIK будем через JSON


class Singleton(type):
    """Метакласс для создания Singleton классов"""
    def __init__(cls, *args, **kwargs):
        """Инициализация класса"""
        super(Singleton, cls).__init__(*args, **kwargs)
        cls._singleton = None  # Экземпляра класса еще нет

    def __call__(cls, *args, **kwargs):
        """Вызов класса"""
        if cls._singleton is None:  # Если класса нет в экземплярах класса
            cls._singleton  = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._singleton  # Возвращаем экземпляр класса


class QuikPy(metaclass=Singleton):  # Singleton класс
    """Работа с Quik из Python через LUA скрипты QuikSharp https://github.com/finsight/QUIKSharp/tree/master/src/QuikSharp/lua
     На основе Документации по языку LUA в QUIK из https://arqatech.com/ru/support/files/
     """
    bufferSize = 1048576  # Размер буфера приема в байтах (1 МБайт)
    socketRequests = None  # Соединение для запросов
    callbackThread = None  # Поток обработки функций обратного вызова

    def DefaultHandler(self, data):
        """Пустой обработчик события по умолчанию. Его можно заменить на пользовательский"""
        pass

    def CallbackHandler(self):
        """Поток обработки результатов функций обратного вызова"""
        socketCallbacks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Соединение для функций обратного вызова
        socketCallbacks.connect((self.Host, self.CallbacksPort))  # Открываем соединение для функций обратного вызова
        currentThread = threading.currentThread()  # Получаем текущий поток
        fragments = []  # Будем получать ответ в виде списка фрагментов. Они могут быть разной длины. Ответ может состоять из нескольких фрагментов
        while getattr(currentThread, 'process', True):  # Пока поток нужен
            while True:  # Пока есть что-то в буфере ответов
                fragment = socketCallbacks.recv(self.bufferSize)  # Читаем фрагмент из буфера
                fragments.append(fragment.decode('cp1251'))  # Переводим фрагмент в Windows кодировку 1251, добавляем в список
                if len(fragment) < self.bufferSize:  # Если в принятом фрагменте данных меньше чем размер буфера
                    break  # то, возможно, это был последний фрагмент, выходим из чтения буфера
            data = ''.join(fragments)  # Собираем список фрагментов в строку
            dataList = data.split('\n')  # Одновременно могут прийти несколько функций обратного вызова, разбираем их по одной
            fragments = []  # Сбрасываем фрагменты. Если последнюю строку не сможем разобрать, то занесем ее сюда
            for data in dataList:  # Пробегаемся по всем функциям обратного вызова
                if data == '':  # Если функция обратного вызова пустая
                    continue  # то ее не разбираем, переходим на следующую функцию, дальше не продолжаем
                try:  # Пробуем разобрать функцию обратного вызова
                    data = json.loads(data)  # Возвращаем полученный ответ в формате JSON
                except json.decoder.JSONDecodeError:  # Если разобрать не смогли (пришла не вся строка)
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
        socketCallbacks.close()  # Закрываем соединение для ответов

    def ProcessRequest(self, Request):
        """Отправляем запрос в QUIK, получаем ответ из QUIK"""
        rawData = json.dumps(Request)  # Переводим запрос в формат JSON
        self.socketRequests.sendall(f'{rawData}\r\n'.encode())  # Отправляем запрос в QUIK
        fragments = []  # Гораздо быстрее получать ответ в виде списка фрагментов
        while True:  # Пока фрагменты есть в буфере
            fragment = self.socketRequests.recv(self.bufferSize)  # Читаем фрагмент из буфера
            fragments.append(fragment.decode('cp1251'))  # Переводим фрагмент в Windows кодировку 1251, добавляем в список
            if len(fragment) < self.bufferSize:  # Если в принятом фрагменте данных меньше чем размер буфера
                data = ''.join(fragments)  # Собираем список фрагментов в строку
                try:  # Бывает ситуация, когда данных приходит меньше, но это еще не конец данных
                    return json.loads(data)  # Попробуем вернуть ответ в формате JSON в Windows кодировке 1251
                except json.decoder.JSONDecodeError:  # Если это еще не конец данных
                    pass  # то ждем фрагментов в буфере дальше

    # Инициализация и вход

    def __init__(self, Host='127.0.0.1', RequestsPort=34130, CallbacksPort=34131):
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

        self.Host = Host  # IP адрес или название хоста
        self.RequestsPort = RequestsPort  # Порт для отправки запросов и получения ответов
        self.CallbacksPort = CallbacksPort  # Порт для функций обратного вызова
        self.socketRequests = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Создаем соединение для запросов
        self.socketRequests.connect((self.Host, self.RequestsPort))  # Открываем соединение для запросов

        self.callbackThread = threading.Thread(target=self.CallbackHandler, name='CallbackThread')  # Создаем поток обработки функций обратного вызова
        self.callbackThread.start()  # Запускаем поток

    def __enter__(self):
        """Вход в класс, например, с with"""
        return self

    # Фукнции связи с QuikSharp
    
    def Ping(self, TransId=0):
        """Проверка соединения. Отправка ping. Получение pong"""
        return self.ProcessRequest({'data': 'Ping', 'id': TransId, 'cmd': 'ping', 't': ''})

    def Echo(self, Message, TransId=0):
        """Эхо. Отправка и получение одного и того же сообщения"""
        return self.ProcessRequest({'data': Message, 'id': TransId, 'cmd': 'echo', 't': ''})

    def DivideStringByZero(self, TransId=0):
        """Тест обработки ошибок. Выполняется деление на 0 с выдачей ошибки"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'divide_string_by_zero', 't': ''})

    def IsQuik(self, TransId=0):
        """Скрипт запущен в Квике"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'is_quik', 't': ''})

    # 2.1 Сервисные функции

    def IsConnected(self, TransId=0):  # 1
        """Состояние подключения терминала к серверу QUIK. Возвращает 1 - подключено / 0 - не подключено"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'isConnected', 't': ''})

    def GetScriptPath(self, TransId=0):  # 2
        """Путь скрипта без завершающего обратного слэша"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'getScriptPath', 't': ''})

    def GetInfoParam(self, Params, TransId=0):  # 3
        """Значения параметров информационного окна"""
        return self.ProcessRequest({'data': Params, 'id': TransId, 'cmd': 'getInfoParam', 't': ''})

    # message - 4. Сообщение в терминале QUIK. Реализовано в виде 3-х отдельных функций в QuikSharp

    def Sleep(self, Time, TransId=0):  # 5
        """Приостановка скрипта. Время в миллисекундах"""
        return self.ProcessRequest({'data': Time, 'id': TransId, 'cmd': 'sleep', 't': ''})

    def GetWorkingFolder(self, TransId=0):  # 6
        """Путь к info.exe, исполняющего скрипт без завершающего обратного слэша"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'getWorkingFolder', 't': ''})

    def PrintDbgStr(self, Message, TransId=0):  # 7
        """Вывод отладочной информации. Можно посмотреть с помощью DebugView"""
        return self.ProcessRequest({'data': Message, 'id': TransId, 'cmd': 'PrintDbgStr', 't': ''})

    # sysdate - 8. Системные дата и время
    # isDarkTheme - 9. Тема оформления. true - тёмная, false - светлая

    # Сервисные функции QuikSharp
    
    def MessageInfo(self, Message, TransId=0):  # В QUIK LUA message icon_type=1
        """Отправка информационного сообщения в терминал QUIK"""
        return self.ProcessRequest({'data': Message, 'id': TransId, 'cmd': 'message', 't': ''})

    def MessageWarning(self, Message, TransId=0):  # В QUIK LUA message icon_type=2
        """Отправка сообщения с предупреждением в терминал QUIK"""
        return self.ProcessRequest({'data': Message, 'id': TransId, 'cmd': 'warning_message', 't': ''})

    def MessageError(self, Message, TransId=0):  # В QUIK LUA message icon_type=3
        """Отправка сообщения об ошибке в терминал QUIK"""
        return self.ProcessRequest({'data': Message, 'id': TransId, 'cmd': 'error_message', 't': ''})

    # 3.1. Функции для обращения к строкам произвольных таблиц

    # getItem - 1. Строка таблицы
    # getOrderByNumber - 2. Заявка
    # getNumberOf - 3. Кол-во записей в таблице
    # SearchItems - 4. Быстрый поиск по таблице заданной функцией поиска

    # Функции для обращения к строкам произвольных таблиц QuikSharp

    def GetTradeAccounts(self, TransId=0):
        """Торговые счета, у которых указаны поддерживаемые классы инструментов"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'getTradeAccounts', 't': ''})

    def GetTradeAccount(self, ClassCode, TransId=0):
        """Торговый счет для запрашиваемого кода класса"""
        return self.ProcessRequest({'data': ClassCode, 'id': TransId, 'cmd': 'getTradeAccount', 't': ''})
        
    def GetAllOrders(self, TransId=0):
        """Таблица заявок (вся)"""
        return self.ProcessRequest({'data': f'', 'id': TransId, 'cmd': 'get_orders', 't': ''})

    def GetOrders(self, ClassCode, SecCode, TransId=0):
        """Таблица заявок (по инструменту)"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}', 'id': TransId, 'cmd': 'get_orders', 't': ''})

    def GetOrderByNumber(self, OrderId, TransId=0):
        """Заявка по номеру"""
        return self.ProcessRequest({'data': OrderId, 'id': TransId, 'cmd': 'getOrder_by_Number', 't': ''})

    def GetOrderById(self, ClassCode, SecCode, OrderTransId, TransId=0):
        """Заявка по инструменту и Id транзакции"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}|{OrderTransId}', 'id': TransId, 'cmd': 'getOrder_by_ID', 't': ''})

    def GetOrderByClassNumber(self, ClassCode, OrderId, TransId=0):
        """Заявка по классу инструмента и номеру"""
        return self.ProcessRequest({'data': f'{ClassCode}|{OrderId}', 'id': TransId, 'cmd': 'getOrder_by_Number', 't': ''})

    def GetMoneyLimits(self, TransId=0):
        """Все денежные лимиты"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'getMoneyLimits', 't': ''})

    def GetClientCode(self, TransId=0):
        """Основной (первый) код клиента"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'getClientCode', 't': ''})

    def GetClientCodes(self, TransId=0):
        """Все коды клиента"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'getClientCode', 't': ''})

    def GetAllDepoLimits(self, TransId=0):
        """Лимиты по бумагам (всем)"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'get_depo_limits', 't': ''})

    def GetDepoLimits(self, SecCode, TransId=0):
        """Лимиты по бумагам (по инструменту)"""
        return self.ProcessRequest({'data': SecCode, 'id': TransId, 'cmd': 'get_depo_limits', 't': ''})

    def GetAllTrades(self, TransId=0):
        """Таблица сделок (вся)"""
        return self.ProcessRequest({'data': f'', 'id': TransId, 'cmd': 'get_trades', 't': ''})

    def GetTrades(self, ClassCode, SecCode, TransId=0):
        """Таблица сделок (по инструменту)"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}', 'id': TransId, 'cmd': 'get_trades', 't': ''})

    def GetTradesByOrderNumber(self, OrderNum, TransId=0):
        """Таблица сделок по номеру заявки"""
        return self.ProcessRequest({'data': OrderNum, 'id': TransId, 'cmd': 'get_Trades_by_OrderNumber', 't': ''})

    def GetAllStopOrders(self, TransId=0):
        """Стоп заявки (все)"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'get_stop_orders', 't': ''})

    def GetStopOrders(self, ClassCode, SecCode, TransId=0):
        """Стоп заявки (по инструменту)"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}', 'id': TransId, 'cmd': 'get_stop_orders', 't': ''})

    def GetAllTrade(self, TransId=0):
        """Таблица обезличенных сделок (вся)"""
        return self.ProcessRequest({'data': f'', 'id': TransId, 'cmd': 'get_all_trades', 't': ''})

    def GetTrade(self, ClassCode, SecCode, TransId=0):
        """Таблица обезличенных сделок (по инструменту)"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}', 'id': TransId, 'cmd': 'get_all_trades', 't': ''})

    # 3.2 Функции для обращения к спискам доступных параметров

    def GetClassesList(self, TransId=0):  # 1
        """Список классов"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'getClassesList', 't': ''})

    def GetClassInfo(self, ClassCode, TransId=0):  # 2
        """Информация о классе"""
        return self.ProcessRequest({'data': ClassCode, 'id': TransId, 'cmd': 'getClassInfo', 't': ''})

    def GetClassSecurities(self, ClassCode, TransId=0):  # 3
        """Список инструментов класса"""
        return self.ProcessRequest({'data': ClassCode, 'id': TransId, 'cmd': 'getClassSecurities', 't': ''})
    
    # Функции для обращения к спискам доступных параметров QuikSharp

    def GetOptionBoard(self, ClassCode, SecCode, TransId=0):
        """Доска опционов"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}', 'id': TransId, 'cmd': 'getOptionBoard', 't': ''})

    # 3.3 Функции для получения информации по денежным средствам

    def GetMoney(self, ClientCode, FirmId, Tag, CurrCode, TransId=0):  # 1
        """Денежные позиции"""
        return self.ProcessRequest({'data': f'{ClientCode}|{FirmId}|{Tag}|{CurrCode}', 'id': TransId, 'cmd': 'getMoney', 't': ''})

    def GetMoneyEx(self, FirmId, ClientCode, Tag, CurrCode, LimitKind, TransId=0):  # 2
        """Денежные позиции указанного типа"""
        return self.ProcessRequest({'data': f'{FirmId}|{ClientCode}|{Tag}|{CurrCode}|{LimitKind}', 'id': TransId, 'cmd': 'getMoneyEx', 't': ''})

    # 3.4 Функции для получения позиций по инструментам

    def GetDepo(self, ClientCode, FirmId, SecCode, Account, TransId=0):  # 1
        """Позиции по инструментам"""
        return self.ProcessRequest({'data': f'{ClientCode}|{FirmId}|{SecCode}|{Account}', 'id': TransId, 'cmd': 'getDepo', 't': ''})

    def GetDepoEx(self, FirmId, ClientCode, SecCode, Account, LimitKind, TransId=0):  # 2
        """Позиции по инструментам указанного типа"""
        return self.ProcessRequest({'data': f'{FirmId}|{ClientCode}|{SecCode}|{Account}|{LimitKind}', 'id': TransId, 'cmd': 'getDepoEx', 't': ''})

    # 3.5 Функция для получения информации по фьючерсным лимитам

    def GetFuturesLimit(self, FirmId, AccountId, LimitType, CurrCode, TransId=0):  # 1
        """Фьючерсные лимиты"""
        return self.ProcessRequest({'data': f'{FirmId}|{AccountId}|{LimitType}|{CurrCode}', 'id': TransId, 'cmd': 'getFuturesLimit', 't': ''})

    # Функция для получения информации по фьючерсным лимитам QuikSharp

    def GetFuturesClientLimits(self, TransId=0):
        """Все фьючерсные лимиты"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'getFuturesClientLimits', 't': ''})

    # 3.6 Функция для получения информации по фьючерсным позициям

    def GetFuturesHolding(self, FirmId, AccountId, SecCode, PositionType, TransId=0):  # 1
        """Фьючерсные позиции"""
        return self.ProcessRequest({'data': f'{FirmId}|{AccountId}|{SecCode}|{PositionType}', 'id': TransId, 'cmd': 'getFuturesHolding', 't': ''})

    # Функция для получения информации по фьючерсным позициям QuikSharp

    def GetFuturesHoldings(self, TransId=0):
        """Все фьючерсные позиции"""
        return self.ProcessRequest({'data': '', 'id': TransId, 'cmd': 'getFuturesHolding', 't': ''})

    # 3.7 Функция для получения информации по инструменту

    def GetSecurityInfo(self, ClassCode, SecCode, TransId=0):  # 1
        """Информация по инструменту"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}', 'id': TransId, 'cmd': 'getSecurityInfo', 't': ''})

    # Функция для получения информации по инструменту QuikSharp

    def GetSecurityInfoBulk(self, ClassCodes, SecCodes, TransId=0):
        """Информация по инструментам"""
        return self.ProcessRequest({'data': f'{ClassCodes}|{SecCodes}', 'id': TransId, 'cmd': 'getSecurityInfoBulk', 't': ''})

    def GetSecurityClass(self, ClassesList, SecCode, TransId=0):
        """Класс по коду инструмента из заданных классов"""
        return self.ProcessRequest({'data': f'{ClassesList}|{SecCode}', 'id': TransId, 'cmd': 'getSecurityClass', 't': ''})

    # 3.8 Функция для получения даты торговой сессии

    # getTradeDate - 1. Дата текущей торговой сессии

    # 3.9 Функция для получения стакана по указанному классу и инструменту

    def GetQuoteLevel2(self, ClassCode, SecCode, TransId=0):  # 1
        """Стакан по классу и инструменту"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}', 'id': TransId, 'cmd': 'GetQuoteLevel2', 't': ''})

    # 3.10 Функции для работы с графиками

    # getLinesCount - 1. Кол-во линий в графике

    def GetNumCandles(self, Tag, TransId=0):  # 2
        """Кол-во свечей по тэгу"""
        return self.ProcessRequest({'data': Tag, 'id': TransId, 'cmd': 'get_num_candles', 't': ''})

    # getCandlesByIndex - 3. Информация о свечках (реализовано в get_candles)
    # CreateDataSource - 4. Создание источника данных c функциями: (реализовано в get_candles_from_data_source)
    # - SetUpdateCallback - Привязка функции обратного вызова на изменение свечи
    # - O, H, L, C, V, T - Функции получения цен, объемов и времени
    # - Size - Функция кол-ва свечек в источнике данных
    # - Close - Функция закрытия источника данных. Терминал прекращает получать данные с сервера
    # - SetEmptyCallback - Функция сброса функции обратного вызова на изменение свечи

    # Функции для работы с графиками QuikSharp

    def GetCandles(self, Tag, Line, FirstCandle, Count, TransId=0):
        """Свечки по идентификатору графика"""
        return self.ProcessRequest({'data': f'{Tag}|{Line}|{FirstCandle}|{Count}', 'id': TransId, 'cmd': 'get_candles', 't': ''})

    def GetCandlesFromDataSource(self, ClassCode, SecCode, Interval, Count):  # ichechet - Добавлен выход по таймауту
        """Свечки"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}|{Interval}|{Count}', 'id': '1', 'cmd': 'get_candles_from_data_source', 't': ''})

    def SubscribeToCandles(self, ClassCode, SecCode, Interval, TransId=0):
        """Подписка на свечки"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}|{Interval}', 'id': TransId, 'cmd': 'subscribe_to_candles', 't': ''})

    def IsSubscribed(self, ClassCode, SecCode, Interval, TransId=0):
        """Есть ли подписка на свечки"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}|{Interval}', 'id': TransId, 'cmd': 'is_subscribed', 't': ''})

    def UnsubscribeFromCandles(self, ClassCode, SecCode, Interval, TransId=0):
        """Отмена подписки на свечки"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}|{Interval}', 'id': TransId, 'cmd': 'unsubscribe_from_candles', 't': ''})

    # 3.11 Функции для работы с заявками

    def SendTransaction(self, Transaction, TransId=0):  # 1
        """Отправка транзакции в торговую систему"""
        return self.ProcessRequest({'data': Transaction, 'id': TransId, 'cmd': 'sendTransaction', 't': ''})

    # CalcBuySell - 2. Максимальное кол-во лотов в заявке

    # 3.12 Функции для получения значений таблицы "Текущие торги"

    def GetParamEx(self, ClassCode, SecCode, ParamName, TransId=0):  # 1
        """Таблица текущих торгов"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}|{ParamName}', 'id': TransId, 'cmd': 'getParamEx', 't': ''})

    def GetParamEx2(self, ClassCode, SecCode, ParamName, TransId=0):  # 2
        """Таблица текущих торгов по инструменту с возможностью отказа от получения"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}|{ParamName}', 'id': TransId, 'cmd': 'getParamEx2', 't': ''})

    # Функция для получения значений таблицы "Текущие торги" QuikSharp

    def GetParamEx2Bulk(self, ClassCodes, SecCodes, ParamNames, TransId=0):
        """Таблица текущих торгов по инструментам с возможностью отказа от получения"""
        return self.ProcessRequest({'data': f'{ClassCodes}|{SecCodes}|{ParamNames}', 'id': TransId, 'cmd': 'getParamEx2Bulk', 't': ''})

    # 3.13 Функции для получения параметров таблицы "Клиентский портфель"

    def GetPortfolioInfo(self, FirmId, ClientCode, TransId=0):  # 1
        """Клиентский портфель"""
        return self.ProcessRequest({'data': f'{FirmId}|{ClientCode}', 'id': TransId, 'cmd': 'getPortfolioInfo', 't': ''})

    def GetPortfolioInfoEx(self, FirmId, ClientCode, LimitKind, TransId=0):  # 2
        """Клиентский портфель по сроку расчетов"""
        return self.ProcessRequest({'data': f'{FirmId}|{ClientCode}|{LimitKind}', 'id': TransId, 'cmd': 'getPortfolioInfoEx', 't': ''})

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

    def AddLabel(self, Price, CurDate, CurTime, Qty, Path, LabelId, Alignment, Background, TransId=0):  # 1
        """Добавление метки на график"""
        return self.ProcessRequest({'data': f'{Price}|{CurDate}|{CurTime}|{Qty}|{Path}|{LabelId}|{Alignment}|{Background}', 'id': TransId, 'cmd': 'AddLabel', 't': ''})

    def DelLabel(self, ChartTag, LabelId, TransId=0):  # 2
        """Удаление метки с графика"""
        return self.ProcessRequest({'data': f'{ChartTag}|{LabelId}', 'id': TransId, 'cmd': 'DelLabel', 't': ''})

    def DelAllLabels(self, ChartTag, TransId=0):  # 3
        """Удаление всех меток с графика"""
        return self.ProcessRequest({'data': ChartTag, 'id': TransId, 'cmd': 'DelAllLabels', 't': ''})

    def GetLabelParams(self, ChartTag, LabelId, TransId=0):  # 4
        """Получение параметров метки"""
        return self.ProcessRequest({'data': f'{ChartTag}|{LabelId}', 'id': TransId, 'cmd': 'GetLabelParams', 't': ''})

    # SetLabelParams - 5. Установка параметров метки

    # 3.17 Функции для заказа стакана котировок

    def SubscribeLevel2Quotes(self, ClassCode, SecCode, TransId=0):  # 1
        """Подписка на стакан по Классу|Коду бумаги"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}', 'id': TransId, 'cmd': 'Subscribe_Level_II_Quotes', 't': ''})

    def UnsubscribeLevel2Quotes(self, ClassCode, SecCode, TransId=0):  # 2
        """Отмена подписки на стакан по Классу|Коду бумаги"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}', 'id': TransId, 'cmd': 'Unsubscribe_Level_II_Quotes', 't': ''})

    def IsSubscribedLevel2Quotes(self, ClassCode, SecCode, TransId=0):  # 3
        """Есть ли подписка на стакан по Классу|Коду бумаги"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}', 'id': TransId, 'cmd': 'IsSubscribed_Level_II_Quotes', 't': ''})

    # 3.18 Функции для заказа параметров Таблицы текущих торгов

    def ParamRequest(self, ClassCode, SecCode, ParamName, TransId=0):  # 1
        """Заказ получения таблицы текущих торгов по инструменту"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}|{ParamName}', 'id': TransId, 'cmd': 'paramRequest', 't': ''})

    def CancelParamRequest(self, ClassCode, SecCode, ParamName, TransId=0):  # 2
        """Отмена заказа получения таблицы текущих торгов по инструменту"""
        return self.ProcessRequest({'data': f'{ClassCode}|{SecCode}|{ParamName}', 'id': TransId, 'cmd': 'cancelParamRequest', 't': ''})

    # Функции для заказа параметров Таблицы текущих торгов QuikSharp

    def ParamRequestBulk(self, ClassCodes, SecCodes, ParamNames, TransId=0):
        """Заказ получения таблицы текущих торгов по инструментам"""
        return self.ProcessRequest({'data': f'{ClassCodes}|{SecCodes}|{ParamNames}', 'id': TransId, 'cmd': 'paramRequestBulk', 't': ''})

    def CancelParamRequestBulk(self, ClassCodes, SecCodes, ParamNames, TransId=0):
        """Отмена заказа получения таблицы текущих торгов по инструментам"""
        return self.ProcessRequest({'data': f'{ClassCodes}|{SecCodes}|{ParamNames}', 'id': TransId, 'cmd': 'cancelParamRequestBulk', 't': ''})

    # 3.19 Функции для получения информации по единой денежной позиции

    def GetTrdAccByClientCode(self, FirmId, ClientCode, TransId=0):  # 1
        """Торговый счет срочного рынка по коду клиента фондового рынка"""
        return self.ProcessRequest({'data': f'{FirmId}|{ClientCode}', 'id': TransId, 'cmd': 'getTrdAccByClientCode', 't': ''})

    def GetClientCodeByTrdAcc(self, FirmId, TradeAccountId, TransId=0):  # 2
        """Код клиента фондового рынка с единой денежной позицией по торговому счету срочного рынка"""
        return self.ProcessRequest({'data': f'{FirmId}|{TradeAccountId}', 'id': TransId, 'cmd': 'getClientCodeByTrdAcc', 't': ''})

    def IsUcpClient(self, FirmId, Client, TransId=0):  # 3
        """Имеет ли клиент единую денежную позицию"""
        return self.ProcessRequest({'data': f'{FirmId}|{Client}', 'id': TransId, 'cmd': 'IsUcpClient', 't': ''})

    # Выход и закрытие

    def CloseConnectionAndThread(self):
        """Закрытие соединения для запросов и потока обработки функций обратного вызова"""
        self.socketRequests.close()  # Закрываем соединение для запросов
        self.callbackThread.process = False  # Поток обработки функций обратного вызова больше не нужен

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из класса, например, с with"""
        self.CloseConnectionAndThread()  # Закрываем соединение для запросов и поток обработки функций обратного вызова

    def __del__(self):
        self.CloseConnectionAndThread()  # Закрываем соединение для запросов и поток обработки функций обратного вызова
