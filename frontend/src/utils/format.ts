export const formatPercent = (value: number, digits = 1) =>
  `${(value * 100).toFixed(digits)}%`;

export const shortId = (value: string, length = 12) =>
  value.length > length ? `${value.slice(0, length)}…` : value;
