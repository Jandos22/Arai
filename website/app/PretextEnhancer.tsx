"use client";

import { useEffect } from "react";
import Script from "next/script";

declare global {
  interface Window {
    Pretext?: {
      prepare: (text: string, font: string) => unknown;
      layout: (handle: unknown, maxWidth: number, lineHeight: number) => { height: number; lineCount: number };
    };
  }
}

// Self-sizes any element marked `data-pretext`. The layout is computed
// from the element's actual font/width on every resize, so card descriptions
// and the hero headline reflow without `line-clamp` clipping anything.
export default function PretextEnhancer() {
  useEffect(() => {
    let cancelled = false;
    let cleanup: (() => void) | null = null;

    async function enhance() {
      const Pretext = window.Pretext;
      if (!Pretext) return;
      if (document.fonts && "ready" in document.fonts) {
        try {
          await document.fonts.ready;
        } catch {
          /* ignore — fall through and measure anyway */
        }
      }
      if (cancelled) return;

      const elements = Array.from(document.querySelectorAll<HTMLElement>("[data-pretext]"));
      const prepared = new Map<HTMLElement, unknown>();

      const fontFor = (el: HTMLElement) => {
        const cs = getComputedStyle(el);
        return `${cs.fontStyle || "normal"} ${cs.fontWeight || 400} ${cs.fontSize} ${cs.fontFamily}`;
      };
      const lineHeightFor = (el: HTMLElement) => {
        const cs = getComputedStyle(el);
        const lh = cs.lineHeight;
        const fs = parseFloat(cs.fontSize);
        if (!lh || lh === "normal") return fs * 1.2;
        if (lh.endsWith("px")) return parseFloat(lh);
        return fs * parseFloat(lh);
      };
      const reprep = (el: HTMLElement) => {
        const text = el.textContent || "";
        if (!text.trim()) {
          prepared.delete(el);
          return;
        }
        try {
          prepared.set(el, Pretext.prepare(text, fontFor(el)));
        } catch {
          /* swallow — leaves element with natural CSS height */
        }
      };
      const relayoutEl = (el: HTMLElement) => {
        const handle = prepared.get(el);
        if (!handle) return;
        const w = el.clientWidth;
        if (w <= 0) return;
        try {
          const { height, lineCount } = Pretext.layout(handle, w, lineHeightFor(el));
          el.style.minHeight = `${height}px`;
          el.dataset.pretextLines = String(lineCount);
        } catch {
          /* ignore */
        }
      };
      const relayoutAll = () => {
        for (const el of elements) relayoutEl(el);
      };

      for (const el of elements) reprep(el);
      relayoutAll();

      let raf: number | null = null;
      const schedule = () => {
        if (raf) return;
        raf = requestAnimationFrame(() => {
          raf = null;
          relayoutAll();
        });
      };

      const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(schedule) : null;
      if (ro) {
        ro.observe(document.body);
        for (const el of elements) ro.observe(el);
      } else {
        window.addEventListener("resize", schedule);
      }

      const observers: MutationObserver[] = [];
      for (const el of elements) {
        if (el.getAttribute("contenteditable")) {
          const mo = new MutationObserver(() => {
            reprep(el);
            relayoutEl(el);
          });
          mo.observe(el, { characterData: true, subtree: true, childList: true });
          observers.push(mo);
        }
      }

      cleanup = () => {
        if (raf) cancelAnimationFrame(raf);
        if (ro) ro.disconnect();
        else window.removeEventListener("resize", schedule);
        for (const mo of observers) mo.disconnect();
      };
    }

    // Pretext might not be loaded yet — retry a few times after the script tag fires.
    let attempts = 0;
    const tick = () => {
      if (cancelled) return;
      if (window.Pretext) {
        enhance();
        return;
      }
      if (attempts++ < 30) {
        setTimeout(tick, 100);
      }
    };
    tick();

    return () => {
      cancelled = true;
      if (cleanup) cleanup();
    };
  }, []);

  return <Script src="/pretext.js" strategy="afterInteractive" />;
}
