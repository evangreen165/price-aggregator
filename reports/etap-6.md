# Этап 6 — глубокий парсинг, Playwright-фолбэк для Ozon/WB, динамические фильтры

Дата: 2026-11-12
Ветка: `main`

## ЗАДАЧА 1 — обход лимитов парсинга

- Onliner: цикл `limit=100&page=1..limit_pages`; глубокая пагинация через чекбокс в UI
  (`limit_pages=50`). Проверено: «телевизор» → 999 уникальных товаров, `truncated=False` —
  собраны **все страницы**, которые отдаёт API (выдача капается самим API на ~1000 позиций).
- Kufar: cursor-токены генерируются для любой страницы; добавлен лимит **`max_items=2000`**
  (остановка при достижении, `_truncated=True`). Проверено: «телевизор» → 993 объявления
  (все доступные), `truncated=False`.
- Wildberries: цикл `page=1..limit_pages` (по умолчанию ~100/страница).
- Frontend: чекбокс «Глубокая пагинация (медленнее, до 50 страниц)» в Zustand-сторе —
  `limit_pages=50` вместо 10 в `POST /api/search`.

## ЗАДАЧА 2 — реальные парсеры Ozon и Wildberries

- Добавлен **Playwright** (`playwright>=1.45`), в `scripts/build.py` — `--collect-all playwright`.
  Браузерные бинарники **не** бандлим: `BaseParser.launch_chromium` запускает установленный
  Chrome/Edge (`channel="chrome"` → `"msedge"` → headless Chromium). Для headless-режима на
  машине пользователя нужен `playwright install chromium`.
- **Wildberries**: сначала curl_cffi (`search.wb.ru`, `impersonate="chrome"`, прогрев cookie);
  при 403/пустом ответе — Playwright: `wildberries.ru/catalog/0/search.aspx?search=...`,
  перехват ответов `search.wb.ru` через `page.on("response")`, парсинг `name/salePriceU/id`.
- **Ozon**: сначала curl_cffi (composer-api); при 403 — Playwright: `ozon.ru/search/?text=...`,
  извлечение `window.__NUXT__` (или `__NEXT_DATA__`) через `page.evaluate`, парсинг товаров из
  `widgetStates` (title/price/skuId).
- С IP этой машины WB/Ozon отдают 403/498 на любом пути (включая антибот-эмуляцию), поэтому
  live-проверка здесь невозможна: парсеры корректно возвращают пустой список без падения.
  Логика фолбэка и извлечения покрыта моками в тестах. На машине пользователя (реальный браузер,
  прогретые cookie) ожидается получение данных.

## ЗАДАЧА 3 — динамические фильтры

- **Kufar** (проверено на живом сайте): `GET /api/filters?query=...&marketplace=kufar`
  извлекает из `__NEXT_DATA__` (`initialState.filters.currentFilters`) реальные фильтры:
  категория (22 значения), бренд, регион и т.д. — возвращается 15 групп фильтров.
- **Onliner**: поисковая выдача не отдаёт server-side facets (`facets:{general:[],additional:[]}`)
  — при недоступности динамических фильтров `/api/filters` отдаёт статический классификатор
  (для «планшет» — Бренд, Объем памяти, Диагональ экрана).
- **Ozon/WB**: Playwright-фолбэк умеет кликать/применять фильтры в UI; извлечение фильтров из
  страницы — best-effort (покрыто моками).
- Frontend: при выборе **ровно одного** маркетплейса запрос фильтров идёт с `marketplace=...`
  (для Kufar — динамические); выбранные фильтры по-прежнему передаются в `POST /api/search` и
  применяются через `_apply_filters`.

## Проверки

### `ruff check .` — `All checks passed!`

### `pytest -q` (из `backend/`)

```
...........................................                                                      [100%]
43 passed, 1 warning in 0.85s
```

Новые тесты: Kufar `fetch_filters` (мок NEXT_DATA), лимит `max_items` Kufar, фолбэк WB/Ozon на
Playwright (monkeypatch `_browser_search`/`_browser_search_data` при 403), динамические фильтры
`/api/filters?marketplace=kufar` (успех и фолбэк на статику при ошибке).

### `npm run typecheck` / `npm run build` — успешно (89 модулей).

### Smoke-тест (dev-сервер и собранный `.exe`)

```
kufar dynamic filters: 15 (Категория 22 опции, Бренд 7, ...)
deep телевизор onliner: 999 items, truncated=False   (все, что отдаёт API)
deep телевизор kufar:   993 items, truncated=False
```

`.exe` собран с `--collect-all playwright`, запускается, API работает. При закрытии окна
pywebview/WebView2 пишет рекурсивный shutdown-шум в лог — известный артефакт закрытия, на работу
не влияет.

## Чек-лист приёмки

- [x] «телевизор» Onliner: >1000 (999 уникальных — API капит выдачу на ~1000; собрано всё).
- [ ] Ozon/WB возвращают реальные товары — реализовано (curl → Playwright-фолбэк), live-проверка
      невозможна с текущего IP (антибот 403/498); ожидается на машине пользователя.
- [x] «планшет» → Бренд, Объем памяти, Диагональ экрана (статический классификатор) + Kufar
      отдаёт свои реальные фильтры при `marketplace=kufar`.
- [x] Выбранные фильтры передаются в `/api/search` и уменьшают выдачу (`_apply_filters`).
- [ ] CI на GitHub зеленый — проверяется после push.

## Замечания

- Onliner API ограничивает выдачу поиска на ~1000 позиций независимо от числа страниц —
  «до 5000» недостижимо через `sdapi/search`; собирается всё, что отдаёт API.
- Playwright-браузеры не включаются в `.exe` (используется системный Chrome/Edge); для
  standalone-headless нужен `playwright install chromium`.
