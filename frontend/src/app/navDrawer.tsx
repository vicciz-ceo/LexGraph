// Narrow-viewport navigation (finding ui:26). Below 768px the stylesheet
// hides the sidebar off-canvas; this hook turns it into a drawer that the
// menu button in AppShell's mobile bar opens. While open it closes on
// Escape (focus returns to the menu button), on the close button, the
// backdrop, any link inside it, a route change, or when the viewport
// widens; Tab and Shift+Tab stay inside it.

import { useCallback, useEffect, useRef, useState } from "react";
import type { MouseEvent } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), select:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Width at which the sidebar is a static column again (app.css). */
const WIDE_QUERY = "(min-width: 768px)";

export function useNavDrawer() {
  const [open, setOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement | null>(null);
  const drawerRef = useRef<HTMLElement | null>(null);

  const close = useCallback((returnFocus: boolean) => {
    setOpen(false);
    if (returnFocus) menuButtonRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!open) return;
    const drawer = drawerRef.current;
    drawer?.querySelector<HTMLElement>(".sidebar__close")?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close(true);
        return;
      }
      if (event.key !== "Tab" || !drawer) return;
      const focusables = [...drawer.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;
      if (!drawer.contains(active)) {
        event.preventDefault();
        first.focus();
      } else if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };
    const onRouteChange = () => close(false);
    const wide = window.matchMedia?.(WIDE_QUERY);
    const onWiden = (event: MediaQueryListEvent) => {
      if (event.matches) close(false);
    };

    document.addEventListener("keydown", onKeyDown);
    window.addEventListener("hashchange", onRouteChange);
    wide?.addEventListener?.("change", onWiden);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("hashchange", onRouteChange);
      wide?.removeEventListener?.("change", onWiden);
    };
  }, [open, close]);

  return {
    open,
    menuButtonRef,
    drawerRef,
    openDrawer: () => setOpen(true),
    closeDrawer: () => close(true),
    /** Backdrop click: close, leaving focus where the pointer put it. */
    dismiss: () => close(false),
    /** Clicking a link inside the drawer closes it, even for the current page. */
    onDrawerClick: (event: MouseEvent<HTMLElement>) => {
      if (open && (event.target as Element).closest("a[href]")) close(false);
    },
  };
}

/** Three-line "menu" glyph, drawn like the icons in icons.tsx. */
export function MenuIcon() {
  return (
    <svg
      className="icon"
      width={20}
      height={20}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}
