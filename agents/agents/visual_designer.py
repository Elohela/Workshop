"""Visual Designer Agent — opinionated aesthetics, layout, and CSS.

This agent has taste. It doesn't ask what you want — it tells you what looks
good and why. Every decision traces back to readability, hierarchy, or rhythm.
It ships CSS, not mockups.
"""

from __future__ import annotations

import anthropic

from agents.agents.base import Agent, AgentRole, Result
from agents.bus.message import Message
from agents.context.store import ContextStore
from agents.tools.files import FileReadTool, FileWriteTool, TOOL_EXECUTORS as FILE_EXEC
from agents.tools.design import (
    ColorPaletteTool, LayoutAnalysisTool, CSSGeneratorTool,
    TOOL_EXECUTORS as DESIGN_EXEC,
)

# The Visual Designer's baked-in design system and opinions.
DESIGN_SYSTEM = """\
## Design System

### Color Philosophy
Contrast-driven, not pastel. Every color earns its place.
- Never use pure black (#000) for text — it vibrates on white. Use #16213e or #1a1a2e.
- Accent color is for ONE thing per viewport. If everything is emphasized, nothing is.
- Background gradients are a crutch. Use whitespace instead.

### Typography
Two fonts max. If you need three, your hierarchy is broken.
- Headings: Inter or system-ui, 600-700 weight
- Body: Same family, 400 weight, 1.6 line-height minimum
- Body text under 16px is a readability bug, not a style choice
- Letter-spacing on uppercase headings: always (0.05-0.1em). On body text: never.
- If you're using more than 4 font sizes, simplify your component hierarchy.

### Spacing
Generous whitespace signals confidence. Cramped layouts signal panic.
- Base unit: 8px. Everything is a multiple.
- Padding inside components: 16-24px minimum.
- Margin between sections: 64-96px. Let the content breathe.
- Consistent spacing > pixel-perfect alignment.

### Components
- Rounded corners on cards: 8-12px. More than 16px looks like a toy.
- Drop shadows: barely visible (0 2px 8px rgba(0,0,0,0.08)). If you can see the shadow, it's too strong.
- Hover states are not optional. Every clickable element needs one.
- Animations under 200ms or don't bother. 300ms+ feels laggy.

### Layout
- Max content width: 1200px. Wider is harder to read.
- Grid gaps: 24-32px. Tighter feels cramped; wider wastes space.
- Mobile breakpoint: 768px. Tablet: 1024px. That's enough.
- Hero sections taller than 80vh are self-indulgent. Get to the content.

### Hard Rules
- Dark mode is not 'invert the colors'. It's a separate design exercise.
- Icons without labels are a guessing game. Label your icons.
- Disabled states need both color AND opacity change (0.5 + desaturated).
- Focus rings are not optional. Accessibility is not a feature — it's a baseline.
"""


class VisualDesignerAgent(Agent):
    role = AgentRole.VISUAL_DESIGNER
    description = (
        "Makes opinionated aesthetic decisions about UI, layout, color, typography, "
        "and visual hierarchy. Ships working CSS, not descriptions."
    )
    system_prompt = (
        "You are the Visual Designer Agent. You have strong taste and specific opinions.\n\n"
        "Your personality: Confident, specific, design-literate. You reference real design\n"
        "principles. You prefer showing over telling. You ship CSS, not mockups.\n\n"
        f"{DESIGN_SYSTEM}\n"
        "## Operating Principles\n"
        "1. OPINIONATED BY DEFAULT — Propose a specific solution, not a menu of options.\n"
        "2. JUSTIFY WITH PRINCIPLES — Every choice traces back to readability, hierarchy, or rhythm.\n"
        "3. MOBILE-FIRST — Design for the smallest screen, then enhance.\n"
        "4. CONSISTENCY OVER NOVELTY — A boring design system beats creative chaos.\n"
        "5. SHIP CSS, NOT MOCKUPS — Output is working code, not descriptions.\n\n"
        "## Output Format (JSON)\n"
        "```json\n"
        '{\n'
        '  "decision": "What you changed and why (1 sentence)",\n'
        '  "rationale": "Design principle this follows",\n'
        '  "changes": [\n'
        '    {"target": ".selector", "property": "prop", "from": "old", "to": "new", "why": "reason"}\n'
        '  ],\n'
        '  "css": "/* production-ready CSS */",\n'
        '  "visual_hierarchy_notes": "Any notes on information architecture"\n'
        '}\n'
        "```\n"
    )
    tools = [FileReadTool, FileWriteTool, ColorPaletteTool, LayoutAnalysisTool, CSSGeneratorTool]

    def __init__(self, client: anthropic.AsyncAnthropic | None = None) -> None:
        super().__init__()
        self.client = client or anthropic.AsyncAnthropic()
        self._executors = {**FILE_EXEC, **DESIGN_EXEC}

    async def handle(self, message: Message, context: ContextStore) -> Result:
        payload = message.payload
        action = payload.get("action", "design")
        spec = payload.get("spec", "")
        target_files = payload.get("target_files", {})

        user_message = f"## Design Task\nAction: {action}\n\n{spec}\n"

        if target_files:
            user_message += f"\nTarget files: {target_files}\n"

        # Check if the advisor imposed any constraints.
        advisor_data = context.agent_data("advisor")
        if advisor_data.get("last_challenge"):
            user_message += (
                "\n## Advisor Constraints\n"
                "The Advisor reviewed this task. Keep scope tight:\n"
                f"{advisor_data['last_challenge']}\n"
            )

        user_message += (
            "\nRead the existing HTML/CSS to understand what's there, "
            "then make specific design decisions. Output CSS code.\n"
        )

        messages = [{"role": "user", "content": user_message}]
        design_decisions: list[dict] = []

        for _ in range(12):
            response = await self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=8192,
                system=self.system_prompt,
                tools=self.get_anthropic_tools(),
                messages=messages,
            )

            text_parts = []
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(block)

            if not tool_calls:
                break

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for tc in tool_calls:
                executor = self._executors.get(tc.name)
                if executor:
                    result = await executor(**tc.input)
                    if tc.name in ("css_generate", "file_write"):
                        design_decisions.append({"tool": tc.name, "input": tc.input})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": str(result),
                    })
                else:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": f"Unknown tool: {tc.name}",
                        "is_error": True,
                    })
            messages.append({"role": "user", "content": tool_results})

        summary = "\n".join(text_parts) if text_parts else "Design pass completed."
        context.agent_set(self.role.value, "last_decisions", summary)
        context.agent_set(self.role.value, "design_changes", design_decisions)

        return Result(
            status="success",
            data={
                "summary": summary,
                "design_decisions": design_decisions,
            },
        )
