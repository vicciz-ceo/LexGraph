// The page declares its icon (acceptance run, release candidate). index.html
// declared none, so on every fresh load the browser asked for /favicon.ico,
// which neither the backend (a JSON 404) nor Vite's dev server (a 404) has,
// and Chrome logged the failed request as a console error. The icon is a file
// in public/, which the dev server serves at the root and the build copies
// into dist/, where the backend serves it (docs/RUNBOOK.md, "Serving the web
// app in production").

import indexHtml from "../../index.html?raw";

const PUBLIC_FILES: Record<string, string> = import.meta.glob("../../public/*", {
  query: "?raw",
  import: "default",
  eager: true,
});

function iconLinks(): HTMLLinkElement[] {
  const page = new DOMParser().parseFromString(indexHtml, "text/html");
  return [...page.head.querySelectorAll<HTMLLinkElement>('link[rel~="icon"]')];
}

describe("the page icon", () => {
  it("is declared in index.html, so the browser does not ask for /favicon.ico", () => {
    expect(iconLinks()).not.toHaveLength(0);
  });

  it("is an SVG file in public/, served at the root by the dev server and the build", () => {
    for (const link of iconLinks()) {
      const href = link.getAttribute("href") ?? "";
      expect(href).toMatch(/^\/[\w.-]+\.svg$/);
      expect(link.getAttribute("type")).toBe("image/svg+xml");
      const svg = PUBLIC_FILES[`../../public${href}`];
      expect(svg, `public${href}`).toBeTypeOf("string");
      const parsed = new DOMParser().parseFromString(svg, "image/svg+xml");
      expect(parsed.documentElement.nodeName).toBe("svg");
      expect(parsed.getElementsByTagName("parsererror")).toHaveLength(0);
    }
  });
});
