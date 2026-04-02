"""Design tools for the Visual Designer agent."""

from __future__ import annotations

import json
from typing import Any

from agents.agents.base import ToolDef

ColorPaletteTool = ToolDef(
    name="color_palette",
    description="Generate or analyze a color palette. Can create accessible palettes, check contrast ratios, and suggest harmonious combinations.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["generate", "analyze", "check_contrast"],
                "description": "What to do with the palette",
            },
            "base_color": {"type": "string", "description": "Hex color to start from, e.g. '#1a1a2e'"},
            "style": {
                "type": "string",
                "enum": ["minimal", "vibrant", "dark", "warm", "cool"],
                "description": "Visual style direction",
            },
            "colors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Existing colors to analyze (hex values)",
            },
        },
        "required": ["action"],
    },
)

LayoutAnalysisTool = ToolDef(
    name="layout_analysis",
    description="Analyze an HTML/CSS layout for visual hierarchy, spacing consistency, and responsive issues.",
    parameters={
        "type": "object",
        "properties": {
            "html_path": {"type": "string", "description": "Path to the HTML file"},
            "css_path": {"type": "string", "description": "Path to the CSS file"},
            "viewport": {
                "type": "string",
                "enum": ["mobile", "tablet", "desktop"],
                "default": "desktop",
            },
        },
        "required": ["html_path"],
    },
)

CSSGeneratorTool = ToolDef(
    name="css_generate",
    description="Generate CSS based on design specifications. Outputs production-ready CSS with custom properties.",
    parameters={
        "type": "object",
        "properties": {
            "spec": {
                "type": "object",
                "description": "Design spec with typography, colors, spacing, and component styles",
            },
            "target": {"type": "string", "description": "CSS file path to write to"},
            "format": {
                "type": "string",
                "enum": ["css", "scss", "css-modules"],
                "default": "css",
            },
        },
        "required": ["spec"],
    },
)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG 2.1."""
    def linearize(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(color1: str, color2: str) -> float:
    """Calculate WCAG contrast ratio between two hex colors."""
    l1 = _relative_luminance(*_hex_to_rgb(color1))
    l2 = _relative_luminance(*_hex_to_rgb(color2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


async def execute_color_palette(
    action: str,
    base_color: str | None = None,
    style: str | None = None,
    colors: list[str] | None = None,
) -> dict[str, Any]:
    """Generate or analyze color palettes."""
    if action == "check_contrast" and colors and len(colors) >= 2:
        pairs = []
        for i in range(len(colors)):
            for j in range(i + 1, len(colors)):
                ratio = _contrast_ratio(colors[i], colors[j])
                pairs.append({
                    "pair": [colors[i], colors[j]],
                    "ratio": round(ratio, 2),
                    "wcag_aa": ratio >= 4.5,
                    "wcag_aaa": ratio >= 7.0,
                })
        return {"action": "check_contrast", "pairs": pairs}

    if action == "generate" and base_color:
        # Simple complementary palette generation.
        r, g, b = _hex_to_rgb(base_color)
        palette = {
            "primary": base_color,
            "primary_light": f"#{min(r+40,255):02x}{min(g+40,255):02x}{min(b+40,255):02x}",
            "primary_dark": f"#{max(r-40,0):02x}{max(g-40,0):02x}{max(b-40,0):02x}",
            "complement": f"#{255-r:02x}{255-g:02x}{255-b:02x}",
            "surface": "#f8f9fa",
            "text": "#16213e",
        }
        return {"action": "generate", "palette": palette, "style": style}

    if action == "analyze" and colors:
        analysis = []
        for c in colors:
            r, g, b = _hex_to_rgb(c)
            lum = _relative_luminance(r, g, b)
            analysis.append({"color": c, "luminance": round(lum, 4), "light": lum > 0.5})
        return {"action": "analyze", "colors": analysis}

    return {"error": "Invalid action or missing required parameters"}


async def execute_layout_analysis(
    html_path: str, css_path: str | None = None, viewport: str = "desktop"
) -> dict[str, Any]:
    """Analyze layout structure from HTML/CSS files.

    In production, this would parse the DOM and computed styles.
    For now, it reads the files and returns structural info.
    """
    import os

    result: dict[str, Any] = {"html_path": html_path, "viewport": viewport}

    if os.path.isfile(html_path):
        with open(html_path, "r") as f:
            html = f.read()
        # Count structural elements.
        result["sections"] = html.count("<section")
        result["headings"] = sum(html.count(f"<h{i}") for i in range(1, 7))
        result["images"] = html.count("<img")
        result["links"] = html.count("<a ")
    else:
        result["error"] = f"HTML file not found: {html_path}"

    if css_path and os.path.isfile(css_path):
        with open(css_path, "r") as f:
            css = f.read()
        result["css_rules"] = css.count("{")
        result["media_queries"] = css.count("@media")
        result["custom_properties"] = css.count("--")
    return result


async def execute_css_generate(
    spec: dict[str, Any], target: str | None = None, format: str = "css"
) -> dict[str, Any]:
    """Generate CSS from a design spec."""
    lines = [":root {"]
    colors = spec.get("colors", {})
    for name, value in colors.items():
        lines.append(f"    --color-{name}: {value};")
    typography = spec.get("typography", {})
    for name, value in typography.items():
        lines.append(f"    --font-{name}: {value};")
    spacing = spec.get("spacing", {})
    for name, value in spacing.items():
        lines.append(f"    --space-{name}: {value};")
    lines.append("}")

    css_output = "\n".join(lines)

    if target:
        import os
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        with open(target, "w") as f:
            f.write(css_output)

    return {"css": css_output, "target": target, "format": format}


TOOL_EXECUTORS = {
    "color_palette": execute_color_palette,
    "layout_analysis": execute_layout_analysis,
    "css_generate": execute_css_generate,
}
