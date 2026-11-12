import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { getHealth } from "../api/client";

export default function SearchPage() {
  const [query, setQuery] = useState("");

  const health = useMutation({
    mutationFn: getHealth,
  });

  return (
    <section className="page">
      <header className="page-header">
        <h2>Поиск</h2>
        <p>Задел под поиск по маркетплейсам — реальные парсеры появятся на следующем этапе.</p>
      </header>

      <div className="card">
        <form
          className="search-row"
          onSubmit={(event) => {
            event.preventDefault();
          }}
        >
          <input
            className="input"
            type="text"
            placeholder="Например: iPhone 15"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button className="button primary" type="submit" disabled>
            Найти
          </button>
        </form>
        <p className="muted">Поиск пока не активен: сначала подключаем парсеры.</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Проверка связи с бэкендом</h3>
          <button
            className="button"
            type="button"
            onClick={() => health.mutate()}
            disabled={health.isPending}
          >
            {health.isPending ? "Проверяем…" : "Проверить связь"}
          </button>
        </div>
        {health.isSuccess && (
          <p className="status ok">Статус: {health.data.status}</p>
        )}
        {health.isError && (
          <p className="status error">
            Ошибка: {health.error instanceof Error ? health.error.message : String(health.error)}
          </p>
        )}
        {health.isIdle && <p className="muted">Бэкенд ещё не опрошен.</p>}
      </div>
    </section>
  );
}
