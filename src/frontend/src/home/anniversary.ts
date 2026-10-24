// "Around this time in earlier years", for the Throwback widget.

const DAY = 86_400_000;

// That day and month in `year`. Feb 29 is Feb 28 in a year without one (a plain
// Date rolls it over to Mar 1).
function sameDayIn(year: number, date: Date): Date {
  const leap = new Date(year, 1, 29).getMonth() === 1;
  const day =
    date.getMonth() === 1 && date.getDate() === 29 && !leap
      ? 28
      : date.getDate();
  return new Date(year, date.getMonth(), day);
}

/** The anniversary of `added` nearest to today: how many days away it is, and
 * how many years after `added` it falls. Last and next year count too, so Dec 30
 * is 3 days from Jan 2, not 362. */
export function nearestAnniversary(
  added: Date,
  now: Date,
): { days: number; years: number } {
  const today = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
  ).getTime();
  let best = { days: Number.POSITIVE_INFINITY, years: 0 };
  for (const shift of [-1, 0, 1]) {
    const year = now.getFullYear() + shift;
    const days = Math.round((sameDayIn(year, added).getTime() - today) / DAY);
    if (Math.abs(days) < Math.abs(best.days))
      best = { days, years: year - added.getFullYear() };
  }
  return best;
}
