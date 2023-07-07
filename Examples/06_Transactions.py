from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QuikSharp


def on_trans_reply(data):
    """Обработчик события ответа на транзакцию пользователя"""
    print('OnTransReply')
    print(data['data'])  # Печатаем полученные данные


def on_order(data):
    """Обработчик события получения новой / изменения существующей заявки"""
    print('OnOrder')
    print(data['data'])  # Печатаем полученные данные


def on_trade(data):
    """Обработчик события получения новой / изменения существующей сделки
    Не вызывается при закрытии сделки
    """
    print('OnTrade')
    print(data['data'])  # Печатаем полученные данные


def on_futures_client_holding(data):
    """Обработчик события изменения позиции по срочному рынку"""
    print('OnFuturesClientHolding')
    print(data['data'])  # Печатаем полученные данные


def on_depo_limit(data):
    """Обработчик события изменения позиции по инструментам"""
    print('OnDepoLimit')
    print(data['data'])  # Печатаем полученные данные


def on_depo_limit_delete(data):
    """Обработчик события удаления позиции по инструментам"""
    print('OnDepoLimitDelete')
    print(data['data'])  # Печатаем полученные данные


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK
    qp_provider.OnTransReply = on_trans_reply  # Ответ на транзакцию пользователя. Если транзакция выполняется из QUIK, то не вызывается
    qp_provider.OnOrder = on_order  # Получение новой / изменение существующей заявки
    qp_provider.OnTrade = on_trade  # Получение новой / изменение существующей сделки
    qp_provider.OnFuturesClientHolding = on_futures_client_holding  # Изменение позиции по срочному рынку
    qp_provider.OnDepoLimit = on_depo_limit  # Изменение позиции по инструментам
    qp_provider.OnDepoLimitDelete = on_depo_limit_delete  # Удаление позиции по инструментам

    class_code = 'SPBFUT'  # Код площадки
    sec_code = 'SiU3'  # Код тикера
    trans_id = 12345  # Номер транзакции
    price = 77000  # Цена входа/выхода
    quantity = 1  # Кол-во в лотах

    # Новая лимитная/рыночная заявка
    # transaction = {  # Все значения должны передаваться в виде строк
    #     'TRANS_ID': str(trans_id),  # Номер транзакции задается клиентом
    #     'CLIENT_CODE': '',  # Код клиента. Для фьючерсов его нет
    #     'ACCOUNT': 'SPBFUT00PST',  # Счет
    #     'ACTION': 'NEW_ORDER',  # Тип заявки: Новая лимитная/рыночная заявка
    #     'CLASSCODE': class_code,  # Код площадки
    #     'SECCODE': sec_code,  # Код тикера
    #     'OPERATION': 'S',  # B = покупка, S = продажа
    #     'PRICE': str(price),  # Цена исполнения. Для рыночных фьючерсных заявок наихудшая цена в зависимости от направления. Для остальных рыночных заявок цена = 0
    #     'QUANTITY': str(quantity),  # Кол-во в лотах
    #     'TYPE': 'L'}  # L = лимитная заявка (по умолчанию), M = рыночная заявка
    # print(f'Новая лимитная/рыночная заявка отправлена на рынок: {qp_provider.SendTransaction(transaction)["data"]}')

    # Удаление существующей лимитной заявки
    # orderNum = 1234567890123456789  # 19-и значный номер заявки
    # transaction = {
    #     'TRANS_ID': str(trans_id),  # Номер транзакции задается клиентом
    #     'ACTION': 'KILL_ORDER',  # Тип заявки: Удаление существующей заявки
    #     'CLASSCODE': class_code,  # Код площадки
    #     'SECCODE': sec_code,  # Код тикера
    #     'ORDER_KEY': str(orderNum)}  # Номер заявки
    # print(f'Удаление заявки отправлено на рынок: {qp_provider.SendTransaction(transaction)["data"]}')

    # Новая стоп заявка
    StopSteps = 10  # Размер проскальзывания в шагах цены
    slippage = float(qp_provider.GetSecurityInfo(class_code, sec_code)['data']['min_price_step']) * StopSteps  # Размер проскальзывания в деньгах
    if slippage.is_integer():  # Целое значение проскальзывания мы должны отправлять без десятичных знаков
        slippage = int(slippage)  # поэтому, приводим такое проскальзывание к целому числу
    transaction = {  # Все значения должны передаваться в виде строк
        'TRANS_ID': str(trans_id),  # Номер транзакции задается клиентом
        'CLIENT_CODE': '',  # Код клиента. Для фьючерсов его нет
        'ACCOUNT': 'SPBFUT00PST',  # Счет
        'ACTION': 'NEW_STOP_ORDER',  # Тип заявки: Новая стоп заявка
        'CLASSCODE': class_code,  # Код площадки
        'SECCODE': sec_code,  # Код тикера
        'OPERATION': 'B',  # B = покупка, S = продажа
        'PRICE': str(price),  # Цена исполнения
        'QUANTITY': str(quantity),  # Кол-во в лотах
        'STOPPRICE': str(price + slippage),  # Стоп цена исполнения
        'EXPIRY_DATE': 'GTC'}  # Срок действия до отмены
    print(f'Новая стоп заявка отправлена на рынок: {qp_provider.SendTransaction(transaction)["data"]}')

    # Удаление существующей стоп заявки
    # orderNum = 1234567  # Номер заявки
    # transaction = {
    #     'TRANS_ID': str(trans_id),  # Номер транзакции задается клиентом
    #     'ACTION': 'KILL_STOP_ORDER',  # Тип заявки: Удаление существующей заявки
    #     'CLASSCODE': class_code,  # Код площадки
    #     'SECCODE': sec_code,  # Код тикера
    #     'STOP_ORDER_KEY': str(orderNum)}  # Номер заявки
    # print(f'Удаление стоп заявки отправлено на рынок: {qp_provider.SendTransaction(transaction)["data"]}')

    input('Enter - отмена\n')  # Ждем исполнение заявки
    qp_provider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy
