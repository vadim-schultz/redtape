const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["day", 86_400],
  ["hour", 3_600],
  ["minute", 60],
];

/** Coarsest whole unit that fits `seconds`; null once it is under a minute. */
function pickUnit(
  seconds: number,
): [Intl.RelativeTimeFormatUnit, number] | null {
  for (const [unit, secondsPerUnit] of UNITS) {
    const value = Math.floor(seconds / secondsPerUnit);
    if (value >= 1) return [unit, value];
  }
  return null;
}

/** "5 minutes ago" for a past ISO date; "just now" once it rounds to zero. */
export function formatRelativeTime(
  isoDate: string,
  locale: string,
  now: Date = new Date(),
): string {
  const elapsedSeconds = Math.max(
    0,
    (now.getTime() - new Date(isoDate).getTime()) / 1000,
  );
  const picked = pickUnit(elapsedSeconds);
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  if (!picked) return formatter.format(0, "second");

  const [unit, value] = picked;
  return formatter.format(-value, unit);
}

/** "in 3 hours" while `notBefore` lies ahead of `now`; null when unset, unparseable, due or past. */
export function formatTimeUntil(
  notBefore: string | null,
  locale: string,
  now: Date = new Date(),
): string | null {
  if (!notBefore) return null;
  const target = new Date(notBefore).getTime();
  if (Number.isNaN(target)) return null;

  const secondsAhead = (target - now.getTime()) / 1000;
  if (secondsAhead <= 0) return null;

  const [unit, value] = pickUnit(secondsAhead) ?? ["minute", 1];
  return new Intl.RelativeTimeFormat(locale, { numeric: "auto" }).format(
    value,
    unit,
  );
}
