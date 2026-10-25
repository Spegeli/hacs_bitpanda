import { afterEach, describe, expect, it, vi } from "vitest";

import { whenRegistryReady } from "../src/register";

/** A registry as Home Assistant's frontend replaces window.customElements
 * with: its own map, nothing of the browser's. */
function fakeRegistry(defined: string[] = []): CustomElementRegistry {
  const names = new Set(defined);
  return { get: (name: string) => (names.has(name) ? class extends HTMLElement {} : undefined) } as unknown as CustomElementRegistry;
}

afterEach(() => {
  vi.useRealTimers();
});

describe("whenRegistryReady", () => {
  it("is ready at once where Home Assistant's app is already defined", async () => {
    const registry = fakeRegistry(["home-assistant"]);
    await expect(whenRegistryReady(() => registry, registry)).resolves.toBe(registry);
  });

  it("waits for the registry Home Assistant puts in place after the module loaded", async () => {
    vi.useFakeTimers();
    const loadedWith = fakeRegistry();
    let current = loadedWith;
    let ready: CustomElementRegistry | undefined;
    void whenRegistryReady(() => current, loadedWith).then((registry) => {
      ready = registry;
    });
    await vi.advanceTimersByTimeAsync(500);
    expect(ready).toBeUndefined();
    const replaced = fakeRegistry();
    current = replaced;
    await vi.advanceTimersByTimeAsync(100);
    expect(ready).toBe(replaced);
  });

  it("gives up waiting after ten seconds", async () => {
    vi.useFakeTimers();
    const loadedWith = fakeRegistry();
    let ready: CustomElementRegistry | undefined;
    void whenRegistryReady(() => loadedWith, loadedWith).then((registry) => {
      ready = registry;
    });
    await vi.advanceTimersByTimeAsync(9_900);
    expect(ready).toBeUndefined();
    await vi.advanceTimersByTimeAsync(200);
    expect(ready).toBe(loadedWith);
  });
});
