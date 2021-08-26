import pytest


@pytest.mark.sphinx_params(
    "basic_unrun.md",
    conf={"jupyter_execute_notebooks": "cache", "source_suffix": {".md": "myst-nb"}},
)
def test_basic_run(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    # print(sphinx_run.status())
    assert sphinx_run.warnings() == ""
    assert set(sphinx_run.app.env.metadata["basic_unrun"].keys()) == {
        "jupytext",
        "kernelspec",
        "author",
        "source_map",
        "language_info",
        "wordcount",
    }
    assert sphinx_run.app.env.metadata["basic_unrun"]["author"] == "Chris"
    assert (
        sphinx_run.app.env.metadata["basic_unrun"]["kernelspec"]
        == '{"display_name": "Python 3", "language": "python", "name": "python3"}'
    )
    file_regression.check(
        sphinx_run.get_nb(),
        check_fn=check_nbs,
        extension=f"{sphinx_run.software_versions}.ipynb",
        encoding="utf8",
    )
    file_regression.check(
        sphinx_run.get_doctree().pformat(),
        extension=f"{sphinx_run.software_versions}.xml",
        encoding="utf8",
    )


@pytest.mark.sphinx_params(
    "basic_unrun.md",
    conf={"jupyter_execute_notebooks": "off", "source_suffix": {".md": "myst-nb"}},
)
def test_basic_run_exec_off(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    # print(sphinx_run.status())
    assert "language_info" not in set(sphinx_run.app.env.metadata["basic_unrun"].keys())
    assert sphinx_run.app.env.metadata["basic_unrun"]["author"] == "Chris"

    file_regression.check(
        sphinx_run.get_nb(),
        check_fn=check_nbs,
        extension=f"{sphinx_run.software_versions}.ipynb",
        encoding="utf8",
    )
    file_regression.check(
        sphinx_run.get_doctree().pformat(),
        extension=f"{sphinx_run.software_versions}.xml",
        encoding="utf8",
    )


@pytest.mark.sphinx_params(
    "basic_nometadata.md",
    conf={"jupyter_execute_notebooks": "off", "source_suffix": {".md": "myst-nb"}},
)
def test_basic_nometadata(sphinx_run, file_regression, check_nbs):
    """A myst-markdown notebook with no jupytext metadata should raise a warning."""
    sphinx_run.build()
    # print(sphinx_run.status())
    assert "Found an unexpected `code-cell` directive." in sphinx_run.warnings()
