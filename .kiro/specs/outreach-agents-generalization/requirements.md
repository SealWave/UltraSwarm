# Requirements Document

## Introduction

This document specifies the functional requirements for the Outreach Agents Generalization feature. The feature redesigns the UltraSwarm outreach swarm to autonomously handle any outreach mission — lead generation, B2B partnerships, investor relations, recruitment, event promotion, PR/media outreach, or customer success — without hardcoded playbooks or per-agent text heuristics.

The core change introduces an **OutreachContext** shared envelope that flows through every agent in the pipeline, a new **OutreachClassifierAgent** that interprets free-text goals, and behavioral drip timing driven by engagement signals rather than fixed calendar intervals.

## Glossary

- **OutreachContext**: A typed, serializable dataclass that carries all campaign configuration and runtime state through the entire agent pipeline. It is the single source of truth for "what kind of outreach is this."
- **OutreachClassifierAgent**: A new agent that accepts a free-text goal string and returns a fully populated OutreachContext. Entry point to the pipeline.
- **ResearchAgent**: Existing agent enhanced with ICP matching and type-specific research focus.
- **StrategyAgent**: Existing agent redesigned to generate LLM-driven DynamicStrategy objects with no hardcoded playbooks.
- **OutreachAgent**: Existing message-drafting agent updated to accept OutreachContext and tune framing per outreach type.
- **AnalysisAgent**: Existing reply-analysis agent enhanced with type-specific signal taxonomy and Campaign_Stage_Recommendation.
- **FollowUpAgent**: Existing agent redesigned with behavioral drip timing driven by engagement signals.
- **OrchestratorAgent**: Existing state machine updated with CLASSIFYING and ICP_CHECK states and context threading.
- **MemoryAgent**: Existing persistence agent updated to store and retrieve OutreachContext alongside history.
- **ICPMatchResult**: A dataclass returned by ResearchAgent.score_icp_match() containing a normalized score, matched criteria, failed criteria, recommendation, and confidence.
- **DynamicStrategy**: A dataclass returned by StrategyAgent containing a channel sequence, drip plan, tone directives, hook strategy, and persona classification.
- **ChannelStep**: A single step in the ordered channel sequence, specifying the channel, wait days, and trigger condition.
- **DripStep**: A single step in the drip plan, specifying days after previous step, message theme, trigger condition, and channel.
- **outreach_type**: One of eight values classifying the kind of outreach: LEAD_GEN, PARTNERSHIP, INVESTOR, RECRUITMENT, EVENT_PROMO, PR_MEDIA, CUSTOMER_SUCCESS, GENERAL.
- **outreach_goal**: One of six values describing the desired outcome: START_CONVERSATION, BOOK_INTRO_CALL, GET_REPLY, REQUEST_DEMO, COLLECT_INFO, SECURE_COMMITMENT.
- **campaign_mode**: One of two values describing scope: SINGLE_PROSPECT or BULK_CAMPAIGN.
- **ICP**: Ideal Customer Profile — a dict of constraints used to score whether a prospect is a good fit (industries, seniority levels, company size range, geo, keywords, exclusions, min_icp_score).
- **SwarmState**: The shared state object used by OrchestratorAgent; OutreachContext is stored at SwarmState.metadata["outreach_context"].
- **engagement_signals**: A list of timestamped event dicts (open, click, reply, bounce) recorded per prospect per platform.
- **opted_out**: A boolean flag on OutreachContext; when True, no message may be drafted or sent to the prospect.
- **compliance_flags**: A list of compliance requirements on OutreachContext (e.g., "GDPR", "CAN-SPAM") that impose mandatory message content rules.
- **Campaign_Stage_Recommendation**: One of four values returned by AnalysisAgent: ADVANCE, PAUSE, ESCALATE_TO_HUMAN, STOP.
- **rule_fallback**: A code path in ClassifierAgent and StrategyAgent that executes when the LLM is unavailable, using keyword matching or type-specific defaults to produce valid output.

---

## Requirements

### Requirement 1: OutreachContext Classification

**User Story:** As an outreach campaign manager, I want the system to interpret my free-text goal and produce a structured campaign context, so that all downstream agents have the information they need without me configuring each agent manually.

#### Acceptance Criteria

1. WHEN a non-empty raw goal string is provided to the OutreachClassifierAgent, THE OutreachClassifierAgent SHALL return an OutreachContext whose `outreach_type` is one of the eight valid values: LEAD_GEN, PARTNERSHIP, INVESTOR, RECRUITMENT, EVENT_PROMO, PR_MEDIA, CUSTOMER_SUCCESS, GENERAL.
2. WHEN a non-empty raw goal string is provided to the OutreachClassifierAgent, THE OutreachClassifierAgent SHALL return an OutreachContext whose `outreach_goal` is one of the six valid values: START_CONVERSATION, BOOK_INTRO_CALL, GET_REPLY, REQUEST_DEMO, COLLECT_INFO, SECURE_COMMITMENT.
3. WHEN a non-empty raw goal string is provided to the OutreachClassifierAgent, THE OutreachClassifierAgent SHALL return an OutreachContext whose `campaign_mode` is one of the two valid values: SINGLE_PROSPECT, BULK_CAMPAIGN.
4. WHEN a non-empty raw goal string is provided to the OutreachClassifierAgent, THE OutreachClassifierAgent SHALL return an OutreachContext with a non-empty `preferred_channels` list.
5. WHEN the LLM is unavailable during classification, THE OutreachClassifierAgent SHALL execute a rule-based keyword matching fallback to produce a valid OutreachContext.
6. IF no keyword in the raw goal matches any outreach type rule, THEN THE OutreachClassifierAgent SHALL set `outreach_type` to GENERAL and continue pipeline execution without error.

---

### Requirement 2: LLM-Driven Dynamic Strategy Generation

**User Story:** As an outreach specialist, I want the StrategyAgent to generate strategies using LLM reasoning rather than fixed playbooks, so that every campaign gets a tailored channel sequence and drip plan suited to its context.

#### Acceptance Criteria

1. FOR ALL valid OutreachContext inputs, THE StrategyAgent SHALL return a DynamicStrategy containing at least one ChannelStep in `channel_sequence`.
2. FOR ALL valid OutreachContext inputs, THE StrategyAgent SHALL return a DynamicStrategy containing at least one DripStep in `drip_plan`.
3. THE StrategyAgent SHALL set `target_contact_status` to either APPROVED or REJECTED for every DynamicStrategy it returns.
4. WHEN the LLM is unavailable during strategy generation, THE StrategyAgent SHALL execute a type-aware rule-based fallback that selects default channels and drip intervals based on `outreach_type`.
5. THE StrategyAgent SHALL NOT contain hardcoded playbooks; all strategy content SHALL be generated from the OutreachContext and ProspectProfile at runtime.

---

### Requirement 3: ICP Scoring and Rejection Propagation

**User Story:** As a campaign manager, I want prospects scored against my ICP before any strategy or message is generated, so that resources are not spent on poor-fit contacts.

#### Acceptance Criteria

1. THE ResearchAgent SHALL produce an ICPMatchResult with a `score` value in the closed interval [0.0, 1.0] for every prospect profile and ICP dict it evaluates.
2. WHEN an ICPMatchResult has `score` equal to 1.0, THE ResearchAgent SHALL populate `matched_criteria` with at least one criterion.
3. WHEN an ICPMatchResult has `score` equal to 0.0, THE ResearchAgent SHALL populate `failed_criteria` with at least one criterion.
4. WHEN the OutreachContext contains an ICPMatchResult with `recommendation` equal to REJECT, THE StrategyAgent SHALL return a DynamicStrategy with `target_contact_status` equal to REJECTED and a non-empty `rejection_reason`.
5. WHEN `ICPMatchResult.score` is below `icp["min_icp_score"]` (default 0.3), THE OrchestratorAgent SHALL transition to the REJECTED state and log the contact with the score and failed criteria.
6. WHILE `campaign_mode` is BULK_CAMPAIGN, THE OrchestratorAgent SHALL skip rejected contacts and continue processing the next prospect without halting the campaign.

---

### Requirement 4: Behavioral Drip Timing

**User Story:** As an outreach specialist, I want the FollowUpAgent to schedule follow-ups based on prospect engagement behavior rather than fixed calendar intervals, so that engaged prospects are followed up sooner and unengaged prospects receive appropriately spaced messages.

#### Acceptance Criteria

1. FOR ALL valid OutreachContext inputs and engagement signal lists (including empty lists), THE FollowUpAgent SHALL return a DripStep with `days_after_previous` greater than zero.
2. FOR ALL valid OutreachContext inputs, THE FollowUpAgent SHALL return a DripStep with a non-empty `channel` value.
3. WHEN `engagement_signals` is empty, THE FollowUpAgent SHALL use the per-`outreach_type` default drip cadence as the timing source.
4. WHEN an engagement signal of type "open" or "click" is present and the DripStep has `accelerate_on_open` set to True, THE FollowUpAgent SHALL compress the next `days_after_previous` interval by 30% relative to the default.
5. THE FollowUpAgent SHALL derive message themes from `drip_step.message_theme` rather than from the step number alone.

---

### Requirement 5: Opted-Out Contact Protection

**User Story:** As a compliance officer, I want the system to guarantee that contacts who have opted out never receive any outreach messages, so that the platform remains legally compliant and respects user consent.

#### Acceptance Criteria

1. WHEN `OutreachContext.opted_out` is True, THE OutreachAgent SHALL return an empty string or a non-delivery sentinel for any `draft_message` call, regardless of `outreach_type`, `step`, or `DynamicStrategy` content.
2. WHEN `OutreachContext.opted_out` is True, THE OrchestratorAgent SHALL not invoke any message-drafting agent for that contact.
3. THE opted-out check SHALL occur in the OrchestratorAgent before any downstream agent call, ensuring no individual agent can bypass the restriction.

---

### Requirement 6: OutreachContext Serialization and Persistence

**User Story:** As a system operator, I want the OutreachContext to be durably stored and perfectly restored across pipeline restarts, so that campaigns can resume from the correct state after interruptions.

#### Acceptance Criteria

1. FOR ALL valid OutreachContext instances, THE MemoryAgent SHALL serialize the instance to JSON and deserialize it back to an object with all fields equal to the original, with no field dropped or type-coerced.
2. WHEN an OutreachContext is stored by the MemoryAgent and then retrieved by the same MemoryAgent, THE MemoryAgent SHALL return an OutreachContext with `outreach_type`, `outreach_goal`, `campaign_mode`, `opted_out`, `current_drip_step`, `engagement_signals`, and `compliance_flags` equal to the stored values.
3. IF the stored OutreachContext JSON is corrupted or missing required fields, THEN THE MemoryAgent SHALL log the error, reconstruct a minimal context from any available fields (at minimum `contact_id` and `outreach_type` if present), and signal the OrchestratorAgent to re-run classification for the contact.

---

### Requirement 7: Orchestrator Context Threading and State Machine

**User Story:** As a pipeline engineer, I want the OrchestratorAgent to propagate OutreachContext through every agent handoff and manage the new CLASSIFYING and ICP_CHECK states, so that all agents always operate on current, consistent context.

#### Acceptance Criteria

1. WHEN a new lead or goal is received, THE OrchestratorAgent SHALL transition to the CLASSIFYING state and invoke the OutreachClassifierAgent before any other agent.
2. WHEN the OutreachClassifierAgent returns a populated OutreachContext, THE OrchestratorAgent SHALL transition to the RESEARCHING state and store the context at `SwarmState.metadata["outreach_context"]`.
3. WHEN the ResearchAgent returns a ProspectProfile, THE OrchestratorAgent SHALL transition to the ICP_CHECK state and evaluate the ICPMatchResult before proceeding to STRATEGIZING.
4. WHEN `ICPMatchResult.recommendation` is REJECT, THE OrchestratorAgent SHALL transition to the REJECTED terminal state.
5. THE OrchestratorAgent SHALL pass the current OutreachContext to every agent call and update `SwarmState.metadata["outreach_context"]` with the returned context after each call.
6. THE OrchestratorAgent SHALL invoke the MemoryAgent to persist the OutreachContext at each state transition.

---

### Requirement 8: Type-Aware Research and Profiling

**User Story:** As a researcher, I want the ResearchAgent to adjust its research focus based on the outreach type, so that the prospect profile contains the signals most relevant to each campaign mission.

#### Acceptance Criteria

1. WHILE `outreach_type` is INVESTOR, THE ResearchAgent SHALL include portfolio companies, fund stage, and investment thesis in the research scope.
2. WHILE `outreach_type` is RECRUITMENT, THE ResearchAgent SHALL include current role tenure, career trajectory, and open roles at the prospect's company in the research scope.
3. WHILE `outreach_type` is PARTNERSHIP, THE ResearchAgent SHALL include tech stack, integration ecosystem, and shared customer segments in the research scope.
4. WHILE `outreach_type` is EVENT_PROMO, THE ResearchAgent SHALL include past event attendance and community activity in the research scope.
5. THE ResearchAgent SHALL apply ICP scoring via `score_icp_match()` before passing a ProspectProfile to the StrategyAgent.

---

### Requirement 9: Context-Aware Message Drafting

**User Story:** As an outreach specialist, I want the OutreachAgent to tune message framing, tone, and length based on the outreach type and goal, so that every message feels appropriate for its mission rather than generic.

#### Acceptance Criteria

1. WHILE `outreach_type` is INVESTOR, THE OutreachAgent SHALL include credibility signals, traction metrics, and peer-level tone in all drafted messages.
2. WHILE `outreach_type` is RECRUITMENT, THE OutreachAgent SHALL apply candidate-centric framing and growth opportunity emphasis in all drafted messages.
3. WHILE `outreach_type` is PARTNERSHIP, THE OutreachAgent SHALL apply mutual-benefit framing and reference shared audience or technology alignment in all drafted messages.
4. WHILE `outreach_type` is EVENT_PROMO, THE OutreachAgent SHALL include urgency, exclusivity, and a clear RSVP call-to-action in all drafted messages.
5. THE OutreachAgent SHALL derive message length and formality from `DynamicStrategy.tone_directives` rather than from hardcoded defaults.
6. THE OutreachAgent SHALL preserve existing platform routing logic (Email → EmailDraftingAgent, Social → SocialMediaAgent) unchanged.

---

### Requirement 10: Type-Aware Reply Analysis

**User Story:** As a campaign analyst, I want the AnalysisAgent to interpret reply signals in the context of the campaign type, so that positive and negative signals are calibrated correctly per mission.

#### Acceptance Criteria

1. WHEN `analyze_message` is called with an OutreachContext, THE AnalysisAgent SHALL return a `Campaign_Stage_Recommendation` that is one of the four valid values: ADVANCE, PAUSE, ESCALATE_TO_HUMAN, STOP.
2. WHILE `outreach_type` is INVESTOR, THE AnalysisAgent SHALL treat a reply containing "send deck" or equivalent as a high-positive signal.
3. WHILE `outreach_type` is RECRUITMENT, THE AnalysisAgent SHALL treat a reply containing "open to opportunities" or equivalent as a high-positive signal.
4. THE AnalysisAgent SHALL apply type-specific signal taxonomy when scoring reply intent for any `outreach_type`.

---

### Requirement 11: Compliance Flag Enforcement

**User Story:** As a compliance officer, I want mandatory content requirements enforced automatically based on the compliance flags set on the OutreachContext, so that all outgoing messages satisfy legal obligations without manual review.

#### Acceptance Criteria

1. WHEN `OutreachContext.compliance_flags` contains "GDPR", THE OutreachAgent SHALL include an unsubscribe link in every email message it drafts.
2. WHEN `OutreachContext.compliance_flags` contains "CAN-SPAM", THE OutreachAgent SHALL include a physical mailing address in every email message it drafts.
3. THE OutreachAgent SHALL check `compliance_flags` before finalizing any drafted message and apply the corresponding content requirements.
4. THE ResearchAgent and OutreachClassifierAgent SHALL check ICP exclusion lists (competitor companies, opted-out domains) before spending research resources on a contact.

---

### Requirement 12: Multi-Channel Sequence Execution

**User Story:** As a campaign manager, I want the OrchestratorAgent to follow the ordered channel sequence from the DynamicStrategy, so that the system attempts each channel in the correct order and only escalates to the next channel when the trigger condition is met.

#### Acceptance Criteria

1. THE OrchestratorAgent SHALL attempt channels in the order specified by `DynamicStrategy.channel_sequence`, starting with the ChannelStep with the lowest `order` value.
2. WHEN a ChannelStep has `trigger_condition` of "no_reply_after_N_days", THE OrchestratorAgent SHALL wait the specified number of days after the previous attempt before advancing to that channel.
3. WHEN a ChannelStep has `trigger_condition` of "bounce", THE OrchestratorAgent SHALL advance to that channel only if the previous channel produced a delivery bounce.
4. WHEN a ChannelStep has `trigger_condition` of "always", THE OrchestratorAgent SHALL execute that channel step without waiting for a prior-channel result.
5. IF the `channel_sequence` specifies a channel not supported by the OutreachAgent, THEN THE StrategyAgent rule-based fallback SHALL substitute a default channel for that `outreach_type`.
