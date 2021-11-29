from time import time
import os.path

import pandas as pd
from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QuikSharp


def SaveCandlesToFile(classCode='TQBR', secCodes=('SBER',), timeFrame='D', compression=1, skipLast=False):
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
        if skipLast:  # Для дневных баров мы получаем еще несформировавшийся бар текущей сессии. Он нам не нужен
            newBars = newBars[:len(newBars) - 1]  # Берем все бары кроме последнего
        pdBars = pd.DataFrame.from_dict(pd.json_normalize(newBars), orient='columns')  # Внутренние колонки даты/времени разворачиваем в отдельные колонки
        pdBars.rename(columns={'datetime.year': 'year', 'datetime.month': 'month', 'datetime.day': 'day',
                               'datetime.hour': 'hour', 'datetime.min': 'minute', 'datetime.sec': 'second'},
                      inplace=True)  # Чтобы получить дату/время переименовываем колонки
        pdBars.index = pd.to_datetime(pdBars[['year', 'month', 'day', 'hour', 'minute', 'second']])  # Собираем дату/время из колонок
        pdBars = pdBars[['open', 'high', 'low', 'close', 'volume']]  # Отбираем нужные колонки
        pdBars.index.name = 'datetime'  # Ставим название индекса даты/времени
        pdBars.volume = pd.to_numeric(pdBars.volume, downcast='integer')  # Объемы могут быть только целыми
        print(f'- Первая запись в QUIK: {pdBars.index[0]}')
        print(f'- Последняя запись в QUIK: {pdBars.index[-1]}')
        print(f'- Кол-во записей в QUIK: {len(pdBars)}')

        if isFileExists:  # Если файл существует
            pdBars = pd.concat([fileBars, pdBars]).drop_duplicates(keep='last').sort_index()  # Объединяем файл с данными из QUIK, убираем дубликаты, сортируем заново
        pdBars.to_csv(fileName, sep='\t', date_format='%d.%m.%Y %H:%M')
        print(f'- В файл {fileName} сохранено записей: {len(pdBars)}')


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    startTime = time()  # Время начала запуска скрипта
    qpProvider = QuikPy()  # Вызываем конструктор QuikPy с подключением к локальному компьютеру с QUIK
    # qpProvider = QuikPy(Host='<Ваш IP адрес>')  # Вызываем конструктор QuikPy с подключением к удаленному компьютеру с QUIK

    timeFrame = 'M'  # Временной интервал: 'M'-Минуты, 'D'-дни, 'W'-недели, 'MN'-месяцы
    compression1 = 5  # Кол-во минут для минутного графика. Для остальных = 1
    compression2 = 15

    classCode = 'TQBR'  # Акции ММВБ
    secCodes = ('SBER', 'GMKN', 'GAZP', 'LKOH', 'TATN', 'YNDX', 'TCSG', 'ROSN', 'NVTK', 'MVID',
                'CHMF', 'POLY', 'OZON', 'ALRS', 'MAIL', 'MTSS', 'NLMK', 'MAGN', 'PLZL', 'MGNT',
                'MOEX', 'TRMK', 'RUAL', 'SNGS', 'AFKS', 'SBERP', 'SIBN', 'FIVE', 'SNGSP', 'AFLT',
                'IRAO', 'PHOR', 'TATNP', 'VTBR', 'QIWI', 'CBOM', 'FEES', 'BELU', 'TRNFP', 'FIXP')  # TOP 40 акций ММВБ
    SaveCandlesToFile(classCode, secCodes, skipLast=True)  # Получаем дневные бары без последнего бара
    SaveCandlesToFile(classCode, secCodes, timeFrame, compression1)  # Получаем 5-и минутные бары
    SaveCandlesToFile(classCode, secCodes, timeFrame, compression2)  # Получаем 15-и минутные бары

    classCode = 'SPBFUT'  # Фьючерсы РТС
    secCodes = ('SiH2', 'RIH2')  # Формат фьючерса: <Тикер><Месяц экспирации><Последняя цифра года> Месяц экспирации: 3-H, 6-M, 9-U, 12-Z
    SaveCandlesToFile(classCode, secCodes, skipLast=True)  # Получаем дневные бары без последнего бара
    SaveCandlesToFile(classCode, secCodes, timeFrame, compression1)  # Получаем 5-и минутные бары
    SaveCandlesToFile(classCode, secCodes, timeFrame, compression2)  # Получаем 15-и минутные бары

    qpProvider.CloseConnectionAndThread()  # Перед выходом закрываем соединение и поток QuikPy из любого экземпляра
    print(f'Скрипт выполнен за {(time() - startTime):.2f} с')
