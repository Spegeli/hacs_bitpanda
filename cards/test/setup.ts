// Home Assistant's app element: the cards define themselves once it is
// there (register.ts, whenRegistryReady), as in a loaded frontend.
customElements.define("home-assistant", class extends HTMLElement {});
// Home Assistant's form, as a card's editor finds it loaded: here an element
// that only keeps the properties the editor gives it.
customElements.define("ha-form", class extends HTMLElement {});
