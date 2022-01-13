from datetime import datetime
import time  # Подписка на события по времени
from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QuikSharp


def PrintCallback(data):
    """Пользовательский обработчик событий:
    - Изменение стакана котировок
    - Получение обезличенной сделки
    - Получение новой свечки
    """
    print(f'{datetime.now().strftime("%d.%m.%Y %H:%M:%S")} - {data["data"]}')  # Печатаем полученные данные


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    qpProvider = QuikPy()  # Вызываем конструктор QuikPy с подключением к локальному компьютеру с QUIK
    # qpProvider = QuikPy(Host='<Ваш IP адрес>')  # Вызываем конструктор QuikPy с подключением к удаленному компьютеру с QUIK

    # classCode = 'TQBR'  # Класс тикера
    # secCode = 'GAZP'  # Тикер

    classCode = 'SPBFUT'  # Класс тикера
    secCode = 'SiH2'  # Для фьючерсов: <Код тикера><Месяц экспирации: 3-H, 6-M, 9-U, 12-Z><Последняя цифра года>

    # Запрос текущего стакана. Чтобы получать, в QUIK открыть Таблицу Котировки, указать тикер
    # print(f'Текущий стакан {classCode}.{secCode}:', qpProvider.GetQuoteLevel2(classCode, secCode)['data'])

    # Стакан. Чтобы отмена подписки работала корректно, в QUIK должна быть ЗАКРЫТА таблица Котировки тикера
    qpProvider.OnQuote = PrintCallback  # Обработчик изменения стакана котировок
    print(f'Подписка на изменения стакана {classCode}.{secCode}:', qpProvider.SubscribeLevel2Quotes(classCode, secCode)['data'])
    print('Статус подписки:', qpProvider.IsSubscribedLevel2Quotes(classCode, secCode)['data'])
    sleepSec = 3  # Кол-во секунд получения котировок
    print('Секунд котировок:', sleepSec)
    time.sleep(sleepSec)  # Ждем кол-во секунд получения котировок
    print(f'Отмена подписки на изменения стакана:', qpProvider.UnsubscribeLevel2Quotes(classCode, secCode)['data'])
    print('Статус подписки:', qpProvider.IsSubscribedLevel2Quotes(classCode, secCode)['data'])
    qpProvider.OnQuote = qpProvider.DefaultHandler  # Возвращаем обработчик по умолчанию

    # Обезличенные сделки. Чтобы получать, в QUIK открыть Таблицу обезличенных сделок, указать тикер
    qpProvider.OnAllTrade = PrintCallback  # Обработчик получения обезличенной сделки
    sleepSec = 1  # Кол-во секунд получения обезличенных сделок
    print('Секунд обезличенных сделок:', sleepSec)
    time.sleep(sleepSec)  # Ждем кол-во секунд получения обезличенных сделок
    qpProvider.OnAllTrade = qpProvider.DefaultHandler  # Возвращаем обработчик по умолчанию

    # Подписка на новые свечки. При первой подписке получим все свечки с начала прошлой сессии
    # TODO В QUIK 9.2.13.15 перестала работать повторная подписка
    #  Перед повторной подпиской нужно перезапустить скрипт QuikSharp.lua Подписка станет первой, все заработает
    qpProvider.OnNewCandle = PrintCallback  # Обработчик получения новой свечки
    print(f'Статус подписки:', qpProvider.IsSubscribed(classCode, secCode, 1)['data'])
    print(f'Подписка на минутные свечки', qpProvider.SubscribeToCandles(classCode, secCode, 1)['data'])
    print(f'Статус подписки:', qpProvider.IsSubscribed(classCode, secCode, 1)['data'])
    input('Enter - отмена\n')
    print(f'Отмена подписки на минутные свечки', qpProvider.UnsubscribeFromCandles(classCode, secCode, 1)['data'])
    print(f'Статус подписки:', qpProvider.IsSubscribed(classCode, secCode, 1)['data'])
    qpProvider.OnNewCandle = qpProvider.DefaultHandler  # Возвращаем обработчик по умолчанию

    # Выход
    qpProvider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
