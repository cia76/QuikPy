from time import time
import os.path

import pandas as pd
from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QuikSharp


def SaveCandlesToFile(classCode='TQBR', secCodes=('SBER',), timeFrame='D', compression=1,
                      skipFirstDate=False, skipLastDate=False, fourPriceDoji=False):
    """Получение баров, объединение с имеющимися барами в файле (если есть), сохранение баров в файл

    :param classCode: Код рынка
    :param secCodes: Коды тикеров в виде кортежа
    :param timeFrame: Временной интервал 'M'-Минуты, 'D'-дни, 'W'-недели, 'MN'-месяцы
    :param compression: Кол-во минут для минутного графика. Для остальных = 1
    :param skipFirstDate: Убрать бары на первую полученную дату
    :param skipLastDate: Убрать бары на последнюю полученную дату
    :param fourPriceDoji: Оставить бары с дожи 4-х цен
    """
    interval = compression  # Для минутных временнЫх интервалов ставим кол-во минут
    if timeFrame == 'D':  # Дневной временной интервал
        interval = 1440  # В минутах
    elif timeFrame == 'W':  # Недельный временной интервал
        interval = 10080  # В минутах
    elif timeFrame == 'MN':  # Месячный временной интервал
        interval = 23200  # В минутах

    for secCode in secCodes:  # Пробегаемся по всем тикерам
        fileName = f'..\\..\\Data\\{classCode}.{secCode}_{timeFrame}{compression}.txt'
        isFileExists = os.path.isfile(fileName)  # Существует ли файл
        if not isFileExists:  # Если файл не существует
            print(f'Файл {fileName} не найден и будет создан')
        else:  # Файл существует
            print(f'Получение файла {fileName}')
            fileBars = pd.read_csv(fileName, sep='\t', index_col='datetime')  # Считываем файл в DataFrame
            fileBars.index = pd.to_datetime(fileBars.index, format='%d.%m.%Y %H:%M')  # Переводим индекс в формат datetime
            print(f'- Первая запись файла: {fileBars.index[0]}')
            print(f'- Последняя запись файла: {fileBars.index[-1]}')
            print(f'- Кол-во записей в файле: {len(fileBars)}')

        newBars = qpProvider.GetCandlesFromDataSource(classCode, secCode, interval, 0)["data"]  # Получаем все свечки
        pdBars = pd.DataFrame.from_dict(pd.json_normalize(newBars), orient='columns')  # Внутренние колонки даты/времени разворачиваем в отдельные колонки
        pdBars.rename(columns={'datetime.year': 'year', 'datetime.month': 'month', 'datetime.day': 'day',
                               'datetime.hour': 'hour', 'datetime.min': 'minute', 'datetime.sec': 'second'},
                      inplace=True)  # Чтобы получить дату/время переименовываем колонки
        pdBars.index = pd.to_datetime(pdBars[['year', 'month', 'day', 'hour', 'minute', 'second']])  # Собираем дату/время из колонок
        pdBars = pdBars[['open', 'high', 'low', 'close', 'volume']]  # Отбираем нужные колонки
        pdBars.index.name = 'datetime'  # Ставим название индекса даты/времени
        pdBars.volume = pd.to_numeric(pdBars.volume, downcast='integer')  # Объемы могут быть только целыми
        if skipFirstDate:  # Если убираем бары на первую дату
            lenWithFirstDate = len(pdBars)  # Кол-во баров до удаления на первую дату
            firstDate = pdBars.index[0].date()  # Первая дата
            pdBars.drop(pdBars[(pdBars.index.date == firstDate)].index, inplace=True)  # Удаляем их
            print(f'- Удалено баров на первую дату {firstDate}: {lenWithFirstDate - len(pdBars)}')
        if skipLastDate:  # Если убираем бары на последнюю дату
            lenWithLastDate = len(pdBars)  # Кол-во баров до удаления на последнюю дату
            lastDate = pdBars.index[-1].date()  # Последняя дата
            pdBars.drop(pdBars[(pdBars.index.date == lastDate)].index, inplace=True)  # Удаляем их
            print(f'- Удалено баров на последнюю дату {lastDate}: {lenWithLastDate - len(pdBars)}')
        if not fourPriceDoji:  # Если удаляем дожи 4-х цен
            lenWithDoji = len(pdBars)  # Кол-во баров до удаления дожи
            pdBars.drop(pdBars[(pdBars.high == pdBars.low)].index, inplace=True)  # Удаляем их по условия High == Low
            print('- Удалено дожи 4-х цен:', lenWithDoji - len(pdBars))
        print('- Первая запись в QUIK:', pdBars.index[0])
        print('- Последняя запись в QUIK:', pdBars.index[-1])
        print('- Кол-во записей в QUIK:', len(pdBars))

        if isFileExists:  # Если файл существует
            pdBars = pd.concat([fileBars, pdBars]).drop_duplicates(keep='last').sort_index()  # Объединяем файл с данными из QUIK, убираем дубликаты, сортируем заново
        pdBars.to_csv(fileName, sep='\t', date_format='%d.%m.%Y %H:%M')
        print(f'- В файл {fileName} сохранено записей: {len(pdBars)}')


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    startTime = time()  # Время начала запуска скрипта
    qpProvider = QuikPy()  # Вызываем конструктор QuikPy с подключением к локальному компьютеру с QUIK
    # qpProvider = QuikPy(Host='<Ваш IP адрес>')  # Вызываем конструктор QuikPy с подключением к удаленному компьютеру с QUIK

    classCode = 'TQBR'  # Акции ММВБ
    # classCode = 'SPBFUT'  # Фьючерсы РТС
    # secCodes = ('GAZP',)  # Для тестов
    secCodes = ('GAZP', 'LKOH', 'SBER', 'NVTK', 'YNDX', 'GMKN', 'ROSN', 'MTLR', 'MGNT', 'CHMF',
                'PHOR', 'VTBR', 'TCSG', 'PLZL', 'ALRS', 'MAGN', 'CBOM', 'SMLT', 'MVID', 'AFLT',
                'SNGS', 'SBERP', 'NLMK', 'RUAL', 'MTSS', 'TATN', 'MOEX', 'VKCO', 'MTLRP', 'AFKS',
                'SNGSP', 'PIKK', 'ISKJ', 'OZON', 'POLY', 'HYDR', 'RASP', 'IRAO', 'SIBN', 'FESH')  # TOP 40 акций ММВБ
    # secCodes = ('SiM2', 'RIM2')  # Формат фьючерса: <Тикер><Месяц экспирации><Последняя цифра года> Месяц экспирации: 3-H, 6-M, 9-U, 12-Z

    # Получаем бары в первый раз / когда идет сессия
    SaveCandlesToFile(classCode, secCodes, skipLastDate=True, fourPriceDoji=True)  # Дневные бары
    SaveCandlesToFile(classCode, secCodes, 'M', 15, skipFirstDate=True, skipLastDate=True)  # 15-и минутные бары
    SaveCandlesToFile(classCode, secCodes, 'M', 5, skipFirstDate=True, skipLastDate=True)  # 5-и минутные бары

    # Получаем бары, когда сессия не идет
    # SaveCandlesToFile(classCode, secCodes, fourPriceDoji=True)  # Дневные бары
    # SaveCandlesToFile(classCode, secCodes, 'M', 15, skipFirstDate=True)  # 15-и минутные бары
    # SaveCandlesToFile(classCode, secCodes, 'M', 5, skipFirstDate=True)  # 5-и минутные бары

    qpProvider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
    print(f'Скрипт выполнен за {(time() - startTime):.2f} с')
