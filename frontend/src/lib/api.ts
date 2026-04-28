export async function createConversation(): Promise<{ conv_id: string }> {
  const r = await fetch("/api/conversations", { method: "POST" });
  if (!r.ok) throw new Error(`createConversation: ${r.status}`);
  return r.json();
}

export async function listConversations() {
  const r = await fetch("/api/conversations");
  if (!r.ok) throw new Error(`listConversations: ${r.status}`);
  return r.json();
}

export async function getConversation(id: string) {
  const r = await fetch(`/api/conversations/${id}`);
  if (!r.ok) throw new Error(`getConversation: ${r.status}`);
  return r.json();
}

export async function takeTurnStream(
  convId: string,
  message: string,
): Promise<Response> {
  const r = await fetch(`/api/conversations/${convId}/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!r.ok) throw new Error(`takeTurn: ${r.status}`);
  if (!r.body) throw new Error("takeTurn: no body");
  return r;
}

export async function uploadFile(
  convId: string,
  filename: string,
  blob: Blob,
): Promise<{ path: string }> {
  const r = await fetch(
    `/api/upload/${encodeURIComponent(convId)}/${encodeURIComponent(filename)}`,
    {
      method: "PUT",
      body: blob,
    },
  );
  if (!r.ok) throw new Error(`upload: ${r.status}`);
  return r.json();
}

export async function getBudget(
  convId?: string | null,
): Promise<{ context_window_pct: number; context_window_total: number }> {
  const url = convId ? `/api/budget?conv_id=${encodeURIComponent(convId)}` : "/api/budget";
  const r = await fetch(url);
  if (!r.ok) throw new Error(`budget: ${r.status}`);
  return r.json();
}
