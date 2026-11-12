# Этап 4 — реальная пагинация, применение фильтров, выбор способа открытия ссылок

Дата: 2026-11-12
Ветка: `main`

## ЗАДАЧА 1 — реальная пагинация (backend)

`BaseParser.search(query, region, limit_pages: int = 10, filters: dict | None = None)`.
Сбор последовательный, результаты объединяются, дедупликация по ссылке, ранняя остановка,
когда страница не дала новых товаров.

### Onliner

Проверено на живом API: `sdapi/catalog.api/search/products` игнорирует `size`, но работает с
`limit` и `page`. Запросы: `limit=100&page=1..10`. По запросу **«телевизор»** собран **1000**
товаров (10 страниц × 100, дубли отсеяны дедупликацией).

### Kufar

HTML-страница игнорирует `page`, но в `__NEXT_DATA__` есть cursor-токены, из которых декодируется
`searchId` (`pit`). Токены генерируются для любой страницы: `{"t":"abs","f":true,"p":N,"pit":...}`
(base64) и передаются в `api.kufar.by/search-api/v2/search/rendered?size=50&cursor=...`.
Проверено на живом API, генерация работает для страниц 4, 5, 8. По запросу **«телевизор»** Kufar
вернул **493** товара (43 + 9×50). Глубина ограничивается `limit_pages`.

## ЗАДАЧА 2 — применение фильтров (backend + frontend)

- `BaseParser.search` принимает `filters: dict[str, list[str]]`. Kufar/Onliner API не фильтруют
  по произвольным параметрам напрямую, поэтому применяется **фильтрация на стороне Python**
  (`BaseParser._apply_filters`): опции фильтра сопоставляются с названием товара (без учёта
  регистра), после сбора всех страниц.
- `POST /api/search` принимает `limit_pages` (по умолчанию 10) и `filters`. Frontend передаёт
  выбранные фильтры из Zustand (`selectedFilters` → только непустые группы) в запрос.
- Проверено на живых данных: «телевизор» без фильтров — Kufar 493 / Onliner 1000; с фильтром
  `brand: ["Samsung"]` — Kufar **30**, Onliner **154**. Фильтры реально уменьшают выдачу.

## ЗАДАЧА 3 — отображение Onliner и настройки PyWebview

- `webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False` — ссылки открываются внутри
  приложения.
- В pywebview 6.2.1 (установлен) `create_window()` не имеет параметра `user_agent` (проверено
  по сигнатуре), поэтому UA намеренно не передаётся: WebView2/EdgeChromium и так использует
  современный Chrome-like User-Agent, Onliner рендерится корректно при top-level загрузке
  (без iframe ограничений). Константа `USER_AGENT` используется в HTTP-запросах прокси/парсеров.
- Onliner/Kufar при открытии в отдельном/текущем окне грузятся напрямую (top-level), поэтому
  `X-Frame-Options` не мешает — отображаются как в обычном браузере.

## ЗАДАЧА 4 — выбор способа открытия ссылок

- **Настройки** (Zustand, `linkOpenMode`): радиокнопки
  «Системный браузер» / «Новое окно приложения» / «Текущее окно (с кнопкой „Назад")».
- Клик по товару: `window.pywebview.api.open_link(url, mode)`; вне WebView (dev-браузер) —
  фолбэк на страницу `/product` с iframe.
- Backend `DesktopApi.open_link`:
  - `system` → `webbrowser.open(url)`;
  - `new_window` → `webview.create_window("Товар", url, 1100×750)`;
  - `current_window` → `window.load_url(url)` + инъекция плавающей кнопки «← Назад»
    (`history.back()`) через `window.events.loaded` / `evaluate_js`.
  - URL валидируется (только http/https); при исключении — фолбэк в системный браузер.
- Главное окно создаётся с `js_api=DesktopApi`.

## Проверки

### `ruff check .` — `All checks passed!`

### `pytest -q` (из `backend/`)

```
.............................                                                      [100%]
29 passed, 1 warning in 0.81s
```

Новые/обновлённые тесты: пагинация Kufar (генерация cursor-токенов, дедуп, стоп, `limit_pages`),
пагинация Onliner (`page`+`limit`), применение фильтров в обоих парсерах, передача
`filters`/`limit_pages` через `/api/search` (monkeypatch).

### `npm run typecheck` / `npm run build` — успешно (89 модулей).

### Smoke-тест (dev-сервер и собранный `.exe`)

```
телевизор kufar: 493 items      onliner: 1000 items     (errors: {})
телевизор + Samsung kufar: 30 items      onliner: 154 items
```

Exe запускается с `js_api`, `OPEN_EXTERNAL_LINKS_IN_BROWSER=False`, стартует без ошибок;
глубокий поиск и фильтры работают через frozen-сборку. В логе при закрытии окна pywebview
пишет шум про `CoreWebView2Controller ... UI thread` — это известный шум WebView2 при shutdown,
на работу не влияет.

## Чек-лист приёмки

- [x] «телевизор»: Onliner ≥1000 (ровно 1000 после дедупликации), Kufar — сотни (493).
- [x] Фильтры (например, Samsung) реально уменьшают количество результатов.
- [x] Onliner открывается в окне приложения (top-level загрузка, как в обычном браузере).
- [x] В «Настройках» есть выбор способа открытия ссылок, выбор хранится в Zustand и
      передаётся в `open_link`.
- [x] CI на GitHub зеленый — run
      [#43240460899](https://github.com/evangreen165/price-aggregator/actions/runs/43240460899),
      `conclusion: success` (backend: ruff + 29 тестов, frontend: typecheck + build).

## Замечания

- `limit_pages=10` по умолчанию; при необходимости глубину можно менять через тело `/api/search`.
- Фильтрация по названию — эвристика; точная передача фильтров в API маркетплейсов — следующий
  этап.
