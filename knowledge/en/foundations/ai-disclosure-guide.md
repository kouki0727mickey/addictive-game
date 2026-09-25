---
title: Playbook — Disclosing AI Use in Entertainment Works
domain: foundations
maturity: L3
last_reviewed: 2026-09-25
tags: [playbook, disclosure, credits, trust, regulation]
---

# Playbook — Disclosing AI Use in Entertainment Works

> Built from 44 cases ([film, music, anime/manga](../domains/case-studies.md): 30; [AI characters](../ai-characters/case-studies.md): 14): what separated disclosures that were accepted from those that drew backlash.
> Legal labeling duties differ by country (→ [comparison by country](../ethics-legal/by-country/README.md)). This guide covers disclosure that goes **beyond the legal minimum to protect the trust of fans and creators**.
> Japanese edition: [../../foundations/ai-disclosure-guide.md](../../foundations/ai-disclosure-guide.md)

## In one line
What decided the backlash was less *whether* AI was used than **when, who, what, and how it was said**.
Disclosure that comes **early, voluntarily, specifically, and together with the human work** tends to be accepted. Disclosure that comes **late, after discovery, vaguely, and downplaying the human work** draws the strongest backlash.

## Four dividing lines from the cases

| Dividing line | Accepted | Backlash |
|---|---|---|
| **When** (timing) | Voluntarily, at announcement or before release (A04 Twins Hinahima, A06 Cyberpunk: Peach John, F02 The Eternaut) | Only after being discovered post-release (F07 Late Night with the Devil, C14 Level-5, A09 Crunchyroll) |
| **What** (specificity) | Which process, how much, and why (F02 "blockbuster-level VFX within budget", A04 "assisted in 95% of cuts") | Just "we used AI", or "labor shortage" as the only reason (A01 The Dog & The Boy) |
| **Human work** (credits) | Names and roles of the people involved (A04, F10 Here) | People credited as a small "+Human" (A01), or AI marketed as a "replacement for people" (F05 Tilly Norwood, M10 TaTa) |
| **Consent** (voice, likeness, works) | Consent from the person or rights holder (M06 Randy Travis, M02 Grimes, F04 Disney × OpenAI) | Unauthorized voices or art styles (M01 AI Drake, A07 voice actors' voices, A08 "Ghibli style") |

**Timing and context** matter too. During labor negotiations or strikes (F01 Secret Invasion), or when the industry is especially sensitive to AI, the same use draws more backlash.

## The disclosure process (5 steps)

### Step 1. Inventory where AI was used
Record, process by process, what used AI and what did not. Include subcontractors (in A09 a vendor used AI in breach of contract).

| Category | Examples | Disclosure priority |
|---|---|---|
| Content the audience or players see or hear | Art, backgrounds, voices, music, lines, NPC dialogue generated at runtime | **High** (also most likely to be legally required) |
| Correcting or restoring human performance or work | Stem separation, de-aging, pronunciation correction | Medium (high if it touches what awards evaluate — F08 The Brutalist) |
| Tools for production efficiency | Coding assistants, scheduling, internal draft translation | Low (Steam also does not require it to be declared) |

### Step 2. Check the legal minimum
- **EU** (AI Act Art. 50, from August 2026): notice that users are interacting with AI, machine-readable marking of outputs, disclosure of deepfakes. Artistic works may disclose in a way that does not hamper enjoyment
- **China** (Labeling Measures, from September 2025): both visible labels and metadata
- **South Korea** (AI Basic Act, from January 2026): advance notice of generative AI services and labeling of outputs
- **US state laws**: AI notices for AI companions (New York: all users, every 3 hours)
- **Store and platform rules**: Steam's generative AI disclosure (including runtime generation), AI labels on Spotify and Deezer
→ Details: [comparison by country](../ethics-legal/by-country/README.md)

### Step 3. Decide what to say (the four-point set)
1. **Where**: the process or scene ("part of the backgrounds", "one building-collapse shot")
2. **Why**: the creative reason ("an expression impossible on this budget", "hair movement"). Never only "labor shortage" or "cost cutting"
3. **What people did**: human judgment and finishing by the director, art staff, voice actors. Credit them by name
4. **Consent and rights**: consent of people whose voice, likeness, or works were used; where training data came from

### Step 4. Decide when and where to say it
- **At announcement, before release**, voluntarily, through official channels (press release, official site, store page)
- **Inside the work**: end credits, work information. In games, the character profile screen or the first conversation (AI characters → [ai-characters P30](../ai-characters/patterns.md))
- **Machine-readable marks**: metadata and watermarks on outputs (for the EU, China, Korea)
- In sensitive periods (e.g., during labor negotiations), be especially careful about how you announce

### Step 5. Prepare how to respond when questioned
- Keep the Step 1 records so you can explain the facts immediately
- Answer with "what, why, what people did". A bare denial, or only a grand plan, leaves distrust (A03 Toei)
- Be ready to withdraw output whose quality fell short (A10 Prime Video's AI dubbing) — but make sure withdrawal does not remove the alternative altogether

## Example wording

**△ Likely to draw backlash**
> This work makes use of the latest AI technology. (Backgrounds: AI + Human)

**○ Likely to be accepted**
> The background art is based on concept art by art director ___. In some scenes, an image generation model was used to add detail, and art staff ___ and ___ finished every cut by hand. This was our choice to achieve the density of the ___ scenes within a limited production schedule. The model was trained only on art materials whose rights we hold.

**For an AI character (in-game)**
> ___'s (character name) conversations are generated on the spot by generative AI. The character's setting and voice are supervised by scenario writer ___. Conversation content is stored for ___ days and can be reviewed and deleted from the "Memories" screen.

## Common mistakes
- **"It's minor, so no need to say anything"** → even three still images triggered boycott calls (F07)
- **Leading with "more, faster, cheaper with AI"** → read as lower quality (A02 Orange)
- **Writing people as assistants to the AI** → the credit format itself causes backlash (A01)
- **Saying "we don't use AI" without checking vendors** → no contract terms or checks in place (A09)
- **Marketing AI as a "replacement for people"** → criticized on both employment and representation (F05, M10)

## Checklist
- [ ] Recorded AI use per process, including subcontractors (Step 1)
- [ ] Checked legal labeling duties for each country and store you ship to (Step 2)
- [ ] Wrote all four points: where, why, what people did, consent and rights (Step 3)
- [ ] Plan to disclose voluntarily, before release, through official channels (Step 4)
- [ ] Credited the people involved by name
- [ ] Confirmed consent of people and rights holders whose voice, likeness, or works were used
- [ ] Prepared an explanation for when questioned, and criteria for withdrawal (Step 5)

## Open questions
- How much does the wording of a disclosure actually change reception? (💡 testable with surveys or A/B tests)
- Does labeling a work as "made without AI" (human-made labels) function as value for the work?
