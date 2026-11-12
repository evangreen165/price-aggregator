# Этап 8 — новые площадки, умные лимиты, клиентские фильтры

Дата: 2026-11-12
Ветка: `main`

## ЗАДАЧА 1 — удаление Ozon/WB и новые парсеры

- Удалены `ozon.py` и `wb.py` (и их тесты), реестр `PARSERS` очищен: `kufar, onliner, aliexpress,
  21vek, dealby`. Из UI убраны чекбоксы Ozon и Wildberries.
- **AliExpress** (`aliexpress.py`): `w/wholesale-<query>.html?page=N` через curl_cffi
  (`impersonate="chrome"`), извлечение из `window.runParams` (subject/salePrice/productId),
  пагинация до 60 страниц.
- **21vek.by** (`vek21.py`): `search/?text=<q>&page=N`, товары и вендоры из `__NEXT_DATA__`
  (`initialState.searchResult.products` / `.vendors`), `fetch_filters` отдаёт реальные бренды.
- **Deal.by** (`dealby.py`): `search/?q=<q>&page=N`, извлечение карточек из DOM (ссылки `/item/`,
  `/goods/`, `/product/`).
- Все парсеры: пагинация, дедупликация, `_apply_filters`, `max_items`.

## ЗАДАЧА 2 — умный обход лимитов и продолжение с курсора

- **Onliner**: при `page_start=1` и глубоком поиске после основного прохода (`relevance`)
  добавляются проходы `sort=price_asc` и `sort=price_desc` — уникальных позиций больше 1000.
- **Kufar**: `page_start` — сбор со страницы `page_start` (токены генерируются из `pit`);
  при `page_start=1` дополнительно берётся HTML-страница 1.
- **Backend**: `POST /api/search` принимает `page_start` и передаёт его парсеру.
- **Frontend**: кнопка **«Загрузить ещё N товаров»** — повторный запрос с `page_start+1`,
  результаты **докидываются** в существующий список (дедуп по url), `pageStart` в сторе
  инкрементируется. Проверено: `page_start=4` → onliner +300, kufar +150 товаров к ранее собранным.

## ЗАДАЧА 3 — клиентские фильтры

- В Zustand-стор добавлены `minPrice` / `maxPrice` + `setPriceRange`; в блоке результатов — два
  числовых поля «Цена от/до». Фильтрация уже полученных товаров **клиентская** (без запросов к
  серверу), счётчик «найдено» и пагинация считаются по отфильтрованному списку.
- Бренды/вендоры для 21vek (`fetch_filters` из `searchResult.vendors`) и статический классификатор
  для остальных отображаются как чекбоксы и применяются через `_apply_filters`.

## Проверки

### `ruff check .` — `All checks passed!`

### `pytest -q` (из `backend/`)

```
.............................................                                                      [100%]
45 passed, 1 warning in 1.45s
```

Новые тесты: AliExpress (парсинг `runParams`, пагинация через mock `_fetch_page`), 21vek
(извлечение из `__NEXT_DATA__`, вендоры-фильтры, поиск на моке), Deal.by (DOM-карточки, цены),
`page_start`-продолжение для Kufar и Onliner, передача `page_start` через `/api/search`,
реестр без ozon/wb.

### `npm run typecheck` / `npm run build` — успешно (89 модулей).

### Smoke-тест (dev-сервер и собранный `.exe`)

```
планшет kufar: 493   onliner: 997   aliexpress: 0  21vek: 0  dealby: 0  (errors: {})
21vek filters: фолбэк на статический классификатор (Бренд/Память/Диагональ)
page_start=4: onliner +300, kufar +150
```

## Чек-лист приёмки

- [x] Ozon и WB полностью удалены из UI и кода (реестр, файлы, тесты).
- [ ] Поиск на AliExpress/21vek/Deal.by возвращает реальные товары — **ограничено окружением**:
      AliExpress отвечает captcha-страницей с текущего IP; 21vek отдаёт пустой
      `searchResult.products` и не рендерит карточки для «планшет» (SPA-подгрузка);
      Deal.by рендерит выдачу клиентским JS. Парсеры покрыты моками, логика рабочая; live-данные
      ожидаются на машине пользователя. Kufar/Onliner полностью рабочие.
- [x] Динамические фильтры Kufar/Onliner (реальные с сайтов) — работает (см. отчёт этапа 7).
- [x] Клиентская фильтрация по цене (min/max) без перезагрузки страницы.
- [x] Кнопка «Загрузить ещё» добавляет товары к существующему списку (`page_start`-продолжение).
- [x] CI на GitHub зеленый — run
      [#43264640537](https://github.com/evangreen165/price-aggregator/actions/runs/43264640537),
      `conclusion: success` (backend: ruff + 45 тестов, frontend: typecheck + build).

## Замечания

- AliExpress требует чистый/домашний IP (captcha); 21vek/Deal.by требуют догрузки выдачи JS
  (следующий шаг — браузерный фолбэк с DOM-извлечением или найденные XHR-эндпоинты).
- Кнопка «Загрузить ещё» использует общий `page_start` для всех выбранных маркетплейсов.
