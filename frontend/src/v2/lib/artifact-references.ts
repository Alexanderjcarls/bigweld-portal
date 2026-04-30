export function extractArtifactReferences(text: string): string[] {
  return [...text.matchAll(artifactReferencePattern())].map((match) => match[1]);
}

export type ArtifactTextSegment =
  | { type: "text"; value: string }
  | { type: "artifact"; value: string };

export function splitArtifactReferences(text: string): ArtifactTextSegment[] {
  const segments: ArtifactTextSegment[] = [];
  let cursor = 0;

  for (const match of text.matchAll(artifactReferencePattern())) {
    if (match.index === undefined) continue;
    if (match.index > cursor) {
      segments.push({ type: "text", value: text.slice(cursor, match.index) });
    }
    segments.push({ type: "artifact", value: match[1] });
    cursor = match.index + match[0].length;
  }

  if (cursor < text.length) {
    segments.push({ type: "text", value: text.slice(cursor) });
  }

  return segments.length > 0 ? segments : [{ type: "text", value: text }];
}

function artifactReferencePattern(): RegExp {
  return /@artifact:([A-Za-z0-9][A-Za-z0-9_.:-]*)/g;
}

