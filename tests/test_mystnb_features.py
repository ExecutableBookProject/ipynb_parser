import pytest


@pytest.mark.sphinx_params(
    "mystnb_codecell_file.md",
    conf={"jupyter_execute_notebooks": "cache", "source_suffix": {".md": "myst-nb"}},
)
def test_codecell_file(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    assert sphinx_run.warnings() == ""
    assert set(sphinx_run.app.env.metadata["mystnb_codecell_file"].keys()) == {
        "jupytext",
        "kernelspec",
        "author",
        "source_map",
        "language_info",
    }
    assert sphinx_run.app.env.metadata["mystnb_codecell_file"]["author"] == "Matt"
    assert (
        sphinx_run.app.env.metadata["mystnb_codecell_file"]["kernelspec"]
        == '{"display_name": "Python 3", "language": "python", "name": "python3"}'
    )
    file_regression.check(
        sphinx_run.get_nb(), check_fn=check_nbs, extension=".ipynb", encoding="utf8"
    )
    file_regression.check(
        sphinx_run.get_doctree().pformat(), extension=".xml", encoding="utf8"
    )