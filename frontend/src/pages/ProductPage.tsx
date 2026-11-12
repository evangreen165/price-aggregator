import { Link, useSearchParams } from "react-router-dom";

export default function ProductPage() {
  const [searchParams] = useSearchParams();
  const url = searchParams.get("url") ?? "";

  let host = "товар";
  try {
    host = new URL(url).hostname;
  } catch {
    host = "товар";
  }

  return (
    <section className="page product-page">
      <header className="page-header product-toolbar">
        <Link className="button" to="/">
          ← Назад к поиску
        </Link>
        <h2>{host}</h2>
      </header>
      <div className="iframe-wrapper">
        {url ? (
          <iframe className="product-frame" src={`/proxy?url=${encodeURIComponent(url)}`} title="Страница товара" />
        ) : (
          <p className="muted">Ссылка на товар отсутствует.</p>
        )}
      </div>
    </section>
  );
}
