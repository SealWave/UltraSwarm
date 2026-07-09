# AI Outreach Swarm

This swarm is designed for highly automated, multi-avenue, multi-platform outreach. It leverages an event-driven architecture to keep resources low while automating the entire sales and outreach pipeline, from initial research to follow-ups.

## Features

- **Multi-Platform Support**: Email, WhatsApp, LinkedIn, Facebook, Instagram, Telegram, SMS.
- **Event-Driven**: Agents sleep until they are needed (e.g., when a prospect replies).
- **Personalized**: Extensive research is done before sending any message.
- **Persistent Memory**: Maintains deep context across multiple platforms and sessions.
- **Intelligent Analysis**: Replaces simple emotion detection with structured intent, objection, and urgency extraction.

## Agent Descriptions

1. **Orchestrator Agent**: The central brain. Coordinates the overall workflow, assigning tasks to the specialized agents and handling failures/retries.
2. **Research Agent**: Gathers public information (LinkedIn, Website, Facebook) prior to outreach to ensure messages are personalized.
3. **Strategy Agent**: Decides the campaign goal, the best platform, the best time to send, and the follow-up strategy.
4. **Outreach Agent**: Responsible for all outgoing communication. Writes and sends personalized messages across platforms, handles basic objections, and books meetings.
5. **Analysis Agent**: Processes every incoming message, converting free-form text into structured data (Emotion, Interest, Intent, Objections, Urgency, Next Action).
6. **Memory Agent**: Stores all conversation history, pain points, and objections so the AI maintains context between messages.
7. **Follow-up Agent**: Manages the drip sequence (e.g., Day 1, Day 3, Day 7, Day 14). Stops automatically if the prospect replies.
8. **Notification Watcher**: The only continuously running component. Listens for incoming replies on supported platforms and wakes the rest of the swarm.

## Overall Workflow

1. Lead Found
2. **Research Agent** gathers info.
3. **Strategy Agent** plans outreach.
4. **Outreach Agent** sends message.
5. System Waits.
6. **Notification Watcher** detects a new reply.
7. **Analysis Agent** processes the reply.
8. **Memory Agent** updates history.
9. **Outreach Agent** replies again (or **Follow-up Agent** triggers if no reply).

## Future Improvements

- Multi-language conversations
- AI-generated images for outreach
- CRM synchronization
- A/B testing of outreach messages
- Lead scoring & sales pipeline prediction
- RAG Integration & Human-in-the-loop workflows
