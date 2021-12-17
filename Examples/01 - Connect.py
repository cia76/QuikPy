from datetime import datetime

from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QuikSharp


def PrintCallback(data):
    """Пользовательский обработчик события"""
    print(data)  # Печатаем полученные данные


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    qpProvider = QuikPy()  # Вызываем конструктор QuikPy с подключением к локальному компьютеру с QUIK
    # qpProvider = QuikPy(Host='<Ваш IP адрес>')  # Вызываем конструктор QuikPy с подключением к удаленному компьютеру с QUIK
    print(f'Подключено к терминалу QUIK по адресу: {qpProvider.Host}:{qpProvider.RequestsPort},{qpProvider.CallbacksPort}')

    # QuikPy - Singleton класс. Будет создан 1 экземпляр класса, на него будут все ссылки
    qpProvider2 = QuikPy()  # QuikPy - это Singleton класс. При попытке создания нового экземпляра получим ссылку на уже имеющийся экземпляр
    # qpProvider2 = QuikPy(Host='<Ваш IP адрес>')  # Вызываем конструктор QuikPy с подключением к удаленному компьютеру с QUIK
    print(f'Экземпляры класса совпадают: {qpProvider2 is qpProvider}')

    # Проверка соединения
    print(f'Терминал QUIK подключен к серверу: {qpProvider.IsConnected()["data"] == 1}')
    print(f'Отклик QUIK на команду Ping: {qpProvider.Ping()["data"]}')  # Проверка работы скрипта QuikSharp. Должен вернуть Pong

    # Сервисные функции
    d = qpProvider.GetInfoParam('TRADEDATE')['data']  # Дата на сервере в виде строки dd.mm.yyyy
    t = qpProvider.GetInfoParam('SERVERTIME')['data']  # Время на сервере в виде строки hh:mi:ss
    dt = datetime.strptime(f'{d} {t}', '%d.%m.%Y %H:%M:%S')  # Переводим строки в дату и время
    print(f'Дата и время на сервере: {dt}')
    msg = 'Hello from Python!'
    print(f'Отправка сообщения в QUIK: {msg}{qpProvider.MessageInfo(msg)["data"]}')  # Проверка работы QUIK. Сообщение в QUIK должно показаться как информационное

    # Просмотр изменений состояния соединения терминала QUIK с сервером брокера
    qpProvider.OnConnected = PrintCallback  # Нажимаем кнопку "Установить соединение" в QUIK
    qpProvider.OnDisconnected = PrintCallback  # Нажимаем кнопку "Разорвать соединение" в QUIK

    # Просмотр изменений параметров
    qpProvider.OnParam = PrintCallback  # Текущие параметры изменяются постоянно. Будем их смотреть, пока не нажмем Enter в консоли

    # Выход
    input('Enter - выход\n')
    qpProvider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
