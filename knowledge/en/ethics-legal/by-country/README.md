---
title: AI × Entertainment Regulation — Comparison by Country
domain: ethics-legal
maturity: L2
last_reviewed: 2026-09-25
tags: [regulation, copyright, publicity, labeling, companion, japan, us, eu, china, korea]
---

# AI × Entertainment Regulation — Comparison by Country

> ⚠️ General information, not legal advice. Base practical decisions on the latest primary sources and professional review.
> A cross-cutting, issue-by-issue overview is in [ethics-legal.md (Japanese)](../../../ethics-legal/ethics-legal.md). This page rearranges it by country and region for comparison.
> Japanese edition: [../../../ethics-legal/by-country/README.md](../../../ethics-legal/by-country/README.md)

## Comparison table (as of September 2026)

| Issue | [Japan](japan.md) | [US](us.md) | [EU](eu.md) | [China](china.md) | [South Korea](korea.md) |
|---|---|---|---|---|---|
| **Training** | Generally permitted under Copyright Act Art. 30-4 (except where an "enjoyment" purpose coexists or rights holders' interests are unreasonably harmed) | Fair use being decided in litigation. A district court upheld training on lawfully acquired books | TDM exception (rights holders may opt out). General-purpose AI must publish a training-data summary | Interim Measures for Generative AI Services (Aug 2023) Art. 7: lawfully sourced data and models, no infringement of others' IP, consent for personal information | Rights holders' permission generally required. The government proposed a TDM exception, not enacted as of 2026 |
| **Labeling AI outputs** | No legal duty (guidelines only) | No federal law; some state laws | **AI Act Art. 50**: from Aug 2026, notice of interaction with AI, machine-readable marking of outputs, deepfake disclosure | **Labeling Measures**: from Sep 2025, both visible labels and metadata | **AI Basic Act**: from Jan 2026, advance notice of generative AI, labels and watermarks (fines deferred at least one year) |
| **Voice & likeness** | Right of publicity. The Ministry of Justice's Aug 2026 interpretive guideline states that **voice is covered** | State laws (e.g., Tennessee's ELVIS Act). The federal NO FAKES Act is pending | National laws and GDPR | Civil Code Art. 1023 protects voice by applying portrait-right rules. In 2024 the Beijing Internet Court held unauthorized use of an AI voice infringing for the first time | — |
| **AI companions & minors** | No legal duty | New York (notice to all users every 3 hours), California SB 243 (protections for minors; in-game bots excluded) | AI Act Art. 50(1) (notice that it is AI) | **Anthropomorphic AI Interim Measures**: from Jul 2026, "virtual partner/family" services banned for minors; notice after 2 hours of continuous use | — |
| **In a word, for entertainment** | Lenient on training, but increasingly strict on **output similarity** and **voice** | Litigation and settlements/licensing proceed in parallel | **Most specific labeling duties**; allowances in how artistic works are labeled | **Strictest on labeling and protecting minors** | New labeling duties; labels that do not hamper artistic enjoyment are allowed |

## A realistic policy for shipping globally
1. **Design to the strictest region**: for AI characters, China (minors, 2 hours) and US state laws (crisis response, 3 hours); for labeling, the EU, China, and Korea
2. **Build in both visible labels and machine-readable marks from the start**: this satisfies EU, China, and Korea requirements together
3. **For voice, use a licensed real voice or one that does not imitate a real person**: works under both Japan's guideline and US state laws (→ [ai-characters P38](../../ai-characters/patterns.md))
4. **Conversation scope changes the legal classification**: design NPCs limited to in-game topics separately from companions (→ [ai-characters P01](../../ai-characters/patterns.md))

## Tracking
- US: the Thomson Reuters v. ROSS appellate decision; NO FAKES Act
- EU: the final Code of Practice for Art. 50
- Japan: consideration of amending the Unfair Competition Prevention Act (voice protection)
- Korea: when the AI Basic Act's fine deferral ends; detailed labeling rules
