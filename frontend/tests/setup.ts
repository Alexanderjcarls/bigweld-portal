import "@testing-library/jest-dom/vitest";

class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(window, "ResizeObserver", {
  configurable: true,
  value: ResizeObserver,
  writable: true,
});
