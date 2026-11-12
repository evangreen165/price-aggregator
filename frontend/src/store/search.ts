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
  meta: Record<string, { truncated: boolean }>;
  requestError: string | null;
  filters: FilterOption[];
  filtersCategory: string | null;
  filtersLoading: boolean;
  selectedFilters: Record<string, string[]>;
  linkOpenMode: LinkOpenMode;
  currentPage: number;
  itemsPerPage: number;
  deepPagination: boolean;
  pageStart: number;
  minPrice: number | null;
  maxPrice: number | null;
  setQuery: (query: string) => void;
  toggleMarketplace: (id: string) => void;
  runSearch: (mode?: { pageStart?: number; append?: boolean }) => Promise<void>;
  loadMore: () => Promise<void>;
  setFilters: (category: string | null, filters: FilterOption[]) => void;
  setFiltersLoading: (loading: boolean) => void;
  toggleFilterOption: (key: string, option: string) => void;
  clearFilters: () => void;
  setLinkOpenMode: (mode: LinkOpenMode) => void;
  setCurrentPage: (page: number) => void;
  setItemsPerPage: (count: number) => void;
  setDeepPagination: (enabled: boolean) => void;
  setPriceRange: (min: number | null, max: number | null) => void;
};

export const useSearchStore = create<SearchStore>((set, get) => ({
  query: "",
  marketplaces: ["kufar", "onliner"],
  status: "idle",
  results: {},
  errors: {},
  meta: {},
  requestError: null,
  filters: [],
  filtersCategory: null,
  filtersLoading: false,
  selectedFilters: {},
  linkOpenMode: "current_window",
  currentPage: 1,
  itemsPerPage: 50,
  deepPagination: false,
  pageStart: 1,
  minPrice: null,
  maxPrice: null,

  setQuery: (query) => set({ query }),

  toggleMarketplace: (id) =>
    set((state) => ({
      marketplaces: state.marketplaces.includes(id)
        ? state.marketplaces.filter((marketplace) => marketplace !== id)
        : [...state.marketplaces, id],
    })),

  runSearch: async (mode) => {
    const { query, marketplaces, selectedFilters, deepPagination } = get();
    const filters = Object.fromEntries(
      Object.entries(selectedFilters).filter(([, options]) => options.length > 0),
    );
    const pageStart = mode?.pageStart ?? 1;
    const append = mode?.append ?? false;
    set({ status: "loading", requestError: null });
    try {
      const response = await searchProducts({
        query: query.trim(),
        marketplaces,
        region: "belarus",
        limit_pages: deepPagination ? 50 : 10,
        filters,
        page_start: pageStart,
      });
      if (append) {
        const merged: Record<string, Product[]> = {};
        for (const [marketplace, products] of Object.entries(response.results)) {
          const existing = get().results[marketplace] ?? [];
          const seen = new Set(existing.map((product) => product.url));
          merged[marketplace] = [
            ...existing,
            ...products.filter((product) => !seen.has(product.url)),
          ];
        }
        set({
          status: "success",
          results: merged,
          errors: response.errors,
          meta: response.meta,
          pageStart: pageStart + 1,
        });
      } else {
        set({
          status: "success",
          results: response.results,
          errors: response.errors,
          meta: response.meta,
          currentPage: 1,
          pageStart: 2,
        });
      }
    } catch (error) {
      set({
        status: "error",
        results: {},
        errors: {},
        requestError: error instanceof Error ? error.message : String(error),
      });
    }
  },

  loadMore: async () => {
    const { pageStart } = get();
    await get().runSearch({ pageStart, append: true });
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

  setCurrentPage: (currentPage) => set({ currentPage }),

  setItemsPerPage: (itemsPerPage) => set({ itemsPerPage, currentPage: 1 }),

  setDeepPagination: (deepPagination) => set({ deepPagination }),

  setPriceRange: (minPrice, maxPrice) => set({ minPrice, maxPrice }),
}));
