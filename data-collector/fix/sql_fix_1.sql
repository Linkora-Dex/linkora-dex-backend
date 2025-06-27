-- Проверка наличия проблемных записей
SELECT symbol, COUNT(*)
FROM candles
WHERE volume::text LIKE '%E%' OR quote_volume::text LIKE '%E%'
GROUP BY symbol;

-- Обновление записей с научной нотацией
UPDATE candles
SET
    volume = CASE
        WHEN volume::text LIKE '%E%' THEN volume::numeric::decimal(20,8)
        ELSE volume
    END,
    quote_volume = CASE
        WHEN quote_volume::text LIKE '%E%' THEN quote_volume::numeric::decimal(20,8)
        ELSE quote_volume
    END,
    taker_buy_volume = CASE
        WHEN taker_buy_volume::text LIKE '%E%' THEN taker_buy_volume::numeric::decimal(20,8)
        ELSE taker_buy_volume
    END,
    taker_buy_quote_volume = CASE
        WHEN taker_buy_quote_volume::text LIKE '%E%' THEN taker_buy_quote_volume::numeric::decimal(20,8)
        ELSE taker_buy_quote_volume
    END
WHERE volume::text LIKE '%E%'
   OR quote_volume::text LIKE '%E%'
   OR taker_buy_volume::text LIKE '%E%'
   OR taker_buy_quote_volume::text LIKE '%E%';