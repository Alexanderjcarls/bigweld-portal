import type { UIMessage } from "ai";
import type {
  Artifact,
  ArtifactFile,
  ArtifactSource,
  ArtifactType,
} from "@/v2/stores/artifactsStore";

export const DEFAULT_CHAT_API_URL = "http://localhost:8886/chat";
export const DEFAULT_V2_API_BASE_URL = "http://localhost:8886";

export function getChatApiUrl(): string {
  return import.meta.env.VITE_BIGWELD_V2_CHAT_URL ?? DEFAULT_CHAT_API_URL;
}

export function getV2ApiBaseUrl(): string {
  return import.meta.env.VITE_BIGWELD_V2_API_URL ?? DEFAULT_V2_API_BASE_URL;
}

export function getV2ApiUrl(path: string): string {
  const baseUrl = getV2ApiBaseUrl().replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}

export interface ChatRequestBody {
  id: string;
  messages: UIMessage[];
  trigger: "submit-message" | "regenerate-message";
  messageId?: string;
  conv_id: string;
  user_msg: string;
}

export function buildChatRequestBody(options: {
  chatId: string;
  conversationId: string;
  messages: UIMessage[];
  trigger: "submit-message" | "regenerate-message";
  messageId?: string;
  body?: Record<string, unknown>;
}): ChatRequestBody & Record<string, unknown> {
  return {
    ...options.body,
    id: options.chatId,
    messages: options.messages,
    trigger: options.trigger,
    messageId: options.messageId,
    conv_id: options.conversationId,
    user_msg: getLastUserText(options.messages),
  };
}

export function getLastUserText(messages: UIMessage[]): string {
  const userMessage = [...messages].reverse().find((message) => message.role === "user");
  if (!userMessage) return "";

  return userMessage.parts
    .map((part) => (part.type === "text" ? part.text : ""))
    .join("")
    .trim();
}

export interface ArtifactCreateInput {
  conv_id: string;
  type: ArtifactType;
  title: string;
  source: ArtifactSource;
  body?: string;
  files?: ArtifactFile[] | ArtifactFile;
}

export interface ArtifactPatchInput {
  section_id: string;
  new_content: string;
}

export async function listArtifacts(options: {
  convId?: string;
  global?: boolean;
}): Promise<Artifact[]> {
  const params = new URLSearchParams();
  if (options.global) {
    params.set("global", "true");
  } else if (options.convId) {
    params.set("conv_id", options.convId);
  }

  const suffix = params.size ? `?${params.toString()}` : "";
  const response = await fetch(getV2ApiUrl(`/api/artifacts${suffix}`));
  if (!response.ok) throw new Error(`listArtifacts: ${response.status}`);

  const payload = (await response.json()) as { artifacts?: Artifact[] };
  return payload.artifacts ?? [];
}

export async function getArtifact(artifactId: string): Promise<Artifact> {
  const response = await fetch(getV2ApiUrl(`/api/artifacts/${encodeURIComponent(artifactId)}`));
  if (!response.ok) throw new Error(`getArtifact: ${response.status}`);
  return response.json();
}

export async function getArtifactVersion(
  artifactId: string,
  version: number,
): Promise<Artifact> {
  const response = await fetch(
    getV2ApiUrl(`/api/artifacts/${encodeURIComponent(artifactId)}/versions/${version}`),
  );
  if (!response.ok) throw new Error(`getArtifactVersion: ${response.status}`);
  return response.json();
}

export async function createArtifact(input: ArtifactCreateInput): Promise<Artifact> {
  const response = await fetch(getV2ApiUrl("/api/artifacts"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`createArtifact: ${response.status}`);
  return response.json();
}

export async function createArtifactFromFile(options: {
  convId: string;
  file: File;
}): Promise<Artifact> {
  const formData = new FormData();
  formData.set("conv_id", options.convId);
  formData.set("type", inferArtifactType(options.file));
  formData.set("title", options.file.name);
  formData.set("source", "user_dropped");
  formData.append("file", options.file, options.file.name);

  const response = await fetch(getV2ApiUrl("/api/artifacts"), {
    method: "POST",
    body: formData,
  });
  if (!response.ok) throw new Error(`createArtifactFromFile: ${response.status}`);
  return response.json();
}

export async function patchArtifactSection(
  artifactId: string,
  input: ArtifactPatchInput,
): Promise<Artifact> {
  const response = await fetch(getV2ApiUrl(`/api/artifacts/${encodeURIComponent(artifactId)}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`patchArtifactSection: ${response.status}`);
  return response.json();
}

export async function deleteArtifact(artifactId: string): Promise<void> {
  const response = await fetch(getV2ApiUrl(`/api/artifacts/${encodeURIComponent(artifactId)}`), {
    method: "DELETE",
  });
  if (!response.ok) throw new Error(`deleteArtifact: ${response.status}`);
}

export async function resolveArtifactReference(reference: string): Promise<Artifact | null> {
  try {
    return await getArtifact(reference);
  } catch {
    const artifacts = await listArtifacts({ global: true });
    const wanted = slugifyArtifactReference(reference);
    return (
      artifacts.find(
        (artifact) =>
          artifact.id === reference ||
          slugifyArtifactReference(artifact.title) === wanted ||
          slugifyArtifactReference(`${artifact.title}-${artifact.id}`) === wanted,
      ) ?? null
    );
  }
}

export function inferArtifactType(file: File): ArtifactType {
  const name = file.name.toLowerCase();
  if (file.type.startsWith("image/")) return "image";
  if (file.type === "text/csv" || name.endsWith(".csv") || name.endsWith(".tsv")) {
    return "spreadsheet";
  }
  if (name.endsWith(".mmd") || name.endsWith(".mermaid")) return "mermaid";
  if (name.endsWith(".d2")) return "d2";
  return "markdown";
}

export function slugifyArtifactReference(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  started_at: string;
  last_active_at: string;
  artifact_count: number;
  archived?: boolean;
}

export interface ConversationMessageRecord {
  id?: string | number;
  turn_idx?: number;
  role: string;
  content?: string | null;
  raw_message?: unknown;
}

export interface ConversationDetail {
  conversation?: ConversationSummary;
  messages: ConversationMessageRecord[];
  active_compacted_summaries?: unknown[];
}

export interface ContextStats {
  tokensUsed: number;
  tokenLimit: number;
  percentUsed: number;
}

export interface CompactPreview {
  proposed_summary: string;
  diff_preview: string;
}

export interface CompactConfirmResponse {
  ok: boolean;
  summary_id?: string | number;
}

export async function listV2Conversations(options: {
  archived?: boolean;
} = {}): Promise<ConversationSummary[]> {
  const params = new URLSearchParams();
  if (options.archived) params.set("archived", "true");

  const suffix = params.size ? `?${params.toString()}` : "";
  const response = await fetch(getV2ApiUrl(`/api/conversations${suffix}`));
  if (!response.ok) throw new Error(`listV2Conversations: ${response.status}`);

  const body = await response.json();
  const conversations = Array.isArray(body) ? body : body.conversations;
  return (Array.isArray(conversations) ? conversations : []).map(normalizeConversationSummary);
}

export async function getV2Conversation(conversationId: string): Promise<ConversationDetail> {
  const response = await fetch(
    getV2ApiUrl(`/api/conversations/${encodeURIComponent(conversationId)}`),
  );
  if (!response.ok) throw new Error(`getV2Conversation: ${response.status}`);

  const body = await response.json();
  return {
    conversation: body.conversation
      ? normalizeConversationSummary(body.conversation)
      : undefined,
    messages: Array.isArray(body.messages) ? body.messages : [],
    active_compacted_summaries: body.active_compacted_summaries,
  };
}

export async function patchV2Conversation(
  conversationId: string,
  patch: { title?: string; archived?: boolean },
): Promise<ConversationSummary> {
  const response = await fetch(
    getV2ApiUrl(`/api/conversations/${encodeURIComponent(conversationId)}`),
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    },
  );
  if (!response.ok) throw new Error(`patchV2Conversation: ${response.status}`);

  return normalizeConversationSummary(await response.json());
}

export async function getContextStats(conversationId: string): Promise<ContextStats> {
  const params = new URLSearchParams({ conv_id: conversationId });
  const response = await fetch(getV2ApiUrl(`/api/context-stats?${params.toString()}`));
  if (!response.ok) throw new Error(`getContextStats: ${response.status}`);

  return normalizeContextStats(await response.json());
}

export async function proposeCompact(options: {
  conversationId: string;
  rangeStartIdx: number;
  rangeEndIdx: number;
}): Promise<CompactPreview> {
  const response = await fetch(getV2ApiUrl("/api/compact"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conv_id: options.conversationId,
      range_start_idx: options.rangeStartIdx,
      range_end_idx: options.rangeEndIdx,
    }),
  });
  if (!response.ok) throw new Error(`proposeCompact: ${response.status}`);

  return response.json();
}

export async function confirmCompact(options: {
  conversationId: string;
  rangeStartIdx: number;
  rangeEndIdx: number;
  summary: string;
}): Promise<CompactConfirmResponse> {
  const response = await fetch(getV2ApiUrl("/api/compact/confirm"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conv_id: options.conversationId,
      range_start_idx: options.rangeStartIdx,
      range_end_idx: options.rangeEndIdx,
      summary: options.summary,
    }),
  });
  if (!response.ok) throw new Error(`confirmCompact: ${response.status}`);

  return response.json();
}

function normalizeConversationSummary(value: Partial<ConversationSummary>): ConversationSummary {
  return {
    id: String(value.id ?? ""),
    title: value.title ?? null,
    started_at: value.started_at ?? new Date(0).toISOString(),
    last_active_at: value.last_active_at ?? value.started_at ?? new Date(0).toISOString(),
    artifact_count: Number(value.artifact_count ?? 0),
    archived: Boolean(value.archived),
  };
}

function normalizeContextStats(value: Record<string, unknown>): ContextStats {
  const tokenLimit = Number(
    value.context_window_total ?? value.token_limit ?? value.limit ?? 50_000,
  );
  const tokensUsed = Number(
    value.tokens_used ?? value.context_tokens_used ?? value.context_window_used ?? 0,
  );
  const rawPercent =
    value.percent_used ?? value.context_window_pct ?? value.context_window_percent;
  const percentUsed =
    rawPercent === undefined ? (tokensUsed / tokenLimit) * 100 : Number(rawPercent);

  return {
    tokensUsed: Number.isFinite(tokensUsed) ? tokensUsed : 0,
    tokenLimit: Number.isFinite(tokenLimit) && tokenLimit > 0 ? tokenLimit : 50_000,
    percentUsed: Number.isFinite(percentUsed) ? percentUsed : 0,
  };
}
