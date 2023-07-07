from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QuikSharp


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK

    firmId = 'MC0063100000'  # Фирма
    classCode = 'TQBR'  # Класс тикера
    secCode = 'SBER'  # Тикер
    
    # firmId = 'SPBFUT'  # Фирма
    # classCode = 'SPBFUT'  # Класс тикера
    # secCode = 'SiU3'  # Для фьючерсов: <Код тикера><Месяц экспирации: 3-H, 6-M, 9-U, 12-Z><Последняя цифра года>

    # Данные тикера
    si = qp_provider.GetSecurityInfo(classCode, secCode)['data']  # Интерпретатор языка Lua, Таблица 4.21 Инструменты
    # print('Ответ от сервера:', si)
    print(f'Информация о тикере {classCode}.{secCode} ({si["short_name"]}):')  # Короткое наименование инструмента
    tradeAccount = qp_provider.GetTradeAccount(classCode)["data"]  # Торговый счет для класса тикера
    print('Торговый счет:', tradeAccount)
    lastPrice = float(qp_provider.GetParamEx(classCode, secCode, 'LAST')['data']['param_value'])  # Последняя цена сделки
    print('Последняя цена сделки:', lastPrice)
    print('Валюта:', si['face_unit'])  # Валюта номинала
    print('Лот:', si['lot_size'])  # Размер лота
    print('Цифр после запятой:', si['scale'])  # Точность (кол-во значащих цифр после запятой)
    print('Шаг цены:', si['min_price_step'])  # Минимальный шаг цены

    # Выход
    qp_provider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy
