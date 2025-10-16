"""Shared Slack bot metadata."""

COMMAND_DESCRIPTIONS = {
    "/files": "List up to 25 depot files matching the given pattern (defaults to //...).",
    "/describe": "Show a summary of the specified changelist (`/describe 12345`).",
    "/changes": "List the 10 most recent submitted changelists for an optional path.",
    "/locked": "Show files currently opened for edit; exclusive locks are flagged with :lock:.",
    "/health": "Run `p4 login -s` to confirm the service account is authenticated.",
}
