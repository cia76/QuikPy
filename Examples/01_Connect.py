from datetime import datetime

from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QuikSharp


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK по портам по умолчанию
    # qp_provider = QuikPy(host='<Адрес IP>')  # Подключение к удаленному QUIK по портам по умолчанию
    # qp_provider = QuikPy(host='<Адрес IP>', requests_port='<Порт запросов>', callbacks_port='<Порт подписок>')  # Подключение к удаленному QUIK по другим портам

    # Проверяем соединение
    print(f'Терминал QUIK подключен к серверу: {qp_provider.IsConnected()["data"] == 1}')
    print(f'Отклик QUIK на команду Ping: {qp_provider.Ping()["data"]}')  # Проверка работы скрипта QuikSharp. Должен вернуть Pong

    # Проверяем работу запрос/ответ
    trade_date = qp_provider.GetInfoParam('TRADEDATE')['data']  # Дата на сервере в виде строки dd.mm.yyyy
    server_time = qp_provider.GetInfoParam('SERVERTIME')['data']  # Время на сервере в виде строки hh:mi:ss
    dt = datetime.strptime(f'{trade_date} {server_time}', '%d.%m.%Y %H:%M:%S')  # Переводим строки в дату и время
    print(f'Дата и время на сервере: {dt}')
    msg = 'Hello from Python!'
    print(f'Отправка сообщения в QUIK: {msg}{qp_provider.MessageInfo(msg)["data"]}')  # Проверка работы QUIK. Сообщение в QUIK должно показаться как информационное

    # Проверяем работу подписок
    qp_provider.OnConnected = lambda data: print(data)  # Нажимаем кнопку "Установить соединение" в QUIK
    qp_provider.OnDisconnected = lambda data: print(data)  # Нажимаем кнопку "Разорвать соединение" в QUIK
    qp_provider.OnParam = lambda data: print(data)  # Текущие параметры изменяются постоянно. Будем их смотреть, пока не нажмем Enter в консоли

    # Выход
    input('Enter - выход\n')
    qp_provider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy
