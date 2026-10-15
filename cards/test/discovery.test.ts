import { describe, expect, it } from "vitest";

import {
  assetLabel,
  findPortfolio,
  findPriceAssets,
  priceCurrencies,
  selectAssets,
  selectGroups,
} from "../src/discovery";
import { BTC, ETH, EUNL, makeHass, portfolioDevice, priceDevice, walletDevice } from "./fixtures";

describe("assetLabel", () => {
  it("joins name and symbol", () => {
    expect(assetLabel("Bitcoin", "BTC")).toBe("Bitcoin (BTC)");
  });

  it("gives the symbol when the name repeats it", () => {
    expect(assetLabel("BCI 5", "BCI5")).toBe("BCI5");
    expect(assetLabel("bci5", "BCI5")).toBe("BCI5");
    expect(assetLabel("", "XYZ")).toBe("XYZ");
    expect(assetLabel(undefined, "XYZ")).toBe("XYZ");
  });
});

describe("findPortfolio", () => {
  it("finds the portfolio and its five returns", () => {
    const hass = makeHass({ devices: [portfolioDevice()] });
    const refs = findPortfolio(hass);
    expect(refs?.deviceId).toBe("dev-portfolio");
    expect(refs?.totalValue).toBe("sensor.bitpanda_portfolio_total_value");
    expect(refs?.cash).toBe("sensor.bitpanda_portfolio_cash");
    expect(refs?.cashPlus).toBe("sensor.bitpanda_portfolio_cash_plus");
    expect(refs?.returns).toEqual({
      day: "sensor.bitpanda_portfolio_return_day",
      week: "sensor.bitpanda_portfolio_return_week",
      month: "sensor.bitpanda_portfolio_return_month",
      six_month: "sensor.bitpanda_portfolio_return_six_month",
      year: "sensor.bitpanda_portfolio_return_year",
    });
  });

  it("finds every wallet with its three sensors", () => {
    const hass = makeHass({ devices: [portfolioDevice(), walletDevice(BTC), walletDevice(ETH), walletDevice(EUNL)] });
    const wallets = findPortfolio(hass)?.wallets ?? [];
    expect(wallets.map((wallet) => wallet.symbol).sort()).toEqual(["BTC", "ETH", "EUNL"]);
    const eth = wallets.find((wallet) => wallet.symbol === "ETH");
    expect(eth).toMatchObject({
      deviceId: "dev-wallet-eth",
      assetId: "id-eth",
      name: "Ethereum (ETH)",
      category: "crypto",
      available: "sensor.bitpanda_eth_wallet",
      total: "sensor.bitpanda_eth_wallet_total",
      staking: "sensor.bitpanda_eth_staking",
    });
    expect(wallets.find((wallet) => wallet.symbol === "EUNL")).toMatchObject({
      isin: "IE00B4L5Y983",
      category: "etf",
    });
  });

  it("a wallet without a staking sensor has none", () => {
    const hass = makeHass({ devices: [portfolioDevice(), walletDevice(BTC)] });
    expect(findPortfolio(hass)?.wallets[0]?.staking).toBeUndefined();
  });

  it("finds sensors whose entity IDs the user renamed", () => {
    const device = portfolioDevice();
    const total = device.sensors.find((sensor) => sensor.translationKey === "total_value");
    if (total) total.entityId = "sensor.my_money";
    const hass = makeHass({ devices: [device] });
    expect(findPortfolio(hass)?.totalValue).toBe("sensor.my_money");
  });

  it("ignores entities of other integrations", () => {
    const device = portfolioDevice();
    device.sensors.push({ entityId: "sensor.foreign_total", translationKey: "total_value", state: "1", platform: "other" });
    const hass = makeHass({
      devices: [device],
      foreign: [{ entityId: "sensor.elsewhere", translationKey: "total_value", state: "5" }],
    });
    expect(findPortfolio(hass)?.totalValue).toBe("sensor.bitpanda_portfolio_total_value");
  });

  it("ignores disabled entities, which Home Assistant leaves out of its list", () => {
    const hass = makeHass({ devices: [portfolioDevice(), walletDevice(ETH)] });
    delete hass.entities["sensor.bitpanda_eth_staking"];
    expect(findPortfolio(hass)?.wallets[0]?.staking).toBeUndefined();
  });

  it("uses the user's device name", () => {
    const hass = makeHass({ devices: [portfolioDevice(), walletDevice({ ...EUNL, nameByUser: "MSCI World" })] });
    expect(findPortfolio(hass)?.wallets[0]?.name).toBe("MSCI World");
  });

  it("ignores sensors it has no use for", () => {
    const device = portfolioDevice();
    device.sensors.push(
      { entityId: "sensor.bitpanda_portfolio_odd", translationKey: "something_new", state: "1" },
      { entityId: "sensor.bitpanda_portfolio_untranslated", translationKey: "", state: "1" },
    );
    const wallet = walletDevice(BTC);
    wallet.sensors.push({ entityId: "sensor.bitpanda_btc_extra", translationKey: "extra", state: "1" });
    const hass = makeHass({ devices: [device, wallet] });
    hass.entities["sensor.bitpanda_portfolio_untranslated"] = {
      entity_id: "sensor.bitpanda_portfolio_untranslated", device_id: "dev-portfolio", platform: "bitpanda", translation_key: null,
    };
    const refs = findPortfolio(hass);
    expect(refs?.totalValue).toBe("sensor.bitpanda_portfolio_total_value");
    expect(Object.keys(refs?.returns ?? {})).toHaveLength(5);
    expect(refs?.wallets[0]).toMatchObject({ available: "sensor.bitpanda_btc_wallet", total: "sensor.bitpanda_btc_wallet_total" });
  });

  it("a wallet whose sensors have no state yet keeps its place under its device's name", () => {
    const hass = makeHass({ devices: [portfolioDevice(), walletDevice({ ...BTC, symbol: "QQQ", name: "Quux" })] });
    delete hass.states["sensor.bitpanda_qqq_wallet"];
    delete hass.states["sensor.bitpanda_qqq_wallet_total"];
    const device = hass.devices["dev-wallet-qqq"];
    if (device) device.serial_number = null;
    expect(findPortfolio(hass)?.wallets[0]).toEqual({
      deviceId: "dev-wallet-qqq",
      assetId: "",
      name: "Quux (QQQ)",
      shortName: "Quux (QQQ)",
      symbol: "",
      available: "sensor.bitpanda_qqq_wallet",
      total: "sensor.bitpanda_qqq_wallet_total",
    });
  });

  it("a wallet whose sensors became unavailable keeps the name, symbol and category it had", () => {
    const before = makeHass({ devices: [portfolioDevice(), walletDevice(EUNL)] });
    expect(findPortfolio(before)?.wallets[0]).toMatchObject({ name: "iShares Core MSCI World UCITS ETF (EUNL)", category: "etf" });
    let after = before;
    for (const entityId of ["sensor.bitpanda_eunl_wallet", "sensor.bitpanda_eunl_wallet_total"]) after = after.withState(entityId, "unavailable", {});
    expect(findPortfolio(after)?.wallets[0]).toMatchObject({
      name: "iShares Core MSCI World UCITS ETF (EUNL)",
      shortName: "iShares Core MSCI World UCITS ETF",
      symbol: "EUNL",
      isin: "IE00B4L5Y983",
      category: "etf",
    });
  });

  it("a wallet never seen with its attributes is named after its device", () => {
    const device = walletDevice({ ...BTC, symbol: "ZZZ", name: "Zeta" });
    const hass = makeHass({ devices: [portfolioDevice(), device] });
    for (const sensor of device.sensors) hass.states[sensor.entityId] = { entity_id: sensor.entityId, state: "unavailable", attributes: {} };
    expect(findPortfolio(hass)?.wallets[0]).toMatchObject({ name: "Zeta (ZZZ)", shortName: "Zeta (ZZZ)", symbol: "" });
    expect(findPortfolio(hass)?.wallets[0]?.category).toBeUndefined();
  });

  it("a price tracker never seen with its attributes is named after its device", () => {
    const device = priceDevice({ symbol: "YYY", name: "Ypsilon", category: "crypto", prices: { EUR: { state: "1" } } });
    const hass = makeHass({ devices: [device] });
    for (const sensor of device.sensors) hass.states[sensor.entityId] = { entity_id: sensor.entityId, state: "unavailable", attributes: { unit_of_measurement: "EUR" } };
    expect(findPriceAssets(hass)[0]).toMatchObject({ name: "Ypsilon (YYY)" });
  });

  it("no portfolio gives undefined", () => {
    expect(findPortfolio(makeHass())).toBeUndefined();
  });
});

describe("findPriceAssets", () => {
  it("groups price sensors by asset and currency", () => {
    const hass = makeHass({
      devices: [
        priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { EUR: { state: "90200.77" }, USD: { state: "105312.09" } } }),
        priceDevice({ symbol: "EUNL", name: "iShares Core MSCI World UCITS ETF", category: "etf", isin: "IE00B4L5Y983", prices: { EUR: { state: "95.57" } } }),
      ],
    });
    const assets = findPriceAssets(hass);
    expect(assets.find((asset) => asset.symbol === "BTC")?.prices).toEqual({
      EUR: "sensor.bitpanda_btc_price_tracker_eur",
      USD: "sensor.bitpanda_btc_price_tracker_usd",
    });
    expect(assets.find((asset) => asset.symbol === "EUNL")).toMatchObject({
      name: "iShares Core MSCI World UCITS ETF (EUNL)",
      isin: "IE00B4L5Y983",
      category: "etf",
      assetId: "id-eunl",
    });
  });

  it("shortName is the asset's own name, or the user's device name", () => {
    const hass = makeHass({
      devices: [
        priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { EUR: { state: "1" } } }),
        priceDevice({ symbol: "ETH", name: "Ethereum", category: "crypto", prices: { EUR: { state: "1" } }, nameByUser: "Ether" }),
        priceDevice({ symbol: "BCI5", name: "", category: "index", prices: { EUR: { state: "1" } } }),
      ],
    });
    const short = Object.fromEntries(findPriceAssets(hass).map((asset) => [asset.symbol, asset.shortName]));
    expect(short).toEqual({ BTC: "Bitcoin", ETH: "Ether", BCI5: "BCI5" });
  });

  it("priceCurrencies lists EUR first, then the others alphabetically", () => {
    const hass = makeHass({
      devices: [
        priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { USD: { state: "1" }, EUR: { state: "1" }, CHF: { state: "1" } } }),
        priceDevice({ symbol: "ETH", name: "Ethereum", category: "crypto", prices: { EUR: { state: "1" }, GBP: { state: "1" } } }),
      ],
    });
    expect(priceCurrencies(findPriceAssets(hass))).toEqual(["EUR", "CHF", "GBP", "USD"]);
  });

  it("a price sensor without a state has no currency yet, and other sensors are no prices", () => {
    const device = priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { EUR: { state: "1" }, USD: { state: "2" } } });
    device.sensors.push({ entityId: "sensor.bitpanda_btc_other", translationKey: "other", state: "3", attributes: { unit_of_measurement: "GBP" } });
    const hass = makeHass({ devices: [device] });
    delete hass.states["sensor.bitpanda_btc_price_tracker_usd"];
    expect(findPriceAssets(hass)[0]?.prices).toEqual({ EUR: "sensor.bitpanda_btc_price_tracker_eur" });
  });

  it("priceCurrencies without EUR lists the others", () => {
    const hass = makeHass({ devices: [priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { USD: { state: "1" } } })] });
    expect(priceCurrencies(findPriceAssets(hass))).toEqual(["USD"]);
  });

  it("an unknown category is left out", () => {
    const hass = makeHass({ devices: [priceDevice({ symbol: "X", name: "X", category: "future", prices: { EUR: { state: "1" } } })] });
    expect(findPriceAssets(hass)[0]?.category).toBeUndefined();
  });
});

describe("selectAssets", () => {
  const items = [
    { deviceId: "a", assetId: "1", name: "A", shortName: "A", symbol: "A" },
    { deviceId: "b", assetId: "2", name: "B", shortName: "B", symbol: "B" },
    { deviceId: "c", assetId: "3", name: "C", shortName: "C", symbol: "C" },
  ];

  it("all returns everything", () => {
    expect(selectAssets(items, "all", ["b"]).map((item) => item.deviceId)).toEqual(["a", "b", "c"]);
  });

  it("all_except drops the picked", () => {
    expect(selectAssets(items, "all_except", ["b"]).map((item) => item.deviceId)).toEqual(["a", "c"]);
  });

  it("only keeps the picked order", () => {
    expect(selectAssets(items, "only", ["c", "a"]).map((item) => item.deviceId)).toEqual(["c", "a"]);
  });

  it("skips picked devices that no longer exist", () => {
    expect(selectAssets(items, "only", ["gone", "b"]).map((item) => item.deviceId)).toEqual(["b"]);
    expect(selectAssets(items, "all_except", ["gone"]).map((item) => item.deviceId)).toEqual(["a", "b", "c"]);
  });

  it("picks an asset by its asset ID as by its device ID", () => {
    expect(selectAssets(items, "only", ["3", "a"]).map((item) => item.deviceId)).toEqual(["c", "a"]);
    expect(selectAssets(items, "all_except", ["2"]).map((item) => item.deviceId)).toEqual(["a", "c"]);
  });

  it("shows an asset named twice, as device and as asset ID, once, at its first mention", () => {
    expect(selectAssets(items, "only", ["c", "2", "3", "b", "c"]).map((item) => item.deviceId)).toEqual(["c", "b"]);
  });

  it("matches no asset by an empty asset ID", () => {
    const blank = [{ deviceId: "x", assetId: "", name: "X", shortName: "X", symbol: "X" }];
    expect(selectAssets(blank, "only", [""])).toEqual([]);
  });
});

describe("selectGroups", () => {
  const items = [
    { deviceId: "a", assetId: "1", name: "A", shortName: "A", symbol: "A", category: "crypto" as const },
    { deviceId: "b", assetId: "2", name: "B", shortName: "B", symbol: "B", category: "etf" as const },
    { deviceId: "c", assetId: "3", name: "C", shortName: "C", symbol: "C" },
  ];

  it("all keeps every group", () => {
    expect(selectGroups(items, "all", ["etf"]).map((item) => item.deviceId)).toEqual(["a", "b", "c"]);
  });

  it("all_except drops the picked groups; an asset without one counts as other", () => {
    expect(selectGroups(items, "all_except", ["etf"]).map((item) => item.deviceId)).toEqual(["a", "c"]);
    expect(selectGroups(items, "all_except", ["other"]).map((item) => item.deviceId)).toEqual(["a", "b"]);
  });

  it("only keeps the picked groups, in the assets' own order", () => {
    expect(selectGroups(items, "only", ["other", "crypto"]).map((item) => item.deviceId)).toEqual(["a", "c"]);
    expect(selectGroups(items, "only", [])).toEqual([]);
  });
});

describe("the registry search", () => {
  it("reads Home Assistant's entity registry again only when it changed", () => {
    const base = makeHass({ devices: [portfolioDevice(), walletDevice(BTC), priceDevice({ symbol: "EUNL", name: "iShares", category: "etf", prices: { EUR: { state: "95.57" } } })] });
    let reads = 0;
    const counted = (entities: typeof base.entities): typeof base.entities =>
      new Proxy(entities, {
        ownKeys(target) {
          reads += 1;
          return Reflect.ownKeys(target);
        },
      });
    const hass = { ...base, entities: counted(base.entities) };
    expect(findPriceAssets(hass)).toHaveLength(1);
    expect(findPortfolio(hass)?.wallets).toHaveLength(1);
    findPriceAssets({ ...hass, states: { ...hass.states } });
    expect(reads).toBe(1);
    // A device registry of its own: the devices are looked at again.
    const renamed = { ...hass, devices: { ...hass.devices, "dev-price-eunl": { ...hass.devices["dev-price-eunl"]!, model: "Something else" } } };
    expect(findPriceAssets(renamed)).toHaveLength(0);
    // A new entity registry: searched again.
    findPriceAssets({ ...hass, entities: counted({ ...base.entities }) });
    expect(reads).toBe(2);
  });
});
