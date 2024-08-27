import logging  # Выводим лог на консоль и в файл
from datetime import datetime  # Дата и время
from locale import currency

from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QUIK#


futures_firm_id = 'SPBFUT'  # Код фирмы для фьючерсов. Измените, если требуется, на фирму, которую для фьючерсов поставил ваш брокер


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    logger = logging.getLogger('QuikPy.Accounts')  # Будем вести лог
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
                        datefmt='%d.%m.%Y %H:%M:%S',  # Формат даты
                        level=logging.DEBUG,  # Уровень логируемых событий NOTSET/DEBUG/INFO/WARNING/ERROR/CRITICAL
                        handlers=[logging.FileHandler('Accounts.log'), logging.StreamHandler()])  # Лог записываем в файл и выводим на консоль
    logging.Formatter.converter = lambda *args: datetime.now(tz=qp_provider.tz_msk).timetuple()  # В логе время указываем по МСК

    class_codes = qp_provider.get_classes_list()['data']  # Режимы торгов через запятую
    class_codes_list = class_codes[:-1].split(',')  # Удаляем последнюю запятую, разбиваем значения по запятой в список режимов торгов
    trade_accounts = qp_provider.get_trade_accounts()['data']  # Все торговые счета
    money_limits = qp_provider.get_money_limits()['data']  # Все денежные лимиты (остатки на счетах)
    depo_limits = qp_provider.get_all_depo_limits()['data']  # Все лимиты по бумагам (позиции по инструментам)
    orders = qp_provider.get_all_orders()['data']  # Все заявки
    stop_orders = qp_provider.get_all_stop_orders()['data']  # Все стоп заявки

    for trade_account in trade_accounts:  # Пробегаемся по всем счетам (Коды клиента/Фирма/Счет)
        trade_account_class_codes = trade_account['class_codes'][1:-1].split('|')  # Режимы торгов счета. Удаляем первую и последнюю вертикальную черту, разбиваем значения по вертикальной черте
        intersection_class_codes = list(set(trade_account_class_codes).intersection(class_codes_list))  # Режимы торгов, которые есть и в списке и в торговом счете
        # for class_code in intersection_class_codes:  # Пробегаемся по всем режимам торгов
        #     class_info = qp_provider.get_class_info(class_code)['data']  # Информация о режиме торгов
        #     logger.info(f'- Режим торгов {class_code} ({class_info["name"]}), Тикеров {class_info["nsecs"]}')
        #     class_securities = qp_provider.get_class_securities(class_code)['data'][:-1].split(',')  # Список инструментов режима торгов. Удаляем последнюю запятую, разбиваем значения по запятой
        #     logger.info(f'  - Тикеры ({class_securities})')

        firm_id = trade_account['firmid']  # Фирма
        trade_account_id = trade_account['trdaccid']  # Счет
        client_code = next((moneyLimit['client_code'] for moneyLimit in money_limits if moneyLimit['firmid'] == firm_id), None)  # Код клиента
        logger.info(f'Учетная запись: Код клиента {client_code if client_code else "не задан"}, Фирма {firm_id}, Счет {trade_account_id} ({trade_account["description"]})')
        logger.info(f'Режимы торгов: {intersection_class_codes}')
        if firm_id == futures_firm_id:  # Для фирмы фьючерсов
            active_futures_holdings = [futuresHolding for futuresHolding in qp_provider.get_futures_holdings()['data'] if futuresHolding['totalnet'] != 0]  # Активные фьючерсные позиции
            for active_futures_holding in active_futures_holdings:  # Пробегаемся по всем активным фьючерсным позициям
                si = qp_provider.get_symbol_info('SPBFUT', active_futures_holding['sec_code'])  # Спецификация тикера
                logger.info(f'- Позиция {si["class_code"]}.{si["sec_code"]} ({si["short_name"]}) {active_futures_holding["totalnet"]} @ {active_futures_holding["cbplused"]}')
            # Видео: https://www.youtube.com/watch?v=u2C7ElpXZ4k
            # Баланс = Лимит откр.поз. + Вариац.маржа + Накоплен.доход
            # Лимит откр.поз. = Сумма, которая была на счету вчера в 19:00 МСК (после вечернего клиринга)
            # Вариац.маржа = Рассчитывается с 19:00 предыдущего дня без учета комисии. Перейдет в Накоплен.доход и обнулится в 14:00 (на дневном клиринге)
            # Накоплен.доход включает Биржевые сборы
            # Тек.чист.поз. = Заблокированное ГО под открытые позиции
            # План.чист.поз. = На какую сумму можете открыть еще позиции
            futures_limit = qp_provider.get_futures_limit(firm_id, trade_account_id, 0, qp_provider.currency)['data']  # Фьючерсные лимиты по денежным средствам (limit_type=0)
            value = futures_limit['cbplused']  # Стоимость позиций
            cash = futures_limit['cbplimit'] + futures_limit['varmargin'] + futures_limit['accruedint']  # Свободные средства = Лимит откр.поз. + Вариац.маржа + Накоплен.доход
            logger.info(f'- Позиции {value:.2f} + Свободные средства {cash:.2f} = {(value + cash):.2f} {futures_limit["currcode"]}')
        else:  # Для остальных фирм
            firm_money_limits = [moneyLimit for moneyLimit in money_limits if moneyLimit['firmid'] == firm_id]  # Денежные лимиты по фирме
            for firm_money_limit in firm_money_limits:  # Пробегаемся по всем денежным лимитам
                limit_kind = firm_money_limit['limit_kind']  # День лимита
                firm_kind_depo_limits = [depoLimit for depoLimit in depo_limits if
                                         depoLimit['firmid'] == firm_id and
                                         depoLimit['limit_kind'] == limit_kind and
                                         depoLimit['currentbal'] != 0]  # Берем только открытые позиции по фирме и дню
                for firm_kind_depo_limit in firm_kind_depo_limits:  # Пробегаемся по всем позициям
                    sec_code = firm_kind_depo_limit["sec_code"]  # Код тикера
                    class_code = qp_provider.get_security_class(class_codes, sec_code)['data']  # Код режима торгов из всех режимов по тикеру
                    entry_price = qp_provider.quik_price_to_price(class_code, sec_code, float(firm_kind_depo_limit["wa_position_price"]))  # Цена входа в рублях за штуку
                    last_price = qp_provider.quik_price_to_price(class_code, sec_code, float(qp_provider.get_param_ex(class_code, sec_code, 'LAST')['data']['param_value']))  # Последняя цена сделки в рублях за штуку
                    si = qp_provider.get_symbol_info(class_code, sec_code)  # Спецификация тикера
                    logger.info(f'- Позиция {class_code}.{sec_code} ({si["short_name"]}) {int(firm_kind_depo_limit["currentbal"])} @ {entry_price} / {last_price}')
                logger.info(f'- T{limit_kind}: Свободные средства {firm_money_limit["currentbal"]} {firm_money_limit["currcode"]}')
        firm_orders = [order for order in orders if order['firmid'] == firm_id and order['flags'] & 0b1 == 0b1]  # Активные заявки по фирме
        for firm_order in firm_orders:  # Пробегаемся по всем заявкам
            buy = firm_order['flags'] & 0b100 != 0b100  # Заявка на покупку
            class_code = firm_order['class_code']  # Код режима торгов
            sec_code = firm_order["sec_code"]  # Тикер
            order_price = qp_provider.quik_price_to_price(class_code, sec_code, firm_order['price'])  # Цена заявки в рублях за штуку
            si = qp_provider.get_symbol_info(class_code, sec_code)  # Спецификация тикера
            order_qty = firm_order['qty'] * si['lot_size']  # Кол-во в штуках
            logger.info(f'- Заявка номер {firm_order["order_num"]} {"Покупка" if buy else "Продажа"} {class_code}.{sec_code} {order_qty} @ {order_price}')
        firm_stop_orders = [stopOrder for stopOrder in stop_orders if stopOrder['firmid'] == firm_id and stopOrder['flags'] & 0b1 == 0b1]  # Активные стоп заявки по фирме
        for firm_stop_order in firm_stop_orders:  # Пробегаемся по всем стоп заявкам
            buy = firm_stop_order['flags'] & 0b100 != 0b100  # Заявка на покупку
            class_code = firm_stop_order['class_code']  # Код режима торгов
            sec_code = firm_stop_order['sec_code']  # Тикер
            stop_order_price = qp_provider.quik_price_to_price(class_code, sec_code, firm_stop_order['price'])  # Цена срабатывания стоп заявки в рублях за штуку
            si = qp_provider.get_symbol_info(class_code, sec_code)  # Спецификация тикера
            stop_order_qty = firm_stop_order['qty'] * si['lot_size']  # Кол-во в штуках
            logger.info(f'- Стоп заявка номер {firm_stop_order["order_num"]} {"Покупка" if buy else "Продажа"} {class_code}.{sec_code} {stop_order_qty} @ {stop_order_price}')

    qp_provider.close_connection_and_thread()  # Перед выходом закрываем соединение для запросов и поток обработки функций обратного вызова
