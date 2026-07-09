# UltraSwarm Infrastructure & Architecture Documentation

Welcome to the **UltraSwarm** infrastructure guide. This document provides a comprehensive overview of the entire codebase architecture, detailing how the multi-agent system operates, communicates, and manages complex tasks.

## Table of Contents
1. [System Overview & Philosophy](#1-system-overview--philosophy)
2. [The Orchestrators](#2-the-orchestrators)
3. [Agent Communication Protocol](#3-agent-communication-protocol)
4. [Newly Added External Agents](#4-newly-added-external-agents)
5. [RAG System (Knowledge Retrieval)](#5-rag-system-knowledge-retrieval)
6. [The Skills System](#6-the-skills-system)
7. [Tools & Capabilities](#7-tools--capabilities)

---

## 1. System Overview & Philosophy

The system is a **dynamic multi-agent orchestration framework** powered by a Large Language Model (e.g., Gemini 2.5 Flash). Instead of hardcoding pipelines, the framework takes high-level user goals, automatically decomposes them into subtasks, and assigns them to the best-suited specialist agent.

**Agent Hierarchy:**
* **Managers (Tier 1):** Plan, route, and monitor task execution. They communicate with helpers and workers but do not execute domain actions directly.
* **Helpers (Tier 2):** Perform cognitive or utility tasks (e.g., decomposing a task into a plan). They have no downstream side effects.
* **Workers (Tier 3):** Execute specific domain actions (e.g., web research, SEO analysis) using tools and APIs.

**Core Rules:**
* Agents are **stateless** between calls. Context is explicitly passed down.
* Agents never talk directly to each other; all routing flows through the **Orchestrator** and **Allocator**.
* Capabilities are defined strictly by the **Skills** injected into an agent's prompt.

---

## 2. The Orchestrators

At the heart of the swarm are the manager agents that govern task execution.

### Orchestrator Agent (`orchestrator_agent.py`)
The Orchestrator is the "boss" of the system. Its lifecycle is as follows:
1. Receives a natural language goal from the user.
2. Calls the **ThinkingAgent** (a helper) to decompose the goal into a structured JSON plan with specific subtasks.
3. Iterates over each subtask and calls the **AllocatorAgent**.
4. Dispatches the subtask to the selected worker agent.
5. Collects the results, handles retries on failures, passes context to the next agent in the chain, and finally synthesizes a response for the user.

### Allocator Agent (`allocator_agent.py`)
The Allocator is the "dispatcher."
* It receives a subtask description from the Orchestrator along with a registry of all available agents and their metadata (skills, descriptions).
* It uses the LLM to analyze the task requirements and dynamically selects the single best agent for the job.
* It does not execute the task itself, returning only the name of the assigned agent.

---

## 3. Agent Communication Protocol

Agents do not "chat" with each other randomly. The communication is highly structured and centrally managed:

1. **Context Passing:** The Orchestrator collects the output of Step N and passes it into the `context` dictionary for Step N+1. 
2. **`AgentResult` Schema:** Every agent's `run()` method must return a strict `AgentResult` object (defined in `core/result_schema.py`). 
   * `success` (bool)
   * `agent_name` (str)
   * `task_id` (str)
   * `output` (Any)
   * `error` (str, optional)
   * `context_for_next` (dict) - Crucial for passing downstream data.

If a worker fails, it returns an error in the schema. The Orchestrator decides whether to retry the task or abort the entire plan based on the subtask's criticality.

---

## 4. Newly Added External Agents

The swarm has been recently expanded with the **500-AI-Agents integration**, adding several powerful external agents located in `agents/external/`:

* **Web Research Agent (`web_research_agent.py`):** Dedicated to browsing the web, searching, and synthesizing information on any given topic.
* **Email Drafting Agent (`email_drafting_agent.py`):** Specializes in writing professional, context-aware emails based on user prompts.
* **Stock Research Agent (`stock_research_agent.py`):** Analyzes financial data, market trends, and investment opportunities.
* **Customer Support Agent (`customer_support_agent.py`):** Acts as a support representative to draft responses for customer tickets and inquiries.
* **Social Media Agent (`social_media_agent.py`):** Creates engaging multi-platform social media content (scripts, posts, threads).
* **Unit Test Generator Agent (`unit_test_generator_agent.py`):** A developer-focused agent that writes unit tests for provided code snippets.
* **Competitive Analysis Agent (`competitive_analysis_agent.py`):** Gathers competitive intelligence, comparing products, pricing, and strategies.
* **Multi-Agent Debate Agent (`multi_agent_debate_agent.py`):** Facilitates a FOR vs. AGAINST analysis, exploring multiple perspectives on a topic.

These agents are registered in the Orchestrator's registry and can be dynamically allocated tasks just like the core e-commerce agents (SERAPH, SCOUT, PULSE, etc.).

---

## 5. RAG System (Knowledge Retrieval)

The Retrieval-Augmented Generation (RAG) system (`core/rag_manager.py`) empowers agents to search and access local knowledge bases effectively.

* **Document Loading & Chunking:** Uses `langchain` (`DirectoryLoader`, `TextLoader`) and `RecursiveCharacterTextSplitter` to ingest Markdown (`.md`) and Text (`.txt`) files from the `knowledge/` directory, breaking them into overlapping 1000-character chunks.
* **Vector Store (`Turbovec`):** Utilizes `Turbovec` for fast, lightweight local vector storage. Documents are embedded and indexed for quick semantic retrieval.
* **Fallback Mechanism:** If `Turbovec` fails to initialize (e.g., due to missing embedding models), the RAG manager falls back to a custom keyword overlap ranking algorithm. It extracts keywords from the query and scores document chunks based on exact term matches.

When an agent needs context, it queries the `RAGManager`, which returns the top 3 most relevant context blocks.

---

## 6. The Skills System

Agents derive their capabilities entirely from **Skills**. A skill is not Python code; it is a JSON contract loaded at runtime (`tools/skill_loader.py`).

**How it Works:**
* Located in the `skills/` directory (e.g., `google_search_skill.json`).
* A skill JSON defines:
  * `input_schema` and `output_schema`
  * Specific `instructions` and `constraints`
  * `tool_dependencies`
* When an agent initializes, the `skill_loader` reads its assigned skills, converts the JSON into a structured Markdown block, and injects it into the agent's core `system_prompt`.
* This ensures the LLM strictly adheres to the input/output formatting expected by the system. The Orchestrator can even dynamically inject *extra* skills into a worker agent at runtime if a task demands it.

---

## 7. Tools & Capabilities

Tools are raw Python functions invoked by agents to interact with the outside world.

* **Browser Operations (`tools/browser.py`):**
  * Powered by `browser-use`.
  * Supports real browser automation via Playwright/Chrome.
  * Agents can perform dynamic actions: `navigate`, `click`, `type`, `scroll`, and `snapshot`.
  * Incorporates a lightweight DuckDuckGo HTML parser for fast, API-free search capabilities (`google_search(query)`).
* **Tool Separation:** Unlike agents, tools have no cognitive logic. They strictly execute code and return data (e.g., extracting titles and text, fetching SEO data). Workers decide *when* and *how* to use these tools based on their assigned Skills.
