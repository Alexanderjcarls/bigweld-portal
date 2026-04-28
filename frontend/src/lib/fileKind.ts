const TEXT_MIME_PREFIXES = ["text/"];
const TEXT_MIME_EXACT = new Set([
  "application/json",
  "application/xml",
  "application/yaml",
  "application/x-yaml",
  "application/x-sh",
  "application/x-python",
  "application/javascript",
  "application/typescript",
]);
const TEXT_EXTENSIONS = new Set([
  "md", "txt", "json", "csv", "tsv", "py", "ts", "tsx", "js", "jsx",
  "yaml", "yml", "toml", "ini", "cfg", "conf", "sh", "bash", "log",
  "html", "htm", "xml", "css", "rs", "go", "java", "c", "cpp", "h",
  "hpp", "rb", "php", "sql", "graphql", "proto",
]);

export type FileKind = "text" | "binary";

export function classifyFile(file: File): FileKind {
  const mime = file.type.toLowerCase();
  if (mime) {
    for (const prefix of TEXT_MIME_PREFIXES) {
      if (mime.startsWith(prefix)) return "text";
    }
    if (TEXT_MIME_EXACT.has(mime)) return "text";
    return "binary";
  }

  const ext = file.name.toLowerCase().split(".").pop() ?? "";
  if (TEXT_EXTENSIONS.has(ext)) return "text";
  return "binary";
}
