import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import {
  createArtifact,
  createArtifactFromFile,
  deleteArtifact,
  getArtifact,
  getArtifactVersion,
  listArtifacts,
  patchArtifactSection,
  resolveArtifactReference,
  type ArtifactCreateInput,
  type ArtifactPatchInput,
} from "@/v2/lib/api";
import { type Artifact, useArtifactsStore } from "@/v2/stores/artifactsStore";

const artifactKeys = {
  all: ["artifacts"] as const,
  lists: () => [...artifactKeys.all, "list"] as const,
  list: (scope: string) => [...artifactKeys.lists(), scope] as const,
  detail: (artifactId: string) => [...artifactKeys.all, "detail", artifactId] as const,
  version: (artifactId: string, version: number) =>
    [...artifactKeys.detail(artifactId), "version", version] as const,
};

export function useArtifacts(conversationId: string | null | undefined) {
  return useQuery({
    queryKey: artifactKeys.list(`conv:${conversationId ?? "none"}`),
    queryFn: () => listArtifacts({ convId: conversationId ?? undefined }),
    enabled: Boolean(conversationId),
  });
}

export function useGlobalArtifacts() {
  return useQuery({
    queryKey: artifactKeys.list("global"),
    queryFn: () => listArtifacts({ global: true }),
  });
}

export function useArtifact(artifactId: string | null | undefined) {
  return useQuery({
    queryKey: artifactKeys.detail(artifactId ?? "none"),
    queryFn: () => getArtifact(artifactId ?? ""),
    enabled: Boolean(artifactId),
  });
}

export function useArtifactVersion(
  artifactId: string | null | undefined,
  version: number | null | undefined,
) {
  return useQuery({
    queryKey: artifactKeys.version(artifactId ?? "none", version ?? 0),
    queryFn: () => getArtifactVersion(artifactId ?? "", version ?? 1),
    enabled: Boolean(artifactId && version),
  });
}

export function useCreateArtifact() {
  const queryClient = useQueryClient();
  const openArtifact = useArtifactsStore((state) => state.openArtifact);

  return useMutation({
    mutationFn: (input: ArtifactCreateInput) => createArtifact(input),
    onSuccess: (artifact) => {
      openArtifact(artifact);
      void queryClient.invalidateQueries({ queryKey: artifactKeys.lists() });
    },
  });
}

export function useCreateDroppedArtifact(conversationId: string) {
  const queryClient = useQueryClient();
  const openArtifact = useArtifactsStore((state) => state.openArtifact);

  return useMutation({
    mutationFn: (file: File) => createArtifactFromFile({ convId: conversationId, file }),
    onSuccess: (artifact) => {
      openArtifact(artifact);
      void queryClient.invalidateQueries({ queryKey: artifactKeys.lists() });
    },
  });
}

export function usePatchArtifact(artifactId: string | null | undefined) {
  const queryClient = useQueryClient();
  const openArtifact = useArtifactsStore((state) => state.openArtifact);

  return useMutation({
    mutationFn: (input: ArtifactPatchInput) => patchArtifactSection(artifactId ?? "", input),
    onSuccess: (artifact) => {
      openArtifact(artifact);
      void queryClient.invalidateQueries({ queryKey: artifactKeys.all });
    },
  });
}

export function useDeleteArtifact() {
  const queryClient = useQueryClient();
  const closeSidecar = useArtifactsStore((state) => state.closeSidecar);

  return useMutation({
    mutationFn: (artifactId: string) => deleteArtifact(artifactId),
    onSuccess: () => {
      closeSidecar();
      void queryClient.invalidateQueries({ queryKey: artifactKeys.lists() });
    },
  });
}

export function usePullArtifact(conversationId: string) {
  const createMutation = useCreateArtifact();

  return useMutation({
    mutationFn: (artifact: Artifact) =>
      createMutation.mutateAsync({
        conv_id: conversationId,
        type: artifact.type,
        title: artifact.title,
        source: "cross_conv_pulled",
        ...(artifact.body
          ? { body: artifact.body }
          : artifact.files
            ? { files: artifact.files }
            : { body: "Pulled artifact content unavailable." }),
      }),
  });
}

export function useOpenArtifactReference() {
  const openArtifact = useArtifactsStore((state) => state.openArtifact);
  const setLastOpenedReference = useArtifactsStore((state) => state.setLastOpenedReference);

  return useCallback(
    async (reference: string) => {
      const artifact = await resolveArtifactReference(reference);
      if (!artifact) return;
      setLastOpenedReference(reference);
      openArtifact(artifact);
    },
    [openArtifact, setLastOpenedReference],
  );
}

