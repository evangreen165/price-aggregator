import { NavLink, Route, Routes } from "react-router-dom";

import PluginsPage from "./pages/PluginsPage";
import ProductPage from "./pages/ProductPage";
import ResultsPage from "./pages/ResultsPage";
import SearchPage from "./pages/SearchPage";
import SettingsPage from "./pages/SettingsPage";

const navigation = [
  { to: "/", label: "Поиск", end: true },
  { to: "/results", label: "Результаты", end: false },
  { to: "/plugins", label: "Плагины", end: false },
  { to: "/settings", label: "Настройки", end: false },
];

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">PA</span>
          <div>
            <div className="brand-title">Price Aggregator</div>
            <div className="brand-subtitle">Этап 1 · скелет</div>
          </div>
        </div>
        <nav className="nav">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">v0.1 · локальный бэкенд</div>
      </aside>
      <div className="main">
        <header className="topbar">
          <h1>Агрегатор цен</h1>
          <span className="topbar-hint">FastAPI · React · PyWebview</span>
        </header>
        <main className="content">
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/product" element={<ProductPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/plugins" element={<PluginsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
