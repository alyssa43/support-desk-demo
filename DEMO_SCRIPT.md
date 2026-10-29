# Kitaru evaluation loop: forward deployed engineer demo

**Length:** approximately 10–12 minutes, plus questions.  
**Audience:** an engineering team considering Kitaru for an existing agent application.  
**Format:** italicized directions are presenter cues. Quoted paragraphs are spoken.

## Before recording

- Use the saved sessions and experiment results. The walkthrough does not require launching new jobs.
- Open the `support-desk` agent, its original sessions, and `support-desk-v1-baseline-review` investigation.
- Have `support-desk-v1-reproduction-20261028`, `support-desk-v2-day30-20261028`, and `support-desk-v6-predicate-20261028` ready under Experiments.
- Open `support_desk/main.py`, `support_desk/specialists.py`, `evals.py`, and `prompts/refund_v6.md` in the editor.
- Keep `sessions/iteration_summary_20261028/results.md` available for the complete version history.

## 1. Frame the customer problem

*Start on the support-desk agent’s Sessions page.*

> “Imagine this is the support agent inside your application. It looks up an order, decides whether a refund is allowed, and can call a refund tool.
>
> Your team changes a prompt or a model. The question is: did that change improve the behavior you care about, and did it break anything that already worked?
>
> I’m going to show how we answer that with Kitaru: inspect recorded sessions, agree on the expected behavior, turn those situations into repeatable checks, replay a change, and compare the results.
>
> Today’s example uses 20 curated support requests and isolated mock order tools. In your application, we would start from the agent and business rules you already operate.”

## 2. Explain where Kitaru connects to their application

*Switch to `support_desk/main.py` and point to the `KitaruRunner` call in `record()`.*

> “The first integration point is the place your application invokes its agent.
>
> This application uses the OpenAI Agents SDK, so we use Kitaru’s packaged OpenAI Agents adapter. We still build the agent, supply its instructions, and define its tools in our application. The adapter wraps that invocation, records the supported model and tool activity, and returns the SDK’s native result.
>
> In a production integration, I would register your agent identity and executable version, configure the Kitaru endpoint and a dedicated service credential, and connect this wrapper at the existing agent call.”

*Show this simplified illustration; do not change the running application during the demo.*

```python
# Existing OpenAI Agents invocation
result = await Runner.run(agent, customer_message)

# Invocation with Kitaru's OpenAI Agents adapter
runner = KitaruRunner(agent_version_id=registered_agent_version_id)
result = await runner.run(agent, customer_message)
```

> “Before choosing an integration, I would check your actual framework and invocation mode. Streaming, approvals, persistent conversation state, and tool interception all affect what we can faithfully capture and replay. This demo uses a supported, non-streaming invocation.
>
> If you already collect traces in a supported system, such as Langfuse or LangSmith, we can import a bounded set to begin reviewing behavior. Replay also needs a runnable agent entrypoint and an integration that supports the changes we want to test.
>
> For a framework without suitable support, we would assess its public hooks and build a project-local adapter if those hooks expose the required behavior.”

## 3. Use a session to explain the failure

*Return to Sessions. Open original case 10, order 1008. Show the input, lookup result, policy, and final response.*

> “A session is one recorded agent execution. Here we can inspect the customer request, the model calls, the tools and their arguments, the tool results, and the final response.
>
> This customer received a damaged shirt. The order lookup says it was delivered exactly 30 days ago. Our existing policy allows damaged-item refunds at 30 days or fewer.
>
> The agent looked up the right order, but denied the refund. The evidence gives us a specific failure: it excluded the inclusive boundary of the refund window.
>
> In your application, I would use this same process to connect a surprising response to the underlying tool evidence and your business policy. That is how we choose a useful behavior to measure.”

## 4. Turn the observation into an evaluation

*Open the investigation, then `evals.py` and the baseline cohort.*

> “An investigation organizes review around the recorded evidence. We can record observations, the expected behavior, and uncertainty.
>
> One useful example was case 16. The customer asks whether they can still cancel and get a refund. Some runs issued the refund; others asked for confirmation. That raises a product question about authorization. The trace alone cannot decide your intended policy.
>
> Our review here was AI-assisted, with that provenance retained. In a customer engagement, I would have your domain owners confirm the behavior we intend to reward before treating a score as an acceptance signal.
>
> Once that expectation is explicit, we can write an evaluator. This one, `action_correct`, checks whether an eligible request produced exactly one refund for the requested order, and whether an ineligible request produced no refund.
>
> It examines recorded actions. A response that says ‘I refunded you’ still fails if the refund tool was never called. Missing evidence or execution errors are reported separately.
>
> For this check, deterministic Python is sufficient. In production, your evaluator should match the outcome you need to establish. A tool call alone would not establish that money actually moved; that would require evidence from the payment system.
>
> We preserved all 20 original sessions in a versioned cohort, including the passing cases. That gives us a fixed population for finding both improvements and regressions.”

## 5. Establish variation before changing the agent

*Open `support-desk-v1-reproduction-20261028`. Show both runs and their Sessions views.*

> “The original v1 batch scored 18 out of 20. Before changing anything, we replayed the same original cohort twice with v1 unchanged.
>
> Those runs scored 18 out of 20 and 17 out of 20. The aggregate score alone hides which cases changed, so we inspect the paired results.
>
> Case 10 failed all three v1 executions. Case 13 varied on the same day-30 boundary. Case 16 varied between asking permission and executing the refund.
>
> That matters when we interpret the next experiment: one green result can happen without an implementation change. We want to understand the variation before attributing an improvement to our prompt.”

*Presenter note: a run’s Sessions view shows replay scores alongside the original with labels such as “Pass was Fail.” The two-run Compare view shows the selected runs’ scores and their delta. Its original-session reference does not include a separate original-score column.*

## 6. Explain exactly what replay executes

*Show `task()` in `support_desk/main.py` and the registered command below.*

```sh
.venv/bin/python -m support_desk.main task
```

> “An experiment holds the candidate change, the evaluator configuration, and the tool policy. A run applies that configuration to a particular cohort version and executable agent version.
>
> For each original session, Kitaru creates a replay task. A worker in our execution environment claims that task and launches this registered command.
>
> Our `task()` function reads the input Kitaru supplies, builds the agent, and invokes `KitaruRunner`. The adapter applies supported prompt or model overrides, executes the agent through its framework, and records a new result session. An evaluator task then scores that result.
>
> These are fresh executions from the stored original inputs. They make new model calls. They do not restore an arbitrary process checkpoint, conversation memory, or historical external world state. If your agent needs additional state, we need to make that state explicit or establish a narrower replay boundary.
>
> The server coordinates the work and stores the session evidence. The worker executes our code in an environment we control.”

*Briefly point to `support_desk/tools.py`.*

> “Tool behavior is an explicit part of the experiment. Our lookup reads fixed local data, and our refund tool returns a confirmation without moving money. We deliberately execute those isolated tools again.
>
> In your production application, a replay could otherwise send another email, modify a record, or issue another payment. We would choose a tool policy before execution: for supported tools, that could mean recorded results, configured static responses, or isolated staging implementations. We would also define what happens when a replay makes a new tool call that has no recorded match.
>
> Adapter support determines which of those policies are available. We verify that support against your installed integration before running the experiment.”

## 7. Walk through the evaluation loop and its regressions

*Open the v2 experiment, show its prompt change, and then show the saved version-history table.*

> “Our first hypothesis was small: make the day-30 boundary explicit. V2 added one sentence: ‘Day 30 qualifies; day 31 does not.’ The model, cohort, order data, and evaluator stayed fixed.
>
> Its first run scored 20 out of 20. Its repeat scored 19 out of 20. The day-30 cases stayed green; the remaining red result was the authorization ambiguity in case 16.
>
> We then iterated one change per version. V3 clarified authorization, which made case 16 execute in both runs, but a later run improperly refunded an undamaged item. V4 clarified that authorization does not override eligibility; that case still failed.
>
> V5 changed only the model. It passed that case, but incorrectly refunded an in-transit order. That is why we keep the whole cohort: a candidate can fix the example we are watching and regress somewhere else.
>
> V6 kept that model and added one exact eligibility condition using the order-record fields, explicitly distinguishing ‘in transit’ from ‘not shipped.’”

| Version | One change from the previous condition | Observed results |
| --- | --- | --- |
| V1 | Original policy and `gpt-4o-mini` | Original: 18/20; unchanged replays: 18/20, 17/20 |
| V2 | Explicit day-30 inclusion | 20/20, 19/20 |
| V3 | Clarify authorization for eligible cancellation/refund requests | 20/20, 19/20 |
| V4 | Clarify that authorization cannot override eligibility | 19/20 |
| V5 | Change only the model to `gpt-4.1-mini` | 19/20 |
| V6 | Add an exact eligibility condition | **20/20, 20/20** |

*Open `support-desk-v6-predicate-20261028`. Show both runs, then case 10’s lookup and refund call.*

> “V6 passed all 20 action checks in two consecutive runs. Here is the original damaged day-30 order: the agent now looks it up and issues the refund. The previously observed ineligible-refund cases also pass in both runs.
>
> We stopped at that predeclared condition. Every failed candidate remains in the history. We kept the original inputs and evaluator unchanged throughout.
>
> These are results on the same development cases we used to guide the changes. In your application, I would assess the frozen candidate on separate cases before making a broader reliability claim. Our action evaluator also leaves reply quality unmeasured.”

*Presenter note: v1–v6 are the tested prompt/model conditions. This demo reused one executable agent version and recorded candidate differences as experiment overrides. Avoid describing them as six separately registered executable agent versions.*

## 8. Describe the production rollout you would own as the FDE

*Return to the application code. Speak directly to the viewer’s engineering team.*

> “For your application, I would make the first integration deliverable one complete recorded request that your team can inspect and one bounded replay that your team can explain.
>
> First, we identify the agent invocation and agree on what counts as one session in your product. We select a supported adapter or trace-import path, register the executable, and decide what payloads may be stored. Prompts and tool results can contain customer data, so access, capture, and retention decisions belong in the integration design.
>
> Next, we verify the request-path behavior. In this OpenAI Agents integration, session creation is an awaited dependency before the agent runs. A recording failure after the agent finishes can raise an error that carries the native result. We must handle that deliberately; blindly retrying could repeat a business action.
>
> Live recording connects directly from the application to Kitaru. Workers handle the separate replay and evaluation work. We would deploy those workers with the required application build, dependencies, credentials, and controlled tool access, and scope them to the work their environment can safely execute.
>
> Then we review a bounded set of your sessions, agree on one important behavior, create a versioned cohort, and establish the evaluator. We run the unchanged agent first, then test one candidate and inspect every regression.
>
> As the workflow matures, your CI can start an experiment, wait for its results, and apply your team’s explicit release criteria. We would pin the executable build and dependencies as well as the cohort and evaluator versions. Your delivery process owns the deployment decision.”

## 9. Close with the value and next step

*Finish on the two completed v6 runs.*

> “The useful result is a repeatable connection between a production behavior, an explicit expectation, and the effect of a change.
>
> We can show where the original agent failed, what changed, which other cases regressed, and what passed when we repeated the candidate.
>
> For your team, I would start with one agent, one important workflow, and a bounded set of reviewed sessions. We would leave you with a recorded integration, a controlled replay entrypoint, and a regression cohort you can reuse for the next change.”

## Optional questions

### “Does the agent know it is being evaluated?”

> “The model receives the support policy, customer message, order ID, tool descriptions, and tool results. Our filter removes case labels before model calls. The evaluator and answer key run separately. We verified that no evaluation or mock-data markers were supplied in the recorded model inputs or tool responses. That describes what the application sends; it cannot prove what a model might infer.”

### “What did the custom adapter do in your other project?”

> “The entrypoint is the code that builds and invokes the application’s agent. The adapter connects the framework’s execution to Kitaru’s recording and supported replay controls. This demo has a small application entrypoint and a packaged OpenAI Agents adapter. For another framework, we would first check the supported integrations; custom adapter work is needed when those routes do not expose the required boundary.”

### “Does 20/20 mean this is ready for production?”

> “It means these action checks passed on this cohort in these runs. We would separately assess new cases, explanation quality, real business outcomes, and operational behavior according to your release criteria.”

### “What did this evaluation loop cost?”

> “The saved model-usage estimates total about 7.1 cents for all 200 replay sessions across 10 runs. That excludes hosting and the original recordings. The action evaluator is deterministic Python and makes no model calls.”

## Presenter reference

| Screen or file | Use |
| --- | --- |
| Original session `01a18487-b691-7b42-9756-24cd7a312fd6` | Case 10: original day-30 denial |
| Investigation `support-desk-v1-baseline-review` | Observations, uncertainty, and AI-assisted review provenance |
| Cohort `support-desk-v1-baseline@1` | All 20 original inputs, fixed for every comparison |
| `support-desk-v1-reproduction-20261028` | Two unchanged v1 replays |
| `support-desk-v2-day30-20261028` | First prompt hypothesis and its repeat |
| `support-desk-v6-predicate-20261028` | Final condition, two 20/20 runs |
| V6 run 1 session `01a184e0-cad4-72f1-bc46-2b3ada933856` | Case 10’s successful refund trace |
| `support_desk/main.py`, `task()` | The registered replay entrypoint |
| `support_desk/specialists.py`, `show_model_only_message()` | Separates model-visible customer content from case metadata |
| `evals.py`, `action_correct()` | The deterministic action evaluator |
| `sessions/iteration_summary_20261028/results.md` | Complete version history and costs |

## Technical basis

The script is grounded in this project’s code, saved session/evaluation evidence,
and the local Kitaru documentation checked while drafting:

- `docs/book/adapters/openai-agents.md`: native result handling, supported replay overrides/tool policies, invocation limits, recording errors.
- `docs/book/adapters/record-in-production.md`: registration, service credentials, in-band recording, payload handling and production failure behavior.
- `docs/book/concepts/workers.md` and `docs/book/deploy/workers.md`: execution environment, task subprocesses, scoping and worker lifecycle.
- `docs/book/guides/tool-policies.md`: tool sources and miss behavior; adapter-specific limits must be verified.
- `docs/book/adapters/importer-backed.md`: imported-trace wrappers have a different interception/override boundary.

Those documentation paths are relative to `/Users/alyssaeaster/kitaru`. They are
presenter references, not claims that every framework supports the same features.
