/// <reference types="vite/client" />

export {};

declare global {
  interface Window {
    pywebview?: {
      api: {
        open_link: (url: string, mode: string) => void;
      };
    };
  }
}
