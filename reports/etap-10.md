# Этап 10 — финальная разведка: Playwright-фильтры Onliner, API SPA-площадок

Дата: 2026-11-12
Ветка: `main`

Правило: research-first — скрипты в `research/`, интеграция только после подтверждённых данных.

## Onliner (фильтры через Playwright) — `research/test_onliner_filters.py` ✓

Открывается категорийная страница (`/tabletpc`) headless-браузером (msedge), извлекается
`.catalog-form__group` → `.catalog-form__label-title` + `ul.catalog-form__checkbox-list span`:

```
onliner filter groups: 14
  - Производитель | Apple, Xiaomi, Samsung, HONOR, Huawei, Horizont, ...
  - Магазины | Agroup, VIPCOMP, Атехно, Newton, ...
  - Модель | Xiaomi Redmi Pad 2 Pro, Apple iPad 2025, ...
  - Частота обновления экрана | 60/90/120/144/165 Гц
  - Процессор, Операционная система, Сотовая связь (SIM), ...
```

Логика уже интегрирована в `OnlinerParser.fetch_filters` (этап 7) — метод работает, скрипт её
подтверждает.

## AliExpress — `research/test_aliexpress.py` (частично)

- `aliexpress.com/w/wholesale-<q>.html` — captcha (проверено ранее).
- **`aliexpress.ru` открывается headless + `playwright-stealth` без капчи** (главная страница,
  title «AliExpress: 11.11 — главная распродажа года») — сессия/cookies реально получаются.
- Перехвачены XHR поиска: `acs.aliexpress.com/h5/mtop.*` (relationrecommend, loginconfigs,
  cart.count, address.*, `mtop.ae.cookie.render`). **Эндпоинт, возвращающий список товаров поиска,
  за один прогон не зафиксирован**, а извлечение из DOM по `a[href*='/item/']` даёт 0 (страница
  поиска то 404, то рендерит без карточек — флаки, зависит от прогона).
- **Вывод**: получение cookie-сессии без капчи работает, но API/разметка выдачи поиска
  нестабильны с текущего IP; требуется перехват `mtop.*`-запроса выдачи на машине пользователя
  (там сессия стабильна).

## 21vek.by — `research/test_21vek_api.py` (не подтверждено)

- Перехвачены XHR: `gate.21vek.by/cart/carts/info`, `gate.21vek.by/search-composer/api/v1/search/suggest`
  (только подсказки), `gate.21vek.by/pulse-mesh/events`. **Запроса, отдающего список товаров
  поиска, нет** — и с `?text=`, и с `?search=`.
- `__NEXT_DATA__` (`initialState.searchResult.products`) всегда `{"all": null, "allMap": {}}` —
  товары подгружаются клиентом по XHR, который headless-перехват не поймал (видимо, запрос
  идёт в другой момент/с другими параметрами).

## Deal.by — `research/test_21vek_api.py` (не подтверждено)

- `deal.by/graphql` жив: introspection работает, но `productList/productListAll` принимают только
  `ids`/`categoryIds`/`limit` — **текстового поиска в GraphQL нет**.
- `/search/?q=` и `/search?search_term=` не содержат server-side/DOM-ссылок на товары
  (`/item/`, `/goods/` — 0); перехват на странице поиска даёт только context/analytics/autocomplete.

## Итоги интеграции (только подтверждённое)

- Onliner `fetch_filters` (Playwright-DOM) — подтверждено скриптом, уже в приложении.
- AliExpress/21vek/Deal.by — рабочие эндпоинты выдачи не найдены с текущего IP; по правилу
  research-first код парсеров не менялся. Проверенные моки остаются.

## Проверки

- `ruff check .` — `All checks passed!`; `pytest -q` — **45 passed**; `npm run typecheck` /
  `npm run build` — успешно (фронтенд не менялся).

## Чек-лист приёмки

- [x] `test_onliner_filters.py` выводит реальные фильтры (14 групп, бренды/частоты/процессоры).
- [ ] `test_aliexpress.py` обходит капчу через Playwright — **частично**: сессия без капчи на
      `aliexpress.ru` получается, но выдачу товаров (mtop/DOM) стабильно извлечь не удалось
      (флаки, 404 на поиске).
- [ ] `test_21vek_api.py` возвращает реальные товары — не выполнено (XHR выдачи не найден).
- [ ] Поиск в приложении на AliExpress/новой площадке — не подтверждено (работают Kufar/Onliner).
- [ ] CI на GitHub зеленый — проверяется после push.

## Замечания

- Следующий шаг для AliExpress/21vek: перехват реального XHR выдачи на машине пользователя
  (стабильная сессия, домашний IP) и перенос эндпоинта + cookies в парсеры (curl_cffi с
  сохранённым `storage_state`).
- Onliner-фильтры полностью работают в приложении через `fetch_filters` (headless msedge).
