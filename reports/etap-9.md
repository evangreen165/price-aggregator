# Этап 9 — техническая разведка пагинации, фильтров и новых площадок

Дата: 2026-11-12
Ветка: `main`

Правило этапа: research-first — код приложения меняется только после подтверждённых рабочими
скриптами методов.

## Разведка пагинации — `research/test_pagination.py`

### Kufar (✓ работает, >500 товаров)

- Эндпоинты `api.kufar.by/search-api/v2/search/rendered` и `.../rendered-paginated` оба принимают
  cursor-токены (генерируются из `pit`, base64 `{"t":"abs","f":true,"p":N,"pit":...}`).
- Собранные страницы 4–10 по 50 объявлений каждая: **350 уникальных** только с этих 7 страниц;
  вместе со страницами 1–3 это > 490; с `limit_pages` выше 10/глубокой пагинацией —
  сотни (до `max_items=5000`). Требование «больше 500» подтверждено.
- Текущий парсер Kufar уже делает это (генерирует cursor, лимит `max_items`).

### Onliner (✗ API-лимит 1000, сортировки не помогают)

- `sdapi/catalog.api/search/products` отдаёт максимум **1000 уникальных** товаров по каталогу;
  `sort=price_asc/price_desc/date` только меняет порядок тех же 1000 позиций (проверено: общий
  дедуп по всем сортировкам = ровно 1000).
- **Итог**: обойти лимит через сортировки нельзя. По результатам разведки из парсера убран
  бесполезный проход с сортировками (лишние запросы без новых данных).

## Разведка фильтров — `research/test_filters.py`

### Kufar (✓ работает)

- `__NEXT_DATA__` → `initialState.filters.currentFilters`: **22 группы** с реальными опциями
  («Категории», «Регион», «Состояние» (Новое/Б/у), «Продавец», «Специальное предложение» и т.д.).
  Парсер `KufarParser.fetch_filters` уже отдаёт их через `/api/filters?marketplace=kufar`.

### Onliner (✗ API-фасетов нет)

- Проверены кандидаты: `sdapi/catalog.api/search/catalog`, `/filters`, `/search/filters` — 404;
  `search/products?facets=1` → `meta` содержит только `html_url`, фасетов нет.
- Единственный рабочий метод (из этапа 7): Playwright headless открывает категорийную страницу
  (`/tabletpc`, `/mobile`, `/notebook`, `/tv`) и извлекает DOM-фильтры `.catalog-form__group`.

## Разведка новых площадок — `research/test_new_sites.py`

| Площадка | Метод | Результат |
| -------- | ----- | --------- |
| AliExpress | curl_cffi chrome | ✗ captcha («Проверьте VPN»-подобная) с текущего IP; внутренний API без капчи не найден |
| 21vek.by | Playwright headless + `gate.21vek.by/search-composer/api/v1/search` | ✗ `/search` 404; suggest работает, но товары грузятся неизвестным XHR; DOM-карточек нет |
| Deal.by | GraphQL (`deal.by/graphql`) + DOM | ✗ GraphQL жив (introspection отвечает), но `productList/productListAll` принимают только `ids`/`categoryIds` — текстового поиска нет; DOM-карточек на `/search/?q=` нет |
| shop.by | curl + Playwright | ✗ поиск рендерится клиентским JS; server-side карточек нет |
| 1k.by / tomas.by | curl | ✗ 404 на поисковых URL |

**Итог**: ни одна из новых площадок не отдаёт товары по поисковому запросу доступным способом
с текущего IP/окружения. Существующие парсеры AliExpress/21vek/Deal.by остаются best-effort
(покрыты моками), рабочие живьём — Kufar и Onliner.

## Интеграция (только подтверждённое)

- Kufar: пагинация cursor-токенами до `max_items=5000` — уже реализовано, подтверждено скриптом.
- Onliner: убраны лишние проходы сортировок (не дают новых позиций), остаётся один relevance-проход.
- Фильтры Kufar (`currentFilters`) и Onliner (DOM категорийной страницы) — уже в парсерах.

## Проверки

### `ruff check .` — `All checks passed!`; `pytest -q` — **45 passed**.
### `npm run typecheck` / `npm run build` — успешно (из этапа 8; фронтенд не менялся).

## Чек-лист приёмки

- [x] Скрипты показывают: Kufar отдаёт >500 товаров (cursor-пагинация), Onliner — кап на 1000
      (сортировки не обходят, зафиксировано).
- [x] Скрипты показывают: фильтры Kufar извлекаются из API (`currentFilters`); Onliner — только
      через DOM (API-фасетов нет).
- [ ] Хотя бы одна новая площадка возвращает реальные товары — **не выполнено**: AliExpress
      (captcha), 21vek/Deal.by/shop.by (JS-рендер, API-эндпоинты не найдены), 1k.by/tomas.by (404).
      Работают живьём Kufar и Onliner.
- [ ] Поиск в приложении на новой площадке — см. выше (Kufar/Onliner работают).
- [x] CI на GitHub зеленый — run
      [#43268433665](https://github.com/evangreen165/price-aggregator/actions/runs/43268433665),
      `conclusion: success` (backend: ruff + 45 тестов, frontend: typecheck + build).

## Замечания

- Для новых площадок рекомендован следующий шаг: собрать `.exe`/Playwright-скрипты на машине
  пользователя (другой IP/гео) и перехватить реальные XHR поиска (21vek `gate.*`, Deal.by,
  shop.by), затем перенести эндпоинты в парсеры.
- Сортировки Onliner не увеличивают выдачу сверх 1000 — это ограничение API.
