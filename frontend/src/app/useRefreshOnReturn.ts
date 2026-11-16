// For a page that lists what other people change (the Review Queue): calls
// `refresh` when the user comes back to the page it shows, so that the list is
// read again then.
//
// - "link": the route changed while the page stayed shown, or the user clicked
//   the nav link of the page already shown. That click changes nothing in the
//   URL, so AppShell signals a hashchange, which gives the location a new
//   identity (the topbar search does the same).
// - "return": this browser tab is shown again, or its window regains focus.

import { useEffect, useRef } from "react";

import { useHashLocation } from "./router";

export type ReturnCause = "link" | "return";

export function useRefreshOnReturn(refresh: (cause: ReturnCause) => void): void {
  const latest = useRef(refresh);
  useEffect(() => {
    latest.current = refresh;
  });

  const location = useHashLocation();
  const shown = useRef(location);
  useEffect(() => {
    if (location === shown.current) return;
    shown.current = location;
    latest.current("link");
  }, [location]);

  useEffect(() => {
    const onFocus = () => latest.current("return");
    const onVisibility = () => {
      if (document.visibilityState === "visible") latest.current("return");
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);
}
