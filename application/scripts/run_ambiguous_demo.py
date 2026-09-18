from pathlib import Path

from linkops_ai.orchestration.runner import WorkflowRunner

runner = WorkflowRunner(Path.cwd())
requirement = "Make the analytics privacy-friendly and near real time."
run_id = "demo-ambiguous"
result = runner.run(requirement, "ambiguous", run_id=run_id)
print(result.status, result.approval_requests)
for gate in ("requirements", "architecture", "release"):
    result = runner.resume(run_id, requirement, "ambiguous", gate)
    print(gate, result.status, result.approval_requests)
