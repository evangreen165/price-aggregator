export default function ResultsPage() {
  return (
    <section className="page">
      <header className="page-header">
        <h2>Результаты</h2>
        <p>Здесь появятся собранные предложения с фильтрами и сортировкой.</p>
      </header>
      <div className="card empty-state">
        <p className="empty-title">Пока пусто</p>
        <p className="muted">Список результатов появится после подключения парсеров на следующем этапе.</p>
      </div>
    </section>
  );
}
