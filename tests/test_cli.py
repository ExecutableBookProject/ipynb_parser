"""Test the quickstart CLI"""

import os
from pathlib import Path

import nbformat
from sphinx import version_info as sphinx_version_info

from myst_nb.cli import md_to_nb, quickstart


def test_quickstart(tmp_path: Path, make_app):
    """Test the quickstart CLI builds a valid sphinx project."""
    project_path = tmp_path / "project"
    quickstart([str(project_path)])
    assert {p.name for p in project_path.iterdir()} == {
        ".gitignore",
        "conf.py",
        "index.md",
        "notebook1.ipynb",
        "notebook2.md",
    }

    # For compatibility with multiple versions of sphinx, convert pathlib.Path to
    # sphinx.testing.path.path here.
    if sphinx_version_info >= (7, 2):
        app_srcdir = project_path
    else:
        from sphinx.testing.path import path

        app_srcdir = path(os.fspath(project_path))

    app = make_app(srcdir=app_srcdir, buildername="html")
    app.build()
    assert app._warning.getvalue().strip() == ""
    assert (project_path / "_build/html/index.html").exists()


def test_md_to_nb(tmp_path: Path):
    """Test the md_to_nb CLI."""
    path = tmp_path / "notebook.md"
    outpath = path.with_suffix(".ipynb")
    path.write_text(
        """\
---
kernelspec:
    name: python3
---
# Title
+++
next cell
""",
        "utf-8",
    )
    md_to_nb([str(path)])
    assert path.exists()
    with outpath.open("r") as handle:
        nb = nbformat.read(handle, as_version=4)
    assert nb.metadata == {"kernelspec": {"display_name": "python3", "name": "python3"}}
    assert len(nb.cells) == 2
