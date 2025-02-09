import json
import os
from pathlib import Path
import re
import uuid
import shutil

import bs4
from docutils.nodes import image as image_node
from nbconvert.filters import strip_ansi
from nbdime.diffing.notebooks import (
    diff_notebooks,
    set_notebook_diff_ignores,
    set_notebook_diff_targets,
)
from nbdime.prettyprint import pretty_print_diff
import nbformat as nbf
import pytest
import sphinx
from sphinx import version_info as sphinx_version_info
from sphinx.util.console import nocolor

pytest_plugins = "sphinx.testing.fixtures"

# -Diff Configuration-#
NB_VERSION = 4
set_notebook_diff_ignores({"/nbformat_minor": True})
set_notebook_diff_targets(metadata=False)

TEST_FILE_DIR = Path(__file__).parent.joinpath("notebooks")


@pytest.fixture(autouse=True, scope="session")
def build_matplotlib_font_cache():
    """This is to mitigate errors on CI VMs, where you can get the message:
    "Matplotlib is building the font cache" in output notebooks
    """
    from matplotlib.font_manager import FontManager

    FontManager()


def _split_ext(conf, sphinx_params):
    if custom_formats := conf.get("nb_custom_formats"):
        split_files = [
            file.rstrip(k)
            for file in sphinx_params["files"]
            for k in custom_formats.keys()
            if file.endswith(k)
        ]
    else:
        split_files = [os.path.splitext(file)[0] for file in sphinx_params["files"]]

    return split_files[0], split_files


@pytest.fixture()
def get_test_path():
    def _get_test_path(name):
        return TEST_FILE_DIR.joinpath(name)

    return _get_test_path


class SphinxFixture:
    """A class returned by the ``sphinx_run`` fixture, to run sphinx,
    and retrieve aspects of the build.
    """

    def __init__(self, app, filenames):
        self.app = app
        self.env = app.env
        self.files = filenames
        self.software_versions = (
            f".sphinx{sphinx.version_info[0]}"  # software version tracking for fixtures
        )

        # self.nb_file = nb_file
        # self.nb_name = os.path.splitext(nb_file)[0]

    def build(self):
        """Run the sphinx build."""
        # TODO reset streams before each build,
        # but this was wiping the warnings of a build
        self.app.build()

    def status(self):
        """Return the stdout stream of the sphinx build."""
        return self.app._status.getvalue().strip()

    def warnings(self):
        """Return the stderr stream of the sphinx build."""
        return self.app._warning.getvalue().strip()

    def invalidate_files(self):
        """Invalidate the files, such that it will be flagged for a re-read."""
        for name in self.files:
            self.env.all_docs.pop(name)

    def get_resolved_doctree(self, docname=None):
        """Load and return the built docutils.document, after post-transforms."""
        docname = docname or self.files[0]
        doctree = self.env.get_and_resolve_doctree(docname, self.app.builder)
        doctree["source"] = docname
        return doctree

    def get_doctree(self, docname=None):
        """Load and return the built docutils.document."""
        docname = docname or self.files[0]
        doctree = self.env.get_doctree(docname)
        doctree["source"] = docname
        return doctree

    def get_html(self, index=0):
        """Return the built HTML file."""
        name = self.files[index]
        _path = self.app.outdir / (name + ".html")
        if not _path.exists():
            pytest.fail("html not output")
        return bs4.BeautifulSoup(_path.read_text(), "html.parser")

    def get_latex(self, index=0):
        """Return the built LaTeX file."""
        name = self.files[index][0]
        _path = self.app.outdir / (name + ".tex")
        if not _path.exists():
            pytest.fail("tex not output")
        return _path.read_text(encoding="utf-8")

    def get_nb(self, index=0):
        """Return the output notebook (after any execution)."""
        name = self.files[index]
        _path = self.app.srcdir / "_build" / "jupyter_execute" / (name + ".ipynb")
        if not _path.exists():
            pytest.fail("notebook not output")
        return _path.read_text(encoding="utf-8")

    def get_report_file(self, index=0):
        """Return the report file for a failed execution."""
        name = self.files[index]
        _path = self.app.outdir / "reports" / (name + ".err.log")
        if not _path.exists():
            pytest.fail("report log not output")
        return _path.read_text()


@pytest.fixture()
def sphinx_params(request):
    """Parameters that are specified by 'pytest.mark.sphinx_params'
    are passed to the ``sphinx_run`` fixture::

        @pytest.mark.sphinx_params("name.ipynb", conf={"option": "value"})
        def test_something(sphinx_run):
            ...

    The first file specified here will be set as the master_doc
    """
    markers = request.node.iter_markers("sphinx_params")
    kwargs = {}
    if markers is not None:
        for info in reversed(list(markers)):
            kwargs.update(info.kwargs)
            kwargs["files"] = info.args
    return kwargs


@pytest.fixture()
def sphinx_run(sphinx_params, make_app, tmp_path):
    """A fixture to setup and run a sphinx build, in a sandboxed folder.

    The `myst_nb` extension is added by default,
    and the first file will be set as the masterdoc

    """
    assert len(sphinx_params["files"]) > 0, sphinx_params["files"]
    conf = sphinx_params.get("conf", {})
    buildername = sphinx_params.get("buildername", "html")

    master_doc, split_files = _split_ext(conf, sphinx_params)

    confoverrides = {
        "extensions": ["myst_nb"],
        "master_doc": master_doc,
        "exclude_patterns": ["_build"],
        "nb_execution_show_tb": True,
    }
    confoverrides.update(conf)

    current_dir = os.getcwd()
    if "working_dir" in sphinx_params:
        base_dir = Path(sphinx_params["working_dir"]) / str(uuid.uuid4())
    else:
        base_dir = tmp_path
    srcdir = base_dir / "source"
    srcdir.mkdir(exist_ok=True)
    os.chdir(base_dir)
    (srcdir / "conf.py").write_text(
        "# conf overrides (passed directly to sphinx):\n"
        + "\n".join(
            ["# " + ll for ll in json.dumps(confoverrides, indent=2).splitlines()]
        )
        + "\n"
    )
    if "language" in conf:
        shutil.copytree(TEST_FILE_DIR / "locale", srcdir / "locale")

    for nb_file in sphinx_params["files"]:
        nb_path = TEST_FILE_DIR.joinpath(nb_file)
        assert nb_path.exists(), nb_path
        (srcdir / nb_file).parent.mkdir(exist_ok=True)
        (srcdir / nb_file).write_text(
            nb_path.read_text(encoding="utf-8"), encoding="utf-8"
        )

    nocolor()

    # For compatibility with multiple versions of sphinx, convert pathlib.Path to
    # sphinx.testing.path.path here.
    if sphinx_version_info >= (7, 2):
        app_srcdir = srcdir
    else:
        from sphinx.testing.path import path

        app_srcdir = path(os.fspath(srcdir))
    app = make_app(
        buildername=buildername, srcdir=app_srcdir, confoverrides=confoverrides
    )

    yield SphinxFixture(app, split_files)

    # reset working directory
    os.chdir(current_dir)


def empty_non_deterministic_outputs(cell):
    if "outputs" in cell and len(cell.outputs):
        for item in cell.outputs:
            if "data" in item and "image/png" in item.data:
                item.data["image/png"] = ""
            if "filenames" in item.get("metadata", {}):
                item["metadata"]["filenames"] = {
                    k: os.path.basename(v)
                    for k, v in item["metadata"]["filenames"].items()
                }
            if "traceback" in item:
                item["traceback"] = [strip_ansi(line) for line in item["traceback"]]


@pytest.fixture()
def check_nbs():
    def _check_nbs(obtained_filename, expected_filename):
        obtained_nb = nbf.read(str(obtained_filename), nbf.NO_CONVERT)
        expect_nb = nbf.read(str(expected_filename), nbf.NO_CONVERT)
        obtained_nb.nbformat_minor = 5
        expect_nb.nbformat_minor = 5
        for cell in expect_nb.cells:
            empty_non_deterministic_outputs(cell)
            cell.id = "none"
        for cell in obtained_nb.cells:
            empty_non_deterministic_outputs(cell)
            cell.id = "none"
        diff = diff_notebooks(obtained_nb, expect_nb)
        filename_without_path = str(expected_filename)[
            str(expected_filename).rfind("/") + 1 :
        ]
        if diff:
            raise AssertionError(
                pretty_print_diff(obtained_nb, diff, str(filename_without_path))
            )

    return _check_nbs


@pytest.fixture()
def clean_doctree():
    def _func(doctree):
        if os.name == "nt":  # on Windows file paths are absolute
            findall = getattr(doctree, "findall", doctree.traverse)
            for node in findall(image_node):  # type: image_node
                if "candidates" in node:
                    node["candidates"]["*"] = (
                        "_build/jupyter_execute/"
                        + os.path.basename(node["candidates"]["*"])
                    )
                if "uri" in node:
                    node["uri"] = "_build/jupyter_execute/" + os.path.basename(
                        node["uri"]
                    )
        return doctree

    return _func


# comparison files will need updating
# alternatively the resolution of https://github.com/ESSS/pytest-regressions/issues/32
@pytest.fixture()
def file_regression(file_regression):
    return FileRegression(file_regression)


class FileRegression:
    ignores = (
        # TODO: Remove when support for Sphinx<=6 is dropped,
        re.escape(" translation_progress=\"{'total': 0, 'translated': 0}\""),
        # TODO: Remove when support for Sphinx<7.2 is dropped,
        r"original_uri=\"[^\"]*\"\s",
        # TODO: Remove when support for Sphinx<8 is dropped,
        re.escape(' translated="True"'),
        re.escape(" translation_progress=\"{'total': 4, 'translated': 2}\""),
    )

    def __init__(self, file_regression):
        self.file_regression = file_regression

    def check(self, data, **kwargs):
        return self.file_regression.check(self._strip_ignores(data), **kwargs)

    def _strip_ignores(self, data):
        for ig in self.ignores:
            data = re.sub(ig, "", data)
        return data
