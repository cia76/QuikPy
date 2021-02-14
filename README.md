# QuikPy
Библиотека-обертка, которая позволяет получить доступ к функционалу Quik на основе [Документации по языку LUA в QUIK](https://arqatech.com/ru/support/files/) из Python. В качестве коннектора используются lua-скрипты [проекта QUIKSharp](https://github.com/finsight/QUIKSharp).

### Для чего нужна
С помощью этой библиотеки можно создавать автоматические торговые системы любой сложности на Python для Quik. Также библиотека может быть использована для написания дополнений на Python к системам Технического Анализа. Например, для тестирования и автоматической торговли в [BackTrader](https://www.backtrader.com/).

### Установка коннектора. Метод 1. Из этого репозитория
1.	Скопируйте папку **QUIK\lua** в папку установки Quik. В ней находятся скрипты LUA.
2.	Скопируйте папку **QUIK\socket** в папку установки Quik.
3.	Запустите Quik. Из меню **Сервисы** выберите **Lua скрипты**. Нажмите кнопку **Добавить**. Выберете скрипт **QuikSharp.lua** Нажмите кнопку **OK**. Выделите скрипт из списка. Нажмите кнопку **Запустить**.

Скрипт должен запуститься без ошибок, в окне сообщений Quik выдать **QUIK# is waiting for client connection...**

### Установка коннектора. Метод 2. Из оригинального [репозитория QuikSharp](https://github.com/finsight/QUIKSharp/tree/master/src/QuikSharp/lua)
1. В файле **config.json** замените строки "responseHostname": "127.0.0.1" на "responseHostname": "*" Иначе удаленный компьютер с Quik не будет отвечать на запросы.
2. В файле **qsfunctions.lua** замените функцию **qsfunctions.getFuturesHolding(msg)** на:

        --- (ichechet) Через getFuturesHolding позиции не приходили. Пришлось сделать обработку таблицы futures_client_holding
        function qsfunctions.getFuturesHolding(msg)
            if msg.data ~= "" then
                local spl = split(msg.data, "|")
                local firmId, accId, secCode, posType = spl[1], spl[2], spl[3], spl[4]
            end
            
            local fchs = {}
            for i = 0, getNumberOf("futures_client_holding") - 1 do
                local fch = getItem("futures_client_holding", i)
                if msg.data == "" or (fch.firmid == firmId and fch.trdaccid == accId and fch.sec_code == secCode and fch.type == posType*1) then
                    table.insert(fchs, fch)
                end
            end
            msg.data = fchs
            return msg
        end
    Иначе, фьючерсные позиции приходить не будут.
3. В файле **qsfunctions.lua** дополните функцию **qsfunctions.get_candles_from_data_source(msg)**

        --- Возвращаем все свечи по заданному инструменту и интервалу
        --- (ichechet) Если исторические данные по тикеру не приходят, то QUIK блокируется. Чтобы это не происходило, вводим таймаут
        function qsfunctions.get_candles_from_data_source(msg)
            local ds, is_error = create_data_source(msg)
            if not is_error then
                --- Источник данных изначально приходит пустым. Нужно подождать пока он заполнится данными. Бесконечно ждать тоже нельзя. Вводим таймаут
                local s = 0 --- Будем ждать 5 секунд, прежде чем вернем таймаут
                repeat --- Ждем
                    sleep(100) --- 100 миллисекунд
                    s = s + 100 --- Запоминаем кол-во прошедших миллисекунд
                until (ds:Size() > 0 or s > 5000) --- До тех пор, пока не придут данные или пока не наступит таймаут
        
                local count = tonumber(split(msg.data, "|")[4]) --- возвращаем последние count свечей. Если равен 0, то возвращаем все доступные свечи.
                local class, sec, interval = get_candles_param(msg)
                local candles = {}
                local start_i = count == 0 and 1 or math.max(1, ds:Size() - count + 1)
                for i = start_i, ds:Size() do
                    local candle = fetch_candle(ds, i)
                    candle.sec = sec
                    candle.class = class
                    candle.interval = interval
                    table.insert(candles, candle)
                end
                ds:Close()
                msg.data = candles
            end
            return msg
        end
    Иначе, если исторические данные по тикеру Quik не возвращает, то он блокируется, дальнейшая работа невозможна.

### Начало работы
В папке Examples находится хорошо документированный код примеров. С них лучше начать разбираться с библиотекой.

1. **Connect.py** - Подключение, Singleton класс, проверка соединения, сервисные функции, пользователь обработчик событий.
2. **Accounts.py** - Список всех торговых счетов с лимитами, позициями, заявками и стоп заявками. Аналогично для заданного торгового счета.
3. **Ticker.py** - Информация о тикере, получение свечек.
4. **Stream.py** - Подписки на получение стакана, обезличенные сделки, новые свечки.
5. **Transactions.py** - Выставление новой лимитной/рыночной заявки, стоп заявки, отмена заявки.

### Авторство и право использования
Автор данной библиотеки Чечет Игорь Александрович. Библиотека написана в рамках проекта [Финансовая Лаборатория](https://chechet.org/) и предоставляется бесплатно. При распространении ссылка на автора и проект обязательны.

### Что дальше
Исправление ошибок, доработка и развитие библиотеки осуществляется как автором, так и сообществом проекта [Финансовая Лаборатория](https://chechet.org/).