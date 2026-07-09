# Requirements Document

## Introduction

This feature adds three tightly coupled subsystems to the UltraSwarm multi-agent framework:

1. **I/O Validator** — every structured (non-AI) agent declares an input schema and an output schema. The framework enforces both at call-time and return-time, providing rich validation errors instead of silent schema drift.

2. **Orchestrator Dependency Tracker** — the outreach orchestrator (and the supreme orchestrator) gain dependency-aware scheduling: before dispatching an agent the system checks whether any required output is already held in the shared context, and applies mutex-like critical-section locking to prevent two concurrent execution paths from computing the same result redundantly or causing races.

3. **Cost / Token Calculator** — a post-execution script (and lightweight in-process hook) measures tokens consumed and, for cloud models, translates them into USD cost; for local models it reports token counts and wall-clock time per agent and per session.

---

## Glossary

- **Agent**: Any class registered in `agents/registry.py` that exposes `run(input_data: dict) -> dict`.
- **BaseAgent**: The base class at `core/base_agent.py` from which skill-based agents inherit.
- **Cloud_Model**: A model whose API charges per token (e.g. Gemini 2.0 Flash via `GeminiClient`).
- **Local_Model**: A model running locally via `LocalLLMClient` (LM Studio / Ollama).
- **Cost_Calculator**: The new utility module responsible for tracking and reporting token usage and costs.
- **Dependency_Tracker**: The new component that records which agent outputs already exist in a shared context and coordinates access to them.
- **IO_Validator**: The new component that validates agent inputs and outputs against declared schemas.
- **Critical_Section**: A named, non-reentrant execution guard that prevents two concurrent calls from producing the same result twice.
- **Input_Schema**: A Pydantic `BaseModel` subclass (or `TypedDict`) declared by an agent to describe its accepted input fields.
- **Output_Schema**: A Pydantic `BaseModel` subclass (or `TypedDict`) declared by an agent to describe its produced output fields.
- **Orchestrator**: Either the domain-level `OutreachOrchestrator` (`agents/outreach/orchestrator_agent.py`) or the supreme `OrchestratorAgent` (`agents/managers/orchestrator_agent.py`).
- **Session**: A single top-level `Orchestrator.run()` invocation, identified by `session_id`.
- **Token_Report**: A structured object containing per-agent and per-session token/cost data.
- **SwarmState**: The `dataclass` in `agents/outreach/orchestrator_agent.py` holding per-contact execution state.

---

## Requirements

---

### Requirement 1: Agent I/O Schema Declaration

**User Story:** As a UltraSwarm developer, I want each structured agent to declare typed input and output schemas, so that schema contracts are explicit and enforceable rather than implied by documentation.

#### Acceptance Criteria

1. THE `BaseAgent` SHALL expose two optional class attributes — `input_schema` and `output_schema` — each accepting a Pydantic `BaseModel` subclass or `None`.
2. WHEN an agent class sets `input_schema` to a Pydantic `BaseModel` subclass and the agent's `role` attribute is NOT `"domain"` or `"manager"`, THE `IO_Validator` SHALL use that class to validate all input dicts passed to the agent's entry-point method before execution begins.
3. WHEN an agent class sets `output_schema` to a Pydantic `BaseModel` subclass and the agent's `role` attribute is NOT `"domain"` or `"manager"`, THE `IO_Validator` SHALL use that class to validate the dict returned by the agent's entry-point method before it is forwarded to the caller.
4. WHERE an agent does not declare `input_schema` or `output_schema`, THE `IO_Validator` SHALL skip validation for that agent without raising an error.
5. IF an agent's `role` attribute is `"domain"` or `"manager"`, THEN THE `IO_Validator` SHALL not enforce field-level schema validation; it SHALL instead verify only that the returned dict contains at least one key and includes a `"success"` key.
6. THE `IO_Validator` SHALL attach a `"validation_passed": true` flag to every successfully validated output dict before returning it to the caller, and a `"validation_passed": false` flag along with a `"validation_errors"` field listing field-level error messages when validation fails.
7. WHEN the `IO_Validator` fails validation on either input or output, THE `IO_Validator` SHALL abort further execution for that call (not invoke the agent for input failures, not forward the output for output failures) and return `"validation_passed": false` with a structured error message to the caller.

---

### Requirement 2: Input Validation Enforcement

**User Story:** As a UltraSwarm developer, I want validation errors to be caught early and surfaced clearly, so that agents never silently receive malformed data.

#### Acceptance Criteria

1. WHEN the `IO_Validator` detects that an input dict does not conform to the declared `input_schema`, THE `IO_Validator` SHALL raise a `ValidationError` aggregating all field violations — each containing the field name, the received value, and the expected type — before the agent's entry-point method is called.
2. WHEN a required field defined in `input_schema` is absent from the input dict, THE `IO_Validator` SHALL raise a `ValidationError` listing all missing required fields.
3. WHEN an input field value fails a Pydantic validator (e.g. out-of-range integer, wrong string pattern), THE `IO_Validator` SHALL raise a `ValidationError` that includes the Pydantic error messages as returned by Pydantic's `ValidationError.errors()`.
4. IF the `IO_Validator` raises a `ValidationError` on input, THEN THE `Orchestrator` SHALL catch the error, log it at `ERROR` level including the agent name and the full validation message, and return an `AgentResult` with `success=False` and `error` set to the validation message — without calling the agent.
5. WHEN the input schema contains 50 or fewer fields, THE `IO_Validator` SHALL complete validation within 5 ms of receiving the input dict.
6. WHEN the input schema contains more than 50 fields, THE `IO_Validator` SHALL complete validation within 20 ms of receiving the input dict.

---

### Requirement 3: Output Validation Enforcement

**User Story:** As a UltraSwarm developer, I want output validation to catch schema violations at the source, so that downstream agents never receive structurally invalid data.

#### Acceptance Criteria

1. WHEN an agent's entry-point method returns a value that is not a dict, THE `IO_Validator` SHALL raise a `ValidationError` stating the expected type (`dict`) and the actual type received, before the result is forwarded to the caller.
2. WHEN an agent's entry-point method returns a dict that does not conform to the declared `output_schema`, THE `IO_Validator` SHALL raise a `ValidationError` containing the field name, the returned value, and the expected type.
3. WHEN a required output field is absent from the returned dict, THE `IO_Validator` SHALL raise a `ValidationError` listing all missing required output fields.
4. IF THE `IO_Validator` raises a `ValidationError` on output, THEN THE `Orchestrator` SHALL log the error at `ERROR` level, replace the agent result with an `AgentResult` containing `success=False` and `error` set to the validation message, and return this `AgentResult` to the caller.
5. WHEN the output schema contains 50 or fewer fields, THE `IO_Validator` SHALL complete output validation within 5 ms of receiving the output dict.
6. WHEN an agent's output dict passes both schema validation and round-trip serialization (Pydantic model instantiation followed by `.model_dump()`), THE resulting dict SHALL contain the same field names, types, and values as the original validated output dict.

---

### Requirement 4: Outreach Agent Schema Definitions

**User Story:** As a UltraSwarm developer, I want every outreach swarm agent to have explicit schemas, so that the outreach pipeline has end-to-end type safety.

#### Acceptance Criteria

1. THE `AnalysisAgent` SHALL declare an `input_schema` requiring at minimum: `message: str` and an optional `context: OutreachContext` field.
2. THE `AnalysisAgent` SHALL declare an `output_schema` requiring at minimum: `Emotion` as a `Literal["Happy", "Curious", "Neutral", "Frustrated", "Angry"]`, `Interest_Level` as a `Literal["None", "Low", "Medium", "High"]`, `Intent` as a `Literal["Wants information", "Wants pricing", "Wants a demo", "Wants a meeting", "Rejecting", "Asking questions", "Requesting callback"]`, `Objections` as a `Literal["Too expensive", "Busy", "Already using another provider", "No budget", "Wrong contact", "Not interested", "None"]`, `Urgency` as a `Literal["Immediate", "Soon", "Future", "Unknown"]`, `Recommended_Next_Action` as a `Literal["Reply immediately", "Send pricing", "Send case study", "Schedule meeting", "Follow up later", "Escalate to human", "Stop outreach"]`, `Campaign_Stage_Recommendation` as a `Literal["ADVANCE", "PAUSE", "ESCALATE_TO_HUMAN", "STOP"]`, and `Confidence: float` in the range 0.0 to 1.0 inclusive.
3. THE `ResearchAgent` SHALL declare an `input_schema` requiring at minimum: `prospect_name: str` and `company: str`.
4. THE `StrategyAgent` SHALL declare an `input_schema` requiring at minimum: `prospect_profile: str` and `icp_score: float` in the range 0.0 to 1.0 inclusive.
5. THE `OutreachAgent` SHALL declare an `input_schema` requiring at minimum: `strategy: dict` and `prospect_profile: str`.
6. THE `MemoryAgent` SHALL declare an `input_schema` requiring at minimum: `contact_id: str` and `context: dict`.
7. THE `FollowUpAgent` SHALL declare an `input_schema` requiring at minimum: `contact_id: str` and `days_since_last_contact: int` with a minimum value of 0.
8. THE outreach pipeline SHALL include an `IO_Validator` component responsible for validating agent inputs and outputs against their declared schemas at the point of each agent's `run()` invocation.
9. IF a schema field is declared as a `Literal` type in any outreach agent schema, THEN THE `IO_Validator` SHALL verify that the supplied value is one of the declared allowed literals and raise a `ValidationError` indicating the field name and the invalid value when the check fails, without modifying pipeline state.

---

### Requirement 5: Orchestrator Dependency Tracking

**User Story:** As a UltraSwarm developer, I want the orchestrators to check whether a required output already exists in the accumulated context before dispatching an agent, so that no agent is called redundantly.

#### Acceptance Criteria

1. THE `Dependency_Tracker` SHALL initialise a per-session registry when a session starts and clear it when the session ends, mapping output key names to their values and the name of the agent that produced them.
2. WHEN the `Orchestrator` is about to dispatch an agent, THE `Dependency_Tracker` SHALL check whether all output keys declared in the agent's `output_schema` fields are present (key exists with a non-null value) in the accumulated context for the current session; if the agent declares both `output_schema` and a `provides` class attribute, the `output_schema` field names SHALL take precedence.
3. WHEN all required output keys for a subtask are already present in the accumulated context, THE `Orchestrator` SHALL skip dispatching that agent and log a message at `INFO` level identifying the agent name and the satisfied output keys.
4. WHEN only a subset of required output keys are present in the accumulated context, THE `Orchestrator` SHALL dispatch the agent and pass the already-satisfied fields via the input context without overwriting them in the agent's input if the agent also declares those keys as inputs.
5. THE `Dependency_Tracker` SHALL record the producing agent's name alongside each output key entry, so that the audit log can reconstruct the full provenance chain for any session.
6. IF the `Dependency_Tracker` itself raises an exception during a dependency check, THEN THE `Orchestrator` SHALL log a `WARNING` and dispatch the agent as if no dependencies were satisfied, rather than propagating the exception to the caller.

---

### Requirement 6: Critical Section Locking

**User Story:** As a UltraSwarm developer, I want concurrent execution paths to be prevented from producing the same result twice, so that there are no race conditions or redundant LLM calls when the swarm runs agents in parallel.

#### Acceptance Criteria

1. THE `Dependency_Tracker` SHALL maintain a dict of named `threading.Lock` objects, one per unique agent-output-key per session.
2. WHEN two concurrent threads attempt to populate the same output key simultaneously, THE `Dependency_Tracker` SHALL allow the first thread to acquire the lock and SHALL block the second thread until the first completes or the lock times out.
3. WHEN the first thread completes successfully and releases the lock, THE `Dependency_Tracker` SHALL provide the second thread with the result produced by the first thread — without re-executing the agent.
4. WHEN the first thread raises an exception before releasing the lock, THE `Dependency_Tracker` SHALL release the lock via `finally`, and the second thread SHALL proceed to execute the agent independently; the second thread's result SHALL be cached in the per-session registry.
5. WHEN a lock has been held for longer than `lock_timeout_seconds` (configurable, minimum 1 s, maximum 300 s, default 30 s), THE `Dependency_Tracker` SHALL release the lock, log a `WARNING` identifying the output key and the elapsed time, and allow the waiting thread to execute the agent independently.
6. WHEN N threads (N ≥ 2) concurrently request the same output key and the lock is available, THE `Dependency_Tracker` SHALL allow exactly one thread to acquire the lock; the remaining N-1 threads SHALL block until the lock is released.
7. WHEN a `Critical_Section` is entered successfully, THE `Dependency_Tracker` SHALL guarantee the lock is released on exit — whether the protected block completes normally or raises an exception — using `try/finally` semantics.

---

### Requirement 7: Orchestrator Context Threading Improvements

**User Story:** As a UltraSwarm developer, I want the orchestrators to manage context in a structured, dependency-aware way, so that agents always receive exactly the context they need and nothing is silently lost.

#### Acceptance Criteria

1. THE `Orchestrator` SHALL maintain an `accumulated_context` dict for the duration of a session, initialised from `input_data.get("context", {})`.
2. WHEN an agent returns a result with `success=True`, THE `Orchestrator` SHALL perform a shallow merge of the result's `context_for_next` dict into `accumulated_context` using update semantics (keys in `context_for_next` overwrite existing keys), before dispatching the next agent; if `context_for_next` is absent or `None` the merge SHALL be skipped without error.
3. WHEN the `Dependency_Tracker` marks an agent as skipped (dependency satisfied), THE `Orchestrator` SHALL perform the same shallow merge of the already-computed values from the `Dependency_Tracker`'s per-session registry into `accumulated_context`, using the same overwrite semantics.
4. WHEN the `OutreachOrchestrator` is about to dispatch an agent, THE `OutreachOrchestrator` SHALL include the current `OutreachContext` serialized to dict under the key `"outreach_context"` in the agent's input, and SHALL update `SwarmState.metadata["outreach_context"]` with the agent's returned `OutreachContext` after each agent returns a result with `success=True`.
5. WHEN the `OutreachOrchestrator` is about to dispatch any agent and the `opted_out` flag in the current `OutreachContext` is `True`, THE `Orchestrator` SHALL not dispatch `OutreachAgent` or `FollowUpAgent` and SHALL log a `WARNING` that includes the `contact_id` and the suppressed agent's name.

---

### Requirement 8: Cost and Token Tracking for Cloud Models

**User Story:** As a UltraSwarm developer, I want to know exactly how many tokens each agent used and what it cost in USD when using cloud models, so that I can optimise agent prompts and control API spend.

#### Acceptance Criteria

1. WHEN `GeminiClient.ask()` or `GeminiClient.ask_json()` returns a response, THE `Cost_Calculator` SHALL extract prompt token count and completion token count from the token usage metadata in that response.
2. IF `GeminiClient.ask()` or `GeminiClient.ask_json()` raises an exception before returning a response, THEN THE `Cost_Calculator` SHALL record the call with `prompt_tokens=0`, `completion_tokens=0`, `cost_usd=None`, and an `error` flag, and SHALL not raise a secondary exception.
3. WHEN a response is received from a `Cloud_Model`, THE `Cost_Calculator` SHALL compute `cost_usd = (prompt_tokens × input_price_per_token) + (completion_tokens × output_price_per_token)`, rounded to 8 decimal places, where prices are loaded from `model_pricing.json`.
4. THE `Cost_Calculator` SHALL accumulate per-agent totals (total prompt tokens, total completion tokens, total cost USD) across all calls made by that agent within a session.
5. THE `Cost_Calculator` SHALL accumulate per-session totals across all agents within the session.
6. WHEN the swarm run completes or `generate_report()` is called explicitly, THE `Cost_Calculator` SHALL produce a `Token_Report` containing: session ID, per-agent rows (agent name, model name, prompt tokens, completion tokens, total tokens, cost USD, timestamp of first call), and a session-total row.
7. WHERE `model_pricing.json` does not contain an entry for the model in use, THE `Cost_Calculator` SHALL log a `WARNING` identifying the model name and record `cost_usd=None` rather than raising an exception.
8. IF `model_pricing.json` is missing, unreadable, or contains invalid JSON, THEN THE `Cost_Calculator` SHALL log an `ERROR`, set all `cost_usd` values to `None` for the session, and continue tracking tokens without raising an exception.
9. THE `Cost_Calculator` SHALL load `model_pricing.json` once per process from the path specified by the `MODEL_PRICING_FILE` environment variable, defaulting to `config/model_pricing.json`.

---

### Requirement 9: Token Tracking for Local Models

**User Story:** As a UltraSwarm developer, I want to track tokens per section and wall-clock time when running with local models, so that I can measure performance and throughput without incurring cloud costs.

#### Acceptance Criteria

1. WHEN `LocalLLMClient.ask()` or `LocalLLMClient.ask_json()` returns a response, THE `Cost_Calculator` SHALL record prompt token count and completion token count from the `usage` field in that response when present.
2. WHEN the local API response does not include a `usage` field, THE `Cost_Calculator` SHALL estimate token count using a tokenizer function; the default tokenizer SHALL compute `round(len(text.split()) * 1.33)` and an alternative tokenizer MAY be supplied via a `Cost_Calculator` constructor parameter.
3. THE `Cost_Calculator` SHALL record wall-clock time in seconds with millisecond precision for each `LocalLLMClient` call, measured from the moment the request is sent to the moment the response is fully received.
4. IF `LocalLLMClient.ask()` or `LocalLLMClient.ask_json()` raises an exception, THEN THE `Cost_Calculator` SHALL record the call with `prompt_tokens=0`, `completion_tokens=0`, `time_seconds` equal to the elapsed time up to the exception, and an `error` flag.
5. WHEN the swarm run completes or `generate_report()` is called explicitly, THE `Cost_Calculator` SHALL produce a `Token_Report` for local model calls containing: session ID, per-agent rows (agent name, prompt tokens, completion tokens, total tokens, time_seconds), and a session-total row.
6. WHEN the swarm run completes or `generate_report()` is called explicitly and the session contains only local model calls, THE `Token_Report` SHALL contain no `cost_usd` column.
7. THE `Cost_Calculator` SHALL set `cost_usd` to `None` for all local model call records and SHALL not attempt any monetary cost computation for those records.

---

### Requirement 10: Cost Calculator Script

**User Story:** As a UltraSwarm developer, I want a standalone script that I can run to view a cost and token report for any session, so that I can audit usage after the fact without modifying the main runtime.

#### Acceptance Criteria

1. WHEN `scripts/cost_report.py` is invoked with `--session-id <id>`, THE script SHALL print a `Token_Report` for that session containing: session ID, agent name, model name, input tokens, output tokens, total tokens, cost USD (or `N/A` for local), and call timestamp — one row per agent.
2. WHEN `--session-id` is omitted, THE script SHALL print a summary table with one row per session containing: session ID, total input tokens, total output tokens, total tokens, total cost USD (or `N/A`), and total call count.
3. WHEN `--format json` is passed, THE script SHALL output the `Token_Report` as a single JSON object to stdout.
4. WHEN `--format table` is passed or `--format` is omitted, THE script SHALL output the `Token_Report` as an ASCII table where each column is left-aligned and padded to the width of its header or longest value, whichever is greater.
5. THE script SHALL read usage data from the JSONL log file at the path set by the `COST_LOG_FILE` environment variable, defaulting to `logs/cost_log.jsonl`.
6. WHEN the JSONL log file does not exist or contains no records, THE script SHALL print an informational message to stdout and exit with code 0.
7. WHEN `--session-id <id>` is provided but no records for that session exist in the log, THE script SHALL print an error message to stderr and exit with code 1.
8. WHEN an unsupported value is passed to `--format`, THE script SHALL print an error message listing the supported values and exit with code 1.
9. WHEN an agent call completes (successfully or with an error), THE `Cost_Calculator` SHALL append one JSONL record for that call to the log file within 500 ms, so that the log is readable even if the process terminates unexpectedly.

---

### Requirement 11: Non-Invasive Integration with Existing Agents

**User Story:** As a UltraSwarm developer, I want the validator and cost tracker to integrate without requiring changes to every existing agent, so that the system degrades gracefully and adoption can be incremental.

#### Acceptance Criteria

1. THE `IO_Validator` SHALL be implemented as a decorator (`@validated_agent`) that can be applied to individual agent `run()` methods without altering the agent's internal logic; WHEN the decorated `run()` raises an exception, THE decorator SHALL re-raise that exception unchanged without suppressing or wrapping it.
2. WHERE an existing agent's `run()` method does not use the `@validated_agent` decorator, THE system SHALL return the output of `run()` unchanged and SHALL not raise any validation errors or log any validation warnings for that agent.
3. WHEN a `GeminiClient` or `LocalLLMClient` instance is constructed via `make_client()`, THE `Cost_Calculator` SHALL wrap that instance so that all subsequent `ask()` and `ask_json()` calls on it are recorded by the `Cost_Calculator` without requiring modification to any agent that holds a reference to that client.
4. WHEN a new agent is added to the registry and its class does not declare `input_schema` or `output_schema`, THE `IO_Validator` SHALL log a `DEBUG`-level message noting that the agent has no schema declarations, and proceed without error.
5. IF the `Orchestrator` is initialised with `dependency_tracking=True` (the default), THEN THE `Dependency_Tracker` SHALL be active and SHALL execute its full dependency-check and locking logic on every agent dispatch.
6. IF the `Orchestrator` is initialised with `dependency_tracking=False`, THEN THE `Dependency_Tracker` SHALL be inactive: it SHALL execute no tracking logic and SHALL mutate no tracking state during any agent dispatch.
