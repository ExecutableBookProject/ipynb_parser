"""Run parsing tests against the docutils parser."""

from io import StringIO
import json
from pathlib import Path

from docutils.core import publish_doctree, publish_string
import pytest
import sphinx
import yaml

from myst_nb.docutils_ import Parser

FIXTURE_PATH = Path(__file__).parent.joinpath("nb_fixtures")


@pytest.mark.param_file(FIXTURE_PATH / "basic.txt")
def test_basic(file_params):
    """Test basic parsing."""
    if (
        "Footnote definitions defined in different cells" in file_params.title
        and sphinx.version_info[0] < 5
    ):
        pytest.skip("footnote definition ids changes")
    dct = yaml.safe_load(file_params.content)
    dct.update({"nbformat": 4, "nbformat_minor": 4})
    dct.setdefault("metadata", {})
    dct["metadata"].setdefault(
        "kernelspec", {"name": "python3", "display_name": "Python 3", "language": ""}
    )
    report_stream = StringIO()
    doctree = publish_doctree(
        json.dumps(dct),
        parser=Parser(),
        settings_overrides={
            "nb_execution_mode": "off",
            "nb_output_folder": "",
            "myst_all_links_external": True,
            "warning_stream": report_stream,
        },
    )
    assert report_stream.getvalue().rstrip() == ""

    file_params.assert_expected(doctree.pformat(), rstrip=True)


@pytest.mark.param_file(FIXTURE_PATH / "reporter_warnings.txt")
def test_reporting(file_params):
    """Test that warnings and errors are reported as expected."""
    dct = yaml.safe_load(file_params.content)
    dct.update({"metadata": {}, "nbformat": 4, "nbformat_minor": 4})
    report_stream = StringIO()
    publish_doctree(
        json.dumps(dct),
        parser=Parser(),
        settings_overrides={
            "nb_execution_mode": "off",
            "nb_output_folder": "",
            "warning_stream": report_stream,
        },
    )
    file_params.assert_expected(report_stream.getvalue(), rstrip=True)


def test_html_resources(tmp_path):
    """Test HTML resources are correctly output."""
    report_stream = StringIO()
    result = publish_string(
        json.dumps({"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 4}),
        parser=Parser(),
        writer_name="html",
        settings_overrides={
            "nb_execution_mode": "off",
            "nb_output_folder": str(tmp_path),
            "warning_stream": report_stream,
            "output_encoding": "unicode",
            "embed_stylesheet": False,
        },
    )
    assert report_stream.getvalue().rstrip() == ""
    assert "mystnb.css" in result
    assert "pygments.css" in result
    assert tmp_path.joinpath("mystnb.css").is_file()
    assert tmp_path.joinpath("pygments.css").is_file()
