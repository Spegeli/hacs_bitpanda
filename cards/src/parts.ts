// Pieces every card is built from: header with the eye, return chip,
// timeframe and currency switches, wallet rows, empty states. A tap opens
// Home Assistant's more-info dialog; every tappable piece works by keyboard.
import { html, nothing, svg, type TemplateResult } from "lit";
import { createRef, ref } from "lit/directives/ref.js";

import { arrow, formatPercent, formatShare, formatState, formatUnits, numberAttribute, numericState, trendClass } from "./format";
import { languageOf, t, type TextKey } from "./i18n";
import { TIMEFRAMES, type Hass, type Timeframe, type WalletRefs, type WalletSort } from "./types";

const EYE = "M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z";
const EYE_OFF = "M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.08L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.07,15.5 22.27,13.86 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.74,7.13 11.35,7 12,7Z";
const CHEVRON_DOWN = "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z";
const CHEVRON_UP = "M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z";
const CHEVRON_RIGHT = "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z";
const MAGNIFY =
  "M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z";
const CLOSE = "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z";

export const icon = (path: string): TemplateResult => svg`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${path}></path></svg>`;

export const CHEVRONS = { down: CHEVRON_DOWN, up: CHEVRON_UP, right: CHEVRON_RIGHT };

/** A keydown listener that acts on Enter and Space, as a button does. */
export function onActivate(handler: () => void): (event: KeyboardEvent) => void {
  return (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handler();
    }
  };
}

export function moreInfo(element: HTMLElement, entityId: string): void {
  element.dispatchEvent(new CustomEvent("hass-more-info", { bubbles: true, composed: true, detail: { entityId } }));
}

/** A tap's action: the entity's more-info dialog, or nothing without one. */
export function opener(element: HTMLElement, entityId: string | undefined): () => void {
  return () => {
    if (entityId) moreInfo(element, entityId);
  };
}

/** Whether every cell with a second part has room for both side by side,
 * `gap` pixels apart (widths in pixels); cells without one do not count.
 * Rows and tiles that should look alike use one answer for all. */
export function allFit(cells: readonly { room: number; first: number; second?: number }[], gap: number): boolean {
  const paired = cells.filter((cell) => cell.second !== undefined);
  return paired.length > 0 && paired.every((cell) => cell.first + gap + (cell.second as number) <= cell.room);
}

export function amount(text: string | undefined, hidden: boolean): TemplateResult {
  return html`<span class="amount ${hidden ? "blur" : ""}">${text ?? "—"}</span>`;
}

/** A text whose {`name`} placeholder holds `value` that never breaks inside
 * itself -- a date: the line breaks before it when space runs short. */
export function unbroken(text: string, name: string, value: string): TemplateResult {
  const [before, ...rest] = text.split(`{${name}}`);
  return rest.length === 0 ? html`${text}` : html`${before}<span class="nw">${value}</span>${rest.join(`{${name}}`)}`;
}

export function emptyState(text: string): TemplateResult {
  return html`<div class="empty">${text}</div>`;
}

export interface Eye {
  hidden: boolean;
  toggle: () => void;
}

export function header(hass: Hass, title: string, eye?: Eye): TemplateResult {
  return html`<div class="head">
    <div class="title">${title}</div>
    ${eye
      ? html`<button
          class="icon-btn eye"
          aria-label=${t(hass, eye.hidden ? "eye_show" : "eye_hide")}
          title=${t(hass, eye.hidden ? "eye_show" : "eye_hide")}
          @click=${eye.toggle}
        >
          ${icon(eye.hidden ? EYE_OFF : EYE)}
        </button>`
      : nothing}
  </div>`;
}

/** The return of `timeframe` in a chip, with its amount beside it in the
 * chip's colour when one is given (blurred by the eye, like every amount). */
export function returnChip(
  hass: Hass,
  value: number | undefined,
  timeframe: Timeframe,
  onTap: () => void,
  money?: { text: string | undefined; hidden: boolean },
): TemplateResult {
  const { text, direction } = formatPercent(hass, value);
  const mark = arrow(direction);
  return html`<div class="hero-line">
    <span class="chip ${trendClass(direction)}" role="button" tabindex="0" @click=${onTap} @keydown=${onActivate(onTap)}
      >${mark ? `${mark} ` : ""}${text}</span
    >
    ${direction !== "none" && money?.text
      ? html`<span class="chip-amount ${trendClass(direction)}">${amount(money.text, money.hidden)}</span>`
      : nothing}
    <span class="chip-label">${t(hass, `return_${timeframe}` as TextKey)}</span>
  </div>`;
}

/** A row of options as a radio group: arrow keys move the selection and
 * the focus with it, Space and Enter select the focused option. */
function radioGroup<T extends string>(
  name: string,
  values: readonly T[],
  selected: T,
  label: (value: T) => string,
  onSelect: (value: T) => void,
): TemplateResult {
  const step = (event: KeyboardEvent): void => {
    const delta = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 0;
    if (delta === 0) return;
    event.preventDefault();
    const next = (values.indexOf(selected) + delta + values.length) % values.length;
    onSelect(values[next] as T);
    (event.currentTarget as HTMLElement).querySelectorAll<HTMLElement>("[role=radio]")[next]?.focus();
  };
  return html`<div class="seg" role="radiogroup" aria-label=${name} @keydown=${step}>
    ${values.map(
      (value) =>
        html`<span
          role="radio"
          aria-checked=${value === selected ? "true" : "false"}
          tabindex=${value === selected ? 0 : -1}
          @click=${() => onSelect(value)}
          @keydown=${onActivate(() => onSelect(value))}
          >${label(value)}</span
        >`,
    )}
  </div>`;
}

export function timeframeSwitch(hass: Hass, selected: Timeframe, onSelect: (timeframe: Timeframe) => void): TemplateResult {
  return radioGroup(t(hass, "aria_timeframe"), TIMEFRAMES, selected, (value) => t(hass, `tf_${value}` as TextKey), onSelect);
}

/** The currency switch, offered only where there is more than one. */
export function currencySwitch(hass: Hass, currencies: readonly string[], selected: string, onSelect: (currency: string) => void): TemplateResult | null {
  return currencies.length < 2 ? null : radioGroup(t(hass, "aria_currency"), currencies, selected, (value) => value, onSelect);
}

/** A search field with the query as typed, and a cross that clears it and
 * gives the field the focus back, ready for the next search. */
export function searchField(hass: Hass, query: string, onQuery: (query: string) => void): TemplateResult {
  const field = createRef<HTMLInputElement>();
  const clear = (): void => {
    onQuery("");
    field.value?.focus();
  };
  return html`<div class="search" role="search">
    ${icon(MAGNIFY)}<input
      ${ref(field)}
      type="text"
      .value=${query}
      placeholder=${t(hass, "search_placeholder")}
      aria-label=${t(hass, "aria_search")}
      autocomplete="off"
      spellcheck="false"
      @input=${(event: Event) => onQuery((event.target as HTMLInputElement).value)}
    />${query
      ? html`<span class="clear" role="button" tabindex="0" aria-label=${t(hass, "aria_search_clear")} @click=${clear} @keydown=${onActivate(clear)}
          >${icon(CLOSE)}</span
        >`
      : nothing}
  </div>`;
}

/** Letters without an accent to strip, by their plain spelling. */
const PLAIN: Record<string, string> = { ß: "ss", ø: "o", æ: "ae", œ: "oe", ł: "l", đ: "d", ð: "d", þ: "th", ı: "i" };

/** Text as the search compares it: lower case, without accents and
 * punctuation, so "S&P" reads "sp", "All-World" "allworld" and "Ørsted"
 * "orsted". */
function searchable(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[ßøæœłđðþı]/gu, (letter) => PLAIN[letter] ?? letter)
    .replace(/[^\p{L}\p{N}\s]/gu, "");
}

/** Whether every word of `query` lies in the wallet's name, symbol or ISIN,
 * in any order: each word only narrows the matches. */
export function matchesWallet(wallet: { name: string; symbol: string; isin?: string }, query: string): boolean {
  const words = searchable(query).split(/\s+/).filter(Boolean);
  const text = searchable(`${wallet.name} ${wallet.symbol} ${wallet.isin ?? ""}`);
  return words.length > 0 && words.every((word) => text.includes(word));
}

export interface WalletRowOptions {
  hass: Hass;
  wallet: WalletRefs;
  hidden: boolean;
  onTap: () => void;
  chevron?: { open: boolean; toggle: () => void };
}

export function walletRow(options: WalletRowOptions): TemplateResult {
  const { hass, wallet, hidden, onTap, chevron } = options;
  const totalState = wallet.total ? hass.states[wallet.total] : undefined;
  const units = numberAttribute(totalState, "units");
  const totalValue = numericState(hass, wallet.total);
  const stakedValue = numericState(hass, wallet.staking);
  const share = totalValue && stakedValue && stakedValue > 0 ? (stakedValue / totalValue) * 100 : undefined;
  const { text, direction } = formatPercent(hass, numberAttribute(totalState, "total_return_percent"));
  const mark = arrow(direction);
  // The return since purchase in a chip above the value, as a group shows
  // its own; the amount is in the wallet's detail.
  const chip =
    direction === "none"
      ? html`<span class="wchip none">—</span>`
      : html`<span class="wchip ${trendClass(direction)}">${mark ? `${mark} ` : ""}${text}</span>`;
  // The staked share beside the units or below them, the same in every row
  // (the card decides: PortfolioCard.fitLayout); its APR is in the detail.
  const stake =
    share === undefined ? nothing : html`<div class="stake"><span class="badge">${t(hass, "staked", { share: formatShare(hass, share, 0) })}</span></div>`;
  const toggle = (event: Event): void => {
    event.stopPropagation();
    chevron?.toggle();
  };
  // The row's tap target and the chevron are two buttons side by side, not
  // one inside the other.
  return html`<div class="wallet">
    <div class="tap" role="button" tabindex="0" @click=${onTap} @keydown=${onActivate(onTap)}>
      <div class="main">
        <div class="n" title=${wallet.shortName}>${wallet.shortName}</div>
        <div class="sub ${share === undefined ? "" : "staked"}">
          <div class="s">
            <span class="units"
              >${amount(units === undefined ? undefined : formatUnits(hass, units, wallet.category, wallet.symbol, true), hidden)}</span
            >${wallet.isin ? html` · <span class="isin">${wallet.isin}</span>` : nothing}
          </div>
          ${stake}
        </div>
      </div>
      <div class="right">${chip}<span class="val">${amount(formatState(hass, wallet.total), hidden)}</span></div>
    </div>
    ${chevron
      ? html`<span
          class="chevron"
          role="button"
          tabindex="0"
          aria-expanded=${chevron.open ? "true" : "false"}
          @click=${toggle}
          @keydown=${(event: KeyboardEvent) => {
            event.stopPropagation();
            onActivate(chevron.toggle)(event);
          }}
          >${icon(chevron.open ? CHEVRON_UP : CHEVRON_DOWN)}</span
        >`
      : nothing}
  </div>`;
}

/** Wallets by value or return since purchase, largest first and missing
 * values last, or by name; ties by name. */
export function sortWallets(hass: Hass, wallets: WalletRefs[], sort: WalletSort): WalletRefs[] {
  const value = (wallet: WalletRefs): number => numericState(hass, wallet.total) ?? Number.NEGATIVE_INFINITY;
  const change = (wallet: WalletRefs): number =>
    numberAttribute(wallet.total ? hass.states[wallet.total] : undefined, "total_return_percent") ?? Number.NEGATIVE_INFINITY;
  const byName = (a: WalletRefs, b: WalletRefs): number => a.name.localeCompare(b.name, languageOf(hass));
  return [...wallets].sort((a, b) =>
    sort === "name" ? byName(a, b) : (sort === "value" ? value(b) - value(a) : change(b) - change(a)) || byName(a, b),
  );
}
