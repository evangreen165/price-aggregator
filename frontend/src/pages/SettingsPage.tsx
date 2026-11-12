import { LinkOpenMode, useSearchStore } from "../store/search";

const LINK_MODES: { id: LinkOpenMode; label: string }[] = [
  { id: "system", label: "Открывать ссылки в системном браузере" },
  { id: "new_window", label: "Открывать в новом окне приложения" },
  { id: "current_window", label: "Открывать в текущем окне (с кнопкой «Назад»)" },
];

export default function SettingsPage() {
  const search = useSearchStore();

  return (
    <section className="page">
      <header className="page-header">
        <h2>Настройки</h2>
        <p>Параметры приложения и способ открытия ссылок на товары.</p>
      </header>

      <div className="card">
        <h3>Открытие ссылок на товары</h3>
        <div className="radio-row">
          {LINK_MODES.map((mode) => (
            <label className="radio" key={mode.id}>
              <input
                type="radio"
                name="link-open-mode"
                value={mode.id}
                checked={search.linkOpenMode === mode.id}
                onChange={() => search.setLinkOpenMode(mode.id)}
              />
              {mode.label}
            </label>
          ))}
        </div>
        <p className="muted">
          «Системный браузер» открывает ссылку в Chrome/Edge, «новое окно» — в отдельном окне
          приложения, «текущее окно» — внутри приложения с плавающей кнопкой «Назад».
        </p>
      </div>

      <div className="card">
        <h3>Следующий этап</h3>
        <p className="muted">
          Здесь появятся выбор маркетплейсов, прокси, лимиты запросов и экспорт.
        </p>
      </div>
    </section>
  );
}
