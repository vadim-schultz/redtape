const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["day", 86_400],
  ["hour", 3_600],
  ["minute", 60],
];

/** Coarsest whole unit that fits the seconds ahead, at least one minute. */
function pickUnit(secondsAhead: number): [Intl.RelativeTimeFormatUnit, number] {
  for (const [unit, secondsPerUnit] of UNITS) {
    const value = Math.floor(secondsAhead / secondsPerUnit);
    if (value >= 1) return [unit, value];
  }
  return ["minute", 1];
}

/** "in 3 hours" while ``notBefore`` lies ahead of ``now``; ``null`` once it is due or unset. */
export function formatRetryAfter(
  notBefore: string | null,
  locale: string,
  now: Date = new Date(),
): string | null {
  if (!notBefore) return null;
  const secondsAhead = (new Date(notBefore).getTime() - now.getTime()) / 1000;
  if (secondsAhead <= 0) return null;

  const [unit, value] = pickUnit(secondsAhead);
  return new Intl.RelativeTimeFormat(locale, { numeric: "auto" }).format(
    value,
    unit,
  );
}
