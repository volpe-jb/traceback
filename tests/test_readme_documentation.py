from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_readme_explains_validation_status_distinction_and_prefetch_absent_example() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "## Validation status meanings" in readme
    assert "Matching evidence exists, but one or more fields conflict with the claim" in readme
    assert "No matching evidence was found for the claim" in readme
    assert "prefetch_absent" in readme
    assert "contradicted rather than unsupported" in readme


def test_readme_explains_streamlit_localhost_and_network_urls() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "UV_LINK_MODE=copy uv run streamlit run streamlit_app.py" in readme
    assert "http://localhost:8501" in readme
    assert "Network URL" in readme
    assert "http://<wsl-or-host-ip>:8501" in readme
