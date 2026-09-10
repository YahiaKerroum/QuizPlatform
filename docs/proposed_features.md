# Proposed Features — Taking the Adaptive Quiz Platform Past the Course Project

> **Status:** brainstorm / design backlog. Nothing here is committed work.
> **Baseline:** the ENSIA ML project (Spring 2025–2026), *Adaptive Exam Preparation System using Active Learning*.
> **Scope of this document:** ML core, data, analysis, visualisation, custom input, platform features, UI/UX, engineering, and a few deliberately ambitious swings.

---

## 0. Honest baseline — what actually exists today

Before proposing anything, it's worth writing down precisely what ships, because several of the most valuable improvements are about **closing the gap between the notebook and the running system**, not about inventing new things.

| Layer | What exists | Where |
|---|---|---|
| Level estimation | `HistGradientBoostingClassifier`, 21 fixed features, 3 classes (beginner / intermediate / advanced) | [ml_service.py](../backend/services/ml_service.py) |
| Question selection | **Rule-based difficulty targeting** — thresholds on `overall_acc` and `error_streak` pick a target difficulty value, then the nearest-difficulty item wins | `select_next_question` |
| Stopping rule | min 8, max 20, length-conditional confidence threshold (0.75–0.85) | `should_stop` |
| Difficulty labels | proficiency-weighted wrong-rate, fixed cut points (≤0.30 easy, ≤0.55 medium, else hard), set manually through an admin endpoint | notebook §6.6, [admin_service.py](../backend/services/admin_service.py) |
| Item bank | Sanfoundry scrape (~18 MB CSV), 6 modules, MCQ only | [sanfoundry_all_quiz.csv](../data/quizzes/sanfoundry_all_quiz.csv) |
| Persistence | Supabase / PostgREST — `modules`, `quizzes`, `questions`, `students`, `sessions`, `answers` | [schema.sql](../backend/schema.sql) |
| Frontend | Next.js 14 App Router, Tailwind, 5 student pages + admin subtree, **zero charting dependencies** | [frontend/](../frontend/) |
| Evaluation | grouped CV, ablations, noise robustness, sensitivity analysis, 4 real datasets | [FINAL_NOTEBOOK.ipynb](../ai/research/FINAL_NOTEBOOK.ipynb) |

### The five honest gaps

1. **The active learning in the notebook is not the active learning in production.**
   [session_service.py](backend/services/session_service.py) calls `select_next_question(..., strategy="entropy")`, but `select_next_question` only branches on `"random"`. Everything else falls through to the same difficulty-targeting heuristic. The uncertainty / entropy / QBC comparison from notebook §5 — the literal centre of the project statement — never reaches a real student. **Closing this is proposal 1.1 and it is the single highest-value item in this document.**
2. **The model predicts a label, not an ability.** Three coarse buckets throw away most of the signal, can't be tracked over time, and make "you improved" impossible to say.
3. **Items are never calibrated from live data.** Difficulty is a static string set once by an admin. The platform collects exactly the data needed to calibrate items properly and then ignores it.
4. **Nothing is visualised in the product.** The notebook has excellent plots; the student sees a number out of a number and a coloured pill.
5. **The item bank is a scrape.** No provenance, no per-topic tagging beyond module, no distractor quality control, no duplicate detection, no explanations.

Everything below is ordered so that the gap-closing work comes first and the moonshots come last.

---

## 1. The ML core

### 1.1 Ship the real active learning loop (highest priority)

The project statement asks for uncertainty sampling, entropy-based selection, and query-by-committee. The notebook implements them. The server does not. Make `select_next_question` genuinely score every candidate item:

```
for each unanswered item q:
    for each possible outcome o in {correct, incorrect}:
        p(o | theta_hat, q)                       # from the item model
        features'  = compute_features(history + (q, o))
        posterior' = model.predict_proba(features')
    score(q) = E_o[ acquisition(posterior') ]
choose argmax score(q)
```

Concrete acquisition functions to implement and A/B against each other:

| Strategy | Score | Notes |
|---|---|---|
| **Expected entropy reduction** | `H(p) − E_o[H(p′)]` | The textbook information gain. Direct answer to "provide clear visualization of information gain" in the success criteria. |
| **Margin / least-confidence** | `1 − (p₁ − p₂)` on the posterior | Cheapest; already the notebook's best-behaved baseline. |
| **Query-by-committee** | vote entropy or mean JS-divergence across a bootstrap/bagged committee | The notebook found QBC best (33% reduction). The committee can be cached — train k=10 models once at deploy time. |
| **Fisher information (IRT)** | `I(θ̂, q)` for the 2PL item model | The psychometrically correct answer, and it is *O(1)* per item instead of two forward passes. See 1.2. |
| **Expected model change** | ‖∇θ L(q, o)‖ weighted by p(o) | Interesting to compare, rarely wins in practice, cheap to add once the loop exists. |
| **Thompson sampling over items** | sample θ from the posterior, pick the max-info item at that draw | Naturally handles exploration; pairs well with bandit content balancing (1.7). |

Non-negotiable constraints to layer on top of raw acquisition score, or the system will misbehave in production:

- **Exposure control** (Sympson–Hetter): cap how often any single item can be served, so the top-information items don't leak into every session and burn out.
- **Content balancing**: enforce a minimum spread across topics so a session doesn't become six questions about pointer arithmetic.
- **Enemy items**: never serve two near-duplicate items in the same session (needs the dedup work in 2.1).
- **Anti-frustration guard**: the existing `error_streak >= 3 → serve easy` rule is good pedagogy even when it is bad information theory. Keep it as an override, but make it a named, tunable policy rather than a magic number inside a branch.

**Performance note:** two `predict_proba` calls per candidate × ~100 candidates on every answer submission is real latency on a PostgREST round-trip architecture. Vectorise it: build one `(2·n_candidates, 21)` matrix and call the model once. That is a single `np.vstack` away and turns the loop from ~200 calls into 1.

### 1.2 Item Response Theory — calibrate the bank, estimate θ properly

This is the biggest conceptual upgrade available, and the notebook's own §15 names it as the recommended fix for its highest-severity limitation.

**Item model.** Fit a 2PL (or 3PL with a guessing floor — MCQ with 4 options has `c ≈ 0.25` structurally):

```
P(correct | θ) = c + (1 − c) · sigmoid(a · (θ − b))
```

- `b` = difficulty, on the same scale as ability, continuous instead of three buckets
- `a` = discrimination — *this is the parameter the current system is missing entirely*. A question everyone gets right or wrong regardless of ability carries no information and should never be selected, no matter what tier it is labelled.
- `c` = pseudo-guessing

**Ability estimation.** Replace the 3-class argmax with a posterior over θ:
- EAP (expected a posteriori) with an `N(0,1)` population prior — closed-form enough, and stable with as few as 5 responses.
- Report **θ̂ ± SE(θ̂)**, and stop when `SE(θ̂) < 0.3` — a principled, interpretable stopping rule that replaces the hand-tuned confidence ladder in `_CONFIDENCE_BY_LENGTH`.
- Map θ back to beginner/intermediate/advanced *only for display*, keeping the continuous value as the system of record. Backwards compatible with every existing UI string.

**Why this fixes real problems:**

| Current problem | IRT fix |
|---|---|
| Difficulty labels are heuristic, 60–70% human agreement (§15 limitation #1) | `b` is estimated from response data, not asserted |
| Can't compare two students who took different questions | θ is on a common scale by construction — that's the whole point of IRT |
| Can't say "you improved since last week" | θ trajectory across sessions |
| No sense of which questions are *worth asking* | `a` directly ranks item quality |
| Stopping rule is four hand-tuned magic numbers | stop at a target standard error |

**Migration path that doesn't break anything:** run IRT *alongside* the current model. Log both. Serve the HistGBM prediction to students while θ accumulates in a shadow table. Switch the selection policy to Fisher information first (lowest risk, biggest latency win), then the display, then retire the classifier or keep it as an ensemble member.

**Cold start for `b`:** seed with the existing easy/medium/hard label mapped to `b ∈ {−1, 0, +1}` under a wide prior, then let data move it. Nothing has to be thrown away.

### 1.3 Knowledge tracing — model *learning*, not just *level*

The current model answers "how good is this student right now?" It cannot answer "what do they not know?" or "are they getting better?" Both are more useful to someone preparing for an exam.

| Model | What it adds | Cost |
|---|---|---|
| **BKT** (Bayesian Knowledge Tracing) | Per-skill mastery probability with 4 interpretable parameters (`p_init, p_learn, p_slip, p_guess`). Directly gives a "you have mastered 7 of 12 topics" view. | Low — fits in an afternoon, runs in milliseconds. |
| **Performance Factors Analysis (PFA)** | Logistic model on per-skill success/failure counts. Often beats BKT, trivially interpretable, no HMM machinery. | Very low — it's a logistic regression. |
| **Elo / Glicko for students and items simultaneously** | Online, no retraining, handles cold start elegantly, updates in O(1) per answer. A shockingly strong baseline in the KT literature. | Very low, and it can run *inside the request*. |
| **DKT** (LSTM over the interaction sequence) | Learns skill relationships implicitly; strong at EdNet scale | Medium. Needs the live data flywheel (2.5) to be worth it. |
| **SAKT / AKT / SAINT** (attention over interactions) | Current SOTA family; AKT's monotonic attention models forgetting explicitly | High. Realistically a "we have a semester of live data" project. |

**Recommendation:** Elo first (it's ~30 lines and improves cold start immediately), PFA second (interpretable per-topic mastery for the UI), DKT/SAKT only once real interaction volume exists. Benchmark all of them on EdNet KT1/KT2, which is already sitting in [FINAL_SUBMISSION/data/real/ednet/](FINAL_SUBMISSION/data/real/ednet/) — that gives an apples-to-apples table for a report or a paper.

### 1.4 Calibration and honest uncertainty

The stopping rule depends entirely on `confidence` being meaningful. If the classifier is overconfident, sessions stop early and wrong — the worst possible failure mode for this product.

- **Reliability diagrams + ECE** per session length. The notebook has calibration analysis in §4.5; make it a monitored production metric, not a one-off cell.
- **Temperature scaling / isotonic regression** on a held-out split, applied before the confidence is ever compared to a threshold.
- **Conformal prediction** for a genuinely rigorous alternative: instead of "advanced, 82% confident", output a *prediction set* — `{intermediate, advanced}` at 90% coverage. When the set collapses to one label, stop. Distribution-free guarantee, easy to implement (split conformal on the existing validation data), and far more defensible than a tuned threshold.
- **Abstention**: let the system say "I need more evidence" and simply continue, rather than being forced into a label at `MAX_QUESTIONS`.

### 1.5 Multi-dimensional ability

One θ per student per module is a strong simplification. A student can be strong on data structures and weak on complexity analysis inside the same module.

- **Multidimensional IRT (MIRT)**, or more practically per-topic θ with a hierarchical prior shrinking toward the module-level θ. The hierarchical version is much easier to fit and handles sparse per-topic data gracefully.
- Unlocks the **mastery radar** visual (4.2) and topic-targeted remediation (6.2).

### 1.6 Response-time modelling done properly

`response_time_ms` currently produces four hand-crafted ratio features (`fast_correct_rate`, `fast_wrong_rate`, `slow_correct_rate`, `time_acc_corr`). The literature has a better instrument.

- **van der Linden's lognormal RT model**: each item has a time-intensity `β` and each student a speed `τ`, jointly estimated with the ability model. Turns raw milliseconds into a calibrated second latent trait.
- **Speed–accuracy tradeoff detection**: fast *and* correct is fluency; fast and wrong is guessing; slow and correct is effortful retrieval. These are pedagogically different states that deserve different next questions — currently they get identical treatment.
- **Rapid-guessing filter**: responses under a per-item threshold (say `< 0.3 ×` median time) are almost certainly not real attempts. Down-weight or exclude them from θ estimation — standard practice in operational testing, and it should directly improve the noise-robustness numbers from §6.5.
- ⚠️ **Watch the ablation.** §4.2 found time features contributed +19.7pp on synthetic data but only ~+3pp on real data. That gap strongly suggests the synthetic generator makes time *too* informative. Any RT modelling work should be validated on real data only.

### 1.7 Selection as a bandit / RL problem

A genuinely different framing, and a good source of novelty:

- Treat item selection as a **contextual bandit** where the context is the current knowledge state and the reward mixes information gain, learning gain, and engagement (did they finish the session?).
- Pure information maximisation optimises for *measurement*. A study tool should optimise for *learning*. These objectives diverge: the most informative item is one with a 50% success probability, but the ZPD literature and every well-tuned consumer learning product point at a ~70–80% success rate as where people stay engaged and learn most.
- **Explicit multi-objective selection:** `score = α · info_gain + β · learning_gain + γ · engagement`, with the weights exposed as an "Assessment ↔ Practice" slider in the UI. That single slider is a genuinely novel product feature and it falls straight out of the framing.
- **Offline RL / off-policy evaluation** on logged sessions, to compare policies without shipping them (see 3.2).

### 1.8 More models, better comparison

The project statement asks explicitly to test and compare different models. Broaden the table:

- **Currently:** LogReg, HistGBM. **Add:** Naive Bayes and Decision Tree (both named in the statement), Random Forest, XGBoost/LightGBM/CatBoost, SVM-RBF, a small MLP, and TabPFN (a transformer pretrained on tabular data — very strong at exactly this sample size, and a good talking point).
- **Sequence models on the raw interaction stream** rather than hand-engineered features — the fairest test of whether the 21-feature vector is actually earning its keep.
- **Ensembling / stacking** with a calibrated meta-learner.
- **Interpretability:** SHAP values per prediction, not just LogReg coefficients. Show the student *why* they were assessed as intermediate ("your accuracy on hard items was the deciding factor"). Both an XAI feature and a debugging tool.

---

## 2. Data — the most under-exploited asset in the repo

### 2.1 Mine the 18 MB Sanfoundry dump properly

[sanfoundry_all_quiz.csv](../data/quizzes/sanfoundry_all_quiz.csv) is a large scraped bank that the platform barely touches — six modules are wired up and the rest is dormant. It deserves a real pipeline:

- **Topic taxonomy induction**: embed every question (sentence-transformers or a hosted embedding model), cluster, and induce a topic hierarchy instead of relying on the scraped `topic` string. Gives per-topic mastery for free.
- **Automatic difficulty prediction from text**: train a regressor from question text → calibrated `b`. Features that work: readability, token count, negation count ("which is NOT"), code-block presence, distractor semantic similarity, stem embedding. Solves cold start for every new item and is a genuinely publishable mini-result.
- **Semantic deduplication**: cosine similarity over embeddings to find near-duplicates — essential for the "enemy items" constraint in 1.1, and for honest evaluation (duplicates spanning a train/test split leak).
- **Distractor quality analysis**: an option chosen by nobody is dead weight; a 4-option item with two dead distractors is really a 2-option item with `c = 0.5`. Flag and rewrite.
- **Answer-key validation**: an LLM-as-judge pass over the whole bank to flag likely-wrong scraped keys, ranked by confidence, for human review. On scraped data this will find real errors.
- **Provenance and licensing audit** — worth settling deliberately before anything is published or shared.

### 2.2 A data quality layer

A first-class `item_quality` table and admin surface:

| Signal | Action |
|---|---|
| Point-biserial correlation < 0.1 | Item doesn't discriminate — retire or rewrite |
| Discrimination `a` < 0.3 after calibration | Same, with a principled threshold |
| Distractor chosen by < 2% | Dead option — rewrite |
| Distractor chosen *more* by high-θ students | Miskeyed or ambiguous — flag urgently |
| Near-duplicate cosine > 0.95 | Merge |
| Median response time < 3s with high accuracy | Answer leaked or trivially googlable |

### 2.3 More datasets, and a real benchmark

Currently four datasets. Add the standard KT benchmark suite so results become comparable to published work:

- **ASSISTments 2009/2012/2017** — named in the project statement, still the field's default benchmark.
- **RiiiD / EdNet KT4** — larger slices with richer behavioural signals.
- **Junyi Academy** — ships an explicit prerequisite graph, which unlocks prerequisite-aware selection (6.2).
- **Eedi / NeurIPS 2020 Education Challenge** — has *misconception-labelled distractors*, exactly the data needed for misconception diagnosis (6.3).
- **Duolingo SLAM** — spaced repetition and forgetting curves with real half-life data.

Ship a `benchmarks/` folder with one script per dataset, each producing one row of a shared results table. The honest comparison the notebook does informally then becomes reproducible.

### 2.4 Better synthetic data

The synthetic generator carries a lot of weight in the current results, and §15 flags that the real-vs-synthetic gap is where the model's optimism lives.

- **Fit the generator to real data** instead of asserting `N(0.55, 0.18)` — estimate the proficiency distribution from EdNet/Lectu and sample from that.
- **Simulate learning within a session** — students currently hold a fixed proficiency for a whole session, which is unrealistic for a *study* tool and structurally prevents the model from ever detecting improvement.
- **Simulate realistic failure modes**: fatigue (accuracy decaying with session length), rapid guessing near the end, careless slips on easy items, question-order effects.
- **Adversarial students**: someone who googles every third answer; someone who always picks C.
- **Sim2real gap report** as a standing metric: train on synthetic → test on real, and treat that number as the honest headline instead of the synthetic CV.

### 2.5 The live data flywheel

The single most valuable dataset for this project is the one it doesn't have yet: **real students using the real platform**. §16 says exactly this. Build the infrastructure that makes that data usable the moment it exists:

- Log the **full decision trace** per answer, not just the answer: candidate set, acquisition scores, chosen item, model version, feature vector, posterior. Without this, off-policy evaluation (3.2) is impossible forever.
- **Randomised probe items**: with probability ε, serve a uniformly random item instead of the argmax. This costs almost nothing and it is the *only* way to get unbiased item calibration and unbiased policy evaluation out of an adaptive system. Skipping it is the most common and most expensive mistake in adaptive testing deployments.
- A consented, anonymised **research export**, so the dataset can eventually be published — a genuine contribution, since Algerian/ENSIA-curriculum interaction data doesn't exist publicly.

---

## 3. Analysis and experimentation

### 3.1 A proper simulation harness

The notebook's §5 comparison should become a reusable, runnable tool: a `sim/` package with a `Policy` interface, a `StudentModel` interface, and a runner producing the accuracy-vs-questions curve, AUQC, and steps-to-80% for any (policy, student model, item bank) triple. Adding a new strategy then becomes a subclass, not a notebook cell.

### 3.2 Off-policy evaluation

Once ε-random probes exist, evaluate a new selection policy on *logged* data before shipping it, using inverse propensity scoring or a doubly-robust estimator. This is how you avoid "we shipped a new policy and student outcomes quietly got worse for a month". It requires the decision-trace logging from 2.5 to have been in place from the start — which is why 2.5 is listed before this.

### 3.3 Online A/B experimentation

A small experiment framework: hash `student_id` into an arm, record the assignment, and measure:
- questions needed to reach a target SE (efficiency)
- session completion rate (engagement)
- score on a held-out fixed post-test (**learning** — the only one that really matters)
- return-within-7-days rate

### 3.4 Fairness and bias audit

Rarely done in student projects, and very much worth doing:
- **Differential Item Functioning (DIF)**: does an item behave differently for two groups of equal ability? Mantel–Haenszel or a logistic DIF test over the bank. English-second-language DIF is a genuine concern for a scraped English-language bank used by francophone/arabophone students.
- **Selection-policy fairness**: does the adaptive policy produce systematically shorter (and therefore less reliable) sessions for some subgroup?
- **Feedback-loop bias**: adaptive selection means weak students never see hard items, so hard items never get calibrated against them. Quantify it; ε-probes mitigate it.

### 3.5 Bias–variance, done visually

The statement asks explicitly for bias–variance analysis. Beyond the existing treatment: learning curves per model, validation curves over the key hyperparameters, and a full decomposition plot on the synthetic data — where the true label is known, so the decomposition is actually computable. A nice advantage of having a generator.

### 3.6 Drift monitoring

Once live: population θ distribution over time, per-item `b` drift (an item's difficulty drops the moment its answer leaks), feature-distribution PSI, prediction-distribution stability. Alert on drift rather than discovering it in a semester-end retrospective.

---

## 4. Visualisation — the biggest visible gap

The frontend has **no charting library at all**. Everything here is greenfield. Suggested stack: Recharts or visx for standard charts, D3 for the bespoke ones, a small motion library for transitions.

### 4.1 Live during the quiz

- **A confidence band that narrows as you answer.** A horizontal ability axis with a shaded credible interval that visibly tightens with each response. Makes the entire thesis of the project legible at a glance, and it is genuinely satisfying to watch.
- **"Why this question?"** — an expandable panel showing the current posterior and why the chosen item maximised expected information gain. Directly satisfies "provide clear visualization of information gain" from the success criteria, and it's an unusual, memorable feature.
- **Live difficulty indicator** — a subtle marker showing the question is calibrated to your current estimated level, so adaptivity is *felt* rather than asserted.
- **Question budget remaining** — a shrinking estimate ("~4 more questions") computed from the projected SE trajectory, instead of a fixed `n/20`.

### 4.2 On the result page (currently just `correct / total` and a pill)

- **Ability estimate with a credible interval**, not a bare label.
- **Mastery radar** across topics within the module.
- **Wright map / item-person map** — the classic IRT visual: items placed by difficulty along one axis with the student's θ marked on the same scale. Instantly communicates "here's what you can do, here's the next rung".
- **Per-question replay** — every question, your answer, the correct one, an explanation, your time vs the cohort median, and the item's difficulty.
- **What the model saw** — SHAP-style contribution bars for the level decision.
- **Comparison to cohort** — a distribution with your position marked (opt-in, anonymised).
- **Efficiency callout** — "we estimated your level in 9 questions instead of 20; a random quiz would have needed ~14." That is the project's headline result, finally shown to the person it's about.

### 4.3 Progress over time (needs a new page)

- **θ trajectory** per module with confidence ribbons across all sessions.
- **Forgetting curves** — predicted decay of per-topic mastery since last practice, doubling as the review scheduler's UI (6.1).
- **Streak / activity heatmap** (contributions-graph style) — cheap, effective, instantly understood.
- **Topic mastery over time** as a stacked area or a small-multiples grid.

### 4.4 Instructor / admin analytics

The admin subtree is currently import/export/simulate. Add a real analytics surface:

- **Item Characteristic Curves** per question with the empirical points overlaid — the single most useful plot for spotting a bad item.
- **Item information curves** and a **test information function** for a whole quiz.
- **Distractor analysis plot** — proportion choosing each option, binned by ability. A distractor whose curve *rises* with ability is a miskey, and this plot makes that obvious in one second.
- **Cohort heatmap** — students × topics, sorted, mastery as colour. Instantly surfaces the class-wide weak topic.
- **Live session inspector** — replay any session's decision trace step by step: posterior before, candidate scores, chosen item, posterior after. Invaluable for debugging the policy and for demoing the system.
- **Adaptive vs random comparison, live** — the demo-day requirement, as a permanent dashboard rather than a notebook cell.

### 4.5 Presentation quality

Whatever gets built should be **theme-aware (light/dark), colourblind-safe, responsive down to ~400px, and accessible** — every chart needs a text or table equivalent for screen readers. Charts as a first-class part of the design system, not bolted-on library defaults.

---

## 5. Custom input — let people bring their own material

This is where the project stops being a course artefact and becomes something people would actually use. A student preparing for an ENSIA exam doesn't want Sanfoundry C questions; they want questions on *their* lecture slides.

### 5.1 Document → quiz generation

Upload a PDF, a slide deck, or a set of notes; get a calibrated quiz.

```
upload → extract (PyMuPDF / docling)
       → chunk semantically
       → generate MCQs with an LLM (structured output, one item per chunk)
       → quality gate (answerable from the chunk alone? distractors plausible? no giveaway phrasing?)
       → predict difficulty from text (2.1)
       → seed the IRT prior, publish to the bank
       → recalibrate `b` from real responses as they arrive
```

Details that separate a demo from a product:
- **Grounding**: every generated item stores its source span, so the explanation can quote the slide it came from. Kills hallucination complaints and makes review possible.
- **Distractor generation is the hard part.** Good distractors encode real misconceptions. Generate them from *other* chunks of the same document, or from a catalogue of common errors — not from the model's imagination.
- **Human-in-the-loop review queue** before anything enters the shared bank.
- **Multi-format**: PDF, PPTX, DOCX, Markdown, plain paste, a YouTube lecture transcript, a photo of handwritten notes (OCR).

### 5.2 A question authoring studio

For instructors who want control: a proper editor with live preview, LaTeX/KaTeX for maths, syntax-highlighted code blocks, image upload, drag-to-reorder, bulk CSV import (already exists — give it a UI worthy of it), and an item-statistics panel showing live `a`/`b`/distractor behaviour as students answer.

### 5.3 New question types

The schema currently supports single-answer MCQ with up to six choices. Extending it is a schema change plus a scoring function per type:

| Type | Why it matters |
|---|---|
| Multiple-select | Partial credit; needs a polytomous IRT model |
| Numeric / short answer with tolerance | Removes the guessing floor entirely |
| **Code execution** (write a function, run tests) | Transformative for the CS modules. Sandboxed runner, test cases as the answer key. |
| Fill-in-the-blank / cloze | Great for definitions and syntax |
| Ordering / matching | Algorithms, protocol stacks, lifecycle steps |
| Diagram / hotspot | Click the right part of an architecture diagram |
| Free text graded by rubric | LLM-graded with a rubric and a confidence score; escalate low-confidence to a human |

Polytomous and partial-credit items need **Graded Response** or **Generalised Partial Credit** models — a natural extension of the IRT work in 1.2, not a separate system.

### 5.4 Curriculum import

- **QTI / Moodle XML / Canvas** import-export — makes the platform adoptable *by* an institution instead of a replacement *for* one.
- **Anki deck import/export** — an instant content library and an existing user base.
- **GIFT format** — the quickest text format for instructors to write in directly.

---

## 6. Platform features

### 6.1 Spaced repetition and long-term retention

The platform currently measures. It should also *teach*. This is the highest-leverage product addition in the document.

- **FSRS** (the modern, open, well-benchmarked scheduler — better than SM-2 and actively maintained) over items answered wrong or answered slowly.
- Predicted **retention curve per topic**, with a "review now" queue.
- **Interleaving**: mix topics in review sessions rather than blocking them — well supported by the learning-science literature and trivial once a queue exists.
- The forgetting model is itself an ML problem with a clean evaluation (predict recall probability at time t), so it fits the project's identity rather than diluting it.

### 6.2 Study plans and prerequisite-aware remediation

- Set a goal ("Operating Systems exam, 12 May") and get a generated schedule that allocates time weakest-topic-first and spaces reviews toward the date.
- **Prerequisite graph** over topics — hand-authored, or induced from data (if failing topic A predicts failing topic B, A likely precedes B). When a student fails a topic, route them to its *prerequisite* rather than to more of the same. This is what distinguishes a tutor from a quiz.

### 6.3 Misconception diagnosis

Distractors aren't noise — they're diagnostic. If a student consistently picks the option corresponding to "confuses pass-by-value with pass-by-reference", say *that* instead of "you got 6/10". Requires misconception-tagged distractors (author them, or mine them from Eedi per 2.3). A small feature with an outsized effect on how intelligent the system feels.

### 6.4 Explanations and feedback

Every item should have an explanation. Options, cheapest first: mine them from the Sanfoundry source where present, generate + human-review with an LLM, or crowdsource from students. Optionally add a **"why is my answer wrong?"** conversational follow-up, scoped strictly to that item and its explanation.

### 6.5 Modes

| Mode | Behaviour |
|---|---|
| **Assessment** | Current adaptive behaviour — minimise questions, maximise measurement precision |
| **Practice** | Target ~75% success rate, immediate feedback, unlimited length |
| **Exam simulation** | Fixed length, timed, no feedback until the end |
| **Speed drill** | Short per-item timer, fluency-focused |
| **Boss fight** | Only items at or above your current θ; a deliberately hard, gamified stretch session |
| **Review** | Driven purely by the FSRS queue |

The 1.7 multi-objective slider makes several of these the same code path with different weights.

### 6.6 Social and classroom

- **Classrooms**: an instructor creates a class, assigns quizzes, and sees the cohort heatmap (4.4).
- **Live quiz mode** (Kahoot-style) with a shared leaderboard — but adaptive per student, which no competitor does, and which makes for a very strong demo.
- **Head-to-head duels** on difficulty-matched items.
- **Leagues / leaderboards** ranked by θ *gain* rather than raw θ, so weak students can win. Ranking by raw ability is demotivating and self-reinforcing.
- **Shared community item banks** with upvotes and quality scores.

### 6.7 Integrity

If this is ever used for anything that counts:
- Response-time anomaly detection (answering a hard item in 2 seconds, repeatedly).
- Tab-blur / focus-loss signals during exam mode.
- Item exposure control (already in 1.1) doubles as leak protection.
- Randomised option order per session — cheap, effective, and it also improves data quality by breaking positional bias.
- Statistical answer-copying detection in cohort settings.

### 6.8 Accessibility, i18n, and reach

- **WCAG 2.2 AA**: keyboard-only quiz flow (1–6 to answer, Enter to submit — also just *faster* for everyone), screen-reader labels, visible focus states, no colour-only signalling, respect for `prefers-reduced-motion`.
- **Arabic and French locales** with RTL support. This is an ENSIA project; the reach argument is real.
- **PWA / offline**: cache a session's questions, answer offline, sync later. Enormously valuable on an unreliable connection.
- **Low-bandwidth mode** — the current stack ships a lot of JavaScript for what is fundamentally text and buttons.

---

## 7. UI/UX direction

The current design has an actual point of view (sand/clay/ink/pine palette, Space Grotesk + Source Serif) — more than most student projects manage. The problem isn't taste; it's that the *product surfaces* are thin: a result page showing one number, a dashboard that's a list, an admin area that's forms.

### 7.1 The quiz surface

- **One question, full attention.** No sidebar, no nav, no dashboard chrome. Everything that isn't the question is a distraction.
- **Answer with the keyboard.** Number keys select, Enter confirms, and the UI teaches this on the first question.
- **Meaningful motion**: the confidence band tightening after each answer; questions sliding in with direction encoding difficulty change (up = harder). Motion that *carries information*, not decoration — and gated on `prefers-reduced-motion`.
- **A timer that informs rather than pressures**: a subtle progress arc, not a red countdown, outside exam mode.
- **Instant, honest feedback** in practice mode — correct/incorrect with the explanation inline, no page transition.

### 7.2 The result page — rebuild entirely

Currently: `correct / total`, an accuracy percentage, and a level pill read out of `sessionStorage`. It should be the best page in the product, because it's the payoff. Content per 4.2; structure it as a scrollable narrative: headline result → ability with interval → how few questions it took → topic breakdown → question-by-question review → a concrete next action (into the review queue or the next topic).

⚠️ Also a correctness point: the predicted level currently comes from `sessionStorage`, so it vanishes on refresh or when the page is opened from history. It should be persisted on the session row and returned by `/sessions/{id}/result`.

### 7.3 Dashboard as a home, not a menu

Continue-where-you-left-off, the review queue with due counts, θ trajectory sparklines per module, weakest topic with a one-click drill, and the streak. The quiz catalogue moves *below* all of that.

### 7.4 System level

- **Dark mode** (currently light-only), with theme-aware charts.
- **Design tokens** — the palette lives in `tailwind.config.ts`, but semantic tokens (`surface`, `surface-raised`, `text-muted`, `accent`) would survive a dark-mode addition without a rewrite.
- **Component library discipline**: the `components/ui/` primitives are a good start; add Skeleton, EmptyState, Dialog, Tooltip, Tabs, and chart wrappers.
- **Empty and error states with personality** — currently `if (!result) return null;` renders a blank page, which reads as a bug.
- **Onboarding**: a 3-question calibration mini-quiz on first login to seed θ, framed as "let's find your starting point" rather than as a test.

---

## 8. Engineering and architecture

### 8.1 Security — fix first

- ⚠️ **`admin.py` routes are unauthenticated in router wiring** (noted in CLAUDE.md). Every admin route — import, export, role assignment, bulk student creation — is reachable without a token. `require_admin` already exists; wire it as a router-level dependency.
- Move admin authorisation off the `ADMIN_ALLOWED_EMAILS` env var and onto the `profiles.role` column that already exists.
- Rate limiting on auth and on answer submission.
- Verify the RLS policies actually cover the tables (the files exist; confirm they're applied and tested).
- Tighten CORS — the allow-list is hardcoded in [main.py](backend/main.py); move it to config.
- Answer keys must never reach the client before submission. Confirm `_serialize_question` strips `correct_answer`, and add a test that fails loudly if it ever stops doing so.

### 8.2 Testing — there is currently no test suite

- **Backend**: pytest + httpx against a test Supabase project or a local Postgres. Cover the session state machine hard — sequential enforcement, adaptive termination, double submission, out-of-range `response_time_ms`, resumption.
- **ML**: golden tests on `compute_features` (the 21-feature order is a documented invariant — pin it with a test, not a comment), monotonicity properties (more correct answers must never lower θ̂), and a model-quality gate in CI.
- **Frontend**: Playwright is already a dev dependency and currently unused. E2E the full flow: register → start adaptive → answer → result.
- **CI**: GitHub Actions running lint, types, tests, and a notebook smoke-execute so the deliverable notebook can't silently break.

### 8.3 ML lifecycle

- **Model registry** (MLflow, or a plain versioned artifact store plus a manifest). Right now the model is a `.pkl` at a path built with `parent.parent.parent` — fragile and unversioned.
- **Every prediction logs its model version.** Without this, any before/after analysis is guesswork.
- **Shadow deployment** for new models: compute both, serve one, compare offline.
- **Reproducible training**: `train_model_v4.py` exists at the repo root *and* in `FINAL_SUBMISSION/` — two copies, no pinned seed or environment manifest. One entry point, one config, a locked environment.
- **Share feature computation between training and serving.** The notebook and `ml_service.py` both compute features; any drift between them is a silent accuracy bug. Extract one package imported by both — the classic training/serving skew trap, and this repo is currently exposed to it.

### 8.4 Performance and data layer

- The adaptive path issues 4+ sequential PostgREST round-trips per answer (answers, all questions, quiz module, then updates). Batch them or move to a single RPC; cache the item bank per quiz in memory since it changes rarely. This is the dominant latency cost and the easiest win in the section.
- Add the `answers(session_id, answered_at)` composite index that the ordering actually needs.
- New tables implied by these proposals: `item_parameters` (a, b, c, se, n_responses, calibrated_at), `ability_estimates` (student, module, theta, se, at), `skills` + `question_skills`, `review_schedule`, `decision_traces`, `experiments`.
- Consider whether PostgREST is still the right choice — several proposals here (IRT calibration jobs, decision-trace writes, transactional multi-table updates) want a real driver or ORM. `DATABASE_URL` handling already exists in the codebase, so the door is open.
- **Background jobs** (Celery / arq / pg-boss) for nightly IRT recalibration, embedding generation, and quality-signal recomputation.

### 8.5 Observability

Structured logging with trace IDs, OpenTelemetry spans across the answer path, Sentry, and a small ops dashboard: p95 answer latency, model inference time, sessions started vs completed, and the fallback-to-rule-based rate — currently silent. If the `.pkl` goes missing in production *nothing surfaces that*; sessions just quietly get worse.

### 8.6 Deployment

A `docker-compose.yml` covering Postgres + backend + frontend so the whole thing runs with one command — this matters enormously for a project that will be handed to other people. Plus real migrations (Alembic or Supabase migrations; the `migrations/` folder exists but is ad-hoc), seed scripts, and a documented restore path.

---

## 9. Drastic swings

Deliberately ambitious. Each is roughly a semester of work, and each would make this unmistakably not a course project.

### 9.1 Generative adaptive testing
Don't select from a bank — **generate the item** at exactly the difficulty needed. An LLM produces an item conditioned on target `b` and topic; a difficulty predictor (2.1) verifies it before serving; real responses calibrate it afterward. Infinite non-repeating bank, perfectly targeted, no exposure problem. The research question — *can generated items be pre-calibrated accurately enough to use in adaptive selection?* — is open, current, and genuinely interesting.

### 9.2 A tutor, not a quiz
When a student fails a topic, the system doesn't just serve another question — it explains, works an example, asks a scaffolded sub-question, then re-tests. A dialogue agent with the knowledge state as context and an explicit pedagogical policy. The quiz becomes the assessment layer of a tutor rather than the whole product.

### 9.3 Learn the selection policy end to end
Instead of hand-designed acquisition functions, train a policy (RL over simulated students, then off-policy on logged data) whose reward is post-test learning gain. Compare it against every hand-designed strategy in 1.1. If a learned policy beats entropy sampling on *learning* rather than *measurement*, that's a paper.

### 9.4 An open ability API
Expose θ estimates as a portable, verifiable credential — an interoperable skill profile a student carries between courses and platforms. Positions the project as infrastructure rather than an app.

### 9.5 Curriculum-scale knowledge graph
Every ENSIA module as nodes in a prerequisite graph, with mastery propagating through it. "You're weak on complexity analysis, which is why the dynamic programming module is going badly." Combines 6.2, 1.5 and 2.1 into something no commercial tool does at an individual institution's curriculum level.

### 9.6 Multi-modal items
Diagrams, circuit schematics, code screenshots, audio. A vision model both generates and grades. Opens up modules the current text-only bank simply cannot serve.

---

## 10. Prioritisation

### Effort vs impact

| | **Low effort** | **High effort** |
|---|---|---|
| **High impact** | Wire admin auth · Real acquisition functions (1.1) · Persist predicted level · Elo cold start · Result-page rebuild · Vectorise selection · Explanations on items | IRT calibration (1.2) · Document→quiz (5.1) · Spaced repetition (6.1) · Visualisation suite (4) · Knowledge tracing (1.3) |
| **Low impact** | Dark mode · Streak heatmap · Keyboard shortcuts · Randomised option order | Multi-modal items · Open ability API · Learned policy (9.3) |

### Suggested phases

**Phase 1 — close the gap (weeks 1–4).** Wire admin auth. Implement real acquisition functions so production matches the notebook. Vectorise candidate scoring. Persist the predicted level server-side. Add the test suite and CI. *Outcome: the system finally does what the report says it does.*

**Phase 2 — measure properly (weeks 5–10).** IRT calibration pipeline, θ with credible intervals, SE-based stopping, decision-trace logging, ε-random probes, item quality dashboard. *Outcome: a psychometrically defensible engine, plus the data infrastructure everything after depends on.*

**Phase 3 — make it visible (weeks 8–14, overlapping).** The full visualisation suite, result-page rebuild, progress page, instructor analytics. *Outcome: the intelligence becomes legible — and demo-able.*

**Phase 4 — make it useful (weeks 12–20).** Document→quiz, spaced repetition, per-topic mastery, explanations, study plans. *Outcome: something a student would choose to use with nobody making them.*

**Phase 5 — pick one swing.** Generative adaptive testing (9.1) has the best novelty-to-feasibility ratio, and it composes with everything in phases 2–4.

### Ten quick wins, in order

1. Add `require_admin` to the admin router — one line, closes a real hole.
2. Persist `predicted_level` / `confidence` on the session row; stop reading them from `sessionStorage`.
3. Make `select_next_question` actually honour its `strategy` argument.
4. Vectorise candidate scoring into a single `predict_proba` call.
5. Emit a warning-level metric when the model falls back to rule-based — it's silent today.
6. Randomise answer-option order per session.
7. Keyboard shortcuts in the quiz (1–6, Enter).
8. Skeleton and empty states instead of `return null`.
9. A golden test pinning the 21-feature order.
10. Elo ratings for students and items, updated in-request — the best accuracy-per-line-of-code in this entire document.

---

## 11. Research questions worth writing up

1. Can LLM-generated items be pre-calibrated accurately enough, from text alone, to be used in adaptive selection without prior response data?
2. Does information-maximising selection help or hurt *learning* compared to ZPD-targeted (~75% success) selection? Measurement and pedagogy have been assumed to align; they may not.
3. How large is the sim2real gap for synthetic-student-trained adaptive policies, and which generator assumptions cause most of it?
4. Does the DM construct-validity finding (quiz scores overestimate exam preparedness by +27pp, r = 0.14) replicate on other cohorts? A genuinely publishable negative result, and §7 already has it half-done.
5. Does the feedback loop of adaptive selection systematically bias item calibration, and how large must ε be to correct it?
6. Does per-topic hierarchical θ beat single-θ by enough to justify the sparsity cost at realistic session lengths?

---

## 12. Notes and open questions

- **Item bank licensing.** Sanfoundry content provenance should be settled before anything is published or opened up. Generating an original bank via 5.1 may be the cleaner long-term path anyway.
- **Privacy.** Everything in 2.5 and 6.6 involves student data. Consent, anonymisation, retention, and deletion should be designed in rather than retrofitted — especially if the research export ever happens.
- **Scope discipline.** This document is deliberately over-generated. The realistic advice is Phase 1 + Phase 2 + *one* item from Phase 4. A system that measures properly and does one useful thing well beats a system that half-does twelve.
- **The strongest single narrative** for taking this further: *"we replaced heuristic difficulty labels with a calibrated IRT bank, replaced a 3-class classifier with a continuous ability estimate, and shipped the active learning strategies that were previously only simulated — then showed on live data that it needs fewer questions than the course-project version."* That's a coherent story, it's directly continuous with the existing work, and every piece of it lives in Phases 1–2.
