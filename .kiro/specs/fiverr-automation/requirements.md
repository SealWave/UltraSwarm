# Requirements Document

## Introduction

The Fiverr Automation feature extends the UltraSwarm multi-agent system with a dedicated sub-swarm that fully automates the operation of a Fiverr freelance account. A Fiverr-specific orchestrator (the "Fiverr Manager") acts as the single point of access for all Fiverr operations, delegating work to five specialized sub-agents: Gig Creation, Web Scraping & Lead Generation, Account Management, Inbox & Communication, and Notification. All agents share a common state store, log every action through the orchestrator, and are registered with the existing UltraSwarm `OrchestratorAgent` so they are discoverable alongside all other system agents.

The entire feature lives under `agents/fiverr/` and follows the same `BaseAgent`-compatible pattern already used by agents in `agents/external/` and `agents/ecommerce/`, using `core.make_client()` for LLM access, `core.result_schema.ExecutionResult` for structured output, and the existing `tools/` utilities for browser automation and web search.

---

## Glossary

- **Fiverr_Manager**: The domain-level orchestrator for all Fiverr operations. Accepts user goals, plans sub-tasks, delegates to Fiverr sub-agents, and reports back to the top-level `OrchestratorAgent`.
- **Gig_Creation_Agent**: Sub-agent responsible for marketplace research and publishing optimized Fiverr gig listings.
- **Scraping_Lead_Gen_Agent**: Sub-agent responsible for fulfilling web scraping and lead generation client orders.
- **Account_Management_Agent**: Sub-agent responsible for monitoring gig performance metrics, order deadlines, and account health.
- **Inbox_Communication_Agent**: Sub-agent responsible for monitoring the Fiverr inbox and generating human-like replies.
- **Notification_Agent**: Sub-agent responsible for pushing alerts about key Fiverr events to the user.
- **Shared_State**: The in-memory and optionally persisted context store (`agents/fiverr/shared/state.py`) that all Fiverr sub-agents read from and write to via the Fiverr_Manager.
- **AgentResult**: The standardized dict returned by every agent `run()` call, as defined in `core/result_schema.py`.
- **GeminiClient**: The LLM client created by `core.make_client()`, shared across all agents.
- **BrowserOperatorAgent**: The existing `agents/browser_operator_agent.py` used for Fiverr web automation.
- **ExecutionResult**: The Pydantic model in `core/result_schema.py` returned by agent execution methods.
- **Skill**: A JSON capability definition in `skills/` loaded by `tools/skill_loader.py` and injected into an agent's system prompt.
- **UltraSwarm_Orchestrator**: The existing top-level `agents/managers/orchestrator_agent.py`.

---

## Requirements

### Requirement 1: Fiverr Manager — Central Orchestrator

**User Story:** As a Fiverr freelancer, I want a single AI manager that controls all Fiverr automation tasks, so that I can issue one high-level goal and have it fully delegated and executed without manual coordination.

#### Acceptance Criteria

1. THE Fiverr_Manager SHALL expose a `run(input_data: dict) -> dict` method that accepts a `goal` string and returns an `AgentResult`-compatible dict containing at minimum `status`, `message`, `data`, and `metadata` keys.
2. IF the `goal` key is missing from `input_data` or is an empty string, THEN THE Fiverr_Manager SHALL return an `AgentResult` with `status: "error"` and a `message` describing the missing input, without delegating any sub-task.
3. WHEN the Fiverr_Manager receives a non-empty `goal`, THE Fiverr_Manager SHALL decompose it into an ordered list of sub-tasks before delegating any sub-task to a Fiverr sub-agent.
4. THE Fiverr_Manager SHALL maintain a `Shared_State` instance that is passed as context to every sub-agent invocation during a session.
5. WHEN a sub-agent completes a task, THE Fiverr_Manager SHALL update the `Shared_State` with the sub-agent's `context_for_next` data before invoking the next sub-agent.
6. IF a sub-agent returns `status: "error"` on a task marked `critical: True`, THEN THE Fiverr_Manager SHALL halt the current plan and return an error `AgentResult` without executing remaining sub-tasks.
7. WHEN a sub-agent returns `status: "error"` and the task is not marked `critical`, THE Fiverr_Manager SHALL retry that sub-agent task up to 2 additional times before marking it as failed and continuing execution of remaining sub-tasks.
8. WHEN the Fiverr_Manager assigns a sub-task to an agent, THE Fiverr_Manager SHALL log a structured entry with `[Fiverr_Manager]` prefix to the console using Rich formatting.
9. WHEN a sub-agent returns an execution result, THE Fiverr_Manager SHALL log the agent name, task description, and `status` value with `[Fiverr_Manager]` prefix.
10. WHEN the Fiverr_Manager detects a sub-task status change (e.g., from pending to in_progress, or from in_progress to failed), THE Fiverr_Manager SHALL log the transition with `[Fiverr_Manager]` prefix.
11. WHEN the Fiverr_Manager assembles the final output, THE Fiverr_Manager SHALL return a synthesized natural-language summary of 50–200 words in the `message` field, in addition to the raw sub-agent results in the `data` field.
12. THE Fiverr_Manager SHALL expose a `get_metadata() -> dict` method returning at minimum the keys `name`, `role`, `description`, and `skills`, consistent with the `BaseAgent` interface.
13. THE Fiverr_Manager SHALL register itself and all five Fiverr sub-agents with the `UltraSwarm_Orchestrator` agent registry during initialization so they are accessible via the top-level system.

---

### Requirement 2: Agent Registry and Mutual Awareness

**User Story:** As a system developer, I want every Fiverr sub-agent to be aware of all other Fiverr sub-agents' roles and capabilities via the Fiverr Manager's shared context, so that agents can produce outputs appropriately formatted for the next agent in the chain.

#### Acceptance Criteria

1. WHEN the Fiverr_Manager initializes, THE Fiverr_Manager SHALL call `get_metadata()` on each of the five Fiverr sub-agents — `Gig_Creation_Agent`, `Scraping_Lead_Gen_Agent`, `Account_Management_Agent`, `Inbox_Communication_Agent`, and `Notification_Agent` — and store the results in the `Shared_State` under the `agent_registry` key, keyed by agent name. Each metadata dict SHALL contain at minimum `name`, `role`, and `description`.
2. IF any sub-agent's `get_metadata()` raises an exception during initialization, THEN THE Fiverr_Manager SHALL log the failure with `[Fiverr_Manager]` prefix and return an `AgentResult` with `status: "error"` indicating which agent failed to register, without proceeding to task delegation.
3. WHEN the Fiverr_Manager dispatches a task to a sub-agent, THE Fiverr_Manager SHALL include the `agent_registry` dict from `Shared_State` in the `context` field of the sub-agent's `input_data`.
4. WHEN the Gig_Creation_Agent completes execution, THE Gig_Creation_Agent SHALL include a `context_for_next` key in its result dict containing a non-empty dict with at minimum `gig_titles` (list of strings) and `gig_ids` (list of strings) consumable by downstream agents.
5. WHEN the Scraping_Lead_Gen_Agent completes execution, THE Scraping_Lead_Gen_Agent SHALL include a `context_for_next` key in its result dict containing a non-empty dict with at minimum `record_count` (int) and `data_type` (string) consumable by the Notification_Agent.
6. WHEN a Fiverr sub-agent's `run()` method receives a `context` dict containing an `agent_registry` key, THE sub-agent SHALL use the registry metadata to format its output in a way that is compatible with the next agent's expected input structure.

---

### Requirement 3: Gig Creation Agent

**User Story:** As a Fiverr seller, I want an AI agent that scans the Fiverr marketplace for in-demand AI-serviceable jobs and automatically drafts optimized gig listings, so that my gigs are positioned to attract buyers without manual research.

#### Acceptance Criteria

1. WHEN the Gig_Creation_Agent is tasked with gig discovery, THE Gig_Creation_Agent SHALL use `google_search()` from `tools/browser.py` to identify at least 3 in-demand Fiverr service categories from: lead generation, web scraping, data entry, copywriting, and chatbot building.
2. WHERE multiple service categories are identified, THE Gig_Creation_Agent SHALL rank them by the count of distinct search result snippets containing the category name and select the top categories first.
3. WHEN the Gig_Creation_Agent has identified a target service category, THE Gig_Creation_Agent SHALL generate a gig listing containing: a title (under 80 characters), a description (150–1200 words), at least 5 relevant tags, 3 pricing tiers (Basic, Standard, Premium) each with a price in USD ($5.00–$500.00) and a delivery time (1–30 days), and at least 3 FAQ entries.
4. THE Gig_Creation_Agent SHALL output the generated gig listing as a structured JSON object containing at minimum the keys: `title` (string), `description` (string), `tags` (list of strings), `pricing` (dict with `basic`, `standard`, `premium` sub-keys each having `price` and `delivery_days`), and `faqs` (list of dicts with `question` and `answer` keys).
5. WHEN the Gig_Creation_Agent publishes a gig via browser automation, THE Gig_Creation_Agent SHALL use `BrowserOperatorAgent.run_task()` to navigate the Fiverr seller dashboard and fill the gig creation form, and SHALL consider publication successful only when `run_task()` returns `success == True`.
6. IF `BrowserOperatorAgent.run_task()` returns `success == False` during gig publication, THEN THE Gig_Creation_Agent SHALL return `status: "error"` with the generated gig JSON preserved in the `data` field of the `ExecutionResult` so the listing can be manually published.
7. THE Gig_Creation_Agent SHALL save each generated gig listing to the output directory using `tools/output_manager.save_output()` with `format="json"`.

---

### Requirement 4: Web Scraping and Lead Generation Agent

**User Story:** As a Fiverr seller offering data services, I want an AI agent that automatically fulfills client orders requiring web scraping or lead generation, so that I can deliver structured data to buyers without manual effort.
use repo scrapling https://github.com/d4vinci/Scrapling pip install scrapling for the  scraping  of websites
#### Acceptance Criteria

1. WHEN the Scraping_Lead_Gen_Agent receives an order fulfillment task, THE Scraping_Lead_Gen_Agent SHALL parse the task instruction to extract: the target data type (one of: `emails`, `contacts`, `business_listings`, or `urls`), the target source (a valid website URL or a non-empty business category string), and the requested quantity (a positive integer).
2. WHEN the target source is a website URL, THE Scraping_Lead_Gen_Agent SHALL use `fetch_page()` from `tools/browser.py` to retrieve page content and extract structured records, fetching a maximum of 10 pages per source URL.
3. WHEN the target source is a business category string, THE Scraping_Lead_Gen_Agent SHALL call `google_search()` to obtain source URLs before invoking `fetch_page()`.
4. WHEN records have been collected, THE Scraping_Lead_Gen_Agent SHALL clean them by: removing duplicate records, validating that email-type records match the pattern `[^@]+@[^@]+\.[^@]+`, and removing records missing the primary identifier field — defined as: `email` for `emails` type, `full_name` for `contacts` type, `business_name` for `business_listings` type, and `url` for `urls` type.
5. THE Scraping_Lead_Gen_Agent SHALL return the cleaned data as a list of dicts in the `data` field of its `ExecutionResult`, with a `record_count` key indicating the number of valid records delivered.
6. IF the valid record count after cleaning is less than the requested quantity, THEN THE Scraping_Lead_Gen_Agent SHALL attempt up to 3 additional `google_search()` queries before returning a result with `status: "partial"` and the available records.
7. THE Scraping_Lead_Gen_Agent SHALL save the collected dataset to the output directory using `tools/output_manager.save_output()` with `format="json"`.
8. IF `tools/output_manager.save_output()` raises an exception, THEN THE Scraping_Lead_Gen_Agent SHALL log the exception, set `status: "error"` in the `ExecutionResult`, and preserve the collected data in the `data` field without re-raising.
9. THE Scraping_Lead_Gen_Agent SHALL include a `delivery_summary` string in its output containing at minimum: the data type, the final record count, and the primary source used; the string SHALL be between 50 and 500 characters.

---

### Requirement 5: Account Management Agent

**User Story:** As a Fiverr seller, I want an AI agent that continuously monitors my gig performance and order deadlines, so that I can maintain a high-standing account and never miss a delivery.

#### Acceptance Criteria

1. WHEN the Account_Management_Agent is tasked with a performance check, THE Account_Management_Agent SHALL use `BrowserOperatorAgent.run_task()` to navigate the Fiverr analytics dashboard and extract: `views`, `clicks`, `orders`, and `avg_review_score` for each gig whose dashboard status is `"Active"`.
2. THE Account_Management_Agent SHALL return the extracted metrics in the `data` field of its `ExecutionResult` as a dict keyed by gig title, where each value is a dict with keys `views` (int), `clicks` (int), `orders` (int), and `avg_review_score` (float).
3. IF `BrowserOperatorAgent.run_task()` raises an exception or returns `success == False` during dashboard navigation, THEN THE Account_Management_Agent SHALL return `status: "error"` in the `ExecutionResult` without populating metric fields.
4. WHEN active orders are present, THE Account_Management_Agent SHALL check each order's deadline. IF an order's deadline is within 24 hours of the time of the check, THEN THE Account_Management_Agent SHALL set `deadline_warning: True` for that order.
5. WHEN an order is flagged with `deadline_warning: True`, THE Account_Management_Agent SHALL include that order's `order_id` (string) and `deadline_timestamp` (UTC ISO-8601 string) in `data["deadline_warnings"]` as a list of dicts.
6. IF no active orders are present, THE Account_Management_Agent SHALL set `data["deadline_warnings"]` to an empty list.
7. THE Account_Management_Agent SHALL assess overall account health and return one of three statuses in `data["account_health"]`: `"healthy"` when `avg_review_score >= 4.5` AND `response_rate >= 90%` AND `late_delivery_rate <= 5%`; `"at_risk"` when any one threshold is missed; `"critical"` when two or more thresholds are missed.
8. WHEN account status is `"at_risk"` or `"critical"`, THE Account_Management_Agent SHALL include a non-empty list of string recommendations under `data["recommendations"]`.
9. THE Account_Management_Agent SHALL save the performance report using `tools/output_manager.save_output()` with `format="json"`.

---

### Requirement 6: Inbox and Communication Agent

**User Story:** As a Fiverr seller, I want an AI agent that monitors my Fiverr inbox and sends human-like automated replies to buyer inquiries, so that I maintain fast response times and professional communication without being online 24/7.

#### Acceptance Criteria

1. WHEN the Inbox_Communication_Agent is tasked with an inbox check, THE Inbox_Communication_Agent SHALL use `BrowserOperatorAgent.run_task()` to navigate the Fiverr inbox and extract all unread messages, each as a dict with keys: `sender_username` (string), `message_text` (string), and `timestamp` (UTC ISO-8601 string). IF no unread messages exist, THE agent SHALL return `status: "success"` with `data["messages"]` as an empty list.
2. IF `BrowserOperatorAgent.run_task()` raises an exception or returns `success == False` during inbox navigation, THEN THE Inbox_Communication_Agent SHALL return `status: "error"` in the `ExecutionResult` without processing any messages.
3. THE Inbox_Communication_Agent SHALL classify each unread message into one of four categories: `"price_inquiry"`, `"order_details_request"`, `"revision_request"`, or `"general_inquiry"`. IF a message does not match any of the first three categories, THEN THE agent SHALL assign it `"general_inquiry"`.
4. WHEN a message is classified, THE Inbox_Communication_Agent SHALL generate a reply using the LLM that: directly addresses the classified message category, is under 150 words, and does not contain any of the following phrases: "as an AI", "I am an AI", "I'm an AI assistant", "as a language model".
5. WHEN generating replies, IF `Shared_State` contains a non-empty `active_gigs` list, THE Inbox_Communication_Agent SHALL include gig titles, pricing, and delivery times from that list in the LLM prompt. IF `active_gigs` is absent or empty, THE agent SHALL set `data["missing_gig_context"]: True` in the `ExecutionResult`.
6. WHERE `AUTO_REPLY` is `True` in the Fiverr config, THE Inbox_Communication_Agent SHALL call `BrowserOperatorAgent.run_task()` to send each generated reply in the Fiverr inbox.
7. IF `BrowserOperatorAgent.run_task()` returns `success == False` during reply sending, THEN THE Inbox_Communication_Agent SHALL add the unsent reply dict to `data["unsent_replies"]` and continue processing remaining messages without halting.
8. IF `AUTO_REPLY` is `False` or not set, THEN THE Inbox_Communication_Agent SHALL return all generated replies in `data["replies"]` as a list of dicts (each with `sender_username`, `category`, and `reply_text`) without sending them.
9. WHEN a new unread message is extracted, THE Inbox_Communication_Agent SHALL append an event dict with keys `event_type: "new_message"`, `message: <sender_username>`, and `timestamp: <message timestamp>` to `context_for_next["new_events"]`.
10. THE Inbox_Communication_Agent SHALL save a log of all detected messages and generated replies using `tools/output_manager.save_output()` with `format="json"`.

---

### Requirement 7: Notification Agent

**User Story:** As a Fiverr seller, I want to receive real-time alerts for every key Fiverr event, so that I am always informed of new orders, messages, deadlines, and reviews regardless of whether I am actively monitoring the platform.

#### Acceptance Criteria

1. THE Notification_Agent SHALL support at least two notification channels configured via environment variables: `NOTIFICATION_EMAIL` for email alerts and `NOTIFICATION_WEBHOOK_URL` for webhook-based alerts (e.g., SMS gateway, Slack, or app push).
2. IF both `NOTIFICATION_EMAIL` and `NOTIFICATION_WEBHOOK_URL` are absent or empty at invocation time, THEN THE Notification_Agent SHALL return `status: "error"` with `message: "No notification channels configured"` without attempting any dispatch.
3. WHEN the Notification_Agent receives a task containing a `new_events` list from `Shared_State`, THE Notification_Agent SHALL dispatch one notification per distinct event type present in the list, where "distinct event type" means the `event_type` string value regardless of how many instances of that type are in the list.
4. IF the `new_events` list is empty or absent, THEN THE Notification_Agent SHALL return `status: "no_events"` without dispatching any notification.
5. THE Notification_Agent SHALL support the following event types: `new_order`, `new_message`, `order_completed`, `review_received`, and `deadline_warning`.
6. WHEN dispatching an email notification, THE Notification_Agent SHALL send an email to the address in `NOTIFICATION_EMAIL` using SMTP credentials from environment variables `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD`.
7. WHEN dispatching a webhook notification, THE Notification_Agent SHALL send an HTTP POST request to `NOTIFICATION_WEBHOOK_URL` with a JSON payload containing `event_type`, `message`, and `timestamp`.
8. IF an email dispatch fails due to an SMTP error, THEN THE Notification_Agent SHALL log the error to `data["dispatch_errors"]` in the `ExecutionResult` and attempt delivery via the webhook channel if `NOTIFICATION_WEBHOOK_URL` is configured, without raising an exception.
9. IF a webhook dispatch fails, THEN THE Notification_Agent SHALL log the HTTP status code and response body to `data["dispatch_errors"]` in the `ExecutionResult`.
10. THE Notification_Agent SHALL return `status: "success"` only when at least one notification channel successfully delivers at least one notification.
11. THE Notification_Agent SHALL de-duplicate events within a single invocation by checking the `notified_events` set in `Shared_State` before dispatching; an event whose `event_type + timestamp` composite key already appears in `notified_events` SHALL be skipped and not dispatched again.

---

### Requirement 8: Shared State and Configuration

**User Story:** As a developer integrating the Fiverr automation feature, I want a centralized shared state and configuration module, so that all Fiverr agents operate with consistent context and credentials without duplicating configuration logic.

#### Acceptance Criteria

1. THE Shared_State SHALL be implemented as a class in `agents/fiverr/shared/state.py` with at minimum the following instance attributes initialized in `__init__`: `session_id` (string), `agent_registry` (dict), `active_gigs` (list), `open_orders` (list), `inbox_messages` (list), `new_events` (list), `notified_events` (set), and `change_log` (list).
2. THE Shared_State SHALL provide a `get(key: str) -> Any` method that returns the value for the given key. IF the key does not exist in the instance attributes, THEN `get()` SHALL return `None` without raising an exception.
3. WHEN `Shared_State.set(key, value)` is called, THE method SHALL update the instance attribute for `key` to `value` and append a dict with keys `key`, `value`, and `timestamp` (UTC ISO-8601 string) to the internal `change_log` list.
4. THE Shared_State SHALL provide a `to_context_dict() -> dict` method that returns a dict containing all instance attributes listed in criterion 1, with `notified_events` serialized as a sorted list of strings to ensure JSON serializability.
5. THE `agents/fiverr/shared/config.py` module SHALL load all Fiverr-specific credentials and settings exclusively from environment variables using `os.environ.get()`, with no hardcoded credential values in any source file.
6. THE `agents/fiverr/shared/config.py` module SHALL define and expose the following module-level constants: `FIVERR_USERNAME` (str), `FIVERR_PASSWORD` (str), `NOTIFICATION_EMAIL` (str), `NOTIFICATION_WEBHOOK_URL` (str), `SMTP_HOST` (str), `SMTP_PORT` (str), `SMTP_USER` (str), `SMTP_PASSWORD` (str), and `AUTO_REPLY` (bool, `True` only when the env var value is exactly `"true"` case-insensitively).
7. WHEN an environment variable required by `config.py` is not set, THE config module SHALL use a safe default value — empty string `""` for all string credentials, `"25"` for `SMTP_PORT`, and `False` for `AUTO_REPLY` — and SHALL NOT raise an exception at import time.

---

### Requirement 9: Action Logging and Audit Trail

**User Story:** As a developer or account owner, I want every agent action to be logged with a consistent format, so that I can audit what the system did, diagnose failures, and replay sessions.

#### Acceptance Criteria

1. THE Fiverr_Manager SHALL write one structured JSON Lines (JSONL) log entry to `agent_workspace/fiverr_session_{session_id}.log` per sub-task execution attempt (including retries), where each entry contains: `timestamp` (UTC ISO-8601), `agent_name` (string), `task_description` (string), and `outcome` (one of `"success"` or `"error"`).
2. WHEN an exception is raised inside a Fiverr sub-agent's `run()` method body, THE sub-agent SHALL catch it, write the full traceback string to the session log file identified in criterion 1, and return an `ExecutionResult` with `status: "error"` and the exception message in the `message` field, without re-raising the exception.
3. THE Shared_State `change_log` list SHALL be included in the `metadata` key of the final `AgentResult` dict returned by the Fiverr_Manager at the end of a session.
4. WHEN the Fiverr_Manager writes a console log entry, THE entry SHALL use Rich markup in the format `[bold cyan]\[Fiverr_Manager][/bold cyan] <message>`, where `<message>` is a plain-text description of the action or result.

---

### Requirement 10: Integration with UltraSwarm Entry Point

**User Story:** As a UltraSwarm user, I want to access the Fiverr automation system from the existing main.py interactive menu and CLI, so that I can launch Fiverr automation the same way I launch any other agent or swarm.

#### Acceptance Criteria

1. THE `main.py` interactive menu SHALL include a dedicated "FIVERR AUTOMATION" section with menu slots numbered sequentially after the last existing slot (currently slot 19), listing the Fiverr_Manager as the first option and each of the five Fiverr sub-agents as subsequent selectable options.
2. WHEN the user selects the Fiverr_Manager entry from the `main.py` menu, THE system SHALL instantiate `FiverrManager` and call its `run_interactive()` method.
3. WHEN the `--agent fiverr` CLI argument is provided to `main.py`, THE system SHALL instantiate `FiverrManager` and call its `run_interactive()` method, without displaying the interactive menu.
4. THE `agents/fiverr/__init__.py` module SHALL export `FiverrManager` (the orchestrator class) and `ALL_FIVERR_AGENTS` (a list containing exactly the five sub-agent classes: `GigCreationAgent`, `ScrapingLeadGenAgent`, `AccountManagementAgent`, `InboxCommunicationAgent`, and `NotificationAgent`), following the same `__all__` export pattern as `agents/external/__init__.py`.
5. THE `UltraSwarm_Orchestrator`'s `_build_agent_registry()` method SHALL be extended to import `ALL_FIVERR_AGENTS` from `agents.fiverr` inside a `try/except ImportError` block (consistent with the existing pattern in `orchestrator_agent.py`) and register each agent alongside the existing external agents.
