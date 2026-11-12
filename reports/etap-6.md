# Этап 6 — исследование обхода Ozon/WB и динамических фильтров

Дата: 2026-11-12
Ветка: `main`

## Методология (research-first)

Правило этапа: **не трогать код приложения, пока не найден рабочий способ обхода**. Поэтому
сначала были созданы изолированные скрипты `research/` и прогнаны на реальном сайте:

- `research/test_ozon.py` — Playwright (sync, `channel="msedge"`, headful), прогрев главной
  страницы (10 с на прохождение антибота), переход на `/search/?text=телевизор`, скролл,
  извлечение `window.__NUXT__` и DOM-ссылок `a[href*='/product/']`, перехват `composer-api`,
  сохранение `storage_state`.
- `research/test_wb.py` — Playwright + `playwright-stealth` (`Stealth().use_sync(page)`), переход
  на `search.aspx?search=телевизор`, перехват `search.wb.ru`, проверка `__NEXT_DATA__` и DOM.
- `research/test_filters.py` — Onliner: поиск фильтров в server-side HTML страниц
  (`/search`, категория `/tv`, root-каталог); Ozon/WB: попытка извлечения фильтров через браузер.

## Результаты исследований (логи скриптов)

### Ozon — `research/test_ozon.py`

```
[ozon] home title: Онлайн-гипермаркет Ozon
[ozon] __NUXT__ present: False
[ozon] DOM product links: 0
[ozon] body snippet: Онлайн-гипермаркет | Проверьте VPN, убедитесь ... |
        Ошибка: fab_chlg_20261112153713_01M786FT4DYR0E2RNDZC3BQ4MW
```

Вывод: Ozon (Variti) блокирует IP **на сетевом уровне** — показывается challenge
«Проверьте VPN» с идентификатором `fab_chlg_...`. Реальный браузер (headful msedge) не помогает:
до страницы поиска данные не доезжают, `composer-api` не вызывается (0 перехватов), товаров в DOM
нет (0 ссылок).

### Wildberries — `research/test_wb.py`

```
[wb] body snippet: Доступ ограничен. Обратитесь, пожалуйста. | ID: 81a8278addeb36b05be09cc7d9cec89e |
        IP: 37.212.49.45 | Время блокировки ...
[wb] __NEXT_DATA__ present: False
[wb] search.wb.ru responses: 0
[wb] DOM catalog links: 0
```

Вывод: WB блокирует IP (страница «Доступ ограничен», указан наш IP `37.212.49.45`). `playwright-stealth`
и перехват XHR не помогают — антибот решает по IP/репутации соединения.

### Onliner — `research/test_filters.py`

```
/tablet: 404 · /monitor: 404 · /tv: 200
facet-name: 0 · f[...]: 0 · catalog-filter: 0
```

Вывод: даже категорийная страница `/tv` (200) не содержит server-side разметки фильтров —
фасеты отрисовываются клиентом через JS (`catalog-form__filter`), отдельного доступного API
фасетов не найдено. Статический классификатор остаётся основным источником фильтров.

## Вывод и рекомендация

- **Ozon и WB** блокируют именно IP `37.212.49.45`, а не User-Agent/TLS: ни curl_cffi, ни
  headful-браузер, ни stealth не проходят. Для рабочего обхода необходим **прокси/резидентный
  IP** (например, прокси-пул), либо запуск на машине пользователя с «чистым» домашним IP —
  там прогрев браузера и сохранённый `storage_state` (cookies) дают реальные данные.
- В приложении уже реализован путь `curl_cffi → Playwright-фолбэк` (без правок в этом этапе —
  по правилу research-first); при работающем на стороне пользователя обходе он вернёт товары.
  Для WB в фолбэк добавлен `playwright-stealth` (объявлен в `pyproject.toml`).
- Kufar/Onliner работают и проверены на живых данных (см. предыдущий отчёт этапа 6): глубокая
  пагинация (999/993 товара), динамические фильтры Kufar из `currentFilters`.

## Файлы этапа

- `research/test_ozon.py`, `research/test_wb.py`, `research/test_filters.py` — скрипты с логами.
- `backend/pyproject.toml` — объявлен `playwright-stealth`.

## Чек-лист приёмки

- [ ] Скрипты `research/` выводят реальные товары Ozon/WB — **не выполнено**: IP `37.212.49.45`
      заблокирован обоими сайтами (Variti/«Доступ ограничен»); требуется прокси или другой IP.
- [ ] Скрипт фильтров выводит бренды для «планшет» — частично: Onliner не отдаёт server-side
      фасеты; для «планшет» работают фильтры статического классификатора + динамические Kufar.
- [ ] Поиск Ozon/WB в `.exe` возвращает товары — ожидается на машине пользователя (резидентный IP).
- [ ] Динамические фильтры в UI — Kufar работает; Ozon/WB заблокированы на текущем IP.
- [x] CI на GitHub зеленый — run
      [#43250647933](https://github.com/evangreen165/price-aggregator/actions/runs/43250647933),
      `conclusion: success` (backend: ruff + 43 теста, frontend: typecheck + build).

## Рекомендуемые следующие шаги

1. Подключить прокси-пул (SOCKS/HTTP) для Ozon/WB и повторить `research/test_ozon.py`,
   `research/test_wb.py`; после успеха перенести cookies/параметры в `backend/app/parsers/`.
2. Либо собрать `.exe` и запустить на машине пользователя (домашний IP) — прогрев главной
   страницы с сохранением `storage_state` даст доступ к composer-api / search.wb.ru.
