from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QuikSharp


def get_all_accounts():
    """Получение всех торговых счетов"""
    futures_firm_id = 'SPBFUT'  # Фирма для фьючерсов. Измените, если требуется, на фирму, которую для фьючерсов поставил ваш брокер

    class_codes = qp_provider.GetClassesList()['data']  # Список классов
    class_codes_list = class_codes[:-1].split(',')  # Удаляем последнюю запятую, разбиваем значения по запятой
    trade_accounts = qp_provider.GetTradeAccounts()['data']  # Все торговые счета
    money_limits = qp_provider.GetMoneyLimits()['data']  # Все денежные лимиты (остатки на счетах)
    depo_limits = qp_provider.GetAllDepoLimits()['data']  # Все лимиты по бумагам (позиции по инструментам)
    orders = qp_provider.GetAllOrders()['data']  # Все заявки
    stop_orders = qp_provider.GetAllStopOrders()['data']  # Все стоп заявки

    # Коды клиента / Фирмы / Счета
    for trade_account in trade_accounts:  # Пробегаемся по всем счетам
        firm_id = trade_account['firmid']  # Фирма
        trade_account_id = trade_account['trdaccid']  # Счет
        distinct_client_code = list(set([moneyLimit['client_code'] for moneyLimit in money_limits if moneyLimit['firmid'] == firm_id]))  # Уникальные коды клиента по фирме
        print(f'Код клиента {distinct_client_code[0] if distinct_client_code else "не задан"}, Фирма {firm_id}, Счет {trade_account_id} ({trade_account["description"]})')
        trade_account_class_codes = trade_account['class_codes'][1:-1].split('|')  # Классы торгового счета. Удаляем последнюю вертикальную черту, разбиваем значения по вертикальной черте
        intersection_class_codes = list(set(trade_account_class_codes).intersection(class_codes_list))  # Классы, которые есть и в списке и в торговом счете
        # Классы
        for class_code in intersection_class_codes:  # Пробегаемся по всем общим классам
            class_info = qp_provider.GetClassInfo(class_code)['data']  # Информация о классе
            print(f'- Класс {class_code} ({class_info["name"]}), Тикеров {class_info["nsecs"]}')
            # Инструменты. Если выводить на экран, то занимают много места. Поэтому, закомментировали
            # class_securities = qpProvider.GetClassSecurities(classCode)['data'][:-1].split(',')  # Список инструментов класса. Удаляем последнюю запятую, разбиваем значения по запятой
            # print(f'  - Тикеры ({class_securities})')
        if firm_id == futures_firm_id:  # Для фьючерсов свои расчеты
            # Лимиты
            print(f'- Фьючерсный лимит {qp_provider.GetFuturesLimit(firm_id, trade_account_id, 0, "SUR")["data"]["cbplimit"]} SUR')
            # Позиции
            futures_holdings = qp_provider.GetFuturesHoldings()['data']  # Все фьючерсные позиции
            active_futures_holdings = [futuresHolding for futuresHolding in futures_holdings if futuresHolding['totalnet'] != 0]  # Активные фьючерсные позиции
            for active_futures_holding in active_futures_holdings:
                print(f'  - Фьючерсная позиция {active_futures_holding["sec_code"]} {active_futures_holding["totalnet"]} @ {active_futures_holding["cbplused"]}')
        else:  # Для остальных фирм
            # Лимиты
            firm_money_limits = [moneyLimit for moneyLimit in money_limits if moneyLimit['firmid'] == firm_id]  # Денежные лимиты по фирме
            for firm_money_limit in firm_money_limits:  # Пробегаемся по всем денежным лимитам
                limit_kind = firm_money_limit['limit_kind']  # День лимита
                print(f'- Денежный лимит {firm_money_limit["tag"]} на T{limit_kind}: {firm_money_limit["currentbal"]} {firm_money_limit["currcode"]}')
                # Позиции
                firm_kind_depo_limits = [depoLimit for depoLimit in depo_limits if depoLimit['firmid'] == firm_id and depoLimit['limit_kind'] == limit_kind and depoLimit['currentbal'] != 0]  # Берем только открытые позиции по фирме и дню
                for firm_kind_depo_limit in firm_kind_depo_limits:  # Пробегаемся по всем позициям
                    sec_code = firm_kind_depo_limit["sec_code"]  # Код тикера
                    class_code = qp_provider.GetSecurityClass(class_codes, sec_code)['data']
                    entry_price = float(firm_kind_depo_limit["wa_position_price"])
                    last_price = float(qp_provider.GetParamEx(class_code, sec_code, 'LAST')['data']['param_value'])  # Последняя цена сделки
                    if class_code == 'TQOB':  # Для рынка облигаций
                        last_price *= 10  # Умножаем на 10
                    print(f'  - Позиция {class_code}.{sec_code} {firm_kind_depo_limit["currentbal"]} @ {entry_price:.2f}/{last_price:.2f}')
        # Заявки
        firm_orders = [order for order in orders if order['firmid'] == firm_id and order['flags'] & 0b1 == 0b1]  # Активные заявки по фирме
        for firm_order in firm_orders:  # Пробегаемся по всем заявкам
            buy = firm_order['flags'] & 0b100 != 0b100  # Заявка на покупку
            print(f'- Заявка номер {firm_order["order_num"]} {"Покупка" if buy else "Продажа"} {firm_order["class_code"]}.{firm_order["sec_code"]} {firm_order["qty"]} @ {firm_order["price"]}')
        # Стоп заявки
        firm_stop_orders = [stopOrder for stopOrder in stop_orders if stopOrder['firmid'] == firm_id and stopOrder['flags'] & 0b1 == 0b1]  # Активные стоп заявки по фирме
        for firm_stop_order in firm_stop_orders:  # Пробегаемся по всем стоп заявкам
            buy = firm_stop_order['flags'] & 0b100 != 0b100  # Заявка на покупку
            print(f'- Стоп заявка номер {firm_stop_order["order_num"]} {"Покупка" if buy else "Продажа"} {firm_stop_order["class_code"]}.{firm_stop_order["sec_code"]} {firm_stop_order["qty"]} @ {firm_stop_order["price"]}')


def get_account(client_code='', firm_id='SPBFUT', trade_account_id='SPBFUT00PST', limit_kind=0, currency_code='SUR', futures=True):
    """Получение торгового счета. По умолчанию выдается счет срочного рынка"""
    class_codes = qp_provider.GetClassesList()['data']  # Список классов
    money_limits = qp_provider.GetMoneyLimits()['data']  # Все денежные лимиты (остатки на счетах)
    depo_limits = qp_provider.GetAllDepoLimits()['data']  # Все лимиты по бумагам (позиции по инструментам)
    orders = qp_provider.GetAllOrders()['data']  # Все заявки
    stop_orders = qp_provider.GetAllStopOrders()['data']  # Все стоп заявки

    print(f'Код клиента {client_code}, Фирма {firm_id}, Счет {trade_account_id}, T{limit_kind}, {currency_code}')
    if futures:  # Для фьючерсов свои расчеты
        print(f'- Фьючерсный лимит {qp_provider.GetFuturesLimit(firm_id, trade_account_id, 0, "SUR")["data"]["cbplimit"]} SUR')
        futures_holdings = qp_provider.GetFuturesHoldings()['data']  # Все фьючерсные позиции
        active_futures_holdings = [futuresHolding for futuresHolding in futures_holdings if futuresHolding['totalnet'] != 0]  # Активные фьючерсные позиции
        for active_futures_holding in active_futures_holdings:
            print(f'- Фьючерсная позиция {active_futures_holding["sec_code"]} {active_futures_holding["totalnet"]} @ {active_futures_holding["cbplused"]}')
    else:  # Для остальных фирм
        account_money_limit = [money_limit for money_limit in money_limits  # Денежный лимит
                               if money_limit['client_code'] == client_code and  # Выбираем по коду клиента
                               money_limit['firmid'] == firm_id and  # Фирме
                               money_limit['limit_kind'] == limit_kind and  # Дню лимита
                               money_limit["currcode"] == currency_code][0]  # Валюте
        print(f'- Денежный лимит {account_money_limit["currentbal"]}')
        account_depo_limits = [depo_limit for depo_limit in depo_limits  # Бумажный лимит
                               if depo_limit['client_code'] == client_code and  # Выбираем по коду клиента
                               depo_limit['firmid'] == firm_id and  # Фирме
                               depo_limit['limit_kind'] == limit_kind and  # Дню лимита
                               depo_limit['currentbal'] != 0]  # Берем только открытые позиции по фирме и дню
        for firm_kind_depo_limit in account_depo_limits:  # Пробегаемся по всем позициям
            sec_code = firm_kind_depo_limit["sec_code"]  # Код тикера
            entry_price = float(firm_kind_depo_limit["wa_position_price"])
            class_code = qp_provider.GetSecurityClass(class_codes, sec_code)['data']
            last_price = float(qp_provider.GetParamEx(class_code, sec_code, 'LAST')['data']['param_value'])  # Последняя цена сделки
            if class_code == 'TQOB':  # Для рынка облигаций
                last_price *= 10  # Умножаем на 10
            print(f'- Позиция {class_code}.{sec_code} {firm_kind_depo_limit["currentbal"]} @ {entry_price:.2f}/{last_price:.2f}')
    account_orders = [order for order in orders  # Заявки
                      if (order['client_code'] == client_code or client_code == '') and  # Выбираем по коду клиента
                      order['firmid'] == firm_id and  # Фирме
                      order['account'] == trade_account_id and  # Счету
                      order['flags'] & 0b1 == 0b1]  # Активные заявки
    for account_order in account_orders:  # Пробегаемся по всем заявкам
        buy = account_order['flags'] & 0b100 != 0b100  # Заявка на покупку
        print(f'- Заявка номер {account_order["order_num"]} {"Покупка" if buy else "Продажа"} {account_order["class_code"]}.{account_order["sec_code"]} {account_order["qty"]} @ {account_order["price"]}')
    account_stop_orders = [stop_order for stop_order in stop_orders  # Стоп заявки
                           if (stop_order['client_code'] == client_code or client_code == '') and  # Выбираем по коду клиента
                           stop_order['firmid'] == firm_id and  # Фирме
                           stop_order['account'] == trade_account_id and  # Счету
                           stop_order['flags'] & 0b1 == 0b1]  # Активные стоп заявки
    for account_stop_order in account_stop_orders:  # Пробегаемся по всем стоп заявкам
        buy = account_stop_order['flags'] & 0b100 != 0b100  # Заявка на покупку
        print(f'- Стоп заявка номер {account_stop_order["order_num"]} {"Покупка" if buy else "Продажа"} {account_stop_order["class_code"]}.{account_stop_order["sec_code"]} {account_stop_order["qty"]} @ {account_stop_order["price"]}')


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK

    get_all_accounts()  # Получаем все счета. По ним можно будет сформировать список счетов для торговли
    print()
    get_account()  # Российские фьючерсы и опционы (счет по умолчанию)
    # По списку полученных счетов обязательно проверьте каждый!
    # get_account('<Код клиента>', '<Код фирмы>', '<Счет>', <Номер дня лимита>, '<Валюта>', <Счет фьючерсов=True, иначе=False>)

    # Выход
    qp_provider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy
