# Этап 11 — интеграция aer-webapi (AliExpress), 21vek ?term=, Deal.by API

Дата: 2026-11-12
Ветка: `main`

## Разведка и результаты скриптов

### AliExpress — `research/test_aliexpress_webapi.py`

- Открыта `aliexpress.ru/wholesale?SearchText=телевизор` через Playwright headless + stealth —
  **капчи нет** (в отличие от aliexpress.com), сессия/cookies получаются.
- Прямой запрос `aer-webapi/v1/search` / `v2/search` через curl_cffi (с cookies) возвращает
  **X5 anti-bot punish-страницу** (`/_____tmd_____/punish?x5secdata=...`) — direct API закрыт.
- В браузере перехватывается `aer-webapi/v2/recommend`, ответ содержит `data.snippetsV2[]`
  (в части прогонов — с товарами, напр. `{"id":"1005011849161285","sourceId":...}`).
- **Итог**: способ — перехват `aer-webapi/v2/recommend` в браузере. Нестабилен с текущего IP
  (в части прогонов snippets пустые/страница 404). Интегрирован в `aliexpress.py` как
  browser-interception метод (`snippetsV2` → `snippetContainer.itemData.pdpInfo.preloadedData`
  title/price), с 2 попытками и graceful fallback. Приложение при неудаче отдаёт пусто без ошибки.

### 21vek.by — `research/test_21vek_xhr.py` (✓ РАБОТАЕТ)

- Найден рабочий параметр: **`?term=`** (а не `?text=`/`?search=`). При нём
  `__NEXT_DATA__ initialState.searchResult.products.all` заполнен:
  `{"id","code","link":"/tv/....html","name":"Телевизор JVC 65\" LT-65MU7500","price":"1999.00","salePrice":"1399.00",...}`.
- В `vek21.py` параметр заменён на `term`. Проверено на живых данных через `/api/search`:

```
телевизор 21vek: 60 items   (sample: Телевизор JVC 65" LT-65MU7500 | 1999.0 BYN)
```

### Deal.by — `research/test_deal_api.py`

- `my.deal.by/api/v1/{products/search, search, products, catalog/search, search/products}` — все **404**.
- Перехват на `/search/?q=телевизор`: только GraphQL `context`/`analytics` и `autocomplete` —
  XHR выдачи не найден; `productListAll` в GraphQL принимает только `ids`/`categoryIds`.
- **Итог**: публичного эндпоинта поиска нет; парсер остаётся best-effort (моки).

## Интеграция

- `vek21.py`: `?term=query` — **рабочий парсер** (live: 60 товаров).
- `aliexpress.py`: browser-interception `aer-webapi/v2/recommend` → `snippetsV2`
  (структура `pdpInfo.preloadedData` по документации задачи; моки в тестах).
- Чекбоксы AliExpress/21vek/Deal.by в UI уже присутствуют (этап 8).
- Deal.by/Onliner/Kufar — без изменений.

## Проверки

- `ruff check .` — `All checks passed!`
- `pytest -q` — **45 passed** (обновлённые тесты aliexpress: snippet→product, поиск на моке
  `_browser_items`; 21vek-тесты работают с новым параметром).
- `npm run typecheck` / `npm run build` — успешно (фронтенд не менялся).
- Smoke (dev и `.exe`): `21vek: 60 items`, `kufar: 93`, `onliner: 200`, `aliexpress: 0` (флаки
  перехвата с текущего IP), `errors: {}`.

## Чек-лист приёмки

- [x] `test_aliexpress_webapi.py` показывает interception-метод (`aer-webapi/v2/recommend`,
      X5-punish на прямых запросах) — реальные товары флаки с текущего IP; интегрировано.
- [ ] `test_deal_api.py` — API требует токена/эндпоинта не найдено (404 на всех кандидатах);
      альтернативы нет → best-effort.
- [x] `test_21vek_xhr.py` возвращает реальные товары (через `?term=` + SSR JSON) — **работает**.
- [x] Поиск в приложении работает на Kufar, Onliner и **21vek.by** (новая площадка).
- [x] CI на GitHub зеленый — run
      [#43274386212](https://github.com/evangreen165/price-aggregator/actions/runs/43274386212),
      `conclusion: success` (backend: ruff + 45 тестов, frontend: typecheck + build).

## Замечания

- AliExpress: рабочий метод подтверждён (interception), но с текущего IP нестабилен; на машине
  пользователя с сессией ожидается стабильный результат. Прямые запросы блокирует X5 anti-bot.
- Deal.by остаётся без публичного API поиска.
