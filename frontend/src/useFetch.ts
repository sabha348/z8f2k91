import { useEffect, useState } from "react";

export type FetchState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

/** Run `load` whenever `deps` change; ignores responses from superseded requests. */
export function useFetch<T>(load: () => Promise<T>, deps: unknown[]): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    load().then(
      (data) => active && setState({ status: "ready", data }),
      (err: unknown) =>
        active && setState({ status: "error", message: err instanceof Error ? err.message : String(err) }),
    );
    return () => {
      active = false;
    };
  }, deps);
  return state;
}
