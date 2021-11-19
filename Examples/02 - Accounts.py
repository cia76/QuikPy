from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QuikSharp


def GetAllAccounts():
    """Получение всех торговых счетов"""
    futuresFirmId = 'SPBFUT'  # Фирма для фьючерсов. Измените, если требуется, на фирму, которую для фьючерсов поставил ваш брокер

    classCodes = qpProvider.GetClassesList()['data']  # Список классов
    classCodesList = classCodes[:-1].split(',')  # Удаляем последнюю запятую, разбиваем значения по запятой
    tradeAccounts = qpProvider.GetTradeAccounts()['data']  # Все торговые счета
    moneyLimits = qpProvider.GetMoneyLimits()['data']  # Все денежные лимиты (остатки на счетах)
    depoLimits = qpProvider.GetAllDepoLimits()['data']  # Все лимиты по бумагам (позиции по инструментам)
    orders = qpProvider.GetAllOrders()['data']  # Все заявки
    stopOrders = qpProvider.GetAllStopOrders()['data']  # Все стоп заявки

    # Коды клиента / Фирмы / Счета
    for tradeAccount in tradeAccounts:  # Пробегаемся по всем счетам
        firmId = tradeAccount['firmid']  # Фирма
        tradeAccountId = tradeAccount['trdaccid']  # Счет
        distinctClientCode = list(set([moneyLimit['client_code'] for moneyLimit in moneyLimits if moneyLimit['firmid'] == firmId]))  # Уникальные коды клиента по фирме
        print(f'Код клиента {distinctClientCode[0] if distinctClientCode else "не задан"}, Фирма {firmId}, Счет {tradeAccountId} ({tradeAccount["description"]})')
        tradeAccountClassCodes = tradeAccount['class_codes'][1:-1].split('|')  # Классы торгового счета. Удаляем последнюю вертикальную черту, разбиваем значения по вертикальной черте
        intersectionClassCodes = list(set(tradeAccountClassCodes).intersection(classCodesList))  # Классы, которые есть и в списке и в торговом счете
        # Классы
        for classCode in intersectionClassCodes:  # Пробегаемся по всем общим классам
            classInfo = qpProvider.GetClassInfo(classCode)['data']  # Информация о классе
            print(f'- Класс {classCode} ({classInfo["name"]}), Тикеров {classInfo["nsecs"]}')
            # Инструменты. Если выводить на экран, то занимают много места. Поэтому, закомментировали
            # classSecurities = qpProvider.GetClassSecurities(classCode)['data'][:-1].split(',')  # Список инструментов класса. Удаляем последнюю запятую, разбиваем значения по запятой
            # print(f'  - Тикеры ({classSecurities})')
        if firmId == futuresFirmId:  # Для фьючерсов свои расчеты
            # Лимиты
            print(f'- Фьючерсный лимит {qpProvider.GetFuturesLimit(firmId, tradeAccountId, 0, "SUR")["data"]["cbplimit"]} SUR')
            # Позиции
            futuresHoldings = qpProvider.GetFuturesHoldings()['data']  # Все фьючерсные позиции
            activeFuturesHoldings = [futuresHolding for futuresHolding in futuresHoldings if futuresHolding['totalnet'] != 0]  # Активные фьючерсные позиции
            for activeFuturesHolding in activeFuturesHoldings:
                print(f'  - Фьючерсная позиция {activeFuturesHolding["sec_code"]} {activeFuturesHolding["totalnet"]} @ {activeFuturesHolding["cbplused"]}')
        else:  # Для остальных фирм
            # Лимиты
            firmMoneyLimits = [moneyLimit for moneyLimit in moneyLimits if moneyLimit['firmid'] == firmId]  # Денежные лимиты по фирме
            for firmMoneyLimit in firmMoneyLimits:  # Пробегаемся по всем денежным лимитам
                limitKind = firmMoneyLimit['limit_kind']  # День лимита
                print(f'- Денежный лимит {firmMoneyLimit["tag"]} на T{limitKind}: {firmMoneyLimit["currentbal"]} {firmMoneyLimit["currcode"]}')
                # Позиции
                firmKindDepoLimits = [depoLimit for depoLimit in depoLimits if depoLimit['firmid'] == firmId and depoLimit['limit_kind'] == limitKind and depoLimit['currentbal'] != 0]  # Берем только открытые позиции по фирме и дню
                for firmKindDepoLimit in firmKindDepoLimits:  # Пробегаемся по всем позициям
                    secCode = firmKindDepoLimit["sec_code"]  # Код тикера
                    classCode = qpProvider.GetSecurityClass(classCodes, secCode)['data']
                    entryPrice = float(firmKindDepoLimit["wa_position_price"])
                    lastPrice = float(qpProvider.GetParamEx(classCode, secCode, 'LAST')['data']['param_value'])  # Последняя цена сделки
                    if classCode == 'TQOB':  # Для рынка облигаций
                        lastPrice *= 10  # Умножаем на 10
                    print(f'  - Позиция {classCode}.{secCode} {firmKindDepoLimit["currentbal"]} @ {entryPrice:.2f}/{lastPrice:.2f}')
        # Заявки
        firmOrders = [order for order in orders if order['firmid'] == firmId and order['flags'] & 0b1 == 0b1]  # Активные заявки по фирме
        for firmOrder in firmOrders:  # Пробегаемся по всем заявка
            isBuy = firmOrder['flags'] & 0b100 != 0b100  # Заявка на покупку
            print(f'- Заявка номер {firmOrder["order_num"]} {"Покупка" if isBuy else "Продажа"} {firmOrder["class_code"]}.{firmOrder["sec_code"]} {firmOrder["qty"]} @ {firmOrder["price"]}')
        # Стоп заявки
        firmStopOrders = [stopOrder for stopOrder in stopOrders if stopOrder['firmid'] == firmId and stopOrder['flags'] & 0b1 == 0b1]  # Активные стоп заявки по фирме
        for firmStopOrder in firmStopOrders:  # Пробегаемся по всем стоп заявкам
            isBuy = firmStopOrder['flags'] & 0b100 != 0b100  # Заявка на покупку
            print(f'- Стоп заявка номер {firmStopOrder["order_num"]} {"Покупка" if isBuy else "Продажа"} {firmStopOrder["class_code"]}.{firmStopOrder["sec_code"]} {firmStopOrder["qty"]} @ {firmStopOrder["price"]}')

def GetAccount(ClientCode='', FirmId='SPBFUT', TradeAccountId='SPBFUT00PST', LimitKind=0, CurrencyCode='SUR', IsFutures=True):
    """Получение торгового счета. По умолчанию, выдается счет срочного рынка"""
    classCodes = qpProvider.GetClassesList()['data']  # Список классов
    moneyLimits = qpProvider.GetMoneyLimits()['data']  # Все денежные лимиты (остатки на счетах)
    depoLimits = qpProvider.GetAllDepoLimits()['data']  # Все лимиты по бумагам (позиции по инструментам)
    orders = qpProvider.GetAllOrders()['data']  # Все заявки
    stopOrders = qpProvider.GetAllStopOrders()['data']  # Все стоп заявки

    print(f'Код клиента {ClientCode}, Фирма {FirmId}, Счет {TradeAccountId}, T{LimitKind}, {CurrencyCode}')
    if IsFutures:  # Для фьючерсов свои расчеты
        print(f'- Фьючерсный лимит {qpProvider.GetFuturesLimit(FirmId, TradeAccountId, 0, "SUR")["data"]["cbplimit"]} SUR')
        futuresHoldings = qpProvider.GetFuturesHoldings()['data']  # Все фьючерсные позиции
        activeFuturesHoldings = [futuresHolding for futuresHolding in futuresHoldings if futuresHolding['totalnet'] != 0]  # Активные фьючерсные позиции
        for activeFuturesHolding in activeFuturesHoldings:
            print(f'- Фьючерсная позиция {activeFuturesHolding["sec_code"]} {activeFuturesHolding["totalnet"]} @ {activeFuturesHolding["cbplused"]}')
    else:  # Для остальных фирм
        accountMoneyLimit = [moneyLimit for moneyLimit in moneyLimits  # Денежный лимит
                             if moneyLimit['client_code'] == ClientCode and  # Выбираем по коду клиента
                             moneyLimit['firmid'] == FirmId and  # Фирме
                             moneyLimit['limit_kind'] == LimitKind and  # Дню лимита
                             moneyLimit["currcode"] == CurrencyCode][0]  # Валюте
        print(f'- Денежный лимит {accountMoneyLimit["currentbal"]}')
        accountDepoLimits = [depoLimit for depoLimit in depoLimits  # Бумажный лимит
                             if depoLimit['client_code'] == ClientCode and  # Выбираем по коду клиента
                             depoLimit['firmid'] == FirmId and  # Фирме
                             depoLimit['limit_kind'] == LimitKind and  # Дню лимита
                             depoLimit['currentbal'] != 0]  # Берем только открытые позиции по фирме и дню
        for firmKindDepoLimit in accountDepoLimits:  # Пробегаемся по всем позициям
            secCode = firmKindDepoLimit["sec_code"]  # Код тикера
            entryPrice = float(firmKindDepoLimit["wa_position_price"])
            classCode = qpProvider.GetSecurityClass(classCodes, secCode)['data']
            lastPrice = float(qpProvider.GetParamEx(classCode, secCode, 'LAST')['data']['param_value'])  # Последняя цена сделки
            if classCode == 'TQOB':  # Для рынка облигаций
                lastPrice *= 10  # Умножаем на 10
            print(f'- Позиция {classCode}.{secCode} {firmKindDepoLimit["currentbal"]} @ {entryPrice:.2f}/{lastPrice:.2f}')
    accountOrders = [order for order in orders  # Заявки
                     if (order['client_code'] == ClientCode or ClientCode == '') and  # Выбираем по коду клиента
                     order['firmid'] == FirmId and  # Фирме
                     order['account'] == TradeAccountId and  # Счету
                     order['flags'] & 0b1 == 0b1]  # Активные заявки
    for accountOrder in accountOrders:  # Пробегаемся по всем заявкам
        isBuy = accountOrder['flags'] & 0b100 != 0b100  # Заявка на покупку
        print(f'- Заявка номер {accountOrder["order_num"]} {"Покупка" if isBuy else "Продажа"} {accountOrder["class_code"]}.{accountOrder["sec_code"]} {accountOrder["qty"]} @ {accountOrder["price"]}')
    accountStopOrders = [stopOrder for stopOrder in stopOrders  # Стоп заявки
                         if (stopOrder['client_code'] == ClientCode or ClientCode == '') and  # Выбираем по коду клиента
                         stopOrder['firmid'] == FirmId and  # Фирме
                         stopOrder['account'] == TradeAccountId and  # Счету
                         stopOrder['flags'] & 0b1 == 0b1]  # Активные стоп заявки
    for accountStopOrder in accountStopOrders:  # Пробегаемся по всем стоп заявкам
        isBuy = accountStopOrder['flags'] & 0b100 != 0b100  # Заявка на покупку
        print(f'- Стоп заявка номер {accountStopOrder["order_num"]} {"Покупка" if isBuy else "Продажа"} {accountStopOrder["class_code"]}.{accountStopOrder["sec_code"]} {accountStopOrder["qty"]} @ {accountStopOrder["price"]}')


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    qpProvider = QuikPy()  # Вызываем конструктор QuikPy с подключением к локальному компьютеру с QUIK
    # qpProvider = QuikPy(Host='<Ваш IP адрес>')  # Вызываем конструктор QuikPy с подключением к удаленному компьютеру с QUIK

    GetAllAccounts()  # Получаем все счета. По ним можно будет сформировать список счетов для торговли
    print()
    GetAccount()  # Российские фьючерсы и опционы (счет по умолчанию)
    # По списку полученных счетов обязательно проверьте каждый!
    # GetAccount('<Код клиента>', '<Код фирмы>', '<Счет>', <Номер дня лимита>, '<Валюта>', <Счет фьючерсов=True, иначе=False>)

    # Выход
    qpProvider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
