import logging  # Выводим лог на консоль и в файл
from datetime import datetime  # Дата и время
from threading import Thread  # Каждый скрипт будем запускать в отдельном потоке

from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QUIK#


def script1(provider: QuikPy):  # 1-ый скрипт
    is_connected = provider.is_connected()['data']  # Состояние подключения терминала к серверу QUIK
    logger.info(f'script1: Терминал QUIK подключен к серверу: {is_connected == 1}')
    logger.info(f'script1: Отклик QUIK на команду Ping: {provider.ping()["data"]}')  # Проверка работы скрипта QuikSharp. Должен вернуть Pong


def script2(provider: QuikPy):  # 2-ой скрипт
    msg = 'Hello from Python!'
    logger.info(f'script2: Отправка сообщения в QUIK: {msg}{provider.message_info(msg)["data"]}')  # Проверка работы QUIK. Сообщение в QUIK должно показаться как информационное


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    logger = logging.getLogger('QuikPy.MultiScripts')  # Будем вести лог
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK по портам по умолчанию

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
                        datefmt='%d.%m.%Y %H:%M:%S',  # Формат даты
                        level=logging.DEBUG,  # Уровень логируемых событий NOTSET/DEBUG/INFO/WARNING/ERROR/CRITICAL
                        handlers=[logging.FileHandler('MultiScripts.log'), logging.StreamHandler()])  # Лог записываем в файл и выводим на консоль
    logging.Formatter.converter = lambda *args: datetime.now(tz=qp_provider.tz_msk).timetuple()  # В логе время указываем по МСК

    thread1 = Thread(target=script1, args=(qp_provider,), name='script1')  # Поток запуска 1-го скрипта
    thread1.start()  # Запускаем 1-ый скрипт в отдельном потоке
    thread2 = Thread(target=script2, args=(qp_provider,), name='script2')  # Поток запуска 2-го скрипта
    thread2.start()  # Запускаем 2-ой скрипт в отдельном потоке
    thread1.join()  # Ожидаем завершения 1-го скрипта
    thread2.join()  # Ожидаем завершения 2-го скрипта
    qp_provider.close_connection_and_thread()  # Перед выходом закрываем соединение для запросов и поток обработки функций обратного вызова