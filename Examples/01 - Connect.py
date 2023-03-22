from datetime import datetime

from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QuikSharp


def print_callback(data):
    """Пользовательский обработчик события"""
    print(data)  # Печатаем полученные данные


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    qp_provider = QuikPy()  # Провайдер работает с запущенным терминалом QUIK
    # qp_provider2 = QuikPy(Host='<Адрес IP>', RequestsPort='<Порт запросов>', CallbacksPort='<Порт подписок>')  # Для каждого запущенного терминала будет создан свой экземпляр QuikPy
    # print(f'Экземпляры класса совпадают: {qp_provider2 is qp_provider}')
    # qp_provider2.CloseConnectionAndThread()

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
    qp_provider.OnConnected = print_callback  # Нажимаем кнопку "Установить соединение" в QUIK
    qp_provider.OnDisconnected = print_callback  # Нажимаем кнопку "Разорвать соединение" в QUIK
    qp_provider.OnParam = print_callback  # Текущие параметры изменяются постоянно. Будем их смотреть, пока не нажмем Enter в консоли

    # Выход
    input('Enter - выход\n')
    qp_provider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
