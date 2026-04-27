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
        "relative flex w-2 shrink-0 items-center justify-center bg-border transition-colors after:absolute after:inset-y-0 after:left-1/2 after:w-2 after:-translate-x-1/2 focus-visible:ring-1 focus-visible:ring-primary focus-visible:ring-offset-1 focus-visible:outline-hidden data-[panel-group-direction=horizontal]:w-2 data-[panel-group-direction=horizontal]:hover:bg-primary/40 data-[resize-handle-state=drag]:bg-primary/60 data-[separator=active]:bg-primary/60 data-[panel-group-direction=vertical]:h-px data-[panel-group-direction=vertical]:w-full data-[panel-group-direction=vertical]:after:left-0 data-[panel-group-direction=vertical]:after:h-1 data-[panel-group-direction=vertical]:after:w-full data-[panel-group-direction=vertical]:after:translate-x-0 data-[panel-group-direction=vertical]:after:-translate-y-1/2 data-[panel-group-direction=vertical]:[&>div]:rotate-90 aria-[disabled=true]:pointer-events-none aria-[disabled=true]:!cursor-default aria-[orientation=vertical]:cursor-col-resize aria-[orientation=vertical]:hover:bg-primary/40 aria-[orientation=horizontal]:h-px aria-[orientation=horizontal]:w-full aria-[orientation=horizontal]:after:left-0 aria-[orientation=horizontal]:after:h-1 aria-[orientation=horizontal]:after:w-full aria-[orientation=horizontal]:after:translate-x-0 aria-[orientation=horizontal]:after:-translate-y-1/2 disabled:pointer-events-none disabled:cursor-default",
        className
      )}
      {...props}
    >
      {withHandle && (
        <div className="z-10 flex size-5 items-center justify-center rounded border border-primary/30 bg-primary/20 text-primary">
          <GripVerticalIcon className="size-4" />
        </div>
      )}
    </ResizablePrimitive.Separator>
  )
}

export { ResizableHandle, ResizablePanel, ResizablePanelGroup }
