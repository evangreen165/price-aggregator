# Этап 1 — скелет агрегатора цен

Дата: 2026-11-12
Ветка: `main`
Тег: `v0.1-etap-1`

## Что сделано

- **Backend** (`backend/`): FastAPI-приложение `app.main` с эндпоинтами `/api/health`, `/api/plugins`,
  `/api/plugins/reload`; менеджер плагинов на pluggy (`app/plugins.py`), пример плагина
  `backend/plugins/example_parser.py`, конфигурация и пути для dev/frozen-режима
  (`app/core/config.py`).
- **Desktop-запуск**: uvicorn в daemon-потоке на `127.0.0.1:8000`, ожидание `/api/health`,
  окно PyWebview 1200×800. При занятом порте — ошибка в лог и выход. В frozen-режиме лог
  пишется в `%TEMP%\price_aggregator.log`.
- **Frontend** (`frontend/`): React 18 + TypeScript + Vite, React Router (4 раздела: Поиск,
  Результаты, Плагины, Настройки), React Query, API-клиент `src/api/client.ts`, тёмная тема на
  CSS-переменных без UI-библиотек.
- **Сборка** (`scripts/build.py`): `npm ci` (при отсутствии `node_modules`) → `npm run build` →
  PyInstaller `--onefile --windowed` → `dist/PriceAggregator.exe`.
- **CI** (`.github/workflows/ci.yml`): job `backend` (ruff + pytest) и job `frontend`
  (typecheck + build) на push/PR в `main`.
- **Прочее**: `.gitignore`, README, этот отчёт и скриншот окна.

## Как запустить

Dev (два терминала):

```bash
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev      # http://localhost:5173, /api проксируется на :8000
```

Сборка и запуск desktop-версии:

```bash
python scripts/build.py
dist/PriceAggregator.exe
```

## Проверки

### `ruff check .` (из `backend/`)

```
All checks passed!
```

### `pytest -q` (из `backend/`)

```
.....                                                                    [100%]
5 passed, 1 warning in 0.64s
```

Единственное предупреждение — `StarletteDeprecationWarning` из `fastapi.testclient` о переходе
на `httpx2`; на работу тестов не влияет.

### `npm run typecheck` / `npm run build` (из `frontend/`)

```
> tsc --noEmit            # без ошибок

vite v5.4.21 building for production...
✓ 84 modules transformed.
dist/index.html                 0.40 kB
dist/assets/index-*.css         3.73 kB
dist/assets/index-*.js        212.17 kB
✓ built in 1.81s
```

### Smoke-тест dev-режима

| Проверка                                   | Результат                       |
| ------------------------------------------ | ------------------------------- |
| `GET http://127.0.0.1:8000/api/health`     | `{"status":"ok"}`               |
| `GET http://127.0.0.1:8000/api/plugins`    | содержит `example`              |
| `GET http://127.0.0.1:5173/api/health`     | `{"status":"ok"}` (через proxy) |
| `GET http://127.0.0.1:5173/`               | отдаёт React-приложение         |
| `GET http://127.0.0.1:8000/plugins` (SPA)  | отдаёт `index.html`             |

### Сборка и smoke-тест `.exe`

`python scripts/build.py` → `dist/PriceAggregator.exe` (onefile, windowed). Запущенный exe:

- окно «Price Aggregator» 1200×788 без консольного окна;
- `GET http://127.0.0.1:8000/api/health` → `{"status":"ok"}`;
- `GET http://127.0.0.1:8000/api/plugins` →
  `[{"marketplace_id":"example","name":"Example Parser","version":"0.1.0","file":"example_parser.py","parser_class":"ExampleParser"}]`.

## Скриншот окна

`reports/screenshot-etap-1.png` — окно собранного `PriceAggregator.exe` (1200×788), снято
через `EnumWindows` + `PIL.ImageGrab` по границам окна.

Что видно в окне: тёмная тема, слева сайдбар с брендом «Price Aggregator / Этап 1 · скелет» и
пунктами «Поиск», «Результаты», «Плагины», «Настройки» (активен «Поиск»); сверху шапка
«Агрегатор цен» с подписью «FastAPI · React · PyWebview»; в контенте — карточка поиска с полем
ввода и неактивной кнопкой «Найти» и карточка «Проверка связи с бэкендом» с кнопкой
«Проверить связь».

## Чек-лист приёмки

- [x] `ruff check .` — без ошибок; `pytest -q` — 5 passed (вывод выше).
- [x] `npm run typecheck` и `npm run build` — успешно.
- [x] `GET /api/health` → `{"status":"ok"}`; через Vite proxy — то же.
- [x] `http://localhost:5173` отдаёт React-приложение; `/api/plugins` содержит `example`.
- [x] `python scripts/build.py` создаёт `dist/PriceAggregator.exe`; окно без консоли, health и
      список плагинов работают.
- [x] Коммит `c565af4` и тег `v0.1-etap-1` созданы; `main` и тег запушены в `origin`.
- [x] CI зелёный — run [#43219105670](https://github.com/evangreen165/price-aggregator/actions/runs/43219105670)
      завершился со статусом `success` (jobs `backend` и `frontend`).
- [x] `reports/etap-1.md` присутствует в репозитории.

## CI

Workflow `.github/workflows/ci.yml` отработал на push коммита `c565af4`:

- run id `43219105670`, `conclusion: success`, длительность ~21 с;
- job `backend`: `pip install -e ".[dev]"` → `ruff check .` → `pytest -q`;
- job `frontend`: `npm ci` → `npm run typecheck` → `npm run build`.

Страница: <https://github.com/evangreen165/price-aggregator/actions>

## Замечания

- PyInstaller предупреждает про отсутствующие `pycparser.lextab`, `pycparser.yacctab`, `tzdata`
  и `webview.platforms.android` — это необязательные платформенные зависимости, на Windows-сборку
  не влияют.
- Порт 8000 фиксирован; при занятом порте приложение пишет ошибку в лог и завершается. Выбор
  свободного порта — следующий этап.
- В каталоге репозитория лежит `.gittoken` (вне git, добавлен в `.gitignore`); в файлы проекта
  токены не записывались.
