import { GripVerticalIcon } from "lucide-react"
import * as React from "react"
import * as ResizablePrimitive from "react-resizable-panels"

import { cn } from "@/lib/utils"

type ResizablePanelGroupProps = Omit<
  ResizablePrimitive.GroupProps,
  "orientation"
> & {
  autoSaveId?: string
  direction?: ResizablePrimitive.Orientation
}

function ResizablePanelGroup({
  autoSaveId,
  ...props
}: ResizablePanelGroupProps) {
  if (autoSaveId) {
    return <ResizablePanelGroupWithStorage autoSaveId={autoSaveId} {...props} />
  }

  return <ResizablePanelGroupRoot {...props} />
}

function ResizablePanelGroupWithStorage({
  autoSaveId,
  defaultLayout,
  id,
  onLayoutChange,
  onLayoutChanged,
  ...props
}: ResizablePanelGroupProps & { autoSaveId: string }) {
  const persistedLayout = ResizablePrimitive.useDefaultLayout({
    id: autoSaveId,
  })

  const handleLayoutChange = React.useCallback<
    NonNullable<ResizablePrimitive.GroupProps["onLayoutChange"]>
  >(
    (layout) => {
      persistedLayout.onLayoutChange(layout)
      onLayoutChange?.(layout)
    },
    [onLayoutChange, persistedLayout]
  )

  const handleLayoutChanged = React.useCallback<
    NonNullable<ResizablePrimitive.GroupProps["onLayoutChanged"]>
  >(
    (layout) => {
      persistedLayout.onLayoutChanged(layout)
      onLayoutChanged?.(layout)
    },
    [onLayoutChanged, persistedLayout]
  )

  return (
    <ResizablePanelGroupRoot
      id={id ?? autoSaveId}
      defaultLayout={defaultLayout ?? persistedLayout.defaultLayout}
      onLayoutChange={handleLayoutChange}
      onLayoutChanged={handleLayoutChanged}
      {...props}
    />
  )
}

function ResizablePanelGroupRoot({
  className,
  direction = "horizontal",
  ...props
}: Omit<ResizablePanelGroupProps, "autoSaveId">) {
  return (
    <ResizablePrimitive.Group
      data-slot="resizable-panel-group"
      orientation={direction}
      className={cn(
        "flex h-full w-full aria-[orientation=vertical]:flex-col",
        className
      )}
      {...props}
    />
  )
}

function ResizablePanel({ ...props }: ResizablePrimitive.PanelProps) {
  return <ResizablePrimitive.Panel data-slot="resizable-panel" {...props} />
}

function ResizableHandle({
  withHandle,
  className,
  ...props
}: ResizablePrimitive.SeparatorProps & {
  withHandle?: boolean
}) {
  return (
    <ResizablePrimitive.Separator
      data-slot="resizable-handle"
      className={cn(
        "relative flex w-px items-center justify-center bg-border after:absolute after:inset-y-0 after:left-1/2 after:w-1 after:-translate-x-1/2 focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:outline-hidden aria-[orientation=horizontal]:h-px aria-[orientation=horizontal]:w-full aria-[orientation=horizontal]:after:left-0 aria-[orientation=horizontal]:after:h-1 aria-[orientation=horizontal]:after:w-full aria-[orientation=horizontal]:after:translate-x-0 aria-[orientation=horizontal]:after:-translate-y-1/2 [&[aria-orientation=horizontal]>div]:rotate-90",
        className
      )}
      {...props}
    >
      {withHandle && (
        <div className="z-10 flex h-4 w-3 items-center justify-center rounded-xs border bg-border">
          <GripVerticalIcon className="size-2.5" />
        </div>
      )}
    </ResizablePrimitive.Separator>
  )
}

export { ResizableHandle, ResizablePanel, ResizablePanelGroup }
