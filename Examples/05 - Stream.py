import time  # Подписка на события по времени
from QuikPy import QuikPy  # Работа с Quik из Python через LUA скрипты QuikSharp


def PrintCallback(data):
    """Пользовательский обработчик событий:
    - Изменение стакана котировок
    - Получение обезличенной сделки
    - Получение новой свечки
    """
    print(data['data'])  # Печатаем полученные данные

if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    # qpProvider = QuikPy()  # Вызываем конструктор QuikPy с подключением к локальному компьютеру с QUIK
    qpProvider = QuikPy(Host='192.168.1.7')  # Вызываем конструктор QuikPy с подключением к удаленному компьютеру с QUIK

    firmId = 'MC0063100000'  # Фирма
    classCode = 'TQBR'  # Класс тикера
    secCode = 'GAZP'  # Тикер

    # firmId = 'SPBFUT'  # Фирма
    # classCode = 'SPBFUT'  # Класс тикера
    # secCode = 'SiH1'  # Для фьючерсов: <Код тикера><Месяц экспирации: 3-H, 6-M, 9-U, 12-Z><Последняя цифра года>

    # Стакан
    print(f'Текущий стакан {classCode}.{secCode}: {qpProvider.GetQuoteLevel2(classCode, secCode)}')
    qpProvider.OnQuote = PrintCallback  # Обработчик изменения стакана котировок
    print(f'Подписка на стакан {classCode}.{secCode}: {qpProvider.SubscribeLevel2Quotes(classCode, secCode)["data"]}')
    sleepSec = 1  # Кол-во секунд получения котировок
    print(f'{sleepSec} секунд котировок')
    time.sleep(sleepSec)  # Ждем кол-во секунд получения котировок
    print(f'Отмена подписки на стакан: {qpProvider.UnsubscribeLevel2Quotes(classCode, secCode)["data"]}')
    print(f'Статус подписки: {qpProvider.IsSubscribedLevel2Quotes(classCode, secCode)["data"]}')
    qpProvider.OnQuote = qpProvider.DefaultHandler  # Возвращаем обработчик по умолчанию

    # Обезличенные сделки. Чтобы получать, в QUIK открыть Таблицу обезличенных сделок, указать тикер
    qpProvider.OnAllTrade = PrintCallback  # Обработчик получения обезличенной сделки
    sleepSec = 3  # Кол-во секунд получения обезличенных сделок
    print(f'{sleepSec} секунд обезличенных сделок')
    time.sleep(sleepSec)  # Ждем кол-во секунд получения обезличенных сделок
    qpProvider.OnAllTrade = qpProvider.DefaultHandler  # Возвращаем обработчик по умолчанию

    # Подписка на новые свечки
    qpProvider.OnNewCandle = PrintCallback  # Обработчик получения новой свечки - В первый раз получим все свечки с начала прошлой сессии
    print(f'Подписка на минутные свечки {qpProvider.SubscribeToCandles(classCode, secCode, 1)["data"]}')
    input('Enter - отмена')
    print(f'Отмена подписки на минутные свечки {qpProvider.UnsubscribeFromCandles(classCode, secCode, 1)["data"]}')
    qpProvider.OnNewCandle = qpProvider.DefaultHandler  # Возвращаем обработчик по умолчанию

    # Выход
    qpProvider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
