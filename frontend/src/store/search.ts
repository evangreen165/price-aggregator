import { create } from "zustand";

import { Product, searchProducts } from "../api/client";

type SearchStatus = "idle" | "loading" | "success" | "error";

export type LinkOpenMode = "system" | "new_window" | "current_window";

export type SortMode = "default" | "price_asc" | "price_desc" | "rating_desc";

type SearchStore = {
  query: string;
  marketplaces: string[];
  status: SearchStatus;
  results: Record<string, Product[]>;
  errors: Record<string, string>;
  meta: Record<string, { truncated: boolean }>;
  requestError: string | null;
  nextPage: Record<string, number | null>;
  nextCursor: Record<string, string | null>;
  linkOpenMode: LinkOpenMode;
  currentPage: number;
  itemsPerPage: number;
  deepPagination: boolean;
  minPrice: number | null;
  maxPrice: number | null;
  sortBy: SortMode;
  discountOnly: boolean;
  setQuery: (query: string) => void;
  toggleMarketplace: (id: string) => void;
  runSearch: (mode?: {
    page?: Record<string, number>;
    cursor?: Record<string, string>;
    append?: boolean;
  }) => Promise<void>;
  loadMore: () => Promise<void>;
  setLinkOpenMode: (mode: LinkOpenMode) => void;
  setCurrentPage: (page: number) => void;
  setItemsPerPage: (count: number) => void;
  setDeepPagination: (enabled: boolean) => void;
  setPriceRange: (min: number | null, max: number | null) => void;
  setSortBy: (sortBy: SortMode) => void;
  setDiscountOnly: (enabled: boolean) => void;
};

export const useSearchStore = create<SearchStore>((set, get) => ({
  query: "",
  marketplaces: [],
  status: "idle",
  results: {},
  errors: {},
  meta: {},
  requestError: null,
  nextPage: {},
  nextCursor: {},
  linkOpenMode: "current_window",
  currentPage: 1,
  itemsPerPage: 50,
  deepPagination: false,
  minPrice: null,
  maxPrice: null,
  sortBy: "default",
  discountOnly: false,

  setQuery: (query) => set({ query }),

  toggleMarketplace: (id) =>
    set((state) => ({
      marketplaces: state.marketplaces.includes(id)
        ? state.marketplaces.filter((marketplace) => marketplace !== id)
        : [...state.marketplaces, id],
    })),

  runSearch: async (mode) => {
    const { query, marketplaces, deepPagination } = get();
    const page = mode?.page ?? {};
    const cursor = mode?.cursor ?? {};
    const append = mode?.append ?? false;
    set({ status: "loading", requestError: null });
    try {
      const response = await searchProducts({
        query: query.trim(),
        marketplaces,
        region: "belarus",
        limit_pages: deepPagination ? 50 : 10,
        page,
        cursor,
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
          nextPage: response.next_page,
          nextCursor: response.next_cursor,
        });
      } else {
        set({
          status: "success",
          results: response.results,
          errors: response.errors,
          meta: response.meta,
          nextPage: response.next_page,
          nextCursor: response.next_cursor,
          currentPage: 1,
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
    const { nextPage, nextCursor, marketplaces } = get();
    const page: Record<string, number> = {};
    const cursor: Record<string, string> = {};
    for (const marketplace of marketplaces) {
      if (nextCursor[marketplace]) {
        cursor[marketplace] = nextCursor[marketplace] as string;
      } else if (nextPage[marketplace] != null) {
        page[marketplace] = nextPage[marketplace] as number;
      }
    }
    if (Object.keys(page).length === 0 && Object.keys(cursor).length === 0) {
      return;
    }
    await get().runSearch({ page, cursor, append: true });
  },

  setLinkOpenMode: (linkOpenMode) => set({ linkOpenMode }),

  setCurrentPage: (currentPage) => set({ currentPage }),

  setItemsPerPage: (itemsPerPage) => set({ itemsPerPage, currentPage: 1 }),

  setDeepPagination: (deepPagination) => set({ deepPagination }),

  setPriceRange: (minPrice, maxPrice) => set({ minPrice, maxPrice, currentPage: 1 }),

  setSortBy: (sortBy) => set({ sortBy, currentPage: 1 }),

  setDiscountOnly: (discountOnly) => set({ discountOnly, currentPage: 1 }),
}));
