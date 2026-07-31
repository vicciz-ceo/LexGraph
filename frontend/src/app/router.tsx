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

/** Match "/assertions/:id" against "/assertions/123" → {id: "123"}, or null. */
export function matchPath(pattern: string, path: string): Record<string, string> | null {
  const patternParts = pattern.split("/").filter(Boolean);
  const pathParts = path.split("/").filter(Boolean);
  if (patternParts.length !== pathParts.length) return null;

  const params: Record<string, string> = {};
  for (let i = 0; i < patternParts.length; i++) {
    const expected = patternParts[i];
    const actual = pathParts[i];
    if (expected.startsWith(":")) {
      params[expected.slice(1)] = decodeURIComponent(actual);
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
