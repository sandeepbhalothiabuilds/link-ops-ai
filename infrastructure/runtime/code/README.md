# AgentCore runtime package

package_agentcore.py copies the application package and dependencies into the build
output. The entry point is agentcore_entrypoint.py; it calls the same LangGraph runner
used locally and keeps auto_approve false unless explicitly provided by an approved
caller.
