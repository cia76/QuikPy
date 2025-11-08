import logging  # Выводим лог на консоль и в файл
from datetime import datetime  # Дата и время
import time  # Подписка на события по времени

from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QUIK#


def _on_quote(data): logger.info(f'Стакан - {data}')


def _on_all_trade(data): logger.info(f'Обезличенные сделки - {data}')


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    logger = logging.getLogger('QuikPy.Stream')  # Будем вести лог
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK по портам по умолчанию

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
                        datefmt='%d.%m.%Y %H:%M:%S',  # Формат даты
                        level=logging.DEBUG,  # Уровень логируемых событий NOTSET/DEBUG/INFO/WARNING/ERROR/CRITICAL
                        handlers=[logging.FileHandler('Stream.log', encoding='utf-8'), logging.StreamHandler()])  # Лог записываем в файл и выводим на консоль
    logging.Formatter.converter = lambda *args: datetime.now(tz=qp_provider.tz_msk).timetuple()  # В логе время указываем по МСК

    class_code = 'TQBR'  # Класс тикера
    sec_code = 'SBER'  # Тикер

    # class_code = 'SPBFUT'  # Класс тикера
    # sec_code = 'SiZ5'  # Для фьючерсов: <Код тикера><Месяц экспирации: 3-H, 6-M, 9-U, 12-Z><Последняя цифра года>

    # Запрос текущего стакана. Чтобы получать, в QUIK открыть таблицу "Котировки", указать тикер
    # logger.info(f'Текущий стакан {class_code}.{sec_code}: {qp_provider.get_quote_level2(class_code, sec_code)["data"]}')

    # Подписка на стакан. Чтобы отмена подписки работала корректно, в QUIK должна быть ЗАКРЫТА таблица "Котировки" тикера
    qp_provider.on_quote.subscribe(_on_quote)  # Подписываемся на стакан
    logger.info(f'Подписка на изменения стакана {class_code}.{sec_code}: {qp_provider.subscribe_level2_quotes(class_code, sec_code)["data"]}')
    logger.info(f'Статус подписки: {qp_provider.is_subscribed_level2_quotes(class_code, sec_code)["data"]}')
    sleep_secs = 5  # Кол-во секунд получения котировок
    logger.info(f'Секунд котировок: {sleep_secs}')
    time.sleep(sleep_secs)  # Ждем кол-во секунд получения котировок
    logger.info(f'Отмена подписки на изменения стакана: {qp_provider.unsubscribe_level2_quotes(class_code, sec_code)["data"]}')
    logger.info(f'Статус подписки: {qp_provider.is_subscribed_level2_quotes(class_code, sec_code)["data"]}')
    qp_provider.on_quote.unsubscribe(_on_quote)  # Отменяем подписку на стакан

    # Подписка на обезличенные сделки. Чтобы получать, в QUIK открыть "Таблицу обезличенных сделок", указать тикер
    qp_provider.on_all_trade.subscribe(_on_all_trade)  # Подписываемся на обезличенные сделки
    logger.info(f'Подписка на обезличенные сделки {class_code}.{sec_code}')
    sleep_secs = 5  # Кол-во секунд получения обезличенных сделок
    logger.info(f'Секунд обезличенных сделок: {sleep_secs}')
    time.sleep(sleep_secs)  # Ждем кол-во секунд получения обезличенных сделок
    logger.info(f'Отмена подписки на обезличенные сделки')
    qp_provider.on_all_trade.unsubscribe(_on_all_trade)  # Отменяем подписку на обезличенные сделки

    # Выход
    qp_provider.close_connection_and_thread()  # Закрываем соединение для запросов и поток обработки функций обратного вызова
