import logging  # Выводим лог на консоль и в файл
from sys import exit
from datetime import datetime  # Дата и время
from time import sleep  # Задержка в секундах перед выполнением операций
import itertools  # Итератор для уникальных номеров транзакций

from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QUIK#


def _on_trans_reply(data):
    """Обработчик события ответа на транзакцию пользователя"""
    logger.info(f'OnTransReply: {data}')
    global order_num
    order_num = int(data['data']['order_num'])  # Номер заявки на бирже
    logger.info(f'Номер транзакции: {data["data"]["trans_id"]}, Номер заявки: {order_num}')


def _on_order(data): logger.info(f'Заявка - {data}')


def _on_stop_order(data): logger.info(f'Стоп заявка - {data}')


def _on_trade(data): logger.info(f'Сделка - {data}')


def _on_futures_client_holding(data): logger.info(f'OnFuturesClientHolding: {data}')


def _on_depo_limit(data): logger.info(f'Позиция - {data}')


def _on_depo_limit_delete(data): logger.info(f'OnDepoLimitDelete: {data}')


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    logger = logging.getLogger('QuikPy.Transactions')  # Будем вести лог
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK по портам по умолчанию

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
                        datefmt='%d.%m.%Y %H:%M:%S',  # Формат даты
                        level=logging.DEBUG,  # Уровень логируемых событий NOTSET/DEBUG/INFO/WARNING/ERROR/CRITICAL
                        handlers=[logging.FileHandler('Transactions.log', encoding='utf-8'), logging.StreamHandler()])  # Лог записываем в файл и выводим на консоль
    logging.Formatter.converter = lambda *args: datetime.now(tz=qp_provider.tz_msk).timetuple()  # В логе время указываем по МСК

    class_code = 'TQBR'  # Режим торгов
    sec_code = 'SBER'  # Тикер
    # class_code = 'SPBFUT'  # Режим торгов
    # sec_code = 'CNYRUBF'  # Тикер
    quantity = 1  # Кол-во в лотах

    account = next((account for account in qp_provider.accounts if class_code in account['class_codes']), None)  # Ищем первый счет с режимом торгов тикера
    if not account:  # Если счет не найден
        logger.error(f'Торговый счет для режима торгов {class_code} не найден')
        exit()  # то выходим, дальше не продолжаем
    client_code = account['client_code']  # Код клиента. Для фьючерсов кода клиента нет
    trade_account_id = account['trade_account_id']  # Счет
    last_price = float(qp_provider.get_param_ex(class_code, sec_code, 'LAST')['data']['param_value'])  # Последняя цена сделки
    si = qp_provider.get_symbol_info(class_code, sec_code)  # Спецификация тикера
    order_num = 0  # 19-и значный номер заявки на бирже / номер стоп заявки на сервере. Будет устанавливаться в обработчике события ответа на транзакцию пользователя
    trans_id = itertools.count(1)  # Номер транзакции задается пользователем. Он будет начинаться с 1 и каждый раз увеличиваться на 1

    qp_provider.on_trans_reply.subscribe(_on_trans_reply)  # Подписываемся на транзакции. Если транзакция выполняется из QUIK, то не вызывается
    qp_provider.on_order.subscribe(_on_order)  # Подписываемся на зявки
    qp_provider.on_stop_order.subscribe(_on_stop_order)  # Подписываемся на стоп заявки
    qp_provider.on_trade.subscribe(_on_trade)  # Подписываемся на сделки
    qp_provider.on_futures_client_holding.subscribe(_on_futures_client_holding)  # Подписываемся на позиции по срочному рынку
    qp_provider.on_depo_limit.subscribe(_on_depo_limit)  # Подписываемся на изменение позиций по инструментам
    qp_provider.on_depo_limit_delete.subscribe(_on_depo_limit_delete)  # Подписываемся на удаление позиций по инструментам

    # Новая рыночная заявка (открытие позиции)
    # market_price = qp_provider.price_to_quik_price(class_code, sec_code, qp_provider.quik_price_to_price(class_code, sec_code, last_price * 1.01)) if account['futures'] else 0  # Цена исполнения по рынку. Для фьючерсных заявок цена больше последней при покупке и меньше последней при продаже. Для остальных заявок цена = 0
    # logger.info(f'Заявка {class_code}.{sec_code} на покупку минимального лота по рыночной цене')
    # transaction = {  # Все значения должны передаваться в виде строк
    #     'TRANS_ID': str(next(trans_id)),  # Следующий номер транзакции
    #     'CLIENT_CODE': client_code,  # Код клиента
    #     'ACCOUNT': trade_account_id,  # Счет
    #     'ACTION': 'NEW_ORDER',  # Тип заявки: Новая лимитная/рыночная заявка
    #     'CLASSCODE': class_code,  # Код режима торгов
    #     'SECCODE': sec_code,  # Код тикера
    #     'OPERATION': 'B',  # B = покупка, S = продажа
    #     'PRICE': str(market_price),  # Цена исполнения по рынку
    #     'QUANTITY': str(quantity),  # Кол-во в лотах
    #     'TYPE': 'M'}  # L = лимитная заявка (по умолчанию), M = рыночная заявка
    # logger.info(f'Заявка отправлена на рынок: {qp_provider.send_transaction(transaction)["data"]}')
    #
    # sleep(10)  # Ждем 10 секунд

    # Новая рыночная заявка (закрытие позиции)
    # market_price = qp_provider.price_to_quik_price(class_code, sec_code, qp_provider.quik_price_to_price(class_code, sec_code, last_price * 0.99)) if account['futures'] else 0  # Цена исполнения по рынку. Для фьючерсных заявок цена больше последней при покупке и меньше последней при продаже. Для остальных заявок цена = 0
    # logger.info(f'Заявка {class_code}.{sec_code} на продажу минимального лота по рыночной цене')
    # transaction = {  # Все значения должны передаваться в виде строк
    #     'TRANS_ID': str(next(trans_id)),  # Следующий номер транзакции
    #     'CLIENT_CODE': client_code,  # Код клиента
    #     'ACCOUNT': trade_account_id,  # Счет
    #     'ACTION': 'NEW_ORDER',  # Тип заявки: Новая лимитная/рыночная заявка
    #     'CLASSCODE': class_code,  # Код режима торгов
    #     'SECCODE': sec_code,  # Код тикера
    #     'OPERATION': 'S',  # B = покупка, S = продажа
    #     'PRICE': str(market_price),  # Цена исполнения по рынку
    #     'QUANTITY': str(quantity),  # Кол-во в лотах
    #     'TYPE': 'M'}  # L = лимитная заявка (по умолчанию), M = рыночная заявка
    # logger.info(f'Заявка отправлена на рынок: {qp_provider.send_transaction(transaction)["data"]}')
    #
    # sleep(10)  # Ждем 10 секунд

    # Новая лимитная заявка
    limit_price = qp_provider.price_to_quik_price(class_code, sec_code, qp_provider.quik_price_to_price(class_code, sec_code, last_price * 0.99))  # Лимитная цена на 1% ниже последней цены сделки
    logger.info(f'Заявка {class_code}.{sec_code} на покупку минимального лота по лимитной цене {limit_price}')
    transaction = {  # Все значения должны передаваться в виде строк
        'TRANS_ID': str(next(trans_id)),  # Следующий номер транзакции
        'CLIENT_CODE': client_code,  # Код клиента
        'ACCOUNT': trade_account_id,  # Счет
        'ACTION': 'NEW_ORDER',  # Тип заявки: Новая лимитная/рыночная заявка
        'CLASSCODE': class_code,  # Код режима торгов
        'SECCODE': sec_code,  # Код тикера
        'OPERATION': 'B',  # B = покупка, S = продажа
        'PRICE': str(limit_price),  # Цена исполнения
        'QUANTITY': str(quantity),  # Кол-во в лотах
        'TYPE': 'L'}  # L = лимитная заявка (по умолчанию), M = рыночная заявка
    logger.info(f'Заявка отправлена в стакан: {qp_provider.send_transaction(transaction)["data"]}')

    sleep(10)  # Ждем 10 секунд

    # Удаление существующей лимитной заявки
    transaction = {  # Все значения должны передаваться в виде строк
        'TRANS_ID': str(next(trans_id)),  # Следующий номер транзакции
        'ACTION': 'KILL_ORDER',  # Тип заявки: Удаление существующей заявки
        'CLASSCODE': class_code,  # Код режима торгов
        'SECCODE': sec_code,  # Код тикера
        'ORDER_KEY': str(order_num)}  # Номер заявки
    logger.info(f'Удаление заявки {order_num} из стакана: {qp_provider.send_transaction(transaction)["data"]}')

    sleep(10)  # Ждем 10 секунд

    # Новая стоп заявка
    stop_price = qp_provider.price_to_quik_price(class_code, sec_code, qp_provider.quik_price_to_price(class_code, sec_code, last_price * 1.01))  # Стоп цена на 1% выше последней цены сделки
    transaction = {  # Все значения должны передаваться в виде строк
        'TRANS_ID': str(next(trans_id)),  # Следующий номер транзакции
        'CLIENT_CODE': client_code,  # Код клиента
        'ACCOUNT': trade_account_id,  # Счет
        'ACTION': 'NEW_STOP_ORDER',  # Тип заявки: Новая стоп заявка
        'CLASSCODE': class_code,  # Код режима торгов
        'SECCODE': sec_code,  # Код тикера
        'OPERATION': 'B',  # B = покупка, S = продажа
        'PRICE': str(last_price),  # Цена исполнения
        'QUANTITY': str(quantity),  # Кол-во в лотах
        'STOPPRICE': str(stop_price),  # Стоп цена исполнения
        'EXPIRY_DATE': 'GTC'}  # Срок действия до отмены
    logger.info(f'Стоп заявка отправлена на сервер: {qp_provider.send_transaction(transaction)["data"]}')

    sleep(10)  # Ждем 10 секунд

    # Удаление существующей стоп заявки
    transaction = {
        'TRANS_ID': str(next(trans_id)),  # Следующий номер транзакции
        'ACTION': 'KILL_STOP_ORDER',  # Тип заявки: Удаление существующей заявки
        'CLASSCODE': class_code,  # Код режима торгов
        'SECCODE': sec_code,  # Код тикера
        'STOP_ORDER_KEY': str(order_num)}  # Номер заявки
    print(f'Удаление стоп заявки с сервера: {qp_provider.send_transaction(transaction)["data"]}')

    sleep(10)  # Ждем 10 секунд

    # Отмена подписок
    qp_provider.on_trans_reply.unsubscribe(_on_trans_reply)  # Отменяем подписку на транзакции
    qp_provider.on_order.unsubscribe(_on_order)  # Отменяем подписку на зявки
    qp_provider.on_stop_order.unsubscribe(_on_stop_order)  # Отменяем подписку на стоп заявки
    qp_provider.on_trade.unsubscribe(_on_trade)  # Отменяем подписку на сделки
    qp_provider.on_futures_client_holding.unsubscribe(_on_futures_client_holding)  # Отменяем подписку на позиции по срочному рынку
    qp_provider.on_depo_limit.unsubscribe(_on_depo_limit)  # Отменяем подписку на изменение позиций по инструментам
    qp_provider.on_depo_limit_delete.unsubscribe(_on_depo_limit_delete)  # Отменяем подписку на удаление позиций по инструментам

    # Выход
    qp_provider.close_connection_and_thread()  # Закрываем соединение для запросов и поток обработки функций обратного вызова
