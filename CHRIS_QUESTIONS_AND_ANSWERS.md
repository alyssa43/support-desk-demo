# Chris’s Kitaru questions, answered

Prepared October 29, 2026, from the supplied meeting transcript.

Questions below are lightly paraphrased for clarity, with repeated questions
merged and timestamps retained. Spellings such as “Kitaroo,” “Kotaro,” “Katara,”
and “Guitar Row” are normalized to **Kitaru** where the context supports it.
Conversational checks such as “Does that make sense?” are omitted. Questions
asked by Zach or Jack are not attributed to Chris.

**Evidence boundaries:** The architecture answers use the local Outside the
Sandbox source code, the refund demo’s saved results, and current official
documentation. I did not inspect the running DigitalOcean service, SSH into EC2,
or verify that its deployed commit matches the local checkout. Statements about
the meeting’s deployment describe what was reported there. Suggested team
routines are recommendations, not verified Kitaru customer practices.

## What Chris was really asking

“Show me exactly how this connects to my application, what I must do to use it
successfully, and how it produces better behavior. Then explain the operating
responsibilities and the product’s boundary.”

The distinction he kept making was between **how a coding assistant helped set
something up** and **what code, dependencies, processes, and data flows exist
after setup**.

## A. Architecture and integration

### 1. Is the Kitaru recorder an SDK, installed software, or code embedded in the VPS?

**Asked:** 12:34:07; 12:35:09; 12:37:58; 13:01:48–13:04:44.

**Answer:** “In Outside the Sandbox, it is Python code inside my backend, using
the Kitaru Python package. My custom `kitaru_recording.py` collects the application’s
model/tool activity, then sends it to the Kitaru server through its API. It is
not a separate operating-system monitoring agent on the VPS.”

The application starts the recorder’s sender thread during FastAPI startup.
Its code is independent of the separate Raindrop integration.

**Verified in:** [custom recorder](/Users/alyssaeaster/ai_incident_explainer/backend/kitaru_recording.py:214),
[FastAPI startup](/Users/alyssaeaster/ai_incident_explainer/backend/server/app.py:31),
[dependencies](/Users/alyssaeaster/ai_incident_explainer/backend/pyproject.toml:20).

### 2. What was asking you setup questions? Who is “they”?

**Asked:** 12:34:37–12:35:27.

**Answer:** “The coding assistant was asking integration questions while following
Kitaru’s setup instructions. Those questions helped choose the entrypoint,
recording boundary, and replay behavior. The finished integration is the Python
code and dependencies I can show you; the setup conversation is not part of
the production request path.”

The transcript does not preserve the original setup questions, so I cannot
reconstruct their exact wording.

### 3. What is the application, what is the agent, and what is the recorder?

**Asked:** 12:37:41; 12:39:02.

**Answer:** “Outside the Sandbox is the application. Its RAG assistant is the
agent behavior we are recording. The recorder observes that behavior. In the
Kitaru dashboard, an ‘agent’ is also the registered identity that groups its
sessions and versions. Claude Code is a separate coding assistant used during
development.”

Keeping these names separate prevents the word “agent” from referring to three
different things in the same explanation.

### 4. Does the application call OpenAI, or does the recorder call OpenAI?

**Asked:** 12:37:58–12:38:31.

**Answer:** “The application’s `LanguageModel` calls OpenAI. The recorder wraps
that activity and stores observations. In a replay, the application’s answer
code executes again and makes fresh model calls.”

**Verified in:** [the actual Responses API call](/Users/alyssaeaster/ai_incident_explainer/backend/assistant/llm.py:90).

### 5. Where do the sessions go? Is Neon Postgres part of Kitaru?

**Asked:** 12:37:58–12:38:36; 13:05:22–13:05:58.

**Answer:** “The application sends session data to the Kitaru server. The server
handles its storage; the application is not directly inserting session rows
into Kitaru’s database. In the meeting, my Kitaru server and its Postgres were
reported as two containers on EC2. Neon is the application’s separate RAG
database, used for source documents and retrieval.”

**Verified in:** [session API writes](/Users/alyssaeaster/ai_incident_explainer/backend/kitaru_recording.py:418),
[application database/tracing explanation](/Users/alyssaeaster/ai_incident_explainer/backend/README.md:47).
The live EC2 storage configuration was not audited here.

### 6. Which parts are production, local, and remote? Does the browser view mean Kitaru is running locally?

**Asked:** 12:33:49; 12:36:27; 12:39:39–12:39:48.

**Answer:** “In the architecture I described, the production app runs on
DigitalOcean, the Kitaru server runs on EC2, and I access its UI through my
laptop’s browser. The replay worker can run on my laptop using a development
checkout. A browser displaying a page does not mean that server is running on
the laptop.”

The intended flows are:

```text
Live request:
Browser → DigitalOcean application → model/tools
                         └→ custom recorder → Kitaru API on EC2 → Kitaru storage

Local replay:
Kitaru task → local worker → local application checkout → model/controlled tools
                                └→ new session → Kitaru API → comparison
```

### 7. How does replay integrate with the local application? What actually runs?

**Asked:** 12:39:54; 12:51:21–12:52:18.

**Answer:** “The worker claims a replay task and launches the registered
application command. For Outside the Sandbox, that entrypoint is
`python -m kitaru_replay` from `backend/`. It loads the recorded input and replay
configuration, validates them, runs the existing answer code, and records the
new session.”

Your custom entrypoint checks model permissions and tool policies before model
calls. It supports eligible v2 generated-turn recordings; older v1 recordings
and prewritten suggested answers are explicitly rejected as replay inputs.

**Verified in:** [replay entrypoint and its boundary](/Users/alyssaeaster/ai_incident_explainer/backend/kitaru_replay.py:1),
[input validation](/Users/alyssaeaster/ai_incident_explainer/backend/kitaru_replay.py:63),
[execution](/Users/alyssaeaster/ai_incident_explainer/backend/kitaru_replay.py:210).

### 8. So nothing needed to be installed on the laptop?

**Asked:** 12:52:20–12:52:26.

**Answer:** “There are dependencies installed in the project’s Python
environment, including Kitaru and its worker support, plus the application’s
own dependencies. I do not need the Kitaru server running locally, but I do need
a working runtime, code, credentials, and a worker to execute local replays.”

**Correction to the meeting:** Saying “nothing was installed” was inaccurate.
The project declares `kitaru[cli]` and a development dependency with the worker
extra. These can be installed without a system-wide or root-level deployment.

GitHub can host the code, but its website does not execute the replay by itself.
A GitHub Actions runner or another configured worker supplies the runtime.

**Verified in:** [project dependencies](/Users/alyssaeaster/ai_incident_explainer/backend/pyproject.toml:20),
[worker dependency](/Users/alyssaeaster/ai_incident_explainer/backend/pyproject.toml:34).

### 9. Does every branch need a `kitaru_replay.py` file?

**Asked:** 12:52:43–12:53:04.

**Answer:** “A branch normally inherits the replay entrypoint along with the
rest of the repository. We do not recreate it for every branch. Its filename
is our choice; the requirement is that the registered command can invoke the
agent correctly.”

For example, the refund demo uses `python -m support_desk.main task`, whereas
Outside the Sandbox uses `python -m kitaru_replay`.

### 10. Does Kitaru automatically choose or check out the right Git branch?

**Asked:** 12:43:05; 13:05:58–13:06:15.

**Answer:** “Our integration does not automatically check out a branch. We or
our CI select the checkout or build, start a compatible worker there, and
register/select the agent execution configuration. The worker runs that
command in that environment.”

Your custom entrypoint records the current Git commit and changed backend files.
That is provenance, not automatic branch switching. An agent-version number
also does not by itself freeze a mutable local working directory.

**Verified in:** [Git-state recording](/Users/alyssaeaster/ai_incident_explainer/backend/kitaru_replay.py:148),
[Kitaru worker execution model](https://docs.zenml.io/kitaru/core-concepts/workers).

### 11. Could LSBot use this on Railway or Heroku, or is root access required?

**Asked:** 13:01:48–13:04:44.

**Answer:** “The SDK integration is application code, so root access to the
underlying host is not inherently required. A suitable application runtime,
dependencies, environment variables, and network access to Kitaru are the main
requirements. The replay worker can run separately from the live app.”

Railway supports persistent services and background workers. That makes the
deployment pattern plausible, but we still need to inspect LSBot’s framework,
streaming behavior, and deployment before declaring its integration supported.
That inspection was not performed here. [Railway compute documentation](https://docs.railway.com/build-deploy).

### 12. Specifically, what would I do to integrate LSBot?

**Asked:** 13:01:48; 13:05:22; 13:16:49–13:17:38.

**Answer:** “We would identify the agent entrypoint and framework, choose a
compatible adapter, configure the Kitaru server and service credentials, and
record one complete request. Then we would add a runnable replay entrypoint,
start a worker in a controlled environment, and verify one unchanged replay.
Finally, we would review failures, define a quality criterion, and build a
small regression cohort.”

That is an integration plan, not a claim that LSBot has already been integrated.
The OpenAI Agents wrapper in the refund demo is a concrete example; your custom
RAG adapter is another. [Production integration guide](https://docs.zenml.io/kitaru/adapters/record-in-production).

### 13. Is running repository code or evaluators an attack vector? Does it just use `eval`?

**Asked:** 12:53:07.

**Answer:** “Workers intentionally execute registered application commands and
evaluator code, so that code and whoever can configure it are trust boundaries.
The mechanism we inspected launches an entrypoint; it is not interpreting a
customer’s chat message as Python code.”

Use trusted builds, controlled job-creation permissions, scoped credentials,
and restricted worker environments. A safe tool policy also matters: replay
can repeat external writes if the integration permits them. Your custom
entrypoint already validates allowed models, inputs, parameters, and tool
policies; those checks are useful controls, not a complete security audit.

**Verified in:** [custom preflight checks](/Users/alyssaeaster/ai_incident_explainer/backend/kitaru_replay.py:89).

## B. Evaluation, cohorts, and the everyday workflow

### 14. Once integrated, does it record every session?

**Asked:** 12:36:27; 12:54:15–12:55:05.

**Answer:** “When enabled, our custom adapter attempts to record each `/chat`
answer that goes through its wrapper. This is a choice in our integration.
It does not guarantee that every attempted recording reaches the server.”

The current custom recorder has an in-memory queue with a default capacity of
100 sessions. A full queue or failed send logs a warning and can lose that
recording while allowing the answer to continue. This differs from the
packaged OpenAI Agents adapter’s in-band session-start behavior.

**Verified in:** [chat wrapping](/Users/alyssaeaster/ai_incident_explainer/backend/server/routes/chat.py:81),
[queue and drop behavior](/Users/alyssaeaster/ai_incident_explainer/backend/kitaru_recording.py:255).

### 15. Are recorded sessions already marked good or bad? What does “completed” mean?

**Asked:** 12:39:54–12:40:09; 12:42:35.

**Answer:** “Completed means the execution finished according to its recording
status. It does not mean the answer was correct. Quality judgments come from
review or evaluations stored alongside the session.”

A completed answer can violate policy. A failed execution and a failed quality
check are different outcomes and should be reported separately.
[Sessions](https://docs.zenml.io/kitaru/core-concepts/agents-and-sessions),
[evaluations](https://docs.zenml.io/kitaru/core-concepts/evaluators).

### 16. How did you get the baseline? What did you select in the UI?

**Asked:** 12:42:05–12:42:35.

**Answer:** “I selected the original sessions and saved their membership as a
cohort version. That defines which cases to use. To establish a measured
baseline, we also need results from a fixed evaluator with fixed parameters;
creating a cohort alone does not establish quality.”

In the older meeting, the selected population was 13 sessions. In the refund
demo it was the original 20 sessions, all evaluated with the same action check.
The older meeting’s five-session evaluation is addressed below. A cohort is
not automatically an answer key or a quality score.
[Cohort versions](https://docs.zenml.io/kitaru/core-concepts/cohorts).

### 17. Why were only five of the thirteen sessions evaluated?

**Asked:** 12:46:11–12:46:25; prompted by the discussion at 12:40:30.

**Answer:** “The transcript says thirteen were selected and only five were
checked, but it does not establish why. I would need the original evaluation
job and selection to explain that discrepancy. I should report the observed
result as a five-session evaluation, not a thirteen-session baseline.”

The newer refund demo avoids that ambiguity: all 20 selected cases were
accounted for in each completed run. This review did not reconstruct the old
five-session job or validate its original citation evaluator.

### 18. What is the point of replay? Can I change anything on a branch and rerun it?

**Asked:** 12:42:35–12:43:15; 12:44:24–12:44:41.

**Answer:** “Replay starts a fresh execution using a recorded session’s input.
We can run unchanged code to check reproduction, or test a specific code,
prompt, model, or parameter change and compare the result.”

Automatic overrides and tool substitutions depend on the adapter. They are not
universally supported. Historical external state is only controlled to the
extent our input/state handling and tool policy actually preserve it.
[Replay semantics](https://docs.zenml.io/kitaru/core-concepts/replay).

### 19. How can you show improvement without annotations?

**Asked:** 12:43:19–12:43:26.

**Answer:** “We need a trustworthy definition of better. It can come from
reviewed examples, an explicit business rule, or independent outcome data.
Human annotations are useful evidence, but every check does not require a
separate manual label on every session.”

For example, a known refund policy can support a deterministic action check.
For a subjective criterion, we need a clear rubric and evidence that the judge
agrees with informed reviewers. A replay by itself only gives us another result.

### 20. Who populated pass/fail, and what exactly does it mean?

**Asked:** 12:44:04–12:44:24; 12:44:44–12:45:15.

**Answer:** “The selected evaluator produces that result for a named criterion.
It means the session passed that check. It does not mean the whole answer is
good in every respect.”

The meeting described a citation check, whose exact implementation was not
verified here. Our refund demo’s `action_correct` checks action selection,
refund count, and target order. It does not grade explanation quality.
[Evaluator contract](https://docs.zenml.io/kitaru/core-concepts/evaluators).

### 21. Would a different but better answer fail because it changed? Is there an expected answer?

**Asked:** 12:44:44–12:45:02.

**Answer:** “Only if we wrote an evaluator that requires that exact answer.
A useful behavioral check can accept many different phrasings while requiring
the same important property: supported citations, the correct tool action, or
a valid refusal.”

Our expected refund actions are fixed, but the response wording is not. A
passing action score can coexist with a misleading explanation, which we
actually observed in the refund demo.

### 22. Does evaluating these properties always require AI?

**Asked:** 12:45:15–12:46:10; discussed again at 12:50:51.

**Answer:** “No. Use ordinary code when the criterion can be checked reliably
from structured evidence. Use a model judge when the criterion requires
interpretation, and validate that judge against trusted examples.”

Refund action/count/order checks need no model. Citation-format checks can be
deterministic, while whether a passage truly supports a claim may require
semantic judgment. A cheap yes/no model still needs a good rubric and testing.
[Evaluator inputs and results](https://docs.zenml.io/kitaru/core-concepts/evaluators).

### 23. How many ‘attributes’ or tests should an application have?

**Asked:** 12:46:11; 12:49:01; 12:55:34; 12:58:29; 13:01:48.

**Answer:** “There is no universal required number. I would start with one to
three important behaviors for one workflow, then add checks when actual
failures or business risks justify them.”

Separate **criteria** from **cases**. ‘Citations support claims’ is a criterion;
twenty recorded questions are twenty cases. One evaluator can check many cases.
Our refund demo used one action criterion across twenty cases and multiple
candidate runs. The starting count above is my recommendation, not a Kitaru
customer benchmark.

### 24. How would you organize hundreds of checks or sessions?

**Asked:** 12:49:01 and the surrounding test-suite discussion.

**Answer:** “Organize by application workflow and failure mode, with named
cohorts and clear evaluator names. Keep ownership, versions, and the expected
behavior explicit so the result tells a developer what to investigate.”

For LSBot, possible groups are source grounding, citation support, and refusal
behavior. Those are proposed groups, not an audit of LSBot’s existing suite.
Tags and cohorts help select cases; hundreds of criteria would also require
careful management beyond a flat scrolling list.

### 25. Do I rerun everything after every change, or use focused tests and a full CI suite?

**Asked:** 12:46:48–12:49:01; 12:55:34.

**Answer:** “Use a small, relevant cohort while iterating, including passing
counterexamples. Run a broader regression population at an appropriate CI or
scheduled checkpoint. Expand cohort versions as new failures are accepted.”

This matches Kitaru’s documented small-cohort/broader-scheduled-run pattern.
Your CI must inspect quality results and apply its own acceptance rules;
successful job execution alone is not proof that every evaluator passed.
[Regression-suite workflow](https://docs.zenml.io/kitaru/guides/regression-suite).

### 26. Is it bring-your-own-key? Which model runs? Is cost a factor?

**Asked:** 12:49:01–12:50:51.

**Answer:** “Our workers use our configured provider credentials. The agent’s
model is a candidate setting; a model-based evaluator can have its own model
and credentials. Deterministic evaluators make no judge-model calls.”

Cost depends on case count, repetitions, agent calls, tool/service costs, and
any model judging. Our 200 refund-demo replays made 477 model calls, with a
recorded estimate of **$0.07093205**, excluding hosting and the original batch.
That small example is not a production budget forecast.

**Verified in:** [our per-run cost calculation](/Users/alyssaeaster/support-desk-demo/sessions/iteration_summary_20261028/cost_summary.json).

### 27. How much automation should I expect? What do I do daily or weekly? Do I wait for email or Slack?

**Asked:** 12:58:29–12:59:07; 13:01:48–13:02:40.

**Answer:** “Recording captures executions. Evaluation, review, replay, and
notification are additional workflow decisions. Our demos did not configure
continuous grading or automatic email/Slack alerts.”

My proposed starting routine is:

- During development: run a focused regression cohort when the relevant behavior changes.
- Before merge: inspect the agreed quality checks and regressions.
- On a regular review cadence: sample new traffic and accepted failures, then update cohort versions as needed.
- After an incident: review its evidence promptly and preserve an appropriate regression case.

I would confirm supported scheduling/notification integrations and actual
customer routines with Alex before promising an out-of-the-box daily workflow.

### 28. What does successfully using Kitaru look like? How does this actually improve LSBot?

**Asked:** 13:01:48; 13:16:49–13:18:43; 13:26:00–13:27:25.

**Answer:** “Success is a demonstrated improvement in an important behavior,
with a useful regression check and understood trade-offs. For LSBot, we should
pick a real failure, agree on what should happen, measure the baseline, test
one change, and compare all selected cases with the same criterion.”

The refund demo demonstrates that loop: original day-30 failures became
passing actions, and v6 passed all twenty checks twice. It does not establish
that LSBot’s citation quality improved. That requires LSBot-specific evidence,
and a frozen candidate should also be checked on separate cases.

## C. Product boundaries, customers, and alternatives

### 29. What is Kitaru’s major use case? Who uses it? Are there customer case studies?

**Asked:** 12:55:34–12:57:25; 13:14:36.

**Answer:** “Its documented purpose is to investigate agent behavior and test
changes against recorded situations. Specific applications include preserving
incident cases, assessing prompt/model changes, and regression testing.”

The public case-study page I checked presents ZenML stories. I did not verify
a named Kitaru-specific customer story that answers Chris’s operating questions.
Ask Alex for a concrete customer walkthrough: application, team, criteria,
cohort sizes, cadence, cost, and release decision. Marketing examples are not
proof of that customer routine. [Kitaru product overview](https://www.zenml.io/product/kitaru),
[published case-study index](https://www.zenml.io/case-studies).

### 30. Is this owned by developers, Ops, SRE, or domain experts?

**Asked:** 13:06:15–13:11:46.

**Answer:** “A practical division is: platform/Ops owns hosting, access,
capacity, and recovery; application developers own integration and agent
changes; domain experts help define correct behavior; the release owner
approves deployment.”

That is a proposed responsibility split. It is not proof that all Kitaru
customers organize their teams this way or that the product is sold only to Ops.
The quality decision should have a named owner rather than disappearing
between the teams.

### 31. Where does Kitaru stop, and why does it stop there?

**Asked:** 13:06:15–13:11:46; 13:14:11–13:14:36.

**Answer:** “The verified workflow gives us sessions, review evidence,
evaluations, controlled reruns, and comparisons. Our team or automation uses
that evidence to decide what to change and release.”

Separating measurement from deployment is a reasonable design rationale, but
the founders’ intended boundary and customer reasons need confirmation from
Alex. We should not present a proposed architecture as his stated strategy.

### 32. Why not keep using AI to fix prompts until everything is green, then merge and deploy automatically?

**Asked:** 13:06:15–13:07:40; 13:11:46–13:14:36.

**Answer:** “We can automate a bounded improvement loop, but a green score only
proves the checks we defined. It can miss unmeasured behavior or overfit the
cases used during iteration. Merging and deploying add separate decisions.”

We actually ran that bounded loop in the refund demo: one change per version,
fixed cases and evaluator, stopping after two green runs. The coding assistant
orchestrated the iterations; Kitaru executed and preserved the experiments.
Nothing was automatically merged or deployed. V6 still offered unsupported
return options in some replies despite passing the action check.

### 33. Can you show a good product that was built through fully automatic ‘spin until green’?

**Asked:** 13:14:36–13:15:50.

**Answer:** “I do not have a verified customer example from this transcript or
the checked sources that establishes that claim. Our bounded demo shows that
iteration can reach its action-score target. It does not prove a fully
autonomous process reliably produces a good production product.”

The strongest honest demo is the before/after evidence, the regressions we
caught, and the limits of what our checks measured.

### 34. What changes in hosted Kitaru? Does it look the same?

**Asked:** 13:15:50–13:16:28.

**Answer:** “The core session/cohort/evaluator/experiment workflow remains.
The hosted plan supplies a managed dashboard and control plane. In the
documented standard pattern, replays still use your workers and model keys.”

We did not perform a hosted-UI parity audit in this review.
[Current pricing and hosting description](https://www.zenml.io/pricing).

### 35. Why pay instead of self-hosting? How much is it, and is it unlimited?

**Asked:** 13:16:28–13:16:46.

**Answer:** “The published Cloud price checked on October 29, 2026 is
**$39/month**, with **3 agents, 2 seats, and 90-day session retention**. Its
listed replay/evaluation usage is unmetered, but the plan has those limits.
Your model and worker compute costs remain separate.”

Paying buys hosted operation; self-hosting leaves that operation with your team.
Enterprise lists additional governance and capacity options. Confirm any
contract-specific requirements directly with the vendor.
[Official pricing](https://www.zenml.io/pricing).

### 36. Does the hosted version have an AI assistant that helps me get started?

**Asked:** 13:16:49–13:17:10.

**Answer:** “The documented onboarding path includes instructions and tools
for a coding assistant to help integrate and operate Kitaru. That is distinct
from an embedded assistant inside the hosted UI.”

I did not verify the current hosted UI’s embedded-assistant features. We should
ask or demonstrate that specifically rather than infer it from coding-agent
onboarding. [Project setup documentation](https://docs.zenml.io/kitaru/getting-started/setup).

### 37. Does Raindrop also have replay? How does it compare?

**Asked:** 12:55:05–12:55:33; 13:17:59–13:18:43.

**Answer:** “Yes. Raindrop’s Workshop is described as a local debugger with
replay/evaluation workflows. Its current product also describes issue
detection, Slack triage, and early-access simulations.”

Kitaru’s documented workflow emphasizes versioned cohorts, evaluators,
experiments, and worker-executed reruns. There is overlap; it would be inaccurate
to say Raindrop only monitors or Kitaru is the only product that replays.
The meaningful comparison is how each helps resolve the same application
failure. [Raindrop Workshop](https://www.raindrop.ai/workshop/),
[issue detection](https://www.raindrop.ai/issue-detection/),
[simulation offering](https://docs.raindrop.ai/simulate/).

### 38. What should the comparison with another product actually demonstrate?

**Asked:** 12:55:26; 13:17:59–13:19:15; 13:26:00–13:27:25.

**Answer:** “Use the same application problem and a small fixed set of cases.
Compare integration effort, recorded evidence, control of external tools,
quality measurement, regression visibility, cost, and the steps needed to
reach a reviewed improvement.”

Keep the candidate code/model and judging expectations comparable, and explain
any differences in replay state. That is a proposed evaluation protocol; we
have not yet run a controlled Kitaru-versus-Raindrop comparison. Chris explicitly
said hosted competitor versions were acceptable for that research.

## D. Deployment and the model project

### 39. How hard was the EC2 deployment? Was it just Docker?

**Asked:** 12:53:07–12:54:15.

**Answer:** “The meeting described one EC2 instance running the Kitaru server
and Postgres in separate containers, with network rules allowing the app and
laptop to reach the API. That was a small self-hosted deployment.”

A production deployment also needs deliberately configured authentication,
transport security, storage persistence, backups, and recovery. This review
did not verify the instance’s current ports, volumes, or configuration.

### 40. Is Postgres on EC2 or RDS? Can the database disappear with the instance?

**Asked:** 13:19:29–13:20:33; 13:21:18; discussed at 13:24:29–13:26:00.

**Answer:** “In the meeting, your database was reported on EC2; Vy and Jack
described RDS-based setups. The important questions are where the data is
persisted, what happens on instance termination, and whether restore works.”

“Never put a database on EC2” is too absolute. EC2 can use persistent EBS
storage; lifecycle settings and backups still matter. RDS manages more of the
database operation. Neither option removes the need to verify recovery.
[EC2 root-volume behavior](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/RootDeviceStorage.html).

### 41. Does RDS handle backups and failover? What about synchronization or another region?

**Asked:** 13:20:45–13:21:24; 13:19:29.

**Answer:** “RDS supports automated backups and point-in-time recovery when
configured. Multi-AZ DB-instance deployments maintain a synchronous standby
in another Availability Zone. Those address different recovery needs.”

Multi-AZ is not the same as cross-region disaster recovery, and a backup is
not the same as an immediately available standby. Define acceptable data loss
and downtime, configure the appropriate features, and test restoration.
[RDS backups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html),
[Multi-AZ deployments](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html).

### 42. What happens under burst traffic? Should we put a queue in front of Kitaru?

**Asked:** 13:21:54–13:22:42.

**Answer:** “First measure the actual bottleneck and failure behavior. Your
custom recorder already buffers finished sessions in a bounded in-memory queue
and sends them on a background thread. It can drop recordings when full or
when sending fails. That is buffering, not durable delivery.”

If durable capture is a requirement, a durable outbox or queue, retries,
idempotency, and backlog monitoring are possible design work. We have not
implemented or load-tested that architecture here. Adding Lambda or a queue
does not automatically solve ordering, duplicate delivery, or incomplete traces.

**Verified in:** [queue capacity](/Users/alyssaeaster/ai_incident_explainer/backend/kitaru_recording.py:33),
[submit/drop behavior](/Users/alyssaeaster/ai_incident_explainer/backend/kitaru_recording.py:255),
[sender failure handling](/Users/alyssaeaster/ai_incident_explainer/backend/kitaru_recording.py:384).

### 43. What features should our proposal/spec add beyond Kitaru Core?

**Asked:** 13:19:29; 13:27:38–13:29:11.

**Answer:** “Separate existing Kitaru capabilities, managed-deployment work,
and genuinely new product behavior. A proposal that reproduces the existing
feature set should not present it as newly built functionality.”

Possible research candidates include clearer review handoffs, owned triage
queues, budget visibility, and showing the original evaluator score in the
multi-run comparison view. The missing original-score column is a concrete
gap we observed in this demo’s UI. Other ideas require checking current
features and customer demand before calling them gaps or committing to build.

### 44. What would hosted-versus-open-source research add to the spec?

**Asked:** 13:27:38–13:29:11.

**Answer:** “It tells us which benefits are already supplied by the hosted
product and which responsibilities remain with a self-hosting team. The
current published plans distinguish managed hosting and enterprise governance
from the shared replay/evaluation loop.”

Then compare those benefits with the particular problem our proposed product
solves. A deployment/recovery offering can be legitimate scope, but additional
features need an evidenced user problem. [Published plan comparison](https://www.zenml.io/pricing).

### 45. How do we discover the right scope, roadmap, and customer workflow instead of inventing them?

**Asked:** 12:55:34; 13:14:11–13:14:36; 13:29:11–13:31:00.

**Answer:** “Use one concrete application to expose workflow problems, inspect
competitors against the same goal, and ask users or Alex about actual operating
practice. Bring specific evidence and questions, then distinguish their
answers from our proposed design.”

The most useful unanswered questions for Alex are: who owns quality review,
what triggers it, what gets replayed during development versus CI, what the
typical ongoing workload is, where the product intentionally stops, and which
real customer example illustrates that boundary. We have not contacted Alex
or any customers as part of this task.

### 46. How did you split two tabs inside one Chrome window?

**Asked:** 12:33:14–12:33:27.

**Answer:** “That is Chrome’s Split view. Right-click an active tab and choose
‘Add tab to new split view,’ or an inactive tab and choose ‘New split view with
current tab.’ It is a browser feature, separate from Kitaru.”
[Chrome’s instructions](https://support.google.com/chrome/answer/16971124?hl=en).

## Corrections to keep beside the demo

| Avoid saying | Say instead |
| --- | --- |
| “Claude set it up, so I do not know how it works.” | “The integration is this application code, this dependency, this API connection, and this worker command.” |
| “Nothing is installed on my laptop.” | “The project environment contains the application and Kitaru worker dependencies; the server is remote.” |
| “Kitaru selects my branch.” | “I or CI select the checkout/build; the worker executes the registered command there.” |
| “A completed session passed.” | “Execution status and evaluator results are separate.” |
| “Every production request is guaranteed to be recorded.” | “Our custom wrapper attempts capture; its bounded queue and send failures can lose recordings.” |
| “All Kitaru adapters behave like my custom recorder.” | “Our custom recorder buffers and fails open; packaged adapters have their own documented request-path behavior.” |
| “The hosted plan is unlimited and pays for the model.” | “It has published agent/seat/retention limits, and model/worker costs remain separate.” |
| “We proved LSBot improved.” | “The refund demo proves this bounded action-evaluation loop; LSBot needs its own criteria and evidence.” |
| “Green twice means production-ready.” | “These checks passed twice on these development cases; release decisions require broader evidence.” |

## A short answer you can give Chris

“My application calls OpenAI and runs the RAG logic. A custom Python integration
inside that application records each answer and sends its trace to the remote
Kitaru API. For local experiments, a worker runs `python -m kitaru_replay` in the
checkout I selected, using stored inputs and explicit tool policies. We review
the behavior, define the expected outcome, freeze the cases into a cohort, and
compare candidates with the same evaluator. The application team owns changes
and release decisions. The next step for LSBot would be to apply that loop to
one real quality problem rather than stop at demonstrating replay.”

## Source scope

- **Meeting evidence:** the supplied transcript; timestamps identify where each question or concern appeared.
- **Outside the Sandbox source:** `/Users/alyssaeaster/ai_incident_explainer/backend/`; current local implementation, not a live deployment audit.
- **Refund demo evidence:** `sessions/iteration_summary_20261028/`; saved sessions, evaluator results, prompt/model changes and cost arithmetic.
- **Product and platform facts:** official pages linked beside the relevant answers, checked October 29, 2026.
- **Still unknown:** original five-session citation-job selection/implementation, current deployed revision and infrastructure details, founder intent, real customer operating routines, and untested hosted/competitor behavior.
