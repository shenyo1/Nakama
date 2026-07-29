"use client";

import { useEffect, useState } from "react";

interface ReadingListItem {
  id: number;
  source: string;
  slug: string;
  kind: string;
  added_at: string;
}

interface ReadingList {
  id: number;
  user_id: number;
  username: string;
  name: string;
  is_public: boolean;
  created_at: string;
  items: ReadingListItem[];
}

export function ReadingListManager() {
  const [lists, setLists] = useState<ReadingList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newListName, setNewListName] = useState("");
  const [creating, setCreating] = useState(false);
  const [addingToListId, setAddingToListId] = useState<number | null>(null);
  const [addSource, setAddSource] = useState("");
  const [addSlug, setAddSlug] = useState("");
  const [addKind, setAddKind] = useState<"anime" | "comic" | "novel">("comic");
  const [editingListId, setEditingListId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editPublic, setEditPublic] = useState(false);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const token = typeof window !== "undefined" ? localStorage.getItem("nakama_token") : null;

  async function loadLists() {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/lists`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setLists(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLists();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newListName.trim()) return;

    setCreating(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/lists`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: newListName.trim(), is_public: false }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Error ${res.status}`);
      }
      setNewListName("");
      loadLists();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(listId: number) {
    if (!confirm("Delete this list?")) return;
    try {
      const res = await fetch(`${apiBase}/lists/${listId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      loadLists();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleAddItem(listId: number) {
    if (!addSource.trim() || !addSlug.trim()) return;

    setError(null);
    try {
      const res = await fetch(`${apiBase}/lists/${listId}/items`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          source: addSource.trim(),
          slug: addSlug.trim(),
          kind: addKind,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Error ${res.status}`);
      }
      setAddSource("");
      setAddSlug("");
      setAddingToListId(null);
      loadLists();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleRemoveItem(listId: number, itemId: number) {
    try {
      const res = await fetch(`${apiBase}/lists/${listId}/items/${itemId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      loadLists();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleUpdate(listId: number) {
    if (!editName.trim()) return;
    try {
      const res = await fetch(`${apiBase}/lists/${listId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: editName.trim(), is_public: editPublic }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Error ${res.status}`);
      }
      setEditingListId(null);
      loadLists();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function startEdit(list: ReadingList) {
    setEditingListId(list.id);
    setEditName(list.name);
    setEditPublic(list.is_public);
  }

  if (!token) {
    return (
      <div className="card text-sm text-ink-400">
        <a href="/login" className="text-sakura-400 hover:underline">
          Log in
        </a>{" "}
        to manage reading lists.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-4 w-24 bg-ink-800 rounded" />
        <div className="h-10 w-full bg-ink-800 rounded" />
        <div className="h-10 w-full bg-ink-800 rounded" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">My Reading Lists ({lists.length})</h3>

      {error && <p className="text-xs text-rose-400">{error}</p>}

      {/* Create new list */}
      <form onSubmit={handleCreate} className="card flex gap-2">
        <input
          type="text"
          value={newListName}
          onChange={(e) => setNewListName(e.target.value)}
          placeholder="New list name..."
          maxLength={128}
          className="flex-1 rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-500 focus:border-sakura-500 focus:outline-none focus:ring-1 focus:ring-sakura-500"
        />
        <button
          type="submit"
          disabled={creating || !newListName.trim()}
          className="rounded-md bg-sakura-600 px-4 py-2 text-sm font-medium text-white hover:bg-sakura-500 disabled:opacity-50 transition-colors shrink-0"
        >
          {creating ? "..." : "Create"}
        </button>
      </form>

      {/* Lists */}
      {lists.length === 0 ? (
        <p className="text-sm text-ink-400">No reading lists yet. Create one above!</p>
      ) : (
        <div className="space-y-3">
          {lists.map((list) => (
            <div key={list.id} className="card">
              {editingListId === list.id ? (
                /* Edit mode */
                <div className="space-y-2">
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-1.5 text-sm text-ink-100 focus:border-sakura-500 focus:outline-none focus:ring-1 focus:ring-sakura-500"
                  />
                  <label className="flex items-center gap-2 text-xs text-ink-400">
                    <input
                      type="checkbox"
                      checked={editPublic}
                      onChange={(e) => setEditPublic(e.target.checked)}
                      className="rounded border-ink-600 bg-ink-900"
                    />
                    Public
                  </label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleUpdate(list.id)}
                      className="rounded-md bg-sakura-600 px-3 py-1 text-xs font-medium text-white hover:bg-sakura-500"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingListId(null)}
                      className="rounded-md bg-ink-700 px-3 py-1 text-xs font-medium text-ink-100 hover:bg-ink-600"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                /* View mode */
                <>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-medium">{list.name}</h4>
                      {list.is_public && (
                        <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] text-emerald-300">
                          Public
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => startEdit(list)}
                        className="rounded px-2 py-1 text-xs text-ink-400 hover:bg-ink-800 hover:text-ink-200"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(list.id)}
                        className="rounded px-2 py-1 text-xs text-rose-400 hover:bg-ink-800"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  {/* Items */}
                  {list.items.length > 0 && (
                    <div className="mb-2 space-y-1">
                      {list.items.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between rounded bg-ink-900/50 px-2 py-1 text-xs"
                        >
                          <span>
                            <span className="text-ink-300">{item.kind}</span>{" "}
                            <span className="text-ink-500">→</span>{" "}
                            <span className="text-ink-200">{item.source}/{item.slug}</span>
                          </span>
                          <button
                            onClick={() => handleRemoveItem(list.id, item.id)}
                            className="text-rose-400 hover:text-rose-300"
                            title="Remove"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Add item */}
                  {addingToListId === list.id ? (
                    <div className="space-y-1.5 mt-2 pt-2 border-t border-ink-800">
                      <div className="flex gap-1">
                        <input
                          type="text"
                          value={addSource}
                          onChange={(e) => setAddSource(e.target.value)}
                          placeholder="Source (e.g. komiku)"
                          className="flex-1 rounded border border-ink-700 bg-ink-900 px-2 py-1 text-xs text-ink-100 placeholder:text-ink-500 focus:border-sakura-500 focus:outline-none"
                        />
                        <input
                          type="text"
                          value={addSlug}
                          onChange={(e) => setAddSlug(e.target.value)}
                          placeholder="Slug"
                          className="flex-1 rounded border border-ink-700 bg-ink-900 px-2 py-1 text-xs text-ink-100 placeholder:text-ink-500 focus:border-sakura-500 focus:outline-none"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <select
                          value={addKind}
                          onChange={(e) => setAddKind(e.target.value as "anime" | "comic" | "novel")}
                          className="rounded border border-ink-700 bg-ink-900 px-2 py-1 text-xs text-ink-100"
                        >
                          <option value="anime">Anime</option>
                          <option value="comic">Comic</option>
                          <option value="novel">Novel</option>
                        </select>
                        <button
                          onClick={() => handleAddItem(list.id)}
                          className="rounded bg-sakura-600 px-2 py-1 text-xs text-white hover:bg-sakura-500"
                        >
                          Add
                        </button>
                        <button
                          onClick={() => setAddingToListId(null)}
                          className="rounded bg-ink-700 px-2 py-1 text-xs text-ink-300 hover:bg-ink-600"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setAddingToListId(list.id)}
                      className="text-xs text-sakura-400 hover:underline"
                    >
                      + Add item
                    </button>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
