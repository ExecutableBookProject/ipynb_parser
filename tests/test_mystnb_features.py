import pytest
from sphinx.util.fileutil import copy_asset_file


@pytest.mark.sphinx_params(
    "mystnb_codecell_file.md",
    conf={"jupyter_execute_notebooks": "cache", "source_suffix": {".md": "myst-nb"}},
)
def test_codecell_file(sphinx_run, file_regression, check_nbs, get_test_path):
    asset_path = get_test_path("mystnb_codecell_file.py")
    copy_asset_file(str(asset_path), str(sphinx_run.app.srcdir))
    sphinx_run.build()
    assert sphinx_run.warnings() == ""
    assert set(sphinx_run.app.env.metadata["mystnb_codecell_file"].keys()) == {
        "jupytext",
        "kernelspec",
        "author",
        "source_map",
        "language_info",
        "wordcount",
    }
    assert sphinx_run.app.env.metadata["mystnb_codecell_file"]["author"] == "Matt"
    assert (
        sphinx_run.app.env.metadata["mystnb_codecell_file"]["kernelspec"]
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
    "mystnb_codecell_file_warnings.md",
    conf={"jupyter_execute_notebooks": "force", "source_suffix": {".md": "myst-nb"}},
)
def test_codecell_file_warnings(sphinx_run, file_regression, check_nbs, get_test_path):
    asset_path = get_test_path("mystnb_codecell_file.py")
    copy_asset_file(str(asset_path), str(sphinx_run.app.srcdir))
    sphinx_run.build()
    assert (
        "mystnb_codecell_file_warnings.md:14 content of code-cell "
        "is being overwritten by :load: mystnb_codecell_file.py"
        in sphinx_run.warnings()
    )
    assert set(sphinx_run.app.env.metadata["mystnb_codecell_file_warnings"].keys()) == {
        "jupytext",
        "kernelspec",
        "author",
        "source_map",
        "language_info",
        "wordcount",
    }
    assert (
        sphinx_run.app.env.metadata["mystnb_codecell_file_warnings"]["author"]
        == "Aakash"
    )
    assert (
        sphinx_run.app.env.metadata["mystnb_codecell_file_warnings"]["kernelspec"]
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
