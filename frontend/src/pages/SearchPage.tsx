import { useEffect } from "react";

import { getFilters, Product } from "../api/client";
import { useSearchStore } from "../store/search";

const MARKETPLACES = [
  { id: "kufar", label: "Kufar" },
  { id: "onliner", label: "Onliner" },
  { id: "ozon", label: "Ozon" },
  { id: "wb", label: "Wildberries" },
];

const priceFormat = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function ProductCard({ product }: { product: Product }) {
  return (
    <li className="result-card">
      <div className="result-card-top">
        <span className="badge">{product.marketplace}</span>
        <a
          className="result-title"
          href={product.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          {product.title}
        </a>
      </div>
      <div className="result-meta">
        <span className="result-price">
          {product.price === null ? "—" : priceFormat.format(product.price)} {product.currency}
        </span>
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

  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      search.setFilters(null, []);
      search.setFiltersLoading(false);
      return;
    }
    search.setFiltersLoading(true);
    const timer = setTimeout(async () => {
      try {
        const response = await getFilters(trimmed);
        search.setFilters(response.category, response.filters);
      } catch {
        search.setFilters(null, []);
      } finally {
        search.setFiltersLoading(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [query]);

  const canSubmit = query.trim().length > 0 && marketplaces.length > 0 && status !== "loading";

  const allProducts = Object.entries(results).flatMap(([marketplace, products]) =>
    products.map((product) => ({ ...product, marketplace })),
  );

  return (
    <section className="page">
      <header className="page-header">
        <h2>Поиск</h2>
        <p>
          Поиск по выбранным маркетплейсам. Kufar и Onliner работают, Ozon и Wildberries — задел
          на потом.
        </p>
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
            placeholder="Например: монитор"
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

        {search.filtersLoading && <p className="muted">Подбираем фильтры…</p>}
        {!search.filtersLoading && search.filters.length > 0 && (
          <div className="filters-box">
            {search.filters.map((group) => (
              <fieldset className="filter-group" key={group.key}>
                <legend>{group.label}</legend>
                {group.options.map((option) => {
                  const checked = search.selectedFilters[group.key]?.includes(option) ?? false;
                  return (
                    <label className="checkbox" key={option}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => search.toggleFilterOption(group.key, option)}
                      />
                      {option}
                    </label>
                  );
                })}
              </fieldset>
            ))}
          </div>
        )}

        <p className="muted">
          Регион: Беларусь. Передача выбранных фильтров в парсеры — следующий шаг.
        </p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Результаты</h3>
          {status === "success" && <span className="muted">найдено: {allProducts.length}</span>}
        </div>

        {status === "loading" && <p className="muted">Запрашиваем маркетплейсы…</p>}

        {status === "error" && (
          <p className="status error">
            Ошибка запроса: {requestError ?? "неизвестная ошибка"}
          </p>
        )}

        {status === "success" && allProducts.length === 0 && (
          <p className="muted">
            Товары не найдены.
            {Object.keys(errors).length > 0 &&
              ` Ошибки: ${Object.entries(errors)
                .map(([id, message]) => `${id}: ${message}`)
                .join("; ")}`}
          </p>
        )}

        {status === "success" && allProducts.length > 0 && (
          <>
            <ul className="result-list">
              {allProducts.map((product) => (
                <ProductCard key={`${product.marketplace}-${product.url}`} product={product} />
              ))}
            </ul>
            {Object.keys(errors).length > 0 && (
              <p className="status error">
                Частичные ошибки:{" "}
                {Object.entries(errors)
                  .map(([id, message]) => `${id}: ${message}`)
                  .join("; ")}
              </p>
            )}
          </>
        )}

        {status === "idle" && <p className="muted">Введите запрос и нажмите «Найти».</p>}
      </div>
    </section>
  );
}
