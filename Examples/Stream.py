import logging  # Выводим лог на консоль и в файл
from datetime import datetime  # Дата и время
import time  # Подписка на события по времени

from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QUIK#


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    logger = logging.getLogger('QuikPy.Stream')  # Будем вести лог
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK по портам по умолчанию

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
                        datefmt='%d.%m.%Y %H:%M:%S',  # Формат даты
                        level=logging.DEBUG,  # Уровень логируемых событий NOTSET/DEBUG/INFO/WARNING/ERROR/CRITICAL
                        handlers=[logging.FileHandler('Stream.log'), logging.StreamHandler()])  # Лог записываем в файл и выводим на консоль
    logging.Formatter.converter = lambda *args: datetime.now(tz=qp_provider.tz_msk).timetuple()  # В логе время указываем по МСК

    class_code = 'TQBR'  # Класс тикера
    sec_code = 'SBER'  # Тикер

    # class_code = 'SPBFUT'  # Класс тикера
    # sec_code = 'SiU4'  # Для фьючерсов: <Код тикера><Месяц экспирации: 3-H, 6-M, 9-U, 12-Z><Последняя цифра года>

    # Запрос текущего стакана. Чтобы получать, в QUIK открыть таблицу "Котировки", указать тикер
    # logger.info(f'Текущий стакан {class_code}.{sec_code}: {qp_provider.get_quote_level2(class_code, sec_code)["data"]}')

    # Подписка на стакан. Чтобы отмена подписки работала корректно, в QUIK должна быть ЗАКРЫТА таблица "Котировки" тикера
    qp_provider.on_quote = lambda data: logger.info(data)  # Обработчик изменения стакана котировок
    logger.info(f'Подписка на изменения стакана {class_code}.{sec_code}: {qp_provider.subscribe_level2_quotes(class_code, sec_code)["data"]}')
    logger.info(f'Статус подписки: {qp_provider.is_subscribed_level2_quotes(class_code, sec_code)["data"]}')
    sleep_sec = 3  # Кол-во секунд получения котировок
    logger.info(f'Секунд котировок: {sleep_sec}')
    time.sleep(sleep_sec)  # Ждем кол-во секунд получения котировок
    logger.info(f'Отмена подписки на изменения стакана: {qp_provider.unsubscribe_level2_quotes(class_code, sec_code)["data"]}')
    logger.info(f'Статус подписки: {qp_provider.is_subscribed_level2_quotes(class_code, sec_code)["data"]}')
    qp_provider.on_quote = qp_provider.default_handler  # Возвращаем обработчик по умолчанию

    # Подписка на обезличенные сделки. Чтобы получать, в QUIK открыть "Таблицу обезличенных сделок", указать тикер
    qp_provider.on_all_trade = lambda data: logger.info(data)  # Обработчик получения обезличенной сделки
    logger.info(f'Подписка на обезличенные сделки {class_code}.{sec_code}')
    sleep_sec = 3  # Кол-во секунд получения обезличенных сделок
    logger.info(f'Секунд обезличенных сделок: {sleep_sec}')
    time.sleep(sleep_sec)  # Ждем кол-во секунд получения обезличенных сделок
    logger.info(f'Отмена подписки на обезличенные сделки')
    qp_provider.on_all_trade = qp_provider.default_handler  # Возвращаем обработчик по умолчанию

    # Просмотр изменений состояния соединения терминала QUIK с сервером брокера
    qp_provider.on_connected = lambda data: logger.info(data)  # Нажимаем кнопку "Установить соединение" в QUIK
    qp_provider.on_disconnected = lambda data: logger.info(data)  # Нажимаем кнопку "Разорвать соединение" в QUIK

    # Подписка на новые свечки. При первой подписке получим все свечки с начала прошлой сессии
    qp_provider.on_new_candle = lambda data: logger.info(data)  # Обработчик получения новой свечки
    for interval in (1,):  # (1, 60, 1440) = Минутки, часовки, дневки
        logger.info(f'Подписка на интервал {interval}: {qp_provider.subscribe_to_candles(class_code, sec_code, interval)["data"]}')
        logger.info(f'Статус подписки на интервал {interval}: {qp_provider.is_subscribed(class_code, sec_code, interval)["data"]}')
    input('Enter - отмена\n')
    for interval in (1,):  # (1, 60, 1440) = Минутки, часовки, дневки
        logger.info(f'Отмена подписки на интервал {interval} {qp_provider.unsubscribe_from_candles(class_code, sec_code, interval)["data"]}')
        logger.info(f'Статус подписки на интервал {interval}: {qp_provider.is_subscribed(class_code, sec_code, interval)["data"]}')

    # Выход
    qp_provider.close_connection_and_thread()  # Закрываем соединение для запросов и поток обработки функций обратного вызова
