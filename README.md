# Price Aggregator

[![CI](https://github.com/evangreen165/price-aggregator/actions/workflows/ci.yml/badge.svg)](https://github.com/evangreen165/price-aggregator/actions/workflows/ci.yml)

Десктоп-приложение для сравнения цен на товары с разных маркетплейсов. Этап 1 — рабочий скелет:
FastAPI-бэкенд с плагинной архитектурой, React-фронтенд с четырьмя разделами, запуск в нативном
окне через PyWebview, сборка `.exe` через PyInstaller и CI на GitHub Actions.

Реальных парсеров маркетплейсов, фильтров, Excel-экспорта и аналитики на этом этапе нет.

## Структура

```
backend/
  app/
    main.py            FastAPI-приложение, API и запуск desktop-окна
    plugins.py         менеджер плагинов на pluggy
    parsers/           база парсеров и реестр (base, kufar, onliner, stubs)
    core/config.py     конфигурация и пути (в т.ч. frozen-режим)
  plugins/
    example_parser.py  пример плагина (фейковые данные, без сети)
  tests/               pytest: health, плагины, парсеры, search API
  pyproject.toml
frontend/
  src/                 React + TypeScript + React Router + React Query
  vite.config.ts       dev-proxy /api -> 127.0.0.1:8000
scripts/build.py       сборка фронтенда и упаковка .exe
.github/workflows/     CI (backend: ruff + pytest, frontend: typecheck + build)
reports/               отчёт по этапу
```

## Требования

- Python 3.12
- Node.js 18+ (npm)
- WebView2 Runtime (в Windows 11 уже установлен)

## Установка

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -e ".[dev,build]"

cd ../frontend
npm install
```

## Dev-режим (два терминала)

```bash
# терминал 1 — бэкенд
cd backend
uvicorn app.main:app --reload --port 8000

# терминал 2 — фронтенд с проксированием /api
cd frontend
npm run dev
```

Откройте `http://localhost:5173`. Vite проксирует `/api` на `http://127.0.0.1:8000`.

## Сборка `.exe`

```bash
python scripts/build.py
```

Скрипт собирает фронтенд (`npm ci` при отсутствии `node_modules`, затем `npm run build`) и упаковывает
всё в один файл `dist/PriceAggregator.exe` (`--onefile --windowed`). Бэкенд отдаёт собранный
фронтенд из бандла, окно открывается на `http://127.0.0.1:8000`.

Лог frozen-сборки: `%TEMP%\price_aggregator.log`.

## API

| Метод | Путь                  | Описание                                  |
| ----- | --------------------- | ----------------------------------------- |
| GET   | `/api/health`         | `{"status": "ok"}`                        |
| GET   | `/api/plugins`        | список загруженных парсеров               |
| POST  | `/api/plugins/reload` | перезагрузить плагины и вернуть новый список |
| POST  | `/api/search`         | поиск: `{"query","marketplaces","region"}` → `{"results":{"<marketplace>":[Product]}, "errors":{}}` |

Тело запроса `/api/search`:

```json
{"query": "монитор", "marketplaces": ["kufar", "onliner"], "region": "belarus"}
```

## Парсеры

Реализованы: **Kufar** (JSON из `__NEXT_DATA__` на странице выдачи) и **Onliner**
(JSON-API каталога `sdapi/catalog.api/search/products`). Ozon и Wildberries — заглушки,
реализация отложена из-за сложных защит. Реестр и база — в `backend/app/parsers/`.

## Как добавить плагин

1. Создайте файл `backend/plugins/<name>.py` (файлы с `_` в начале игнорируются).
2. Опишите класс парсера с атрибутами `marketplace_id`, `name`, `version` и методом `search(query)`.
3. Зарегистрируйте его:

```python
from app.plugins import hookimpl


class MyParser:
    marketplace_id = "my-market"
    name = "My Market"
    version = "0.1.0"

    def search(self, query: str) -> list[dict]:
        return []


@hookimpl
def register_parser():
    return "my-market", MyParser
```

4. Нажмите «Перезагрузить плагины» в разделе «Плагины» или вызовите `POST /api/plugins/reload`.

## Проверки

```bash
cd backend
ruff check .
pytest -q

cd ../frontend
npm run typecheck
npm run build
```

## Лицензия

Не задана на этом этапе.
