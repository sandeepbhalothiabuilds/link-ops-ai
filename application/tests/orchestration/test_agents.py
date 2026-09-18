from linkops_ai.orchestration.agents import CodebaseAnalyst, PlannerAgent, RequirementsAgent


def test_requirements_agent_identifies_high_impact_ambiguity() -> None:
    result = RequirementsAgent().normalize(
        "Make analytics privacy-friendly and near real time.", "ambiguous"
    )
    assert result.ambiguities[0].severity == "high"
    assert len(result.acceptance_criteria) >= 5


def test_planner_adds_codebase_analysis_only_for_brownfield() -> None:
    agent = RequirementsAgent()
    green = PlannerAgent().plan(agent.normalize("Build a URL shortener.", "greenfield"))
    brown = PlannerAgent().plan(
        agent.normalize("Enhance the existing URL shortener.", "brownfield")
    )
    assert "T-REPO" not in {task.task_id for task in green.tasks}
    assert "T-REPO" in {task.task_id for task in brown.tasks}


def test_codebase_analyst_returns_a_repo_map(tmp_path) -> None:
    (tmp_path / "example.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
    impact = CodebaseAnalyst().analyze(str(tmp_path))
    assert "example.py" in impact.files
    assert "Demo" in impact.modules
