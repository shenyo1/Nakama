"use client";

/**
 * usePinchZoom — zero-dependency pinch-zoom + pan + double-tap for the reader.
 *
 * Pattern ported from Sanka's `usePinchZoom.ts` (Lovable) and simplified for
 * Nakama's image pages. Gives any element:
 *   - two-finger pinch to zoom
 *   - one-finger pan while zoomed
 *   - double-tap to toggle 1x <-> 2.5x
 *   - programmatic zoomIn / zoomOut / reset (for on-screen buttons)
 *
 * Returns the style transform + bind handlers to spread on a wrapper div.
 */
import { useCallback, useRef, useState } from "react";

export function usePinchZoom(minScale = 1, maxScale = 4, doubleTapScale = 2.5) {
  const [scale, setScale] = useState(1);
  const stateRef = useRef({
    scale: 1,
    translateX: 0,
    translateY: 0,
    startX: 0,
    startY: 0,
    startDist: 0,
    startScale: 1,
    panning: false,
    lastTap: 0,
  });

  const apply = useCallback((next: Partial<typeof stateRef.current>) => {
    const s = stateRef.current;
    Object.assign(s, next);
    // Clamp scale
    if (s.scale < minScale) s.scale = minScale;
    if (s.scale > maxScale) s.scale = maxScale;
    // When not zoomed, recenter pan
    if (s.scale <= minScale) {
      s.translateX = 0;
      s.translateY = 0;
    }
    setScale(s.scale);
  }, [minScale, maxScale]);

  const onPointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    const t = stateRef.current;
    // Single primary pointer starting a pan/zoom
    if (e.pointerType === "touch" && (e as any).touches?.length === 2) {
      return; // handled by touchstart two-finger path
    }
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    t.startX = e.clientX - t.translateX;
    t.startY = e.clientY - t.translateY;
    t.panning = true;
  }, []);

  const onPointerMove = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    const t = stateRef.current;
    if (!t.panning || t.scale <= minScale) return;
    t.translateX = e.clientX - t.startX;
    t.translateY = e.clientY - t.startY;
    setScale(t.scale);
    const el = e.currentTarget as HTMLElement;
    el.style.transform = `translate3d(${t.translateX}px, ${t.translateY}px, 0) scale(${t.scale})`;
  }, [minScale]);

  const onPointerUp = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    const t = stateRef.current;
    t.panning = false;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {}
  }, []);

  // Touch two-finger pinch (mobile)
  const onTouchStart = useCallback((e: React.TouchEvent<HTMLDivElement>) => {
    const t = stateRef.current;
    if (e.touches.length === 2) {
      const [a, b] = [e.touches[0], e.touches[1]];
      t.startDist = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      t.startScale = t.scale;
    }
  }, []);

  const onTouchMove = useCallback((e: React.TouchEvent<HTMLDivElement>) => {
    const t = stateRef.current;
    if (e.touches.length === 2) {
      const [a, b] = [e.touches[0], e.touches[1]];
      const dist = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      if (t.startDist > 0) {
        apply({ scale: t.startScale * (dist / t.startDist) });
      }
    }
  }, [apply]);

  const onDoubleTap = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const t = stateRef.current;
    const now = Date.now();
    if (now - t.lastTap < 300) {
      // double tap -> toggle zoom
      if (t.scale > minScale + 0.1) apply({ scale: minScale });
      else apply({ scale: doubleTapScale });
      t.lastTap = 0;
    } else {
      t.lastTap = now;
    }
  }, [apply, minScale, doubleTapScale]);

  const zoomIn = useCallback(() => apply({ scale: stateRef.current.scale * 1.4 }), [apply]);
  const zoomOut = useCallback(() => apply({ scale: stateRef.current.scale / 1.4 }), [apply]);
  const reset = useCallback(() => apply({ scale: minScale, translateX: 0, translateY: 0 }), [apply, minScale]);

  return {
    scale,
    zoomIn,
    zoomOut,
    reset,
    bind: {
      onPointerDown,
      onPointerMove,
      onPointerUp,
      onTouchStart,
      onTouchMove,
      onDoubleClick: onDoubleTap,
      style: {
        transform: `translate3d(${stateRef.current.translateX}px, ${stateRef.current.translateY}px, 0) scale(${scale})`,
        transformOrigin: "center center",
        touchAction: "pan-x pan-y",
        transition: scale === 1 ? "transform 0.2s ease" : "none",
        willChange: "transform",
      } as React.CSSProperties,
      className: scale > minScale ? "cursor-grab active:cursor-grabbing" : "",
    },
  };
}
