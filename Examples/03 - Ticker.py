from datetime import datetime
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

    # Свечки
    print(f'5-и минутные свечки {classCode}.{secCode}:')
    bars = qpProvider.GetCandlesFromDataSource(classCode, secCode, 5, 0)["data"]  # 5 минут, 0 = все свечки
    print(bars)

    # print(f'Дневные свечки {classCode}.{secCode}:')
    # bars = qpProvider.GetCandlesFromDataSource(classCode, secCode, 1440, 0)['data']  # 1440 минут = 1 день, 0 = все свечки
    # dtjs = [row['datetime'] for row in bars]  # Получаем исходники даты и времени начала свчки (List comprehensions)
    # dts = [datetime(dtj['year'], dtj['month'], dtj['day'], dtj['hour'], dtj['min']) for dtj in dtjs]  # Получаем дату и время
    # print(dts)

    # Выход
    qpProvider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
