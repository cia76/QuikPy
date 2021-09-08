from QuikPy import QuikPy  # Работа с Quik из Python через LUA скрипты QuikSharp


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    # qpProvider = QuikPy()  # Вызываем конструктор QuikPy с подключением к локальному компьютеру с QUIK
    qpProvider = QuikPy(Host='192.168.1.7')  # Вызываем конструктор QuikPy с подключением к удаленному компьютеру с QUIK

    firmId = 'MC0063100000'  # Фирма
    classCode = 'TQBR'  # Класс тикера
    secCode = 'GAZP'  # Тикер
    
    # firmId = 'SPBFUT'  # Фирма
    # classCode = 'SPBFUT'  # Класс тикера
    # secCode = 'SiH1'  # Для фьючерсов: <Код тикера><Месяц экспирации: 3-H, 6-M, 9-U, 12-Z><Последняя цифра года>

    # Данные тикера и его торговый счет
    securityInfo = qpProvider.GetSecurityInfo(classCode, secCode)["data"]
    print(f'Информация о тикере {classCode}.{secCode} ({securityInfo["short_name"]}):')
    print(f'Валюта: {securityInfo["face_unit"]}')
    print(f'Кол-во десятичных знаков: {securityInfo["scale"]}')
    print(f'Лот: {securityInfo["lot_size"]}')
    print(f'Шаг цены: {securityInfo["min_price_step"]}')
    print(f'Торговый счет для тикера класса {classCode}: {qpProvider.GetTradeAccount(classCode)["data"]}')

    # Выход
    qpProvider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
