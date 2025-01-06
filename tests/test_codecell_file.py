"""Test notebooks containing code cells with the `load` option."""

import pytest
from sphinx.util.fileutil import copy_asset_file


@pytest.mark.sphinx_params(
    "mystnb_codecell_file.md",
    conf={"nb_execution_mode": "cache", "source_suffix": {".md": "myst-nb"}},
)
def test_codecell_file(sphinx_run, file_regression, check_nbs, get_test_path):
    asset_path = get_test_path("mystnb_codecell_file.py")
    copy_asset_file(str(asset_path), str(sphinx_run.app.srcdir))
    sphinx_run.build()
    assert sphinx_run.warnings() == ""
    assert set(sphinx_run.env.metadata["mystnb_codecell_file"].keys()) == {
        "jupytext",
        "author",
        "source_map",
        "wordcount",
        "kernelspec",
        "language_info",
    }
    assert set(sphinx_run.env.nb_metadata["mystnb_codecell_file"].keys()) == {
        "exec_data",
    }
    assert sphinx_run.env.metadata["mystnb_codecell_file"]["author"] == "Matt"
    assert sphinx_run.env.metadata["mystnb_codecell_file"]["kernelspec"] == {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    try:
        file_regression.check(
            sphinx_run.get_nb(),
            check_fn=check_nbs,
            extension=".ipynb",
            encoding="utf-8",
        )
    finally:
        file_regression.check(
            sphinx_run.get_doctree().pformat(), extension=".xml", encoding="utf-8"
        )


@pytest.mark.sphinx_params(
    "mystnb_codecell_file_warnings.md",
    conf={"nb_execution_mode": "force", "source_suffix": {".md": "myst-nb"}},
)
def test_codecell_file_warnings(sphinx_run, file_regression, check_nbs, get_test_path):
    asset_path = get_test_path("mystnb_codecell_file.py")
    copy_asset_file(str(asset_path), str(sphinx_run.app.srcdir))
    sphinx_run.build()
    # assert (
    #     "mystnb_codecell_file_warnings.md:14 content of code-cell "
    #     "is being overwritten by :load: mystnb_codecell_file.py"
    #     in sphinx_run.warnings()
    # )
    assert set(sphinx_run.env.metadata["mystnb_codecell_file_warnings"].keys()) == {
        "jupytext",
        "author",
        "source_map",
        "wordcount",
        "kernelspec",
        "language_info",
    }
    assert set(sphinx_run.env.nb_metadata["mystnb_codecell_file_warnings"].keys()) == {
        "exec_data",
    }
    assert (
        sphinx_run.env.metadata["mystnb_codecell_file_warnings"]["author"] == "Aakash"
    )
    assert sphinx_run.env.metadata["mystnb_codecell_file_warnings"]["kernelspec"] == {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    try:
        file_regression.check(
            sphinx_run.get_nb(),
            check_fn=check_nbs,
            extension=".ipynb",
            encoding="utf-8",
        )
    finally:
        file_regression.check(
            sphinx_run.get_doctree().pformat(), extension=".xml", encoding="utf-8"
        )
