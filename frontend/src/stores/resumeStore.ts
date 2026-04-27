import { create } from "zustand";

interface ResumeState {
  lastFailedMessage: string | null;
  setLastFailedMessage: (message: string) => void;
  clear: () => void;
}

export const useResumeStore = create<ResumeState>((set) => ({
  lastFailedMessage: null,
  setLastFailedMessage: (message) => set({ lastFailedMessage: message }),
  clear: () => set({ lastFailedMessage: null }),
}));
