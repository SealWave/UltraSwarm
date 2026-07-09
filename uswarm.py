#!/usr/bin/env python3
"""
🐝 UltraSwarm CLI — Standalone entry point

This is the modern CLI replacement for main.py with full multi-agent control,
skill management, knowledge base queries, and orchestration.

Usage:
    uswarm.py agent list                           # List all agents
    uswarm.py agent run seo                        # Run an agent
    uswarm.py agent create my_agent --type worker  # Create new agent
    uswarm.py skill list                           # List all skills
    uswarm.py rag query "How to optimize?"         # Query knowledge base
    uswarm.py swarm run product                    # Run a swarm
    uswarm.py swarm apex --goal "Your goal"        # Supreme Orchestrator
    uswarm.py                                      # Interactive menu
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

# Import and run the CLI app
from cli.main import app

if __name__ == "__main__":
    app()
