import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Mention from "@tiptap/extension-mention";
import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/stores/chatStore";
import { useStreamJsonChat } from "@/hooks/useStreamJsonChat";
import { createConversation, uploadFile } from "@/lib/api";
import { classifyFile } from "@/lib/fileKind";

const SKILLS = ["graph", "gaps", "orphans", "rollup", "dupes", "citations", "search-past-conversations"];

export function ChatInput() {
  const {
    conversationId,
    setConversationId,
    isStreaming,
    attachFile,
    attachedFiles,
    clearAttachments,
  } = useChatStore();
  const { sendTurn } = useStreamJsonChat();
  const dropRef = useRef<HTMLDivElement>(null);
  const handleSendRef = useRef<() => void>(() => {});

  const editor = useEditor({
    extensions: [
      StarterKit,
      Mention.configure({
        HTMLAttributes: { class: "text-primary font-semibold" },
        suggestion: {
          char: "/",
          items: ({ query }) =>
            SKILLS.filter(s => s.toLowerCase().startsWith(query.toLowerCase())).slice(0, 7),
        },
      }),
    ],
    content: "",
    editorProps: {
      handleKeyDown: (_view, event) => {
        if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
          event.preventDefault();
          handleSendRef.current();
          return true;
        }
        return false;
      },
    },
  });

  useEffect(() => {
    const el = dropRef.current;
    if (!el) return;
    const onDrop = async (e: DragEvent) => {
      e.preventDefault();
      const files = e.dataTransfer?.files;
      if (!files) return;
      let convIdForDrop = conversationId;
      const ensureConversationId = async () => {
        if (convIdForDrop) return convIdForDrop;
        const created = await createConversation();
        convIdForDrop = created.conv_id;
        setConversationId(convIdForDrop);
        return convIdForDrop;
      };
      for (const f of Array.from(files)) {
        if (classifyFile(f) === "text") {
          const data = await f.text();
          attachFile({ kind: "text", name: f.name, size: f.size, data });
          continue;
        }

        try {
          const convId = await ensureConversationId();
          const name = sanitizeAttachmentFilename(f.name);
          const uploaded = await uploadFile(convId, name, f);
          attachFile({ kind: "binary", name: f.name, size: f.size, path: uploaded.path });
        } catch (err) {
          console.error("attachment upload failed", err);
          window.alert(`Could not attach ${f.name}`);
        }
      }
    };
    const onDragOver = (e: DragEvent) => e.preventDefault();
    el.addEventListener("drop", onDrop);
    el.addEventListener("dragover", onDragOver);
    return () => {
      el.removeEventListener("drop", onDrop);
      el.removeEventListener("dragover", onDragOver);
    };
  }, [attachFile, conversationId, setConversationId]);

  const handleSend = async () => {
    if (!editor) return;
    const text = editor.getText().trim();
    if (!text || isStreaming) return;
    const attachmentSummary = attachedFiles.length
      ? "\n\n" + attachedFiles.map(f => {
        if (f.kind === "text") return `[attachment: ${f.name}]\n${f.data}`;
        return `[attached file: ${f.path}]`;
      }).join("\n\n")
      : "";
    editor.commands.setContent("");
    clearAttachments();
    await sendTurn(text + attachmentSummary);
  };
  handleSendRef.current = handleSend;

  return (
    <div ref={dropRef} className="border-t p-4 space-y-2 font-sans">
      {attachedFiles.length > 0 && (
        <div className="flex gap-2 flex-wrap text-xs">
          {attachedFiles.map((f, i) => (
            f.kind === "binary"
              ? <span key={i} className="bg-primary/20 px-2 py-1 rounded">📎 {f.name}</span>
              : <span key={i} className="bg-muted px-2 py-1 rounded">{f.name}</span>
          ))}
        </div>
      )}
      <EditorContent
        editor={editor}
        className="min-h-[60px] max-h-[200px] w-full max-w-none overflow-y-auto rounded border p-2 prose prose-sm focus-within:ring-2 focus-within:ring-primary"
      />
      <div className="flex justify-end">
        <Button onClick={handleSend} disabled={isStreaming}>Send</Button>
      </div>
    </div>
  );
}

function sanitizeAttachmentFilename(name: string): string {
  return name.replace(/[\/\\\s]+/g, "_").replace(/^\.+/, "") || "attachment";
}
