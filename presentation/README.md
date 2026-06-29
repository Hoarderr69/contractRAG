# Contract360 — Manager Presentation

A senior-management briefing deck for **Contract360**, generated from the `prod`
branch `README.md` and `ARCHITECTURE.md`. Corporate palette (yellow / black / grey / white).

## Deliverables

| File | Use |
|---|---|
| `Contract360_Manager_Deck.pptx` | **Editable PowerPoint** — apply your corporate template/theme on top, or present as-is. Each slide has speaker notes. |
| `Contract360_Manager_Deck.html` | **Self-contained HTML deck** — double-click to open in any browser. No internet required (diagrams embedded). Arrow keys / Space to navigate, `F` for fullscreen. Use as the live deck or as a backup. |
| `SPEAKER_NOTES.md` | Talk track, live-demo script, sample questions, and Q&A prep. |
| `hl_arch.png` / `detail_arch.png` | Rendered architecture diagrams (on-brand styling). |

## Slide structure (per the brief)

1. **Title** — Contract360
2. **Slide 1 — Context:** problem, proposed solution, business value, tech stack
3. **Slide 1 (cont.) — High-Level Architecture** diagram
4. **Slide 2 — Detailed Architecture** diagram
5. **Slide 3 — Demo** (flow, sample questions, backup-video reminder, roadmap)

> The brief listed three slides (problem+solution+HL arch / detailed arch / demo).
> The high-level architecture was given its own slide so it stays readable for the
> room, and a title slide was added. Content otherwise maps 1:1 to the brief.

## Before the meeting

- **Insert the backup demo-video link** on Slide 3 (placeholder marked in yellow).
- Drop in your official **logo** image if you have the asset (the deck uses a neutral
  yellow beam accent only — no company name is printed anywhere).
- If your team has an official **.potx template**, open the `.pptx` in PowerPoint
  and apply it via *Design → Themes* — content is built with standard shapes/colors
  so it re-themes cleanly.

## Regenerating

The deck is generated from scripts in `_build/`:

```bash
pip install python-pptx Pillow
# diagrams (needs Node + a Chromium):
npx @mermaid-js/mermaid-cli -i _build/hl_arch.mmd     -o hl_arch.png     -b white -s 3
npx @mermaid-js/mermaid-cli -i _build/detail_arch.mmd -o detail_arch.png -b white -s 3
python _build/build_pptx.py    # → Contract360_Manager_Deck.pptx
python _build/build_html.py    # → Contract360_Manager_Deck.html
```

Brand palette: Yellow `#FFE600` · Black `#2E2E38` · Grey `#747480` · White.
