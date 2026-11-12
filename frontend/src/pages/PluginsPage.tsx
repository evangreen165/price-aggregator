import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getPlugins, reloadPlugins } from "../api/client";

export default function PluginsPage() {
  const queryClient = useQueryClient();
  const plugins = useQuery({
    queryKey: ["plugins"],
    queryFn: getPlugins,
  });

  const reload = useMutation({
    mutationFn: reloadPlugins,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["plugins"] });
    },
  });

  return (
    <section className="page">
      <header className="page-header">
        <h2>Плагины</h2>
        <p>Парсеры подключаются как плагины через pluggy. Здесь видно, что загружено.</p>
      </header>

      <div className="card">
        <div className="card-header">
          <h3>Загруженные плагины</h3>
          <button
            className="button"
            type="button"
            onClick={() => reload.mutate()}
            disabled={reload.isPending}
          >
            {reload.isPending ? "Перезагрузка…" : "Перезагрузить плагины"}
          </button>
        </div>

        {plugins.isLoading && <p className="muted">Загрузка…</p>}

        {plugins.isError && (
          <p className="status error">
            Ошибка:{" "}
            {plugins.error instanceof Error ? plugins.error.message : String(plugins.error)}
          </p>
        )}

        {plugins.isSuccess && plugins.data.length === 0 && (
          <p className="muted">Плагины не найдены. Положите файл в backend/plugins.</p>
        )}

        {plugins.isSuccess && plugins.data.length > 0 && (
          <ul className="plugin-list">
            {plugins.data.map((plugin) => (
              <li className="plugin-card" key={plugin.marketplace_id}>
                <div className="plugin-title">
                  <span className="badge">{plugin.marketplace_id}</span>
                  <strong>{plugin.name}</strong>
                  <span className="muted">v{plugin.version}</span>
                </div>
                <dl className="plugin-meta">
                  <div>
                    <dt>Файл</dt>
                    <dd>{plugin.file || "—"}</dd>
                  </div>
                  <div>
                    <dt>Класс</dt>
                    <dd>{plugin.parser_class}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        )}

        {reload.isError && (
          <p className="status error">
            Не удалось перезагрузить:{" "}
            {reload.error instanceof Error ? reload.error.message : String(reload.error)}
          </p>
        )}
      </div>
    </section>
  );
}
