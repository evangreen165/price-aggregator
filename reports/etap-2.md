# Этап 2 — архитектура парсеров, Kufar и Onliner, поиск

Дата: 2026-11-12
Ветка: `main`

## Что сделано

- **Фикс критического бага exe**: uvicorn запускается с `log_config=None`, чтобы он не трогал
  `sys.stdout` (в `--windowed`-сборках он `None`). Логирование настроено вручную: в frozen-режиме
  только в `%TEMP%\price_aggregator.log`, в dev — в stderr. exe больше не падает с
  `AttributeError: 'NoneType' object has no attribute 'isatty'`.
- **База парсеров** (`backend/app/parsers/`):
  - `base.py` — `@dataclass Product` (title, price, old_price, currency, url, marketplace, region,
    parsed_at) и `BaseParser(ABC)` с `async search(query, region) -> list[Product]`;
  - `__init__.py` — реестр `PARSERS` и `get_parser()` / `list_parsers()`.
- **Парсеры**:
  - `kufar.py` — чтение `__NEXT_DATA__` со страницы выдачи `kufar.by/l` (`price_byn` в копейках,
    регион из `ad_parameters`);
  - `onliner.py` — JSON-API `catalog.onliner.by/sdapi/catalog.api/search/products` (`price_min`);
  - `stubs.py` — заглушки `OzonParser` и `WbParser` (пустой список).
  - Зависимости: `httpx` перенесён в runtime-deps, добавлен `beautifulsoup4`.
- **API**: `POST /api/search` — принимает `{"query", "marketplaces", "region"}`, асинхронно зовёт
  выбранные парсеры, возвращает `{"results": {<marketplace>: [Product]}, "errors": {}}`. Ошибка
  одного маркетплейса не роняет остальные.
- **Frontend**: страница «Поиск» — чекбоксы Kufar/Onliner/Ozon/Wildberries, кнопка «Найти» шлёт
  `POST /api/search`, результат — простой список карточек (цена, валюта, регион, время парсинга,
  ссылка). Красивая таблица — этап 4.

## Проверки

### `ruff check .` (из `backend/`)

```
All checks passed!
```

### `pytest -q` (из `backend/`)

```
.............                                                            [100%]
13 passed, 1 warning in 0.71s
```

Тесты: парсеры (моки httpx `MockTransport` + прямое тестирование `_extract`), реестр, заглушки,
эндпоинт `/api/search` (monkeypatch парсеров, включая случай ошибки парсера).

### `npm run typecheck` / `npm run build` (из `frontend/`)

```
> tsc --noEmit            # без ошибок

vite v5.4.21 building for production...
✓ 84 modules transformed.
dist/index.html                 0.40 kB
dist/assets/index-*.css         4.56 kB
dist/assets/index-*.js        214.07 kB
✓ built in 1.04s
```

### Живой smoke-тест `/api/search` (запрос «монитор», kufar+onliner)

Dev-сервер и собранный exe:

```
kufar: 43 items   (напр. "Монитор 27'', IPS, 1920*1080, 165 Гц..." | 419.99 BYN | Минск)
onliner: 8 items  (напр. ASUS ROG Swift OLED PG34WCDN | 6642.68 BYN | belarus)
```

### Сборка и запуск `.exe`

`python scripts/build.py` → `dist/PriceAggregator.exe`. Запуск:

- окно открывается без консоли, сервер стартует, `/api/health` → `{"status":"ok"}`;
- `POST /api/search` через exe возвращает реальные товары Kufar и Onliner;
- лог `%TEMP%\price_aggregator.log` чистый, без `NoneType`/traceback (строки uvicorn.error/access
  теперь пишутся через нашу конфигурацию логирования).

Скриншот нового окна: `reports/screenshot-etap-2.png`.

## Чек-лист приёмки

- [x] `.exe` собирается и запускается без консоли и без ошибок Uvicorn.
- [x] Поиск «монитор» через Kufar и Onliner возвращает реальные товары.
- [x] `ruff check .` и `pytest -q` проходят (13 тестов, парсеры на моках).
- [ ] CI на GitHub зеленый — проверяется после push.

## Замечания

- Kufar: цена из `price_byn` в копейках делится на 100; валюта "BYR" из API приводится к BYN.
  Старая цена в JSON отсутствует — `old_price=None` (задел на HTML-вариант).
- Onliner: цены берутся из `prices.price_min`; регион фиксирован в параметре запроса.
- Ozon/WB — заглушки, версия 0.0.1.
- Парсеры не являются плагинами pluggy на этом этапе; реестр статический, плагинная интеграция —
  следующий этап.
