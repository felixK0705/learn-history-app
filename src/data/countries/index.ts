import type { CountryInfo } from "../types";
import { asiaCountries } from "./asia";
import { westCountries } from "./west";

export const countries: CountryInfo[] = [...asiaCountries, ...westCountries].sort(
  (a, b) => a.name.localeCompare(b.name, "zh-Hant"),
);

export const countryByIso = new Map(countries.map((c) => [c.iso, c]));
