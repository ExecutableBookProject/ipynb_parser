"""Test parsing of already executed notebooks."""

import os
from pathlib import Path

import pytest


@pytest.mark.sphinx_params("basic_run.ipynb", conf={"nb_execution_mode": "off"})
def test_basic_run(sphinx_run, file_regression):
    sphinx_run.build()
    assert sphinx_run.warnings() == ""
    assert set(sphinx_run.env.metadata["basic_run"].keys()) == {
        "test_name",
        "wordcount",
        "kernelspec",
        "language_info",
    }
    assert set(sphinx_run.env.nb_metadata["basic_run"].keys()) == set()
    assert sphinx_run.env.metadata["basic_run"]["test_name"] == "notebook1"
    assert sphinx_run.env.metadata["basic_run"]["kernelspec"] == {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    file_regression.check(
        sphinx_run.get_doctree().pformat(), extension=".xml", encoding="utf-8"
    )

    filenames = {
        p.name
        for p in Path(
            os.fspath(sphinx_run.app.srcdir / "_build" / "jupyter_execute")
        ).iterdir()
    }
    assert filenames == {"basic_run.ipynb"}


@pytest.mark.sphinx_params(
    "basic_run_intl.ipynb", conf={"language": "es", "locale_dirs": ["locale"]}
)
def test_basic_run_intl(sphinx_run, file_regression):
    sphinx_run.build()
    assert sphinx_run.warnings() == ""
    assert set(sphinx_run.env.metadata["basic_run_intl"].keys()) == {
        "test_name",
        "wordcount",
        "kernelspec",
        "language_info",
    }
    assert set(sphinx_run.env.nb_metadata["basic_run_intl"].keys()) == set()
    assert sphinx_run.env.metadata["basic_run_intl"]["test_name"] == "notebook1"
    assert sphinx_run.env.metadata["basic_run_intl"]["kernelspec"] == {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    file_regression.check(
        sphinx_run.get_doctree().pformat(), extension=".xml", encoding="utf-8"
    )

    filenames = {
        p.name
        for p in Path(
            os.fspath(sphinx_run.app.srcdir / "_build" / "jupyter_execute")
        ).iterdir()
    }
    assert filenames == {"basic_run_intl.ipynb"}


@pytest.mark.sphinx_params("complex_outputs.ipynb", conf={"nb_execution_mode": "off"})
def test_complex_outputs(sphinx_run, file_regression):
    sphinx_run.build()
    assert sphinx_run.warnings() == ""

    assert set(sphinx_run.env.metadata["complex_outputs"].keys()) == {
        "ipub",
        "hide_input",
        "nav_menu",
        "celltoolbar",
        "latex_envs",
        "jupytext",
        "toc",
        "varInspector",
        "wordcount",
        "kernelspec",
        "language_info",
    }
    assert set(sphinx_run.env.nb_metadata["complex_outputs"].keys()) == set()
    assert sphinx_run.env.metadata["complex_outputs"]["celltoolbar"] == "Edit Metadata"
    assert sphinx_run.env.metadata["complex_outputs"]["hide_input"] == "False"
    assert sphinx_run.env.metadata["complex_outputs"]["kernelspec"] == {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    doctree_string = sphinx_run.get_doctree().pformat()
    if os.name == "nt":  # on Windows image file paths are absolute
        doctree_string = doctree_string.replace(
            Path(sphinx_run.app.srcdir).as_posix() + "/", ""
        )
    file_regression.check(doctree_string, extension=".xml", encoding="utf-8")

    filenames = {
        p.name.replace(".jpeg", ".jpg")
        for p in Path(
            os.fspath(sphinx_run.app.srcdir / "_build" / "jupyter_execute")
        ).iterdir()
    }
    # print(filenames)
    assert filenames == {
        "16832f45917c1c9862c50f0948f64a498402d6ccde1f3a291da17f240797b160.png",
        "a4c9580c74dacf6f3316a3bd2e2a347933aa4463834dcf1bb8f20b4fcb476ae1.jpg",
        "8c43e5c8cccf697754876b7fec1b0a9b731d7900bb585e775a5fa326b4de8c5a.png",
        "complex_outputs.ipynb",
    }


@pytest.mark.sphinx_params(
    "latex_build/index.ipynb",
    "latex_build/other.ipynb",
    conf={"nb_execution_mode": "off"},
    buildername="latex",
)
def test_toctree_in_ipynb(sphinx_run, file_regression):
    sphinx_run.build()
    print(sphinx_run.status())
    print(sphinx_run.warnings())
    file_regression.check(
        sphinx_run.get_doctree("latex_build/other").pformat(), extension=".xml"
    )
    assert sphinx_run.warnings() == ""


@pytest.mark.sphinx_params("ipywidgets.ipynb", conf={"nb_execution_mode": "off"})
def test_ipywidgets(sphinx_run):
    """Test that ipywidget state is extracted and JS is included in the HTML head."""
    sphinx_run.build()
    # print(sphinx_run.status())
    assert sphinx_run.warnings() == ""
    assert "js_files" in sphinx_run.env.nb_metadata["ipywidgets"]
    assert set(sphinx_run.env.nb_metadata["ipywidgets"]["js_files"]) == {
        "ipywidgets_state",
        "ipywidgets_0",
        "ipywidgets_1",
    }
    head_scripts = sphinx_run.get_html().select("head > script")
    assert any("require.js" in script.get("src", "") for script in head_scripts)
    assert any("embed-amd.js" in script.get("src", "") for script in head_scripts)
