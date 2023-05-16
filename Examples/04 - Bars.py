from time import time
import os.path

import pandas as pd
from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QuikSharp


def save_candles_to_file(class_code='TQBR', sec_codes=('SBER',), time_frame='D', compression=1,
                         skip_first_date=False, skip_last_date=False, four_price_doji=False):
    """Получение баров, объединение с имеющимися барами в файле (если есть), сохранение баров в файл

    :param str class_code: Код площадки
    :param tuple sec_codes: Коды тикеров в виде кортежа
    :param str time_frame: Временной интервал 'M'-Минуты, 'D'-дни, 'W'-недели, 'MN'-месяцы
    :param int compression: Кол-во минут для минутного графика. Для остальных = 1
    :param bool skip_first_date: Убрать бары на первую полученную дату
    :param bool skip_last_date: Убрать бары на последнюю полученную дату
    :param bool four_price_doji: Оставить бары с дожи 4-х цен
    """
    interval = compression  # Для минутных временнЫх интервалов ставим кол-во минут
    if time_frame == 'D':  # Дневной временной интервал
        interval = 1440  # В минутах
    elif time_frame == 'W':  # Недельный временной интервал
        interval = 10080  # В минутах
    elif time_frame == 'MN':  # Месячный временной интервал
        interval = 23200  # В минутах

    for sec_code in sec_codes:  # Пробегаемся по всем тикерам
        file_bars = None  # Дальше будем пытаться получить бары из файла
        file_name = f'{datapath}{class_code}.{sec_code}_{time_frame}{compression}.txt'
        file_exists = os.path.isfile(file_name)  # Существует ли файл
        if file_exists:  # Если файл существует
            print(f'Получение файла {file_name}')
            file_bars = pd.read_csv(file_name, sep='\t', index_col='datetime')  # Считываем файл в DataFrame
            file_bars.index = pd.to_datetime(file_bars.index, format='%d.%m.%Y %H:%M')  # Переводим индекс в формат datetime
            print(f'- Первая запись файла: {file_bars.index[0]}')
            print(f'- Последняя запись файла: {file_bars.index[-1]}')
            print(f'- Кол-во записей в файле: {len(file_bars)}')
        else:  # Файл не существует
            print(f'Файл {file_name} не найден и будет создан')
        new_bars = qp_provider.GetCandlesFromDataSource(class_code, sec_code, interval, 0)['data']  # Получаем все бары из QUIK
        pd_bars = pd.json_normalize(new_bars)  # Переводим список баров в pandas DataFrame
        pd_bars.rename(columns={'datetime.year': 'year', 'datetime.month': 'month', 'datetime.day': 'day',
                                'datetime.hour': 'hour', 'datetime.min': 'minute', 'datetime.sec': 'second'},
                       inplace=True)  # Чтобы получить дату/время переименовываем колонки
        pd_bars.index = pd.to_datetime(pd_bars[['year', 'month', 'day', 'hour', 'minute', 'second']])  # Собираем дату/время из колонок
        pd_bars = pd_bars[['open', 'high', 'low', 'close', 'volume']]  # Отбираем нужные колонки
        pd_bars.index.name = 'datetime'  # Ставим название индекса даты/времени
        pd_bars.volume = pd.to_numeric(pd_bars.volume, downcast='integer')  # Объемы могут быть только целыми
        if skip_first_date:  # Если убираем бары на первую дату
            len_with_first_date = len(pd_bars)  # Кол-во баров до удаления на первую дату
            first_date = pd_bars.index[0].date()  # Первая дата
            pd_bars.drop(pd_bars[(pd_bars.index.date == first_date)].index, inplace=True)  # Удаляем их
            print(f'- Удалено баров на первую дату {first_date}: {len_with_first_date - len(pd_bars)}')
        if skip_last_date:  # Если убираем бары на последнюю дату
            len_with_last_date = len(pd_bars)  # Кол-во баров до удаления на последнюю дату
            last_date = pd_bars.index[-1].date()  # Последняя дата
            pd_bars.drop(pd_bars[(pd_bars.index.date == last_date)].index, inplace=True)  # Удаляем их
            print(f'- Удалено баров на последнюю дату {last_date}: {len_with_last_date - len(pd_bars)}')
        if not four_price_doji:  # Если удаляем дожи 4-х цен
            len_with_doji = len(pd_bars)  # Кол-во баров до удаления дожи
            pd_bars.drop(pd_bars[(pd_bars.high == pd_bars.low)].index, inplace=True)  # Удаляем их по условию High == Low
            print('- Удалено дожи 4-х цен:', len_with_doji - len(pd_bars))
        print('- Первая запись в QUIK:', pd_bars.index[0])
        print('- Последняя запись в QUIK:', pd_bars.index[-1])
        print('- Кол-во записей в QUIK:', len(pd_bars))
        if file_exists:  # Если файл существует
            pd_bars = pd.concat([file_bars, pd_bars]).drop_duplicates(keep='last').sort_index()  # Объединяем файл с данными из QUIK, убираем дубликаты, сортируем заново
        pd_bars.to_csv(file_name, sep='\t', date_format='%d.%m.%Y %H:%M')
        print(f'- В файл {file_name} сохранено записей: {len(pd_bars)}')


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    start_time = time()  # Время начала запуска скрипта
    qp_provider = QuikPy()  # Вызываем конструктор QuikPy с подключением к локальному компьютеру с QUIK

    class_code = 'TQBR'  # Акции ММВБ
    # class_code = 'SPBFUT'  # Фьючерсы
    sec_codes = ('SBER', 'VTBR', 'GAZP', 'MTLR', 'LKOH', 'PLZL', 'SBERP', 'BSPB', 'POLY', 'RNFT',
                 'GMKN', 'AFLT', 'NVTK', 'TATN', 'YNDX', 'MGNT', 'ROSN', 'AFKS', 'NLMK', 'ALRS',
                 'MOEX', 'SMLT', 'MAGN', 'CHMF', 'CBOM', 'MTLRP', 'SNGS', 'BANEP', 'MTSS', 'IRAO',
                 'SNGSP', 'SELG', 'UPRO', 'RUAL', 'TRNFP', 'FEES', 'SGZH', 'BANE', 'PHOR', 'PIKK')  # TOP 40 акций ММВБ
    # sec_codes = ('SBER',)  # Для тестов
    # sec_codes = ('SiM3', 'RIM3')  # Формат фьючерса: <Тикер><Месяц экспирации><Последняя цифра года> Месяц экспирации: 3-H, 6-M, 9-U, 12-Z
    datapath = '..\\..\\Data\\'  # Путь к файлам (Windows)

    # Получаем бары в первый раз / когда идет сессия
    # save_candles_to_file(classCode, secCodes, skipLastDate=True, fourPriceDoji=True)  # Дневные бары
    # save_candles_to_file(classCode, secCodes, 'M', 60, skipFirstDate=True, skipLastDate=True)  # часовые бары
    # save_candles_to_file(classCode, secCodes, 'M', 15, skipFirstDate=True, skipLastDate=True)  # 15-и минутные бары
    # save_candles_to_file(classCode, secCodes, 'M', 5, skipFirstDate=True, skipLastDate=True)  # 5-и минутные бары
    # save_candles_to_file(classCode, secCodes, 'M', 1, skipFirstDate=True, skipLastDate=True)  # минутные бары

    # Получаем бары, когда сессия не идет
    save_candles_to_file(class_code, sec_codes, four_price_doji=True)  # Дневные бары
    save_candles_to_file(class_code, sec_codes, 'M', 60, skip_first_date=True)  # часовые бары
    save_candles_to_file(class_code, sec_codes, 'M', 15, skip_first_date=True)  # 15-и минутные бары
    save_candles_to_file(class_code, sec_codes, 'M', 5, skip_first_date=True)  # 5-и минутные бары
    save_candles_to_file(class_code, sec_codes, 'M', 1, skip_first_date=True)  # минутные бары

    qp_provider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
    print(f'Скрипт выполнен за {(time() - start_time):.2f} с')
