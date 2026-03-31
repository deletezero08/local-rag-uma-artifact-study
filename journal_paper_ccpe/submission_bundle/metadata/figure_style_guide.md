# Figure Style Guide for PeerJ / SCI Computer Science Submission

## 1. Goal

The figure set should read as a coherent publication package rather than a collection of engineering screenshots. Each figure should make one main claim visible within a few seconds, with supporting structure only where necessary.

## 2. Global visual principles

- Prefer plain white backgrounds and light gray grid lines.
- Use short panel titles and let the caption carry the full explanation.
- Keep annotations sparse. If a sentence can live in the caption, do not keep it inside the figure.
- Use the same semantic color for the same role across figures.
- Avoid decorative arrows, callout boxes, and slogan-like subtitles.
- Keep typography restrained: dark gray text, medium-weight panel titles, no oversized labels.

## 3. Semantic color system

- Negative or impractical route: muted red
- Baseline or neutral route: blue
- Preferred or stable route: green
- Latency / generation-heavy component: orange
- Non-core / ancillary component: light gray
- Control-plane or orchestration context: soft purple

Rule:
- The same semantic meaning should keep the same color across the paper.

## 4. Figure types in this manuscript

### 4.1 System architecture figures

Target style:
- Three-layer organization whenever possible:
  - Control plane
  - Decision / routing layer
  - Execution path
- Contributions should be visually promoted, not buried in subtitles.
- Constraints such as UMA or shared memory budget should appear as first-class structure, not footnotes.
- Feedback arrows should be dashed and sparse.
- Data flow arrows should be solid.

Do:
- Highlight `TurboQuant`, `KV-aware context compression`, and quantized inference as distinct modules.
- Use concise labels such as `Control plane`, `Retriever`, `Pruner`, `Backend`.
- Keep module subtitles to two or three short lines.

Do not:
- Draw a flat pipeline where every module has equal importance.
- Leave core contributions visually indistinguishable from generic components.

### 4.2 Backend comparison figures

Target style:
- Multi-panel results figure with parallel structure.
- Each panel title begins with `A.`, `B.`, `C.` plus a short noun phrase.
- Numeric labels should be aligned and formatted consistently.

Do:
- Use the same model order in each panel.
- Keep panel titles short: `A. Time to first token`, `B. Decode throughput`, `C. Total latency`.
- Let the panel structure, not the caption, show the comparison logic.

Do not:
- Mix panel-letter labels in two places.
- Use inconsistent wording such as one panel with a sentence and another with a phrase.

### 4.3 Trade-off curves

Target style:
- One panel for latency trend, one panel for throughput trend.
- Mark one operating point only if it is discussed in the text.
- Use one restrained arrow annotation instead of multiple explanatory notes.

Do:
- Name the selected point as `Operating point`.
- Keep legends compact and aligned near the top.
- Preserve enough whitespace around the annotated point.

Do not:
- Use optimization language like `Best` unless the manuscript explicitly proves optimality.

### 4.4 End-to-end decomposition figures

Target style:
- One dominant panel for the main before/after comparison.
- Two smaller panels for summary and post-optimization bottleneck view.
- This figure can be promoted to a cross-column figure because it carries the main systems argument.

Do:
- Make the main panel visually dominant.
- Keep one concise summary metric near the top of the main panel.
- Separate `overall reduction` from `post-optimization composition`.

Do not:
- Overload the figure with long interpretive sentences.
- Use multiple tiny insets that force the reader to decode layout before reading content.

## 5. Panel-title rules

- Use the format `A. <short phrase>`.
- Prefer nouns or noun phrases over sentences.
- Keep titles parallel across related figures.

Examples:
- `A. Time to first token`
- `B. Decode throughput`
- `C. Post-optimization bottleneck composition`

## 6. Caption rules

- A caption should explain what the panels show and what the reader should conclude.
- Put long interpretive statements in the caption rather than in the figure body.
- Use one or two sentences for standard figures; use three only for the central figure.

Preferred pattern:
1. What is being compared.
2. What each panel contributes.
3. What main result the figure supports.

## 7. Typography rules

- Panel titles: short, dark gray, medium emphasis.
- Axis labels: sentence case, concise, units included.
- Tick labels: small but readable.
- In-figure annotations: lighter than axis text unless they communicate a main metric.
- Avoid bold text except for primary in-bar values or the most important module name.

## 8. Layout rules

- Use cross-column placement only for figures that carry a central argument.
- System architecture and end-to-end decomposition are eligible for cross-column treatment.
- Supporting trend figures can remain single-column if the text remains legible.
- When text begins to touch a box boundary, enlarge the box before shrinking the font further.

## 9. Publication-style checklist

Before accepting a figure, check:

- Can the main claim be understood in under five seconds?
- Is the contribution visually identifiable without reading the caption first?
- Are colors semantically consistent with the rest of the paper?
- Are there any overlapping labels, cramped subtitles, or duplicated panel markers?
- Does the caption explain the figure without repeating every label?
- Does the figure look like a paper figure rather than a slide or dashboard?

## 10. Figure-specific guidance for this manuscript

- Figure 1 should foreground control, constraints, and method modules.
- Figure 2 should remain a clean three-panel comparison with stable naming.
- Figure 3 should keep the selected operating point visible but understated.
- Figure 5 should remain the primary visual argument for bottleneck migration and optimization impact.

## 11. Short style summary

If a future figure needs a fast decision rule, use this:

- One figure, one main claim.
- Short panel titles.
- Sparse annotations.
- Consistent colors.
- Contributions made visually explicit.
- Captions do the explaining; figures do the showing.
