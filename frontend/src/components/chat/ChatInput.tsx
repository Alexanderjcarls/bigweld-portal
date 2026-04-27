import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Mention from "@tiptap/extension-mention";
import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/stores/chatStore";
import { useStreamJsonChat } from "@/hooks/useStreamJsonChat";

const SKILLS = ["graph", "gaps", "orphans", "rollup", "dupes", "citations", "search-past-conversations"];

export function ChatInput() {
  const { isStreaming, attachFile, attachedFiles, clearAttachments } = useChatStore();
  const { sendTurn } = useStreamJsonChat();
  const dropRef = useRef<HTMLDivElement>(null);

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
  });

  useEffect(() => {
    const el = dropRef.current;
    if (!el) return;
    const onDrop = async (e: DragEvent) => {
      e.preventDefault();
      const files = e.dataTransfer?.files;
      if (!files) return;
      for (const f of Array.from(files)) {
        const data = await f.text();
        attachFile({ name: f.name, size: f.size, data });
      }
    };
    const onDragOver = (e: DragEvent) => e.preventDefault();
    el.addEventListener("drop", onDrop);
    el.addEventListener("dragover", onDragOver);
    return () => {
      el.removeEventListener("drop", onDrop);
      el.removeEventListener("dragover", onDragOver);
    };
  }, [attachFile]);

  const handleSend = async () => {
    if (!editor) return;
    const text = editor.getText().trim();
    if (!text || isStreaming) return;
    const attachmentSummary = attachedFiles.length
      ? "\n\n" + attachedFiles.map(f => `[attachment: ${f.name}]\n${f.data}`).join("\n\n")
      : "";
    await sendTurn(text + attachmentSummary);
    editor.commands.setContent("");
    clearAttachments();
  };

  return (
    <div ref={dropRef} className="border-t p-4 space-y-2 font-sans">
      {attachedFiles.length > 0 && (
        <div className="flex gap-2 flex-wrap text-xs">
          {attachedFiles.map((f, i) => (
            <span key={i} className="bg-muted px-2 py-1 rounded">{f.name}</span>
          ))}
        </div>
      )}
      <EditorContent
        editor={editor}
        className="min-h-[60px] max-h-[200px] overflow-y-auto rounded border p-2 prose prose-sm focus-within:ring-2 focus-within:ring-primary"
      />
      <div className="flex justify-end">
        <Button onClick={handleSend} disabled={isStreaming}>Send</Button>
      </div>
    </div>
  );
}
