"""
agents/fiverr/shared/config.py

Environment-based configuration for the Fiverr automation sub-swarm.

All credentials and settings are loaded exclusively from environment variables
via os.environ.get(). No credential values are hardcoded here. This module
is safe to import at any time — it will never raise an exception due to a
missing environment variable; safe defaults are used instead.

Set these variables in your shell or .env file before running:

    FIVERR_USERNAME         - Your Fiverr account username
    FIVERR_PASSWORD         - Your Fiverr account password
    NOTIFICATION_EMAIL      - Email address to receive event alerts
    NOTIFICATION_WEBHOOK_URL - Webhook URL for SMS/Slack/push notifications
    SMTP_HOST               - SMTP server hostname (e.g. smtp.gmail.com)
    SMTP_PORT               - SMTP server port number (default: 25)
    SMTP_USER               - SMTP authentication username
    SMTP_PASSWORD           - SMTP authentication password
    AUTO_REPLY              - Set to "true" (case-insensitive) to enable
                              automatic inbox replies; any other value = False
"""

import os

# ---------------------------------------------------------------------------
# Fiverr account credentials
# ---------------------------------------------------------------------------

# The Fiverr seller account username used for browser-based login automation.
# Defaults to an empty string so the module imports cleanly when the variable
# is not yet configured; agents that require login will surface an error at
# runtime rather than at import time.
FIVERR_USERNAME: str = os.environ.get("FIVERR_USERNAME", "")

# The Fiverr seller account password used for browser-based login automation.
# Never hardcoded; must be supplied via environment variable at runtime.
FIVERR_PASSWORD: str = os.environ.get("FIVERR_PASSWORD", "")

# ---------------------------------------------------------------------------
# Notification channel configuration
# ---------------------------------------------------------------------------

# Email address to which the Notification_Agent will send event alerts
# (new orders, messages, deadline warnings, etc.).
# Defaults to empty string; Notification_Agent treats an empty value as
# "channel not configured" and skips email dispatch.
NOTIFICATION_EMAIL: str = os.environ.get("NOTIFICATION_EMAIL", "")

# Webhook URL for HTTP POST-based notification delivery (e.g. Slack incoming
# webhook, SMS gateway, or mobile push service).
# Defaults to empty string; Notification_Agent treats an empty value as
# "channel not configured" and skips webhook dispatch.
NOTIFICATION_WEBHOOK_URL: str = os.environ.get("NOTIFICATION_WEBHOOK_URL", "")

# ---------------------------------------------------------------------------
# SMTP credentials (used by Notification_Agent for email dispatch)
# ---------------------------------------------------------------------------

# Hostname or IP address of the SMTP mail server.
# Example values: "smtp.gmail.com", "smtp.sendgrid.net", "localhost"
SMTP_HOST: str = os.environ.get("SMTP_HOST", "")

# Port number for the SMTP connection as a string.
# Common values: "25" (plain), "465" (SSL), "587" (STARTTLS).
# Defaults to "25" per requirement 8.7; callers should cast to int when
# opening the SMTP connection.
SMTP_PORT: str = os.environ.get("SMTP_PORT", "25")

# Username for SMTP authentication.
# Often identical to the sender email address for hosted mail providers.
SMTP_USER: str = os.environ.get("SMTP_USER", "")

# Password for SMTP authentication.
# Never hardcoded; must be supplied via environment variable at runtime.
SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")

# ---------------------------------------------------------------------------
# Behavioural flags
# ---------------------------------------------------------------------------

# Controls whether the Inbox_Communication_Agent automatically sends
# generated replies inside the Fiverr inbox via browser automation.
#
# True  - replies are sent automatically (AUTO_REPLY env var == "true",
#         case-insensitive comparison, so "True", "TRUE", "true" all work)
# False - replies are returned in the result dict for manual review
#         (default when env var is absent, empty, or any other value)
AUTO_REPLY: bool = os.environ.get("AUTO_REPLY", "").lower() == "true"
