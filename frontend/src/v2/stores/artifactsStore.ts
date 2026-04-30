import { create } from "zustand";

export type ArtifactType =
  | "markdown"
  | "spreadsheet"
  | "image"
  | "mermaid"
  | "d2"
  | "kroki"
  | "pdf"
  | "powerpoint";

export type ArtifactSource =
  | "bigweld"
  | "user_dropped"
  | "user_pasted"
  | "cross_conv_pulled";

export interface ArtifactFile {
  filename?: string;
  name?: string;
  mime_type?: string;
  content_type?: string;
  size?: number;
  url?: string;
  data_url?: string;
  body_base64?: string;
  content?: string;
  [key: string]: unknown;
}

export interface Artifact {
  id: string;
  conv_id: string;
  type: ArtifactType;
  title: string;
  source: ArtifactSource;
  current_version: number;
  version: number;
  body?: string | null;
  files?: ArtifactFile[] | ArtifactFile | null;
  diff_summary?: string | null;
  archived_at?: string | null;
  created_at?: string;
  updated_at?: string;
  version_created_at?: string;
}

interface ArtifactsState {
  isOpen: boolean;
  activeArtifact: Artifact | null;
  displayVersion: number;
  receiveMode: boolean;
  pickerOpen: boolean;
  lastOpenedReference: string | null;
  openArtifact: (artifact: Artifact) => void;
  updateActiveArtifact: (artifact: Artifact) => void;
  setDisplayVersion: (version: number) => void;
  revealDropZone: () => void;
  openPicker: () => void;
  closePicker: () => void;
  closeSidecar: () => void;
  setLastOpenedReference: (reference: string | null) => void;
}

export const useArtifactsStore = create<ArtifactsState>((set) => ({
  isOpen: false,
  activeArtifact: null,
  displayVersion: 1,
  receiveMode: false,
  pickerOpen: false,
  lastOpenedReference: null,
  openArtifact: (artifact) =>
    set({
      isOpen: true,
      activeArtifact: artifact,
      displayVersion: artifact.version ?? artifact.current_version ?? 1,
      receiveMode: true,
      pickerOpen: false,
    }),
  updateActiveArtifact: (artifact) =>
    set((state) => ({
      activeArtifact: artifact,
      displayVersion:
        state.activeArtifact?.id === artifact.id
          ? state.displayVersion
          : artifact.version ?? artifact.current_version ?? 1,
    })),
  setDisplayVersion: (displayVersion) => set({ displayVersion }),
  revealDropZone: () => set({ isOpen: true, receiveMode: true }),
  openPicker: () => set({ isOpen: true, receiveMode: true, pickerOpen: true }),
  closePicker: () => set({ pickerOpen: false }),
  closeSidecar: () =>
    set({
      isOpen: false,
      activeArtifact: null,
      receiveMode: false,
      pickerOpen: false,
    }),
  setLastOpenedReference: (lastOpenedReference) => set({ lastOpenedReference }),
}));

