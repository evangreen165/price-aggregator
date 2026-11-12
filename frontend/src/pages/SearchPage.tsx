import { useState, type MouseEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Product } from "../api/client";
import { SortMode, useSearchStore } from "../store/search";
const MARKETPLACES = [
  { id: "kufar", label: "Kufar" },
  { id: "onliner", label: "Onliner" },
  { id: "21vek", label: "21vek.by" },
];

const priceFormat = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function pageWindow(current: number, total: number): (number | "…")[] {
  if (total <= 10) {
    return Array.from({ length: total }, (_, index) => index + 1);
  }
  const pages = new Set<number>([1, total, current - 1, current, current + 1]);
  const items: (number | "…")[] = [];
  let previous = 0;
  for (const page of [...pages].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b)) {
    if (page - previous > 1) {
      items.push("…");
    }
    items.push(page);
    previous = page;
  }
  return items;
}

function ProductCard({ product }: { product: Product }) {
  const linkOpenMode = useSearchStore((state) => state.linkOpenMode);
  const viewMode = useSearchStore((state) => state.viewMode);
  const navigate = useNavigate();

  const openProduct = (event?: MouseEvent<HTMLAnchorElement>) => {
    event?.preventDefault();
    const api = window.pywebview?.api;
    if (api?.open_link) {
      api.open_link(product.url, linkOpenMode);
    } else {
      navigate(`/product?url=${encodeURIComponent(product.url)}`);
    }
  };

  const isDiscount =
    product.old_price !== null &&
    product.old_price !== undefined &&
    product.old_price > (product.price ?? 0);

  if (viewMode === "grid") {
    return (
      <li className="product-grid-card">
        {product.image ? (
          <img className="thumb" src={product.image} alt="" loading="lazy" />
        ) : (
          <div className="thumb placeholder-thumb" aria-hidden="true">
            {product.title.charAt(0).toUpperCase()}
          </div>
        )}
        <span className="badge">{product.marketplace}</span>
        <a
          className="result-title"
          href={product.url}
          onClick={(event) => openProduct(event)}
        >
          {product.title}
        </a>
        <div className="grid-prices">
          <span className="result-price">
            {product.price === null ? "—" : priceFormat.format(product.price)}{" "}
            {product.currency}
          </span>
          {isDiscount && product.old_price != null && (
            <span className="old-price">
              {priceFormat.format(product.old_price)} {product.currency}
            </span>
          )}
        </div>
        <button className="button open-btn" type="button" onClick={() => openProduct()}>
          Открыть
        </button>
      </li>
    );
  }

  return (
    <li className="result-card">
      <div className="result-card-top">
        <span className="badge">{product.marketplace}</span>
        <a className="result-title" href={product.url} onClick={(event) => openProduct(event)}>
          {product.title}
        </a>
      </div>
      <div className="result-meta">
        <span className="result-price">
          {product.price === null ? "—" : priceFormat.format(product.price)} {product.currency}
        </span>
        {isDiscount && product.old_price != null && (
          <span className="old-price">
            {priceFormat.format(product.old_price)} {product.currency}
          </span>
        )}
        {product.rating != null && <span className="muted">★ {product.rating}</span>}
        <span className="muted">
          регион: {product.region} · {new Date(product.parsed_at).toLocaleString("ru-RU")}
        </span>
      </div>
    </li>
  );
}

export default function SearchPage() {
  const search = useSearchStore();
  const { query, marketplaces, status, results, errors, requestError } = search;
  const [draftMin, setDraftMin] = useState("");
  const [draftMax, setDraftMax] = useState("");

  const applyPrice = () => {
    search.setPriceRange(
      draftMin === "" ? null : Number(draftMin),
      draftMax === "" ? null : Number(draftMax),
    );
  };

  const canSubmit = query.trim().length > 0 && marketplaces.length > 0 && status !== "loading";

  const allProducts = Object.entries(results).flatMap(([marketplace, products]) =>
    products.map((product) => ({ ...product, marketplace })),
  );

  let priceFiltered = allProducts;
  if (search.discountOnly) {
    priceFiltered = priceFiltered.filter(
      (product) =>
        product.old_price !== null &&
        product.old_price !== undefined &&
        product.old_price > (product.price ?? 0),
    );
  }
  priceFiltered = priceFiltered.filter((product) => {
    const price = product.price ?? 0;
    if (search.minPrice !== null && price < search.minPrice) {
      return false;
    }
    if (search.maxPrice !== null && price > search.maxPrice) {
      return false;
    }
    return true;
  });
  const sorted = [...priceFiltered];
  if (search.sortBy === "price_asc") {
    sorted.sort((a, b) => (a.price ?? Number.MAX_VALUE) - (b.price ?? Number.MAX_VALUE));
  } else if (search.sortBy === "price_desc") {
    sorted.sort((a, b) => (b.price ?? 0) - (a.price ?? 0));
  } else if (search.sortBy === "rating_desc") {
    sorted.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
  }
  priceFiltered = sorted;

  const totalPages =
    search.itemsPerPage > 0
      ? Math.max(1, Math.ceil(priceFiltered.length / search.itemsPerPage))
      : 1;
  const currentPage = Math.min(search.currentPage, totalPages);
  const sliceStart = search.itemsPerPage > 0 ? (currentPage - 1) * search.itemsPerPage : 0;
  const visibleProducts =
    search.itemsPerPage > 0
      ? priceFiltered.slice(sliceStart, sliceStart + search.itemsPerPage)
      : priceFiltered;
  const sliceEnd = search.itemsPerPage > 0
    ? Math.min(sliceStart + search.itemsPerPage, priceFiltered.length)
    : priceFiltered.length;
  const truncated = Object.values(search.meta).some((entry) => entry.truncated);
  const hasMore = Object.values(search.nextPage).some((page) => page != null) ||
    Object.values(search.nextCursor).some((cursor) => cursor != null);

  return (
    <section className="page">
      <header className="page-header">
        <h2>Поиск</h2>
        <p>Введите запрос с параметрами, например: «монитор 27 2K IPS».</p>
      </header>

      <div className="card">
        <form
          className="search-row"
          onSubmit={(event) => {
            event.preventDefault();
            search.runSearch();
          }}
        >
          <input
            className="input"
            type="text"
            placeholder="Например: монитор 27 2K IPS"
            value={query}
            onChange={(event) => search.setQuery(event.target.value)}
          />
          <button className="button primary" type="submit" disabled={!canSubmit}>
            {status === "loading" ? "Ищем…" : "Найти"}
          </button>
        </form>

        <div className="checkbox-row">
          {MARKETPLACES.map((marketplace) => (
            <label className="checkbox" key={marketplace.id}>
              <input
                type="checkbox"
                checked={marketplaces.includes(marketplace.id)}
                onChange={() => search.toggleMarketplace(marketplace.id)}
              />
              <span className="badge">{marketplace.id}</span>
              {marketplace.label}
            </label>
          ))}
        </div>

        <div className="price-filter-row">
          <label className="muted" htmlFor="min-price">
            Цена от:
          </label>
          <input
            id="min-price"
            className="input price-input"
            type="number"
            min={0}
            placeholder="от"
            value={draftMin}
            onChange={(event) => setDraftMin(event.target.value)}
          />
          <label className="muted" htmlFor="max-price">
            до:
          </label>
          <input
            id="max-price"
            className="input price-input"
            type="number"
            min={0}
            placeholder="до"
            value={draftMax}
            onChange={(event) => setDraftMax(event.target.value)}
          />
          <button className="button" type="button" onClick={applyPrice}>
            Применить
          </button>
        </div>

        <div className="price-filter-row">
          <label className="checkbox">
            <input
              type="checkbox"
              checked={search.discountOnly}
              onChange={(event) => search.setDiscountOnly(event.target.checked)}
            />
            Только со скидкой
          </label>
          <select
            className="select"
            value={search.sortBy}
            onChange={(event) => search.setSortBy(event.target.value as SortMode)}
            aria-label="Сортировка"
          >
            <option value="default">Без сортировки</option>
            <option value="price_asc">Цена: по возрастанию</option>
            <option value="price_desc">Цена: по убыванию</option>
            <option value="rating_desc">По рейтингу</option>
          </select>
        </div>

        <div className="per-page-row">
          <label className="muted" htmlFor="per-page">
            Показывать по:
          </label>
          <select
            id="per-page"
            className="select"
            value={search.itemsPerPage}
            onChange={(event) => search.setItemsPerPage(Number(event.target.value))}
          >
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={search.deepPagination}
            onChange={(event) => search.setDeepPagination(event.target.checked)}
          />
          Глубокая пагинация (медленнее, до 50 страниц)
        </label>

        <p className="muted">Регион: Беларусь.</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Результаты</h3>
          {status === "success" && <span className="muted">найдено: {priceFiltered.length}</span>}
          <div className="view-toggle">
            <button
              className={search.viewMode === "grid" ? "button page-active" : "button"}
              type="button"
              onClick={() => search.setViewMode("grid")}
            >
              Сетка
            </button>
            <button
              className={search.viewMode === "list" ? "button page-active" : "button"}
              type="button"
              onClick={() => search.setViewMode("list")}
            >
              Список
            </button>
          </div>
        </div>

        {Object.keys(errors).length > 0 && (
          <div className="error-banners">
            {Object.entries(errors).map(([id, message]) => (
              <div className="error-banner" key={id}>
                <strong>{id}</strong>: Сайт заблокировал запросы с вашего IP. Пожалуйста,
                попробуйте позже или используйте VPN.{" "}
                <span className="muted">({message})</span>
              </div>
            ))}
          </div>
        )}

        {status === "loading" && <p className="muted">Запрашиваем маркетплейсы…</p>}

        {status === "error" && (
          <p className="status error">
            Ошибка запроса: {requestError ?? "неизвестная ошибка"}
          </p>
        )}

        {status === "success" && priceFiltered.length === 0 && (
          <p className="muted">Товары не найдены.</p>
        )}

        {status === "success" && priceFiltered.length > 0 && (
          <>
            <ul className={search.viewMode === "grid" ? "result-grid" : "result-list"}>
              {visibleProducts.map((product) => (
                <ProductCard key={`${product.marketplace}-${product.url}`} product={product} />
              ))}
            </ul>

            {totalPages > 1 && (
              <div className="pagination">
                <button
                  className="button"
                  type="button"
                  disabled={currentPage === 1}
                  onClick={() => search.setCurrentPage(currentPage - 1)}
                >
                  Назад
                </button>
                {pageWindow(currentPage, totalPages).map((page, index) =>
                  typeof page === "number" ? (
                    <button
                      className={page === currentPage ? "button page-active" : "button"}
                      type="button"
                      key={page}
                      onClick={() => search.setCurrentPage(page)}
                    >
                      {page}
                    </button>
                  ) : (
                    <span className="muted" key={`ellipsis-${index}`}>
                      …
                    </span>
                  ),
                )}
                <button
                  className="button"
                  type="button"
                  disabled={currentPage === totalPages}
                  onClick={() => search.setCurrentPage(currentPage + 1)}
                >
                  Вперед
                </button>
              </div>
            )}

            <div className="results-footer">
              {hasMore && (
                <button
                  className="button"
                  type="button"
                  onClick={() => search.loadMore()}
                  disabled={search.status === "loading"}
                >
                  Загрузить ещё {search.itemsPerPage} товаров
                </button>
              )}
              {!hasMore && allProducts.length > 0 && (
                <p className="muted">Это все товары.</p>
              )}
              <p className="muted">
                Найдено {priceFiltered.length} товаров
                {search.itemsPerPage > 0 && `, показано ${sliceStart + 1}–${sliceEnd}`}
              </p>
              {truncated && (
                <p className="muted">
                  Показаны не все результаты (достигнут лимит парсинга).
                </p>
              )}
            </div>
          </>
        )}

        {status === "idle" && <p className="muted">Введите запрос и нажмите «Найти».</p>}
      </div>
    </section>
  );
}
