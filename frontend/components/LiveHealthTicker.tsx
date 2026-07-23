"use client";

import { useEffect, useState, useRef } from "react";

interface HealthEvent {
  type: "source_health";
  name: string;
  status: string;
  ok?: number;
  fail?: number;
  kind?: string;
  event?: string;
  prev_status?: string;
}

export function LiveHealthTicker() {
  const [events, setEvents] = useState<HealthEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const apiBase = (process.env.NEXT_PUBLIC_API_BASE || "https://mynakama.web.id")
        .replace(/^https?:\/\//, "");
      const url = `${proto}//${apiBase}/ws?token=`;
      // Use the configured API key from localStorage or skip (will be unauthorized)
      const apiKey = typeof window !== "undefined" ? localStorage.getItem("nakama_api_key") : null;
      const fullUrl = apiKey ? `${url}${apiKey}` : url;

      try {
        const ws = new WebSocket(fullUrl);
        wsRef.current = ws;

        ws.onopen = () => setConnected(true);
        ws.onclose = () => {
          setConnected(false);
          reconnectTimer = setTimeout(connect, 5000);
        };
        ws.onerror = () => ws.close();
        ws.onmessage = (msg) => {
          try {
            const data = JSON.parse(msg.data);
            if (data.type === "source_health") {
              setEvents((prev) => [data as HealthEvent, ...prev].slice(0, 8));
            }
          } catch {
            /* ignore */
          }
        };
      } catch {
        reconnectTimer = setTimeout(connect, 5000);
      }
    }

    connect();
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  if (events.length === 0) return null;

  return (
    <div className="card space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold sm:text-sm">Live Source Health</h3>
        <span className="flex items-center gap-1 text-[10px] text-ink-400 sm:text-xs">
          <span
            className={`inline-block h-1.5 w-1.5 rounded-full ${
              connected ? "bg-emerald-400" : "bg-ink-600"
            }`}
          />
          {connected ? "WS connected" : "WS disconnected"}
        </span>
      </div>
      <div className="space-y-1">
        {events.map((e, i) => {
          const color =
            e.status === "healthy"
              ? "text-emerald-400"
              : e.status === "degraded"
                ? "text-amber-400"
                : "text-sakura-400";
          const arrow = e.event === "changed" && e.prev_status ? " → " : "";
          return (
            <div
              key={`${e.name}-${i}`}
              className="flex items-center gap-2 text-[10px] sm:text-xs"
            >
              <span className={`font-mono ${color}`}>{e.status}</span>
              <span className="text-ink-200">{e.name}</span>
              {arrow && <span className="text-ink-500">{arrow}</span>}
              {e.prev_status && (
                <span className="text-ink-500">({e.prev_status})</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
