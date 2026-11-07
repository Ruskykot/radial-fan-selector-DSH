// Границы валидации и списки фильтров — зеркало data/config.json и data/*.json.
export const VALIDATION = {
  q: { min: 100, max: 100000 },
  p: { min: 10, max: 10000 },
} as const;

export const SERIES_OPTIONS = ["ВР 86-77", "ВР 280-46"] as const;
export const DN_OPTIONS = [2.5, 3.15, 4.0, 5.0, 6.3, 8.0, 10.0, 12.5] as const;
export const DDN_OPTIONS = [0.9, 1.0, 1.05] as const;
export const RPM_OPTIONS = [750, 1000, 1500, 3000] as const;
