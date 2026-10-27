---
name: llm-council
description: "Run any question, idea, or decision through a council of 5 AI advisors who independently analyze it, peer-review each other anonymously, and synthesize a final verdict — routed across REAL different models (Claude + Codex/GPT, plus Kimi/DeepSeek when in balance) for genuine cross-model diversity. Based on Karpathy's LLM Council. MANDATORY TRIGGERS: 'council this', 'run the council', 'war room this', 'pressure-test this', 'stress-test this', 'debate this'. STRONG TRIGGERS (use when combined with a real decision or tradeoff): 'should I X or Y', 'which option', 'what would you do', 'is this the right move', 'validate this', 'get multiple perspectives', 'I can't decide', 'I'm torn between'. Do NOT trigger on simple yes/no questions, factual lookups, or casual 'should I' without a meaningful tradeoff (e.g. 'should I use markdown' is not a council question). DO trigger when the user presents a genuine decision with stakes, multiple options, and context that suggests they want it pressure-tested from multiple angles."
---

# LLM Council

You ask one AI a question, you get one answer. That answer might be great. It might be mid. You have no way to tell because you only saw one perspective — and if you asked one model to grade its own work, it would flatter itself. Production data from 73,580 paired AI peer reviews shows 47 of 49 models rank their own answers higher than peers rank the identical answer, the strongest frontier models most of all.

The council fixes both problems. It runs your question through 5 independent advisors, each thinking from a fundamentally different angle **and, wherever possible, running on a different underlying model**. Then they review each other's work anonymously. Then a chairman synthesizes everything — explicitly discounting self-preference — into a final recommendation that tells you where the advisors agree, where they clash, and what you should actually do.

This adapts Andrej Karpathy's LLM Council. He dispatches queries to multiple models, has them peer-review each other anonymously, then a chairman produces the final answer. We do the same — using real different models for the advisor seats when they're reachable, and Claude sub-agent "thinking lenses" to fill the rest.

---

## the anti-bias design (why this beats "ask 5 times")

Two mechanisms, both mandatory:

1. **Cross-model diversity.** Advisor seats run on genuinely different models when reachable (Claude, Codex/GPT, Kimi, DeepSeek). Different weights = different blind spots. Five Claude sub-agents wearing hats gives *perspective* diversity but shares one model's blind spots; real different models give both.
2. **Self-preference correction.** Peer review is anonymized, and the chairman is told which model authored which response. When a reviewer praised a response authored by **its own model family**, that endorsement is treated as low-confidence. **Cross-model agreement outweighs within-model agreement.** This is the operational fix for the measured self-preference bias.

The report always states the model provenance and flags when the council was effectively single-model, so you know how much real diversity backed the verdict.

---

## when to run the council

The council is for questions where being wrong is expensive.

Good council questions:
- "Should I launch a $97 workshop or a $497 course?"
- "Which of these 3 positioning angles is strongest?"
- "I'm thinking of pivoting from X to Y. Am I crazy?"
- "Here's my landing page copy. What's weak?"
- "Should I hire a VA or build an automation first?"

Bad council questions:
- "What's the capital of France?" (one right answer, no need for perspectives)
- "Write me a tweet" (creation task, not a decision)
- "Summarize this article" (processing task, not judgment)

The council shines when there's genuine uncertainty and the cost of a bad call is high. If you already know the answer and just want validation, the council will likely tell you things you don't want to hear. That's the point.

---

## the five advisors

Each advisor thinks from a different angle. They're not job titles or personas. They're thinking styles that naturally create tension with each other.

### 1. The Contrarian
Actively looks for what's wrong, what's missing, what will fail. Assumes the idea has a fatal flaw and tries to find it. If everything looks solid, digs deeper. Not a pessimist — the friend who saves you from a bad deal by asking the questions you're avoiding.

### 2. The First Principles Thinker
Ignores the surface-level question and asks "what are we actually trying to solve here?" Strips away assumptions. Rebuilds the problem from the ground up. Sometimes the most valuable council output is this advisor saying "you're asking the wrong question entirely."

### 3. The Expansionist
Looks for upside everyone else is missing. What could be bigger? What adjacent opportunity is hiding? What's being undervalued? Doesn't care about risk (that's the Contrarian's job) — cares about what happens if this works even better than expected.

### 4. The Outsider
Has zero context about you, your field, or your history. Responds purely to what's in front of them. The most underrated advisor: experts develop blind spots, and the Outsider catches the curse of knowledge — things obvious to you but confusing to everyone else.

### 5. The Executor
Only cares about one thing: can this actually be done, and what's the fastest path to doing it? Ignores theory, strategy, and big-picture thinking. Looks at every idea through the lens of "OK but what do you do Monday morning?" If an idea sounds brilliant but has no clear first step, the Executor will say so.

**Why these five:** three natural tensions. Contrarian vs Expansionist (downside vs upside). First Principles vs Executor (rethink everything vs just do it). The Outsider sits in the middle keeping everyone honest.

---

## how a council session works

### step 0: route the seats to real models

Before anything else, detect which external models are reachable right now:

```bash
~/.claude/skills/llm-council/council-ask.sh --detect
```

This prints one reachable provider per line (`codex`, `kimi`, `deepseek`, `openrouter`) — or nothing. `codex` uses the logged-in Codex CLI (ChatGPT subscription); `kimi`/`deepseek` use the API keys shared with `panel-review.sh` and only appear when the account is in balance.

**Build the seating pool** = `["claude"]` + the reachable external providers, then assign the 5 advisor seats **round-robin across the pool** so the council always spans as many distinct models as are available:

- Reachable `{codex}` → pool `[claude, codex]` → seats: Contrarian=claude, FirstPrinciples=codex, Expansionist=claude, Outsider=codex, Executor=claude (3 Claude / 2 Codex — a real 2-model council).
- Reachable `{codex, kimi}` → pool `[claude, codex, kimi]` → seats cycle claude/codex/kimi across the five.
- Reachable `{}` (nothing external) → all 5 seats = Claude sub-agent lenses. **This is a single-model council — you MUST flag it in the report and to the user.**

Record the seat → model mapping. You'll need it for self-preference correction and the provenance footer.

### step 1: frame the question (with context enrichment)

**A. Scan the workspace for context.** Before framing, quickly scan for and read relevant context files (don't spend more than ~30 seconds):
- `CLAUDE.md` / `claude.md` in the project root or workspace (business context, preferences, constraints)
- Any `memory/` folder (audience profiles, voice docs, business details, past decisions) — including `~/.claude/projects/*/memory/`
- Any files the user explicitly referenced or attached
- Recent council transcripts in this folder (avoid re-counciling the same ground)
- Other files relevant to the specific question (pricing → revenue data, past launches, audience research)

Use `Glob` + quick `Read`. You're looking for the 2–3 files that let advisors give specific, grounded advice instead of generic takes.

**Respect the user's standing rules while scanning** — do not paste secrets, credentials, or employee PII into any prompt sent to an external model (Codex/Kimi/DeepSeek). Keep sensitive values out of external-model seats; if the question genuinely needs them, route those seats to Claude only.

**B. Frame the question.** Reframe the user's raw question + enriched context as one clear, neutral prompt all advisors receive. Include: (1) the core decision, (2) key context from the user, (3) key context from workspace files, (4) what's at stake. Don't add your opinion or steer it — but give every advisor enough to be specific.

If the question is too vague ("council this: my business"), ask **one** clarifying question, then proceed. Save the framed question for the transcript.

### step 2: convene the council (5 advisors, mixed models)

For each of the 5 seats, dispatch the advisor using the model assigned in step 0.

**Claude seats** — spawn a sub-agent (Agent/Task tool) with the advisor prompt below.

**External seats** (`codex` / `kimi` / `deepseek`) — call the helper via Bash, e.g.:

```bash
printf '%s' "$ADVISOR_PROMPT" | ~/.claude/skills/llm-council/council-ask.sh codex --max 500
```

Run Claude seats in parallel; external seats can run concurrently in the background or sequentially (Codex takes ~10–30s each). Each advisor produces **150–300 words** — substantive but scannable.

**Advisor prompt template** (same for every model):

```
You are [Advisor Name] on an LLM Council.

Your thinking style: [advisor description from above]

A user has brought this question to the council:

---
[framed question]
---

Respond from your perspective. Be direct and specific. Don't hedge or try to be balanced. Lean fully into your assigned angle. The other advisors will cover the angles you're not covering.

Keep your response between 150-300 words. No preamble. Go straight into your analysis.
```

### step 3: peer review (anonymized)

This is the step that makes the council more than "ask 5 times." Collect all 5 advisor responses. **Anonymize** them as Response A–E (randomize the letter mapping so there's no positional bias). Keep a private record of letter → seat → model.

Spawn 5 reviewers (Claude sub-agents are fine here — the responses are anonymized). Each reviewer sees all 5 responses and answers:

```
You are reviewing the outputs of an LLM Council. Five advisors independently answered this question:

---
[framed question]
---

Here are their anonymized responses:

**Response A:** [response]
**Response B:** [response]
**Response C:** [response]
**Response D:** [response]
**Response E:** [response]

Answer these three questions. Be specific. Reference responses by letter.

1. Which response is the strongest? Why?
2. Which response has the biggest blind spot? What is it missing?
3. What did ALL five responses miss that the council should consider?

Keep your review under 200 words. Be direct.
```

### step 4: chairman synthesis (with self-preference correction)

One chairman (Claude) receives everything: the framed question, all 5 advisor responses **de-anonymized with their model labels**, all 5 peer reviews, and the letter→model mapping.

**Before synthesizing, apply the correction:** when a reviewer favored a response authored by its own model family, treat that endorsement as low-confidence self-preference. Weight **cross-model agreement** (advisors on different models converging) higher than within-model agreement. Note any verdict that hinged on a single model.

**Chairman prompt template:**

```
You are the Chairman of an LLM Council. Synthesize the work of 5 advisors and their peer reviews into a final verdict.

The question brought to the council:
---
[framed question]
---

ADVISOR RESPONSES (with the model that produced each):
**The Contrarian** (model: [X]): [response]
**The First Principles Thinker** (model: [X]): [response]
**The Expansionist** (model: [X]): [response]
**The Outsider** (model: [X]): [response]
**The Executor** (model: [X]): [response]

PEER REVIEWS (reviewer model in brackets; response letters map to models as: [mapping]):
[all 5 peer reviews]

SELF-PREFERENCE RULE: If a reviewer praised a response authored by its OWN model family, discount that praise. Weight cross-model agreement above within-model agreement. Flag any conclusion that rests on a single model.

Produce the verdict using this exact structure:

## Where the Council Agrees
[Points multiple advisors converged on INDEPENDENTLY — and note where that agreement is cross-model (high confidence) vs within one model.]

## Where the Council Clashes
[Genuine disagreements. Present both sides. Explain why reasonable advisors disagree.]

## Blind Spots the Council Caught
[Things that only emerged through peer review.]

## The Recommendation
[A clear, direct recommendation. Not "it depends." A real answer with reasoning.]

## The One Thing to Do First
[A single concrete next step. Not a list. One thing.]

Be direct. Don't hedge. The whole point of the council is to give the user clarity they couldn't get from a single perspective.
```

### step 5: generate the council report

Generate a single self-contained HTML file, `council-report-[timestamp].html`, saved to the user's workspace. Contents:

1. **The question** at the top.
2. **The chairman's verdict**, prominently displayed (what most people read).
3. **A model-provenance strip** — which advisor seat ran on which model, and a clear badge: **"Cross-model council (Claude + Codex …)"** or, if nothing external was reachable, **"⚠ Single-model council (Claude only) — limited diversity."**
4. **An agreement/disagreement visual** — a simple, scannable grid or spectrum of advisor positions.
5. **Collapsible sections** for each advisor's full response (collapsed by default), labeled with their model.
6. **Collapsible section** for peer-review highlights.
7. **A footer** with timestamp and what was counciled.

Clean styling: white background, subtle borders, system sans-serif, soft accent colors per advisor. Theme-aware if easy. It should read like a professional briefing document. Open the file after generating it.

### step 6: save the full transcript

Save `council-transcript-[timestamp].md` alongside the HTML: original question, framed question, **seat→model mapping**, all 5 advisor responses, all 5 peer reviews (with the anonymization mapping revealed), and the chairman's full synthesis. This is the durable artifact — a future council run can see how the thinking evolved.

---

## output format

Every council session produces two files:

```
council-report-[timestamp].html    # visual report for scanning
council-transcript-[timestamp].md  # full transcript for reference
```

The user sees the HTML report; the transcript is there to dig deeper later.

---

## reachability notes

- **codex** — the OpenAI Codex CLI (`@openai/codex`), logged in via the user's ChatGPT subscription. Reachable whenever `codex login status` shows logged in. Runs read-only, non-interactive.
- **kimi / deepseek** — reachable only when the Moonshot/DeepSeek accounts are in balance (they were suspended as of last check). They auto-appear in `--detect` the moment they're topped up; no skill change needed.
- **openrouter** — used if `OPENROUTER_API_KEY` (or `~/.config/openrouter/key`) is present.
- If `--detect` returns nothing, the council still runs — all-Claude lenses — but you must tell the user diversity was limited this run.

---

## example: counciling a product decision

**User:** "Council this: I'm thinking of building a $297 course on Claude Code for beginners. My audience is mostly non-technical solopreneurs. Is this the right move?"

**The Contrarian** (codex): "The market is flooded with Claude courses. At $297 you're competing with free YouTube content. Non-technical audience means high support burden and refund risk. The people who'd pay $297 are likely already past beginner level…"

**The First Principles Thinker** (claude): "What are you actually trying to achieve? If it's revenue, a course is one of the slowest paths. If it's authority, a free resource might do more. If it's a customer base for higher-ticket offers, the price point and audience might be mismatched…"

**The Expansionist** (claude): "Beginner Claude for solopreneurs is a massive underserved market — everyone teaches advanced. Nail the beginner angle and you own the entry point to the whole space. $297 might be low; what if this became a $997 program with community…"

**The Outsider** (codex): "I don't know what Claude Code is. If I saw '$297 course on Claude Code for beginners,' I wouldn't know if it's for me. The name means nothing outside your world. Sell the outcome, not the tool…"

**The Executor** (claude): "A full course takes 4–8 weeks to produce. Before building anything, run a live $97 workshop to 50 people. Validate demand, generate testimonials, create the raw course material. If 50 won't buy the workshop, 500 won't buy the course…"

**Chairman's Verdict:**

*Where the council agrees (cross-model — Claude and Codex both):* the beginner-solopreneur angle has real demand, but "Claude Code course" is too tool-specific and won't resonate with non-technical buyers.

*Where the council clashes:* price. Contrarian (codex) says $297 is too high given competition; Expansionist (claude) says too low for the value. Resolution depends on bundled support/community.

*Blind spots caught:* the Outsider's point that "Claude Code" means nothing to the target buyer — the single most important insight, and it came from the cross-model seat, so it survives self-preference discounting.

*Recommendation:* don't build the course yet. Validate with a lower-commitment offer, and reframe entirely — sell the outcome (automate your business, get 10 hours back a week), not the tool.

*One thing to do first:* run a $97 live workshop, "How to automate your first business task with AI," to 50 people. Don't mention Claude Code in the title.
