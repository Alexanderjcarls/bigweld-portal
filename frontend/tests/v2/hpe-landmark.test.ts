import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

type Token = {
  $value: string;
  original?: {
    $value: string;
  };
};

type TokenGroup = Record<string, Token>;

const css = readFileSync(resolve(process.cwd(), "src/v2/index.css"), "utf8");
const packageJson = JSON.parse(
  readFileSync(resolve(process.cwd(), "node_modules/hpe-design-tokens/package.json"), "utf8"),
) as { license: string; version: string };

const { light, dark } = (await import("hpe-design-tokens/docs")) as {
  light: TokenGroup;
  dark: TokenGroup;
};

describe("v2 HPE Landmark token bridge", () => {
  it("uses the Apache-2.0 Landmark package", () => {
    expect(packageJson).toMatchObject({
      license: "Apache-2.0",
      version: "2.2.3",
    });
  });

  it("snapshots the Landmark values used by shadcn semantics", () => {
    expect({
      light: semanticSnapshot(light),
      dark: semanticSnapshot(dark),
    }).toMatchInlineSnapshot(`
      {
        "dark": {
          "background": "#1d1f27",
          "border": "rgba(255, 255, 255, 0.12)",
          "foreground": "#e6e8e9",
          "primary": "#05cc93",
          "primaryForeground": "#292d3a",
          "primaryHover": "#00e0af",
        },
        "light": {
          "background": "#f7f7f7",
          "border": "#d4d8db",
          "foreground": "#3e4550",
          "primary": "#068667",
          "primaryForeground": "#ffffff",
          "primaryHover": "#006750",
        },
      }
    `);
  });

  it("imports published package CSS before mapping Tailwind theme tokens", () => {
    expect(css).toContain('@import "hpe-design-tokens/dist/css/primitives.css";');
    expect(css).toContain('@import "hpe-design-tokens/dist/css/global.css";');
    expect(css).toContain('@import "hpe-design-tokens/dist/css/dimension.css";');
    expect(css).toContain('@import "hpe-design-tokens/dist/css/dimension.small.css";');
    expect(css).toContain('@import "hpe-design-tokens/dist/css/components.css";');
    expect(css).toContain('@import "hpe-design-tokens/dist/css/color.light.css";');
    expect(css).toContain('@import "hpe-design-tokens/dist/css/color.dark.css";');
    expect(css).toContain("@theme inline");
  });

  it("maps Landmark primary green, not the old v1 approximation", () => {
    expect(token(light, "hpe.color.background.primary.strong")).toBe("#068667");
    expect(token(light, "hpe.color.background.primary.strong")).not.toBe("#00b27d");
    expect(css).toContain("--primary: var(--hpe-color-background-primary-strong);");
    expect(css).toContain("--color-primary: var(--primary);");
  });

  it("wires Landmark state, density, and focus tokens onto shadcn controls", () => {
    expect(css).toContain("[data-slot=\"button\"][data-variant=\"default\"]");
    expect(css).toContain("background: var(--primary);");
    expect(css).toContain("background: var(--primary-hover);");
    expect(css).toContain("background: var(--primary-active);");
    expect(css).toContain("outline: var(--hpe-focusIndicator-outline);");
    expect(css).toContain("min-height: var(--hpe-element-medium-minHeight);");
    expect(css).toContain("border-color: var(--input-hover);");
    expect(css).toContain("--motion-duration-default: 150ms;");
    expect(css).toContain("transition-timing-function: var(--motion-easing-standard);");
  });
});

function semanticSnapshot(tokens: TokenGroup) {
  return {
    background: token(tokens, "hpe.color.background.back"),
    foreground: token(tokens, "hpe.color.text.default"),
    border: token(tokens, "hpe.color.border.weak"),
    primary: token(tokens, "hpe.color.background.primary.strong"),
    primaryHover: token(tokens, "hpe.color.background.primary.strong.hover"),
    primaryForeground: token(tokens, "hpe.color.text.onPrimaryStrong"),
  };
}

function token(tokens: TokenGroup, key: string) {
  const value = tokens[key]?.$value;
  if (!value) throw new Error(`Missing HPE token: ${key}`);
  return value.toLowerCase();
}
