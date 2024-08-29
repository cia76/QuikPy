import logging  # Выводим лог на консоль и в файл
from datetime import datetime  # Дата и время

from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QUIK#


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    logger = logging.getLogger('QuikPy.Ticker')  # Будем вести лог
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
                        datefmt='%d.%m.%Y %H:%M:%S',  # Формат даты
                        level=logging.DEBUG,  # Уровень логируемых событий NOTSET/DEBUG/INFO/WARNING/ERROR/CRITICAL
                        handlers=[logging.FileHandler('Ticker.log'), logging.StreamHandler()])  # Лог записываем в файл и выводим на консоль
    logging.Formatter.converter = lambda *args: datetime.now(tz=qp_provider.tz_msk).timetuple()  # В логе время указываем по МСК

    # Формат короткого имени для фьючерсов: <Код тикера><Месяц экспирации: 3-H, 6-M, 9-U, 12-Z><Последняя цифра года>. Пример: SiU4, RIU4
    # datanames = ('SBER',)  # Тикер без режима торгов
    datanames = ('TQBR.SBER', 'TQBR.HYDR', 'SPBFUT.SiU4', 'SPBFUT.RIU4', 'SPBFUT.BRU4', 'SPBFUT.CNYRUBF')  # Кортеж тикеров

    for dataname in datanames:  # Пробегаемся по всем тикерам
        class_code, sec_code = qp_provider.dataname_to_class_sec_codes(dataname)  # Код режима торгов и тикер
        si = qp_provider.get_symbol_info(class_code, sec_code)  # Спецификация тикера
        logger.debug(f'Ответ от сервера: {si}')
        logger.info(f'Информация о тикере {si["class_code"]}.{si["sec_code"]} ({si["short_name"]}):')  # Короткое наименование инструмента
        logger.info(f'- Валюта: {si["face_unit"]}')
        lot_size = si['lot_size']  # Лот
        logger.info(f'- Лот: {lot_size}')
        min_price_step = si['min_price_step']  # Шаг цены
        logger.info(f'- Шаг цены: {min_price_step}')
        scale = si['scale']  # Кол-во десятичных знаков
        logger.info(f'- Кол-во десятичных знаков: {scale}')
        trade_account = qp_provider.get_trade_account(class_code)['data']  # Торговый счет для класса тикера
        logger.info(f'- Торговый счет: {trade_account}')
        last_price = float(qp_provider.get_param_ex(class_code, sec_code, 'LAST')['data']['param_value'])  # Последняя цена сделки
        logger.info(f'- Последняя цена сделки: {last_price}')
        step_price = float(qp_provider.get_param_ex(class_code, sec_code, 'STEPPRICE')['data']['param_value'])  # Стоимость шага цены
        if lot_size > 1 and step_price:  # Если есть лот и стоимость шага цены
            logger.info(f'- Стоимость шага цены: {step_price} руб.')
            lot_price = last_price // min_price_step * step_price  # Цена за лот в рублях
            logger.info(f'- Цена за лот: {last_price} / {min_price_step} * {step_price} = {lot_price} руб.')
            pcs_price = lot_price / lot_size  # Цена за штуку в рублях
            logger.info(f'- Цена за штуку: {lot_price} / {lot_size} = {pcs_price} руб.')
            logger.info(f'- Последняя цена сделки: {qp_provider.price_to_quik_price(class_code, sec_code, pcs_price)} из цены за штуку в рублях')

    qp_provider.close_connection_and_thread()  # Перед выходом закрываем соединение для запросов и поток обработки функций обратного вызова
