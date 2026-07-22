"use client";

import { useEffect, useRef, useState } from "react";
import { wsUrl } from "../../lib/api";
import type { WsEvent } from "../../lib/types";

export default function WsTestPage() {
  const [status, setStatus] = useState<"idle" | "connecting" | "open" | "closed" | "error">(
    "idle"
  );
  const [events, setEvents] = useState<WsEvent[]>([]);
  const [url, setUrl] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    setUrl(wsUrl());
  }, []);

  function connect() {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    const target = url || wsUrl();
    setStatus("connecting");
    try {
      const ws = new WebSocket(target);
      wsRef.current = ws;
      ws.onopen = () => setStatus("open");
      ws.onclose = () => setStatus("closed");
      ws.onerror = () => setStatus("error");
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(String(ev.data)) as WsEvent;
          setEvents((prev) => [data, ...prev].slice(0, 50));
        } catch {
          setEvents((prev) =>
            [{ type: "raw", payload: String(ev.data) }, ...prev].slice(0, 50)
          );
        }
      };
    } catch {
      setStatus("error");
    }
  }

  function disconnect() {
    wsRef.current?.close();
    wsRef.current = null;
    setStatus("closed");
  }

  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return (
    <div className="space-y-4 sm:space-y-6">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">WebSocket live test</h1>
        <p className="text-sm text-ink-400">
          Connects to <code className="text-neon-400">/ws</code> and streams
          hello + <code>chapter_update</code> events from the scheduler.
        </p>
      </header>

      <div className="card space-y-3">
        <label className="block text-sm">
          <span className="mb-1 block text-ink-400">WS URL</span>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="input font-mono text-xs sm:text-sm"
          />
        </label>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <button type="button" className="btn-primary" onClick={connect}>
            Connect
          </button>
          <button type="button" className="btn-ghost" onClick={disconnect}>
            Disconnect
          </button>
          <span className="text-sm text-ink-300">
            Status:{" "}
            <strong
              className={
                status === "open"
                  ? "text-neon-400"
                  : status === "error"
                    ? "text-sakura-400"
                    : "text-ink-100"
              }
            >
              {status}
            </strong>
          </span>
        </div>
      </div>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold sm:text-xl">Events ({events.length})</h2>
        <div className="space-y-2">
          {events.length === 0 ? (
            <div className="card text-sm text-ink-400">No events yet.</div>
          ) : (
            events.map((ev, i) => (
              <pre
                key={i}
                className="card overflow-x-auto text-xs text-ink-200"
              >
                {JSON.stringify(ev, null, 2)}
              </pre>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
