---
title: AI Characters & Conversational NPCs — Focus Area
lang: en
source: ../../ai-characters/README.md
last_reviewed: 2026-09-24
---

# AI Characters & Conversational NPCs

> English edition. The Japanese edition ([../../ai-characters/](../../ai-characters/README.md)) is the source of truth; this translation may lag behind it.

This is the first area where this knowledge base aims to be the best in the world.
Scope: **characters that talk through an LLM, remember, and build a relationship with the player** —
game NPCs, AI companions, AI VTubers, and official IP characters brought to life with AI.

## Why this area
1. **It changes the most.** It is the clearest example of an experience that cannot exist without AI.
2. **Knowledge is fragmented.** Game AI research, companion apps, streaming culture and regulation are discussed in separate silos.
3. **Japan has an edge.** Character culture, VTubers, voice actors — and, since August 2026, a Ministry of Justice guideline on voice rights.
4. **Regulation now shapes design directly.** The scope of a character's conversation alone can change its legal classification (see pattern P01).

## Contents

| File | What it is | Use it for |
|---|---|---|
| [patterns.md](patterns.md) | 38 design patterns in 7 groups | A reference while planning and designing |
| [case-studies.md](case-studies.md) | 14 case studies (3 from Japan), successes and failures | Evidence of what has actually happened |
| [evaluation.md](evaluation.md) | A five-layer evaluation framework with release gates | Development, QA and ship decisions |

## Five principles (the catalog in one screen)
1. **Decide the conversation scope first.** Experience, cost and legal classification all follow from it (P01).
2. **The engine owns facts and rules.** Never let what the LLM *says* become game truth (P16).
3. **Don't let the character judge itself.** Persuasion outcomes are scored by a separate judge (P17).
4. **Keep relationships as numeric state.** Affinity must not depend on the LLM's mood (P11).
5. **Design the ending.** Endless conversation is a weakness for wellbeing and for compliance (P22).

## Experiments
A small harness that compares a naive NPC engine with one that applies these patterns lives in [prototype/](../../../prototype/README.md); results are logged in [experiments/](../../../experiments/).
