import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Product, searchProducts } from "../api/client";

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
        <a className="result-title" href={product.url}>
          {product.title}
        </a>
      </div>
      <div className="result-meta">
        <span className="result-price">
          {product.price === null ? "—" : priceFormat.format(product.price)}{" "}
          {product.currency}
        </span>
        <span className="muted">
          регион: {product.region} · {new Date(product.parsed_at).toLocaleString("ru-RU")}
        </span>
      </div>
    </li>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string[]>(["kufar", "onliner"]);

  const search = useMutation({
    mutationFn: searchProducts,
  });

  const toggleMarketplace = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const canSubmit = query.trim().length > 0 && selected.length > 0 && !search.isPending;

  const allProducts =
    search.data === undefined
      ? []
      : Object.entries(search.data.results).flatMap(([marketplace, products]) =>
          products.map((product) => ({ ...product, marketplace })),
        );

  return (
    <section className="page">
      <header className="page-header">
        <h2>Поиск</h2>
        <p>Поиск по выбранным маркетплейсам. Kufar и Onliner работают, Ozon и Wildberries — задел на потом.</p>
      </header>

      <div className="card">
        <form
          className="search-row"
          onSubmit={(event) => {
            event.preventDefault();
            search.mutate({ query: query.trim(), marketplaces: selected, region: "belarus" });
          }}
        >
          <input
            className="input"
            type="text"
            placeholder="Например: монитор"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button className="button primary" type="submit" disabled={!canSubmit}>
            {search.isPending ? "Ищем…" : "Найти"}
          </button>
        </form>

        <div className="checkbox-row">
          {MARKETPLACES.map((marketplace) => (
            <label className="checkbox" key={marketplace.id}>
              <input
                type="checkbox"
                checked={selected.includes(marketplace.id)}
                onChange={() => toggleMarketplace(marketplace.id)}
              />
              <span className="badge">{marketplace.id}</span>
              {marketplace.label}
            </label>
          ))}
        </div>
        <p className="muted">Регион: Беларусь (параметр region для будущих фильтров).</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Результаты</h3>
          {search.isSuccess && (
            <span className="muted">найдено: {allProducts.length}</span>
          )}
        </div>

        {search.isPending && <p className="muted">Запрашиваем маркетплейсы…</p>}

        {search.isError && (
          <p className="status error">
            Ошибка запроса: {search.error instanceof Error ? search.error.message : String(search.error)}
          </p>
        )}

        {search.isSuccess && allProducts.length === 0 && (
          <p className="muted">
            Товары не найдены.
            {Object.keys(search.data.errors).length > 0 &&
              ` Ошибки: ${Object.entries(search.data.errors)
                .map(([id, message]) => `${id}: ${message}`)
                .join("; ")}`}
          </p>
        )}

        {search.isSuccess && allProducts.length > 0 && (
          <>
            <ul className="result-list">
              {allProducts.map((product) => (
                <ProductCard key={`${product.marketplace}-${product.url}`} product={product} />
              ))}
            </ul>
            {Object.keys(search.data.errors).length > 0 && (
              <p className="status error">
                Частичные ошибки:{" "}
                {Object.entries(search.data.errors)
                  .map(([id, message]) => `${id}: ${message}`)
                  .join("; ")}
              </p>
            )}
          </>
        )}

        {search.isIdle && <p className="muted">Введите запрос и нажмите «Найти».</p>}
      </div>
    </section>
  );
}
