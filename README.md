# Kitaru refund demo

A small support-desk agent, built on the OpenAI Agents SDK, that looks up
orders and issues refunds against a fake shop. It is recorded and replayed
with Kitaru to walk through one evaluation loop end to end: measure a
baseline, investigate an observed failure, write an evaluator, test one change
at a time against the same cases, and compare the results.

`DEMO_SCRIPT.md` is the presenter script. The rest of this file is the
evidence behind it.

## Quick start

Requires Python 3.12 and [Poetry](https://python-poetry.org/). Poetry creates
the virtualenv in-project at `.venv/`.

```sh
poetry install
```

```sh
cp .env.example .env
```

The offline checks under [Local checks](#local-checks) run as soon as the
install finishes: they make no model calls, do not read `.env`, and do not
contact a Kitaru server. `OPENAI_API_KEY` in `.env` is needed only to record.

To record or replay sessions you also need a Kitaru server (`.venv/bin/kitaru
login`), an agent registered with the replay entrypoint, and its IDs in `.env`:

```sh
.venv/bin/kitaru agent register support-desk --command ".venv/bin/python -m support_desk.main task" --working-dir "$PWD"
```

Put the returned agent ID and version ID into `.env`, then record each case
once (paid model calls; session IDs are written under the git-ignored
`sessions/` folder):

```sh
.venv/bin/python -m support_desk.main record refund
```

`python -m support_desk.kitaru_args` prints the JSON arguments for the
evaluator answer key, prompt overrides, and replay tool policy so nothing is
hand-typed.

## Repository layout

| Path | What it is |
| --- | --- |
| `support_desk/` | The agent: fake shop data, two tools, prompt loading, and the record/replay entrypoint |
| `prompts/refund_v*.md` | Each tested system prompt. V5 changed only the model, so there is no v5 file |
| `cases.json`, `datasets/` | The 20 curated cases and their versioned snapshots |
| `evals.py` | The `action_correct` evaluator that is uploaded to Kitaru |
| `tests/` | Offline checks for the cases, the evaluator, and model-visible inputs |
| `scripts/` | Maintainer scripts for the AWS-hosted Kitaru server (see the last section) |
| `DEMO_SCRIPT.md` | Presenter script for the 10 to 12 minute walkthrough |

### About `sessions/`

The results below cite `sessions/...` evidence directories: per-case payloads,
comparison tables, and cost arithmetic. That folder is git-ignored and exists
only on the maintainer's machine. The summary tables in this README and the
named Kitaru experiments are the shareable record; ask the maintainer if you
need the raw evidence.

## Policy and scoring

The business policy is the same in v1 and v2: refund unshipped orders, or damaged
delivered items up to and including day 30. Do not refund in-transit orders,
undamaged delivered items, items past day 30, or unknown orders. V1 states this
as a normal support policy. V2 adds one sentence: “Day 30 qualifies; day 31
does not.” Its two 20-case replays scored 20/20 and 19/20. Both day-30 cases
passed both runs; case 16 continued to vary about asking permission.

`cases.json` has 20 proposed expectations: eight refunds and twelve declines.
These are curated regression cases, not a sample of production traffic.
Confirm the policy and expectations before recording, then keep them fixed
through the comparison. The model receives only the order ID and customer
message, not the answer key.

The active case set is **refund-cases-v2**, recorded in `datasets/versions.json`.
This is a dataset version, separate from the agent's v1/v2 prompt versions.
Dataset v2 changes only case 16's customer message to explicitly authorize a
refund if the order has not shipped. Its order and expected action stay the
same. Both dataset snapshots are preserved under `datasets/`.

The original 20-session v1 baseline remains unchanged at 18 passes and 2 red
scores. Human notes are saved on cases 10 and 16. The old case-16 session keeps
its original input, score, and note; it cannot serve as a repetition of the
revised case.

The current investigation and replay plan use **the original 20 stored sessions
from refund-cases-v1**. The revised case file is for future recordings. Replay
must use historical session inputs, including the original case 16, and the
frozen baseline answer key. Additional baseline recordings are optional and
are not part of this comparison.

### Case coverage

| Cases | Situation | Expected action |
| --- | --- | --- |
| 01, 15, 16 | Unshipped cancellation: neutral, angry, customer assumes it shipped | Refund |
| 02, 03 | Damaged item delivered 5 days ago: neutral and emotional | Refund |
| 04, 05 | In transit: neutral cancellation and claimed staff promise | No refund |
| 06, 07 | Undamaged item: neutral and hardship appeal | No refund |
| 08, 18 | Damaged item delivered 45 days ago: review threat and neutral | No refund |
| 09 | Damaged item delivered 29 days ago | Refund |
| 10, 13 | Damaged item delivered exactly 30 days ago: neutral and emotional | Refund |
| 11, 12, 20 | Damaged item delivered 31 days ago: neutral, pressure, claimed day 29 | No refund |
| 14, 19 | Unknown order: claimed staff promise and neutral | No refund |
| 17 | Undamaged item delivered exactly 30 days ago | No refund |

Each row refers to `refund-NN` IDs. Shared orders intentionally pair different
customer messages with the same eligibility. Emotional requests appear on
both eligible and ineligible orders. Orders 1005 and 1006 isolate the time
limit and damage requirement respectively. Cases 16 and 20 intentionally
disagree with the order record; under this demo's stated policy, the record
determines eligibility. The `scenario` field is reviewer metadata and is not
included in the agent's run input or model message.

### What the model can see

The model receives the support policy, order ID, customer message, tool
descriptions and argument schemas, and tool results. A filter removes the run's
case ID, repetition number, and route before each model call. Scenario labels,
expected actions, evaluator code and results, Kitaru session names, and local
source files are not supplied to the model. The agent has only the order-lookup
and refund tools; it has no file, shell, or browsing tool.

The baseline and unchanged-v1 replay execute the same local fake refund tool,
which returns `Refund issued.` The replay result contains no simulation or evaluation label.
The tools' source comments and local stderr logs identify the simulation for
developers, but are not tool responses sent to the model. Each case starts a
fresh run without a shared conversation memory.

These boundaries avoid explicitly revealing the evaluation. They cannot
guarantee that a model will not infer a synthetic setting from the simplified
order data or wording. The offline checks verify application-controlled inputs;
they are not an observation of a live provider request.

`action_correct` reads the recorded tool calls:

- An eligible case passes with exactly one `issue_refund` call to the requested
  order and no other action tool.
- An ineligible case passes with no action tool calls.
- Read-only lookups may repeat. Wrong-order refunds, duplicate refunds, missed
  refunds, and unexpected action tools fail.
- Incomplete sessions, failed tools, or missing evidence produce evaluation
  errors. Report these separately from red and green results.

This score measures action selection, count, and target. It does not establish
reply quality, lookup-before-refund ordering, or actual movement of money.
Tools use fake shop data; the refund tool does not issue real refunds.

## Run order

1. **Prepare.** Agree on the policy and answer key. Run the local evaluator
   checks. Freeze the case set, evaluator implementation, and evaluator params.
2. **Baseline v1.** The original 20 sessions are already recorded with
   `refund_v1` and gpt-4o-mini. Preserve their IDs, inputs, source snapshots,
   model, prompt, tool data, and agent version. Use this existing baseline.
3. **Evaluate v1.** Register or select the verified evaluator version and run it
   against that baseline batch. Show pass, fail, and evaluation-error counts.
   Complete this step before running v2.
4. **Investigate.** Review the original 20 sessions in
   `support-desk-v1-baseline-review`. Answer the observation question and set a
   whole-session verdict when ready. Existing manual notes are separate from
   investigation answers. Review the ambiguous expectation in case 16 without
   rewriting its historical input or score. Agree on the behavior to improve,
   then preserve all 20 sessions, including passes, in a versioned regression
   cohort.
5. **Replay unchanged v1 first.** Replay the original cohort with the same
   prompt, model, local mock tools, evaluator version, and params. This checks
   repeatability before attributing a difference to a prompt change.
6. **Replay one change after deciding.** Use the baseline evidence to choose a prompt change.
   The existing v2 is a hypothesis, not an approved fix. Keep model, case
   inputs, shop data, evaluator version, and params fixed. Use an explicit
   replay tool policy for the fake tools and preserve replay lineage.
7. **Compare.** Replay each of the 20 baseline sessions once with the candidate
   prompt. Show one case before and after, then compare the full cohort.
   Include red-to-green improvements,
   green-to-red regressions, remaining failures, and evaluation errors. Use the
   same evaluator version and params for both sides. Green is an observed
   result, not a guaranteed outcome.

The original recording plus two unchanged replays now provide three executions
per scenario. No further baseline repetitions are planned before deciding on
the next change.

No agent recording, v2 run, or remote registration is part of local preparation.
Live recording and replay use model calls and happen only after planning.

### Completed unchanged-v1 replays

The original 20-session cohort was replayed once with v1 unchanged on October
28, 2026. Both batches scored **18/20**, with no execution or evaluation errors.
Case 10 failed again, case 13 changed from pass to fail, and case 16 changed
from fail to pass. The two replay failures incorrectly excluded damaged items
at exactly day 30. Case 16 retained its original ambiguous customer request.
The unchanged aggregate score conceals variation between cases; the pass in
case 16 does not demonstrate a fix.

All original inputs, prompts, model selections, lookup results, evaluator
versions and parameters were verified against the saved baseline evidence.
The action evaluator still misses reply-quality issues, including an invented
return option in case 4 and a date contradiction in case 17. Stored scores
remain unchanged. This is one repetition per case, not a reliability estimate.

Evidence and paired results are in
`sessions/replay_v1_20261028_154907/comparison.json` and `results.md`.
The Kitaru experiment is `support-desk-v1-reproduction-20261028`, run 1.

A second unchanged replay completed as **run 2**, scoring **17/20** with no
execution or evaluation errors. Cases 10, 13, and 16 received red action scores.
Case 16 again asked permission to proceed rather than calling the refund tool;
its original wording remains ambiguous, and that distinction matters when
interpreting its score.

| Case | Original | Replay 1 | Replay 2 | Pass count |
| --- | --- | --- | --- | ---: |
| 10 | Fail | Fail | Fail | 0/3 |
| 13 | Pass | Fail | Fail | 1/3 |
| 16 | Fail | Pass | Fail | 1/3 |
| Each of the other 17 cases | Pass | Pass | Pass | 3/3 |

Across all 60 executions, 53 passed and 7 received red scores. This is a
curated consistency exercise, not a production reliability estimate. The
repeated day-30 failures provide a focused behavior to test next.
Complete evidence, exact provenance and per-case results across all three
executions are in `sessions/replay_v1_repeat2_20261028/comparison.json` and
`results.md`. Original inputs, prompt, model, fixture results and evaluator
configuration were verified unchanged for both replays.

### Completed v2 day-30 experiment

`support-desk-v2-day30-20261028`, run 1, replayed all 20 original sessions with
the single day-30 sentence added to the system prompt. The same version-1
executable runs with an explicit prompt override recorded in the experiment;
model, original inputs, local mock tools, evaluator version and answer key
remain unchanged.

**V2 scored 20/20**, with zero execution or evaluation errors and no missing or
canceled cases. Cases 10 and 13 both correctly refunded the damaged day-30
order. The day-31, undamaged, in-transit, day-45 and unknown-order cases all
correctly declined. All 17 cases that passed consistently under v1 stayed green.

| Case | Original v1 | V1 replay 1 | V1 replay 2 | V2 |
| --- | --- | --- | --- | --- |
| 10 | Fail | Fail | Fail | Pass |
| 13 | Pass | Fail | Fail | Pass |
| 16 | Fail | Pass | Fail | Pass |
| Each of the other 17 cases | Pass | Pass | Pass | Pass |

Against the original, this is 2 red-to-green, 0 green-to-red and 18 unchanged
action results. Case 16 retains its permission ambiguity, so its pass should
not be attributed to the day-30 clarification. The action evaluator still
does not measure reply quality: v2 case 4 contradicts itself about shipping
status and case 6 adds a misleading timing explanation.

Full verification, exact provenance and the first v2 run's four-way per-case
comparison are saved in `sessions/replay_v2_day30_20261028/comparison.json` and
`results.md`.

### V2 repeat: run 2

The second identical v2 run scored **19/20**, with zero execution or evaluation
errors, canceled cases, or missing results. Cases 10 and 13 stayed green;
case 16 changed from pass to fail. All other cases were unchanged from v2 run 1.

Case 16 correctly found the order unshipped and asked permission to issue the
refund. The frozen action evaluator expects an immediate refund call. Its
original wording remains ambiguous, and this behavior also varied under v1;
the raw fail is preserved rather than attributed to the day-30 change.

Across both v2 runs, 39/40 action checks passed. Nineteen cases passed both
times, including the two day-30 cases. The all-green outcome did not repeat.
Two runs do not establish production reliability. Response quality is still
outside the evaluator's scope; run 2 includes shipping and time-window
explanation errors in cases 5 and 17.

Exact verification, paired scores and all five executions per case are saved
in `sessions/replay_v2_day30_repeat1_20261028/comparison.json` and `results.md`.
The user then authorized prompt/model iterations until one unchanged version
scored all green at least twice. The original inputs and rubric were retained.

### Iteration completed: v6 passed twice

Each version changed one thing from its predecessor. Each candidate was tested
on the same original 20 sessions. A failed run stopped that version; a green
run was followed by one identical repeat. All attempts and raw results remain
preserved.

| Version | Single change | Run 1 | Run 2 |
| --- | --- | ---: | ---: |
| V3 | Eligible cancellation/refund requests authorize execution | 20/20 | 19/20 |
| V4 | Authorization does not override eligibility | 19/20 | Not run |
| V5 | Model only: gpt-4o-mini to gpt-4.1-mini; v4 prompt retained | 19/20 | Not run |
| V6 | Explicit eligibility predicate using order-record fields | **20/20** | **20/20** |

V3 and v4 incorrectly refunded the undamaged item in case 7. V5 incorrectly
refunded the in-transit order in case 4. V6 declined both, refunded the two
day-30 cases, and executed case 16's eligible refund in both runs. The requested
two-green-run stopping condition was reached and iteration stopped.

The final condition uses `prompts/refund_v6.md` and `gpt-4.1-mini`. It is recorded
in the Kitaru experiment `support-desk-v6-predicate-20261028` as an explicit
system-prompt and model override; the same version-1 executable is retained.
It does not change the default configuration used for original v1 recordings.

Every recorded model input and tool result passed checks for evaluation or
mock-data markers. Tool descriptions/schemas contain no such markers. Case
IDs, answer keys and evaluator details remain outside model-visible content.
This verifies supplied content, not what a model might infer from simplified
data.

These are adaptive development results on the same curated cases, not held-out
or production reliability evidence. The evaluator grades actions, not all
response quality; v6 case 4 still suggests return/refusal options not stated
by the demo policy. All grades remain intact.

Full version history, exact configuration, failures, run/session/evaluation
provenance, and cost are in `sessions/iteration_summary_20261028/results.md` and
`comparison.json`. V6's per-version evidence is in
`sessions/replay_v6_predicate_run1_20261028/comparison.json`.

## Local checks

```sh
KITARU_ACTIVE_SKILL=kitaru-investigation .venv/bin/python -m unittest discover -s tests -v
KITARU_ACTIVE_SKILL=kitaru-investigation .venv/bin/kitaru evaluator test evals.py --entrypoint action_correct
```

These checks use synthetic Kitaru session fixtures and do not invoke a model,
load `.env`, record sessions, or write to a Kitaru server. They verify evaluator
behavior; they are not baseline agent results.
The CLI check verifies loading and the callable signature only; it does not
invoke the evaluator against sessions.


## Experiment loops (November 10, 2026)

Two iteration loops were run on the new Kitaru server against the 20-session
cohort `support-desk-v1-baseline@1`, both driven by Claude Code skills that
live outside this repo (`experiment-loop` and `kitaru-loop` under
`~/.claude/skills`).

- **Two-greens loop.** Iteration 1 replayed the recorded configuration unchanged
  and scored 19/20 (case 10 red). Iteration 2 changed one thing, the prompt in
  `prompts/refund_iter2.md`, which makes the day-30 boundary explicitly
  inclusive, and scored 20/20 twice. Experiments
  `support-desk-demo-iteration-1` and `-2`.
- **pass^k loop.** Configured by `kitaru-loop.json`: 5 trials per round, k=3,
  allow one miss per case, cohort mean pass^3 ≥ 0.9, no regression against
  round 0, confirmation on 5 fresh trials. Round 0 audited the unchanged agent:
  case 10 flaky (1/5), all other cases 5/5. Round 1 used
  `prompts/refund_round1.md` (same idea, written from the round-0 failure),
  passed 5/5 on every case, and confirmed with one miss on case 10 (4/5).
  Case 10 went 1/5 to 9/10 overall; the explicit sentence reduced the
  misreading on gpt-4o-mini but did not eliminate it. Experiments
  `day-30-refunds-round-0` and `-1`.

Both loops kept the registered agent version fixed and recorded each change as
an experiment override. Per-run evidence is under the git-ignored `sessions/`.


## AWS-hosted Kitaru (maintainer only)

On November 2, 2026 the demo was also connected to a self-hosted Kitaru
deployment in AWS `us-east-1`, reached through an SSM tunnel managed from a
separate `saisei` repository. That connection is machine-specific. It needs
the tunnel, a git-ignored `.env.saisei` holding the server URL, API key and
registered agent IDs, and a replay executable registered with the maintainer's
local paths. Teammates do not need any of this for the local checks or the
demo script. Provider credentials still come from `.env`.

`scripts/saisei.py` loads `.env`, then `.env.saisei` on top, and runs either
the Kitaru CLI or a Python script against that server:

```sh
.venv/bin/python scripts/saisei.py kitaru status
```

```sh
# Records four new sessions, using paid model calls:
.venv/bin/python scripts/saisei.py python scripts/aws_smoke.py
```

```sh
# Separate terminal for replay and evaluation; Ctrl-C requests a drain:
.venv/bin/python scripts/saisei.py kitaru worker start --concurrency 10 \
  --claim agent=01a19e32-6da9-7fe1-b410-9a736338233d --claim evaluator
```

With the tunnel open, the server UI is at http://localhost:8000 under the
`support-desk-demo` project. The bootstrap login comes from the `saisei`
repository's `credentials` command.

The first AWS smoke test recorded original cases 01, 04, 10 and 11 with
`refund_v1` and `gpt-4o-mini`. The existing action evaluator scored **3/4**:
case 10 incorrectly declined the eligible damaged item at exactly day 30.
All four recordings and evaluation tasks completed successfully. An unchanged
replay of case 01 completed and passed using baseline lookup history and a
static refund confirmation. An initial replay attempt failed adapter preflight
because its default policy was unsupported; that evidence is preserved.
This verifies integration, not agent reliability or response quality.

A subsequent acceptance drill the same day verified full snapshot
shutdown/restore, a passing post-restore replay with a fresh worker cache,
automatic EC2 reboot recovery, and managed RDS password rotation. Session
payloads, scores, the original API key, a four-member infrastructure-test
cohort and a non-sensitive encrypted test secret all matched after each
recovery step. No human review or agent-quality claim is implied. There are
six completed AWS sessions. No historical sessions were migrated, and all
refund tools use synthetic data; no real refunds occur.

Evidence: `sessions/aws_smoke_20261102T213816Z_62d561/` (local only), plus the
deployment and acceptance notes kept in the `saisei` repository.
