import '@testing-library/jest-dom/vitest';

// jsdom implements neither, and the component tree needs both: Radix's
// ScrollArea observes its viewport, and the citation handler scrolls the
// matching highlight into view. Stubbing them here keeps the tests about
// behaviour rather than about what jsdom happens to ship.
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

Element.prototype.scrollTo = Element.prototype.scrollTo || function scrollTo() {};
