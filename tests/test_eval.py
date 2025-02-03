"""Test the `eval` directives and roles."""

import pytest


@pytest.mark.sphinx_params("with_eval.md", conf={"nb_execution_mode": "inline"})
def test_sphinx(sphinx_run, clean_doctree, file_regression):
    """Test a sphinx build."""
    sphinx_run.build()
    # print(sphinx_run.status())
    # print(sphinx_run.warnings())
    assert sphinx_run.warnings() == ""
    doctree = clean_doctree(sphinx_run.get_resolved_doctree("with_eval"))
    file_regression.check(
        doctree.pformat(),
        encoding="utf-8",
    )
