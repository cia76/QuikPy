from QuikPy import QuikPy  # Работа с Quik из Python через LUA скрипты QuikSharp


def PrintCallback(data):
    """Пользовательский обработчик события"""
    print(data)  # Печатаем полученные данные
    
if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    # qpProvider = QuikPy()  # Вызываем конструктор QuikPy с подключением к локальному компьютеру с QUIK
    qpProvider = QuikPy(Host='192.168.1.7')  # Вызываем конструктор QuikPy с подключением к удаленному компьютеру с QUIK
    print(f'Подключено к терминалу QUIK по адресу: {qpProvider.Host}:{qpProvider.RequestsPort},{qpProvider.CallbacksPort}')

    # QuikPy - Singleton класс. Будет создан 1 экземпляр класса, на него будут все ссылки
    # qpProvider2 = QuikPy()
    qpProvider2 = QuikPy(Host='192.168.1.7')  # QuikPy - это Singleton класс. При попытке создания нового экземпляра получим ссылку на уже имеющийся экземпляр
    print(f'Экземпляры класса совпадают: {qpProvider2 == qpProvider}')

    # Проверка соединения
    print(f'Терминал QUIK подключен к серверу: {qpProvider.IsConnected()["data"] == 1}')
    print(f'Отклик QUIK на команду Ping: {qpProvider.Ping()["data"]}')

    # Сервисные функции
    print(f'Дата на сервере: {qpProvider.GetInfoParam("TRADEDATE")["data"]}')
    print(f'Время на сервере: {qpProvider.GetInfoParam("SERVERTIME")["data"]}')
    msg = 'Hello from Python!'
    print(f'Отправка сообщения в QUIK: {msg}{qpProvider.MessageInfo(msg)["data"]}')

    # Просмотр изменений параметров
    qpProvider.OnParam = PrintCallback  # Текущие параметры изменяются постоянно. Будем их смотреть, пока не нажмем Enter в консоли

    # Выход
    input('Enter - выход')
    qpProvider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
