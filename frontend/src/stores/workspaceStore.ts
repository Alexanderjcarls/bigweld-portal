import { create } from "zustand";

export type ArtifactType = "mermaid" | "d2" | "kroki";

interface Artifact {
  type: ArtifactType;
  source: string;
  rendered_svg: string | null;
  error: string | null;
  diagram_subtype?: string; // for kroki: plantuml, graphviz, etc.
}

interface WorkspaceState {
  current: Artifact | null;
  setSource: (type: ArtifactType, source: string, subtype?: string) => void;
  setRenderedSvg: (svg: string) => void;
  setError: (err: string | null) => void;
  clear: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  current: null,
  setSource: (type, source, diagram_subtype) => set({
    current: { type, source, rendered_svg: null, error: null, diagram_subtype },
  }),
  setRenderedSvg: (svg) => set((s) =>
    s.current ? { current: { ...s.current, rendered_svg: svg, error: null } } : {}
  ),
  setError: (err) => set((s) =>
    s.current ? { current: { ...s.current, error: err } } : {}
  ),
  clear: () => set({ current: null }),
}));
