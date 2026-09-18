from pathlib import Path


def test_required_deployment_assets_exist() -> None:
    root = Path(__file__).parents[1]
    assert (root / "app.py").exists()
    assert (root / "infrastructure" / "product_stack.py").exists()
    assert (root / "infrastructure" / "agentcore_stack.py").exists()
    assert (root / "runtime" / "code" / "agentcore_entrypoint.py").exists()
