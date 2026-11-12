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

async function apiPost<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { Accept: "application/json" },
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
