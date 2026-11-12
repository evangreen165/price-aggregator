export type Health = {
  status: string;
};

export type PluginInfo = {
  marketplace_id: string;
  name: string;
  version: string;
  file: string;
  parser_class: string;
};

export type PluginsReloadResponse = {
  status: string;
  plugins: PluginInfo[];
};

export type Product = {
  title: string;
  price: number | null;
  old_price: number | null;
  currency: string;
  url: string;
  marketplace: string;
  region: string;
  parsed_at: string;
};

export type SearchRequest = {
  query: string;
  marketplaces: string[];
  region: string;
};

export type SearchResponse = {
  results: Record<string, Product[]>;
  errors: Record<string, string>;
};

export type FilterOption = {
  key: string;
  label: string;
  options: string[];
};

export type FiltersResponse = {
  query: string;
  category: string;
  filters: FilterOption[];
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export function getHealth(): Promise<Health> {
  return apiGet<Health>("/api/health");
}

export function getPlugins(): Promise<PluginInfo[]> {
  return apiGet<PluginInfo[]>("/api/plugins");
}

export function reloadPlugins(): Promise<PluginsReloadResponse> {
  return apiPost<PluginsReloadResponse>("/api/plugins/reload");
}

export function searchProducts(request: SearchRequest): Promise<SearchResponse> {
  return apiPost<SearchResponse>("/api/search", request);
}

export function getFilters(query: string): Promise<FiltersResponse> {
  return apiGet<FiltersResponse>(`/api/filters?query=${encodeURIComponent(query)}`);
}
