// Minimal hash router — deliberately dependency-free so a fork can serve
// the built app from any static host (or file://) with zero rewrite
// rules. Routes look like "#/assertions/123?tab=history".

import { useEffect, useState } from "react";
import type { AnchorHTMLAttributes, ReactNode } from "react";

export interface HashLocation {
  path: string;
  query: URLSearchParams;
}

function parseHash(): HashLocation {
  const raw = window.location.hash.replace(/^#/, "");
  const [pathPart, queryPart] = raw.split("?");
  const path = pathPart && pathPart !== "" ? pathPart : "/";
  return { path, query: new URLSearchParams(queryPart ?? "") };
}

export function useHashLocation(): HashLocation {
  const [location, setLocation] = useState<HashLocation>(parseHash);

  useEffect(() => {
    const onChange = () => setLocation(parseHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  return location;
}

export function navigate(to: string): void {
  window.location.hash = to.startsWith("#") ? to.slice(1) : to;
}

/** decodeURIComponent, or null for a malformed escape such as "%E0%A4%A". */
function safeDecode(segment: string): string | null {
  try {
    return decodeURIComponent(segment);
  } catch {
    return null;
  }
}

/** Match "/assertions/:id" against "/assertions/123" → {id: "123"}, or null.
 * A parameter with a malformed percent-escape (a truncated or hand-edited
 * link) is no match: decodeURIComponent's URIError used to escape from
 * render and blank the whole app (finding ui:27). */
export function matchPath(pattern: string, path: string): Record<string, string> | null {
  const patternParts = pattern.split("/").filter(Boolean);
  const pathParts = path.split("/").filter(Boolean);
  if (patternParts.length !== pathParts.length) return null;

  const params: Record<string, string> = {};
  for (let i = 0; i < patternParts.length; i++) {
    const expected = patternParts[i];
    const actual = pathParts[i];
    if (expected.startsWith(":")) {
      const value = safeDecode(actual);
      if (value === null) return null;
      params[expected.slice(1)] = value;
    } else if (expected !== actual) {
      return null;
    }
  }
  return params;
}

export interface LinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> {
  to: string;
  children: ReactNode;
}

export function Link({ to, children, ...rest }: LinkProps) {
  return (
    <a href={`#${to}`} {...rest}>
      {children}
    </a>
  );
}
