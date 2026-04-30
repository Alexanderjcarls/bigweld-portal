import { getToolName, type DynamicToolUIPart, type ToolUIPart, type UITools } from "ai";
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "@/v2/components/ai-elements/tool";
import { CodeBlock } from "@/v2/components/ai-elements/code-block";

type AnyToolPart = ToolUIPart<UITools> | DynamicToolUIPart;

interface ToolCallProps {
  part: AnyToolPart;
}

export function ToolCall({ part }: ToolCallProps) {
  const isErrored = part.state === "output-error";
  const toolName = getToolName(part);
  const output = part.state === "output-available" ? part.output : undefined;
  const errorText = part.state === "output-error" ? part.errorText : undefined;

  return (
    <Tool
      defaultOpen={isErrored}
      data-testid="tool-call"
      aria-label={`Tool call ${toolName}`}
    >
      <ToolHeader name={toolName} state={part.state} type={part.type} />
      <ToolContent>
        <ToolInput input={"input" in part ? part.input : undefined} />
        {(output !== undefined || errorText) && (
          <ToolOutput
            errorText={errorText}
            output={
              output === undefined ? null : (
                <CodeBlock code={formatToolValue(output)} language="json" />
              )
            }
          />
        )}
      </ToolContent>
    </Tool>
  );
}

function formatToolValue(value: unknown): string {
  if (typeof value === "string") return value;

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
