import { useEffect, useState } from "react";
import { subscribeDataChanged } from "./dataEvents";

/**
 * Returns a number that increments whenever app data may have changed
 * (any mutating API call resolving, or the tab regaining focus/visibility).
 * Include it in a data-fetching effect's dependency array to have that
 * effect refetch automatically instead of only on mount -- see
 * dataEvents.ts for why mount-only fetching isn't enough.
 */
export function useDataVersion(): number {
  const [version, setVersion] = useState(0);
  useEffect(() => subscribeDataChanged(() => setVersion((v) => v + 1)), []);
  return version;
}
