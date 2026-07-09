# Implementation Plan: Fiverr Automation Multi-Agent System

## Overview

This feature extends the UltraSwarm multi-agent system with a dedicated Fiverr automation sub-swarm. Implementation follows the requirements-first workflow: shared infrastructure first, then orchestrator, worker agents, and finally entry point integration. All agents conform to BaseAgent-compatible interface using existing tools (browser automation, LLM client, output manager).

**Key Design Decisions**:
- Use existing `core.make_client()` for LLM access across all agents
- Leverage `BrowserOperatorAgent` for Fiverr web automation tasks
- Implement JSONL audit logging to `agent_workspace/` with session ID
- Follow Python naming conventions (snake_case for files, CamelCase for classes)

## Tasks

- [x] 1. Set up shared infrastructure module
  - Create directory structure for Fiverr agents
  - Implement Shared_State class with required methods
  - Implement environment-based configuration module
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x] 1.1 Create `agents/fiverr/` directory structure
    - Create `agents/fiverr/__init__.py` with module exports
    - Create `agents/fiverr/shared/` directory
    - Create `agents/fiverr/shared/__init__.py`
    - _Requirements: 10.4_

  - [x] 1.2 Implement `agents/fiverr/shared/state.py` with Shared_State class
    - Implement `__init__` with all required attributes (session_id, agent_registry, active_gigs, open_orders, inbox_messages, new_events, notified_events, change_log)
    - Implement `get(key: str) -> Any` method returning None for missing keys
    - Implement `set(key, value)` method that updates attribute and appends to change_log
    - Implement `to_context_dict() -> dict` method returning JSON-serializable dict
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 1.3 Implement `agents/fiverr/shared/config.py` with environment-based configuration
    - Import os and define all required module-level constants
    - Define FIVERR_USERNAME, FIVERR_PASSWORD, NOTIFICATION_EMAIL, NOTIFICATION_WEBHOOK_URL, SMTP_HOST, SMTP_PORT (default "25"), SMTP_USER, SMTP_PASSWORD
    - Define AUTO_REPLY as bool (True only when env var is exactly "true" case-insensitively)
    - Use os.environ.get() for all environment variables with safe defaults
    - Include comprehensive inline comments explaining each configuration
    - _Requirements: 8.5, 8.6, 8.7_

- [x] 2. Implement core Fiverr Manager orchestrator
  - Create main orchestrator class with goal decomposition logic
  - Implement sub-agent delegation and state coordination
  - Implement retry logic and error handling
  - Implement audit logging with Rich console formatting
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11, 1.12, 1.13, 2.1, 2.2, 2.3, 9.1, 9.2, 9.3_

  - [x] 2.1 Create `agents/fiverr/fiverr_manager_agent.py` base structure
    - Import BaseAgent, ExecutionResult, Shared_State from shared.state
    - Implement FiverrManager class with get_metadata() method
    - Implement __init__ that instantiates Shared_State with session_id
    - Register agent with UltraSwarm_Orchestrator (try/except ImportError block)
    - Implement initial _build_agent_registry() method to register all sub-agents
    - _Requirements: 1.12, 1.13, 2.1, 10.4_

  - [x] 2.2 Implement run() method with goal validation
    - Validate input_data for "goal" key with non-empty string
    - Return AgentResult with status "error" and descriptive message for invalid goal
    - Extract goal string and proceed to sub-task decomposition
    - _Requirements: 1.1, 1.2_

  - [x] 2.3 Implement sub-task decomposition logic
    - Parse goal string into ordered list of sub-tasks
    - Each sub-task must have: task_id, instruction, required_output, critical flag
    - Store sub-tasks in Shared_State for execution order
    - _Requirements: 1.3, 1.4, 1.5_

  - [x] 2.4 Implement sub-agent delegation and state coordination
    - For each sub-task, determine appropriate sub-agent (based on task type)
    - Build agent_input with context including agent_registry from Shared_State
    - Call sub-agent run() method and capture result
    - Update Shared_State with sub-agent's context_for_next before next delegation
    - _Requirements: 1.3, 1.4, 1.5, 2.3_

  - [x] 2.5 Implement retry logic for non-critical tasks
    - Implement automatic retry up to 2 additional times for failed non-critical tasks
    - Log retry attempts with `[Fiverr_Manager] Retry {attempt}/{max_retries} for {agent_name}`
    - After max retries, mark task as failed and continue with remaining sub-tasks
    - _Requirements: 1.7_

  - [x] 2.6 Implement critical task failure handling
    - Halt execution immediately when critical task returns status "error"
    - Return error AgentResult without executing remaining sub-tasks
    - Preserve all progress in Shared_State for potential replay
    - _Requirements: 1.6_

  - [x] 2.7 Implement audit logging to JSONL file
    - Create session log file `agent_workspace/fiverr_session_{session_id}.log`
    - Write JSONL entry per task execution attempt with timestamp, agent_name, task_description, outcome
    - Catch exceptions in sub-agents, log full traceback, return error result
    - _Requirements: 9.1, 9.2_

  - [x] 2.8 Implement console logging with Rich formatting
    - Use Rich console print with `[bold cyan][Fiverr_Manager][/bold cyan] <message>` format
    - Log goal receipt, sub-task start, sub-task completion, status transitions
    - _Requirements: 1.8, 1.9, 1.10_

  - [x] 2.9 Implement final output synthesis
    - Assemble raw sub-agent results in `data` field
    - Generate 50-200 word natural language summary in `message` field
    - Include change_log in `metadata` field of final AgentResult
    - _Requirements: 1.11, 9.3_

- [ ] 3. Implement worker agents
  - Implement all five Fiverr sub-agents following BaseAgent pattern
  - Each agent uses BrowserOperatorAgent for Fiverr web automation where needed
  - All agents return standardized result with context_for_next field
  - _Requirements: 3.1-3.7, 4.1-4.9, 5.1-5.9, 6.1-6.12, 7.1-7.11_

  - [x] 3.1 Create `agents/fiverr/gig_creation_agent.py`
    - Import BaseAgent, BrowserOperatorAgent, tools/browser, tools/output_manager
    - Implement GigCreationAgent class with get_metadata() method
    - Implement run() method with marketplace research using google_search()
    - Rank service categories by search result snippet counts
    - Generate gig listing with title (80 chars), description (150-1200 words), 5+ tags, 3 pricing tiers, 3+ FAQs
    - Output structured JSON with required keys (title, description, tags, pricing, faqs)
    - Use BrowserOperatorAgent.run_task() for Fiverr gig publication
    - Return error status with gig JSON preserved in data field on browser failure
    - Save output using tools/output_manager.save_output() with format="json"
    - Include context_for_next with gig_titles and gig_ids lists
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 2.4_

  - [ ] 3.2 Create `agents/fiverr/scraping_lead_gen_agent.py`
    - Import BaseAgent, tools/browser, tools/output_manager
    - Implement ScrapingLeadGenAgent class with get_metadata() method
    - Parse task instruction for data_type, target_source, requested_quantity
    - Use google_search() to obtain source URLs for category-based scraping
    - Use fetch_page() to retrieve page content (max 10 pages per URL)
    - Clean collected records (dedup, email validation, primary identifier validation)
    - Return cleaned data as list of dicts in data field with record_count
    - Attempt up to 3 additional google_search() queries if record count insufficient
    - Return partial status with available records when unable to meet quantity
    - Save output using tools/output_manager.save_output() with format="json"
    - Preserve collected data on save exception with error status
    - Include context_for_next with record_count (int) and data_type (string)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 2.5_

  - [ ] 3.3 Create `agents/fiverr/account_management_agent.py`
    - Import BaseAgent, BrowserOperatorAgent, tools/output_manager
    - Implement AccountManagementAgent class with get_metadata() method
    - Use BrowserOperatorAgent.run_task() to navigate Fiverr analytics dashboard
    - Extract metrics: views, clicks, orders, avg_review_score for each active gig
    - Return metrics as dict keyed by gig title in data field
    - Check each order's deadline and flag with deadline_warning if within 24 hours
    - Include order_id and deadline_timestamp in data["deadline_warnings"] list
    - Assess account health based on thresholds (review_score >= 4.5, response_rate >= 90%, late_delivery_rate <= 5%)
    - Return account_health: "healthy", "at_risk", or "critical"
    - Include non-empty recommendations list for at_risk or critical status
    - Save performance report using tools/output_manager.save_output() with format="json"
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

  - [ ] 3.4 Create `agents/fiverr/inbox_communication_agent.py`
    - Import BaseAgent, BrowserOperatorAgent, tools/output_manager
    - Implement InboxCommunicationAgent class with get_metadata() method
    - Use BrowserOperatorAgent.run_task() to extract unread messages
    - Each message as dict with sender_username, message_text, timestamp
    - Classify each message into: price_inquiry, order_details_request, revision_request, or general_inquiry
    - Generate reply using LLM (under 150 words, no "as an AI" phrases)
    - Include gig context from Shared_State.active_gigs in LLM prompt if available
    - Set data["missing_gig_context"]: True when active_gigs is empty
    - Send replies via BrowserOperatorAgent when AUTO_REPLY is True
    - Add unsent replies to data["unsent_replies"] on send failure
    - Return generated replies in data["replies"] when AUTO_REPLY is False
    - Append event to context_for_next["new_events"] for each new message
    - Save message log using tools/output_manager.save_output() with format="json"
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12_

  - [ ] 3.5 Create `agents/fiverr/notification_agent.py`
    - Import BaseAgent, tools/output_manager
    - Implement NotificationAgent class with get_metadata() method
    - Support email notifications via NOTIFICATION_EMAIL env var
    - Support webhook notifications via NOTIFICATION_WEBHOOK_URL env var
    - Return error with "No notification channels configured" when both are absent
    - Dispatch one notification per distinct event_type from Shared_State.new_events
    - Support event types: new_order, new_message, order_completed, review_received, deadline_warning
    - Send email using SMTP credentials from environment variables
    - Send webhook POST with JSON payload (event_type, message, timestamp)
    - Log email SMTP errors to data["dispatch_errors"], attempt webhook fallback
    - Log webhook HTTP errors (status code, response body) to data["dispatch_errors"]
    - De-duplicate events using event_type + timestamp composite key from notified_events
    - Return status "success" only when at least one channel successfully delivers
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11_

- [ ] 4. Update entry points and integrate with UltraSwarm
  - Update main.py to include Fiverr section in interactive menu
  - Add CLI argument support for --agent fiverr
  - Implement run_interactive() method for FiverrManager
  - Extend orchestrator agent registry to include Fiverr agents
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ] 4.1 Update `agents/fiverr/__init__.py` module exports
    - Import all five sub-agent classes from their respective files
    - Define ALL_FIVERR_AGENTS list containing all five agent classes
    - Define __all__ export list following pattern from agents/external/__init__.py
    - Export FiverrManager (orchestrator class) and ALL_FIVERR_AGENTS
    - _Requirements: 10.4_

  - [ ] 4.2 Update `main.py` interactive menu with Fiverr section
    - Add FIVERR AUTOMATION section numbered sequentially after last existing slot (19)
    - Add menu slot for Fiverr_Manager (first option)
    - Add menu slots for each of the five Fiverr sub-agents (subsequent options)
    - Add Fiverr_Manager to agent_map dictionary with key "fiverr"
    - _Requirements: 10.1, 10.2_

  - [ ] 4.3 Add CLI argument support for --agent fiverr in main.py
    - Update run_agent() function to handle "fiverr" agent_name
    - Import FiverrManager and call run_interactive() method
    - Add "fiverr" to argparse help text and existing --agent argument parser
    - _Requirements: 10.3_

  - [ ] 4.4 Implement run_interactive() method for FiverrManager
    - Display Fiverr Manager welcome banner
    - Loop to accept user goal input
    - Call run() with user goal and display AgentResult
    - Allow user to continue or exit
    - Handle KeyboardInterrupt gracefully
    - _Requirements: 10.2_

  - [ ] 4.5 Extend `agents/managers/orchestrator_agent.py` agent registry
    - Import ALL_FIVERR_AGENTS from agents.fiverr inside try/except ImportError
    - Add Fiverr agents to agent_classes list in _build_agent_registry()
    - Register each Fiverr agent alongside existing external agents
    - Log warning for any Fiverr agent that fails to load
    - _Requirements: 10.5_

- [ ] 5. Verify implementation with tests
  - Run verification tests to ensure all acceptance criteria are met
  - Test error handling and edge cases
  - Verify integration points work correctly

  - [ ] 5.1 Write unit tests for Shared_State class
    - Test get() method with existing and missing keys
    - Test set() method updates attribute and appends to change_log
    - Test to_context_dict() returns JSON-serializable dict
    - Test notified_events serialization to sorted list
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ] 5.2 Write unit tests for FiverrManager orchestrator
    - Test goal validation with empty/missing goal
    - Test sub-task decomposition produces valid structure
    - Test retry logic for non-critical task failures
    - Test immediate halt on critical task failure
    - Test agent registry includes all five sub-agents
    - Test metadata exceptions during initialization halt execution
    - _Requirements: 1.1, 1.2, 1.3, 1.6, 1.7, 2.1, 2.2_

  - [ ] 5.3 Write property tests for core orchestration properties
    - **Property 1: Goal Decomposition Produces Valid Sub-Tasks**
    - **Validates: Requirements 1.1, 1.2**
    
    - **Property 2: Sub-Agent Results Update Shared State**
    - **Validates: Requirements 1.3, 1.4, 1.5**
    
    - **Property 3: Critical Task Failures Halt Execution**
    - **Validates: Requirements 1.6**
    
    - **Property 4: Non-Critical Task Retries Up to Two Times**
    - **Validates: Requirements 1.7**
    
    - **Property 5: Agent Registry Contains All Sub-Agents**
    - **Validates: Requirements 2.1, 2.3**
    
    - **Property 6: Audit Logging Records All Task Executions**
    - **Validates: Requirements 9.1, 9.2**

  - [ ] 5.4 Write unit tests for worker agents
    - Test GigCreationAgent returns proper context_for_next with gig_titles and gig_ids
    - Test ScrapingLeadGenAgent returns proper context_for_next with record_count and data_type
    - Test InboxCommunicationAgent classifies all message types correctly
    - Test NotificationAgent de-duplicates events using composite key
    - _Requirements: 2.4, 2.5, 6.4, 7.11_

  - [ ] 5.5 Write integration tests for entry points
    - Test interactive menu includes Fiverr section with correct numbering
    - Test --agent fiverr CLI argument launches FiverrManager
    - Test orchestrator agent registry includes all Fiverr agents
    - Test FiverrManager can be instantiated and run interactively
    - _Requirements: 10.1, 10.2, 10.3, 10.5_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- All agents follow BaseAgent-compatible interface using existing tools
- Browser automation tasks use existing BrowserOperatorAgent
- JSONL audit logging to agent_workspace/ with session ID
- Shared_State provides centralized context for all Fiverr agents
- Environment variables used exclusively for credentials (no hardcoded values)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3"] },
    { "id": 2, "tasks": ["2.1", "2.2", "2.3"] },
    { "id": 3, "tasks": ["2.4", "2.5", "2.6", "2.7", "2.8"] },
    { "id": 4, "tasks": ["2.9"] },
    { "id": 5, "tasks": ["3.1"] },
    { "id": 6, "tasks": ["3.2", "3.3"] },
    { "id": 7, "tasks": ["3.4", "3.5"] },
    { "id": 8, "tasks": ["4.1", "4.2", "4.3"] },
    { "id": 9, "tasks": ["4.4", "4.5"] },
    { "id": 10, "tasks": ["5.1", "5.2"] },
    { "id": 11, "tasks": ["5.3", "5.4", "5.5"] }
  ]
}
```
