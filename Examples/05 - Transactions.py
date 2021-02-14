from QuikPy import QuikPy as qp  # QuikPy = Работа с Quik из Python через LUA скрипты QuikSharp


def OnTransReply(data):
    """Обработчик события ответа на транзакцию пользователя"""
    print('OnTransReply')
    print(data['data'])  # Печатаем полученные данные

def OnOrder(data):
    """Обработчик события получения новой / изменения существующей заявки"""
    print('OnOrder')
    print(data['data'])  # Печатаем полученные данные

def OnTrade(data):
    """Обработчик события получения новой / изменения существующей сделки
    Не вызывается при закрытии сделки
    """
    print('OnTrade')
    print(data['data'])  # Печатаем полученные данные

def OnFuturesClientHolding(data):
    """Обработчик события изменения позиции по срочному рынку"""
    print('OnFuturesClientHolding')
    print(data['data'])  # Печатаем полученные данные

def OnDepoLimit(data):
    """Обработчик события изменения позиции по инструментам"""
    print('OnDepoLimit')
    print(data['data'])  # Печатаем полученные данные

def OnDepoLimitDelete(data):
    """Обработчик события удаления позиции по инструментам"""
    print('OnDepoLimitDelete')
    print(data['data'])  # Печатаем полученные данные

if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    # qpProvider = qp.QuikPy()  # Вызываем конструктор QuikPy с подключением к локальному компьютеру с QUIK
    qpProvider = qp.QuikPy(Host='192.168.1.7')  # Вызываем конструктор QuikPy с подключением к удаленному компьютеру с QUIK
    qpProvider.OnTransReply = OnTransReply  # Ответ на транзакцию пользователя. Если транзакция выполняется из QUIK, то не вызывается
    qpProvider.OnOrder = OnOrder  # Получение новой / изменение существующей заявки
    qpProvider.OnTrade = OnTrade  # Получение новой / изменение существующей сделки
    qpProvider.OnFuturesClientHolding = OnFuturesClientHolding  # Изменение позиции по срочному рынку
    qpProvider.OnDepoLimit = OnDepoLimit  # Изменение позиции по инструментам
    qpProvider.OnDepoLimitDelete = OnDepoLimitDelete  # Удаление позиции по инструментам

    TransId = 12345  # Номер транзакции
    price = 74550  # Цена входа/выхода
    quantity = 1  # Кол-во в лотах

    # Новая лимитная/рыночная заявка
    transaction = {  # Все значения должны передаваться в виде строк
        'TRANS_ID': str(TransId),  # Номер транзакции задается клиентом
        'CLIENT_CODE': '',  # Код клиента. Для фьючерсов его нет
        'ACCOUNT': 'SPBFUT00PST',  # Счет
        'ACTION': 'NEW_ORDER',  # Тип заявки: Новая лимитная/рыночная заявка
        'CLASSCODE': 'SPBFUT',  # Код площадки
        'SECCODE': 'SiH1',  # Код тикера
        'OPERATION': 'S',  # B = покупка, S = продажа
        'PRICE': str(price),  # Цена исполнения. Для рыночных фьючерсных заявок наихудшая цена в зависимости от направления. Для остальных рыночных заявок цена = 0
        'QUANTITY': str(quantity),  # Кол-во в лотах
        'TYPE': 'L'}  # L = лимитная заявка (по умолчанию), M = рыночная заявка
    print(f'Новая лимитная/рыночная заявка отправлена на рынок: {qpProvider.SendTransaction(transaction)["data"]}')

    # Новая стоп заявка
    # transaction = {  # Все значения должны передаваться в виде строк
    #     'TRANS_ID': str(TransId),  # Номер транзакции задается клиентом
    #     'CLIENT_CODE': '',  # Код клиента. Для фьючерсов его нет
    #     'ACCOUNT': 'SPBFUT00PST',  # Счет
    #     'ACTION': 'NEW_STOP_ORDER',  # Тип заявки: Новая стоп заявка
    #     'CLASSCODE': 'SPBFUT',  # Код площадки
    #     'SECCODE': 'SiH1',  # Код тикера
    #     'OPERATION': 'B',  # B = покупка, S = продажа
    #     'PRICE': str(price),  # Цена исполнения
    #     'QUANTITY': str(quantity),  # Кол-во в лотах
    #     'STOPPRICE': str(price),  # Стоп цена исполнения
    #     'EXPIRY_DATE': 'GTC'}  # Срок действия до отмены
    # print(f'Новая стоп заявка отправлена на рынок: {qpProvider.SendTransaction(transaction)["data"]}')

    # Удаление существующей заявки
    # orderNum = 1234567890123456789  # 19-и значный номер заявки
    # transaction = {
    #     'TRANS_ID': str(TransId),  # Номер транзакции задается клиентом
    #     'ACTION': 'KILL_ORDER',  # Тип заявки: Удаление существующей заявки
    #     'CLASSCODE': 'SPBFUT',  # Код площадки
    #     'SECCODE': 'SiH1',  # Код тикера
    #     'ORDER_KEY': str(orderNum)}  # Номер заявки
    # print(f'Удаление заявки отправлено на рынок: {qpProvider.SendTransaction(transaction)["data"]}')

    input('Enter - отмена')  # Ждем исполнение заявки
    qpProvider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
