/** Read a Response.body as line-buffered NDJSON. Yields parsed objects. */
export async function* ndjsonReader<T = unknown>(
  body: ReadableStream<Uint8Array>
): AsyncIterable<T> {
  const reader = body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      const tail = buf.trim();
      if (tail) {
        try { yield JSON.parse(tail) as T; } catch {}
      }
      return;
    }
    buf += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buf.indexOf("\n")) !== -1) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (!line) continue;
      try { yield JSON.parse(line) as T; }
      catch (err) { console.warn("ndjson: skip malformed line", err); }
    }
  }
}
