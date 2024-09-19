import logging  # Выводим лог на консоль и в файл
from datetime import datetime  # Дата и время
from time import time
import os.path

import pandas as pd

from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QUIK#


logger = logging.getLogger('QuikPy.Bars')  # Будем вести лог. Определяем здесь, т.к. возможен внешний вызов ф-ии
datapath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'Data', 'QUIK', '')  # Путь сохранения файла истории
delimiter = '\t'  # Разделитель значений в файле истории. По умолчанию табуляция
dt_format = '%d.%m.%Y %H:%M'  # Формат представления даты и времени в файле истории. По умолчанию русский формат


# noinspection PyShadowingNames
def load_candles_from_file(class_code, security_code, tf) -> pd.DataFrame:
    """Получение бар из файла

    :param str class_code: Код режима торгов
    :param str security_code: Код тикера
    :param str tf: Временной интервал https://ru.wikipedia.org/wiki/Таймфрейм
    """
    filename = f'{datapath}{class_code}.{security_code}_{tf}.txt'
    if os.path.isfile(filename):  # Если файл существует
        logger.info(f'Получение файла {filename}')
        file_bars = pd.read_csv(filename,  # Имя файла
                                sep=delimiter,  # Разделитель значений
                                usecols=['datetime', 'open', 'high', 'low', 'close', 'volume'],  # Для ускорения обработки задаем колонки, которые будут нужны для исследований
                                parse_dates=['datetime'],  # Колонку datetime разбираем как дату/время
                                dayfirst=True,  # В дате/времени сначала идет день, затем месяц и год
                                index_col='datetime')  # Индексом будет колонка datetime  # Дневки тикера
        logger.info(f'Первый бар    : {file_bars.index[0]:{dt_format}}')
        logger.info(f'Последний бар : {file_bars.index[-1]:{dt_format}}')
        logger.info(f'Кол-во бар    : {len(file_bars)}')
        return file_bars
    else:  # Если файл не существует
        logger.warning(f'Файл {filename} не найден')
        return pd.DataFrame()


# noinspection PyShadowingNames
def get_candles_from_provider(qp_provider, class_code, security_code, tf) -> pd.DataFrame:
    """Получение бар из провайдера

    :param QuikPy qp_provider: Провайдер QUIK
    :param str class_code: Код режима торгов
    :param str security_code: Код тикера
    :param str tf: Временной интервал https://ru.wikipedia.org/wiki/Таймфрейм
    """
    time_frame, _ = qp_provider.timeframe_to_quik_timeframe(tf)  # Временной интервал QUIK
    logger.info(f'Получение истории {class_code}.{security_code} {tf} из QUIK')
    history = qp_provider.get_candles_from_data_source(class_code, security_code, time_frame)  # Получаем все бары из QUIK
    if not history:  # Если бары не получены
        logger.error('Ошибка при получении истории: История не получена')
        return pd.DataFrame()  # то выходим, дальше не продолжаем
    if 'data' not in history:  # Если бар нет в словаре
        logger.error(f'Ошибка при получении истории: {history}')
        return pd.DataFrame()  # то выходим, дальше не продолжаем
    new_bars = history['data']  # Получаем все бары из QUIK
    if len(new_bars) == 0:  # Если новых бар нет
        logger.info('Новых записей нет')
        return pd.DataFrame()  # то выходим, дальше не продолжаем
    pd_bars = pd.json_normalize(new_bars)  # Переводим список бар в pandas DataFrame
    pd_bars.rename(columns={'datetime.year': 'year', 'datetime.month': 'month', 'datetime.day': 'day',
                            'datetime.hour': 'hour', 'datetime.min': 'minute', 'datetime.sec': 'second'},
                   inplace=True)  # Чтобы получить дату/время переименовываем колонки
    pd_bars['datetime'] = pd.to_datetime(pd_bars[['year', 'month', 'day', 'hour', 'minute', 'second']])  # Собираем дату/время из колонок
    pd_bars = pd_bars[['datetime', 'open', 'high', 'low', 'close', 'volume']]  # Отбираем нужные колонки. Дата и время нужны, чтобы не удалять одинаковые OHLCV на разное время
    pd_bars.index = pd_bars['datetime']  # Дата/время также будет индексом
    pd_bars.volume = pd.to_numeric(pd_bars.volume, downcast='integer')  # Объемы могут быть только целыми
    pd_bars.drop_duplicates(keep='last', inplace=True)  # Могут быть получены дубли, удаляем их
    logger.info(f'Первый бар    : {pd_bars.index[0]:{dt_format}}')
    logger.info(f'Последний бар : {pd_bars.index[-1]:{dt_format}}')
    logger.info(f'Кол-во бар    : {len(pd_bars)}')
    return pd_bars


# noinspection PyShadowingNames
def save_candles_to_file(qp_provider, class_code, security_codes, tf='D1',
                         skip_first_date=False, skip_last_date=False, four_price_doji=False):
    """Получение новых бар из провайдера, объединение с имеющимися барами в файле (если есть), сохранение бар в файл

    :param QuikPy qp_provider: Провайдер QUIK
    :param str class_code: Код режима торгов
    :param tuple[str] security_codes: Коды тикеров в виде кортежа
    :param str tf: Временной интервал https://ru.wikipedia.org/wiki/Таймфрейм
    :param bool skip_first_date: Убрать бары на первую полученную дату
    :param bool skip_last_date: Убрать бары на последнюю полученную дату
    :param bool four_price_doji: Оставить бары с дожи 4-х цен
    """
    for security_code in security_codes:  # Пробегаемся по всем тикерам
        file_bars = load_candles_from_file(class_code, security_code, tf)  # Получаем бары из файла
        pd_bars = get_candles_from_provider(qp_provider, class_code, security_code, tf)  # Получаем бары из провайдера
        if pd_bars.empty:  # Если бары не получены
            logger.info('Новых бар нет')
            continue  # то переходим к следующему тикеру, дальше не продолжаем
        if file_bars.empty and skip_first_date:  # Если файла нет, и убираем бары на первую дату
            len_with_first_date = len(pd_bars)  # Кол-во баров до удаления на первую дату
            first_date = pd_bars.index[0].date()  # Первая дата
            pd_bars.drop(pd_bars[(pd_bars.index.date == first_date)].index, inplace=True)  # Удаляем их
            logger.warning(f'Удалено баров на первую дату {first_date:{dt_format}}: {len_with_first_date - len(pd_bars)}')
        if skip_last_date:  # Если убираем бары на последнюю дату
            len_with_last_date = len(pd_bars)  # Кол-во баров до удаления на последнюю дату
            last_date = pd_bars.index[-1].date()  # Последняя дата
            pd_bars.drop(pd_bars[(pd_bars.index.date == last_date)].index, inplace=True)  # Удаляем их
            logger.warning(f'Удалено баров на последнюю дату {last_date:{dt_format}}: {len_with_last_date - len(pd_bars)}')
        if not four_price_doji:  # Если удаляем дожи 4-х цен
            len_with_doji = len(pd_bars)  # Кол-во баров до удаления дожи
            pd_bars.drop(pd_bars[(pd_bars.high == pd_bars.low)].index, inplace=True)  # Удаляем их по условию High == Low
            logger.warning('Удалено дожи 4-х цен:', len_with_doji - len(pd_bars))
        if len(pd_bars) == 0:  # Если нечего объединять
            logger.info('Новых бар нет')
            continue  # то переходим к следующему тикеру, дальше не продолжаем
        if not file_bars.empty:  # Если файл существует
            pd_bars = pd.concat([file_bars, pd_bars]).drop_duplicates(keep='last').sort_index()  # Объединяем файл с данными из QUIK, убираем дубликаты, сортируем заново
        pd_bars = pd_bars[['open', 'high', 'low', 'close', 'volume']]  # Отбираем нужные колонки. Дата и время будет экспортирована как индекс
        filename = f'{datapath}{class_code}.{security_code}_{tf}.txt'
        logger.info('Сохранение файла')
        pd_bars.to_csv(filename, sep=delimiter, date_format=dt_format)
        logger.info(f'Первый бар    : {pd_bars.index[0]:{dt_format}}')
        logger.info(f'Последний бар : {pd_bars.index[-1]:{dt_format}}')
        logger.info(f'Кол-во бар    : {len(pd_bars)}')
        logger.info(f'В файл {filename} сохранено записей: {len(pd_bars)}')


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    start_time = time()  # Время начала запуска скрипта
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
                        datefmt='%d.%m.%Y %H:%M:%S',  # Формат даты
                        level=logging.DEBUG,  # Уровень логируемых событий NOTSET/DEBUG/INFO/WARNING/ERROR/CRITICAL
                        handlers=[logging.FileHandler('Bars.log'), logging.StreamHandler()])  # Лог записываем в файл и выводим на консоль
    logging.Formatter.converter = lambda *args: datetime.now(tz=qp_provider.tz_msk).timetuple()  # В логе время указываем по МСК

    class_code = 'TQBR'  # Акции ММВБ
    security_codes = ('SBER',)  # Для тестов
    # security_codes = ('GAZP', 'SBER', 'LKOH', 'MTLR', 'TCSG', 'VTBR', 'NVTK', 'ROSN', 'GMKN', 'PLZL',
    #                   'SGZH', 'MVID', 'TRNFP', 'AFLT', 'AFKS', 'MTLRP', 'NLMK', 'MTSS', 'TATN', 'SBERP',
    #                   'VKCO', 'MOEX', 'SMLT', 'ALRS', 'CHMF', 'RNFT', 'BSPB', 'MAGN', 'FLOT', 'POSI',
    #                   'RUAL', 'PHOR', 'IRAO', 'PIKK', 'AQUA', 'RTKM', 'UPRO', 'TATNP', 'FEES', 'SELG')  # TOP 40 акций ММВБ
    # class_code = 'SPBFUT'  # Фьючерсы
    # security_codes = ('SiU4', 'RIU4')  # Формат фьючерса: <Тикер><Месяц экспирации><Последняя цифра года> Месяц экспирации: 3-H, 6-M, 9-U, 12-Z
    # security_codes = ('USDRUBF', 'EURRUBF', 'CNYRUBF', 'GLDRUBF', 'IMOEXF')  # Вечные фьючерсы ММВБ

    skip_last_date = True  # Если получаем данные внутри сессии, то не берем бары за дату незавершенной сессии
    # skip_last_date = False  # Если получаем данные, когда рынок не работает, то берем все бары
    save_candles_to_file(qp_provider, class_code, security_codes, 'D1', skip_last_date=skip_last_date, four_price_doji=True)  # Дневные бары
    # save_candles_to_file(qp_provider, class_code, security_codes, 'M60', skip_last_date=skip_last_date)  # Часовые бары
    # save_candles_to_file(qp_provider, class_code, security_codes, 'M15', skip_last_date=skip_last_date)  # 15-и минутные бары
    # save_candles_to_file(qp_provider, class_code, security_codes, 'M5', skip_last_date=skip_last_date)  # 5-и минутные бары
    # save_candles_to_file(qp_provider, class_code, security_codes, 'M1', skip_last_date=skip_last_date, four_price_doji=True)  # Минутные бары

    qp_provider.close_connection_and_thread()  # Закрываем соединение для запросов и поток обработки функций обратного вызова

    print(f'Скрипт выполнен за {(time() - start_time):.2f} с')
