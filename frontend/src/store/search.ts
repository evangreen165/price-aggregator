import { create } from "zustand";

import { FilterOption, Product, searchProducts } from "../api/client";

type SearchStatus = "idle" | "loading" | "success" | "error";

export type LinkOpenMode = "system" | "new_window" | "current_window";

type SearchStore = {
  query: string;
  marketplaces: string[];
  status: SearchStatus;
  results: Record<string, Product[]>;
  errors: Record<string, string>;
  requestError: string | null;
  filters: FilterOption[];
  filtersCategory: string | null;
  filtersLoading: boolean;
  selectedFilters: Record<string, string[]>;
  linkOpenMode: LinkOpenMode;
  setQuery: (query: string) => void;
  toggleMarketplace: (id: string) => void;
  runSearch: () => Promise<void>;
  setFilters: (category: string | null, filters: FilterOption[]) => void;
  setFiltersLoading: (loading: boolean) => void;
  toggleFilterOption: (key: string, option: string) => void;
  clearFilters: () => void;
  setLinkOpenMode: (mode: LinkOpenMode) => void;
};

export const useSearchStore = create<SearchStore>((set, get) => ({
  query: "",
  marketplaces: ["kufar", "onliner"],
  status: "idle",
  results: {},
  errors: {},
  requestError: null,
  filters: [],
  filtersCategory: null,
  filtersLoading: false,
  selectedFilters: {},
  linkOpenMode: "current_window",

  setQuery: (query) => set({ query }),

  toggleMarketplace: (id) =>
    set((state) => ({
      marketplaces: state.marketplaces.includes(id)
        ? state.marketplaces.filter((marketplace) => marketplace !== id)
        : [...state.marketplaces, id],
    })),

  runSearch: async () => {
    const { query, marketplaces, selectedFilters } = get();
    const filters = Object.fromEntries(
      Object.entries(selectedFilters).filter(([, options]) => options.length > 0),
    );
    set({ status: "loading", requestError: null });
    try {
      const response = await searchProducts({
        query: query.trim(),
        marketplaces,
        region: "belarus",
        limit_pages: 10,
        filters,
      });
      set({ status: "success", results: response.results, errors: response.errors });
    } catch (error) {
      set({
        status: "error",
        results: {},
        errors: {},
        requestError: error instanceof Error ? error.message : String(error),
      });
    }
  },

  setFilters: (filtersCategory, filters) => set({ filtersCategory, filters }),

  setFiltersLoading: (filtersLoading) => set({ filtersLoading }),

  toggleFilterOption: (key, option) =>
    set((state) => {
      const current = state.selectedFilters[key] ?? [];
      const next = current.includes(option)
        ? current.filter((item) => item !== option)
        : [...current, option];
      return { selectedFilters: { ...state.selectedFilters, [key]: next } };
    }),

  clearFilters: () => set({ selectedFilters: {} }),

  setLinkOpenMode: (linkOpenMode) => set({ linkOpenMode }),
}));
