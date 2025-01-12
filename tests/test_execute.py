"""Test sphinx builds which execute notebooks."""
import os
from pathlib import Path

from IPython import version_info as ipy_version
import pytest

from myst_nb.core.execute import ExecutionError
from myst_nb.sphinx_ import NbMetadataCollector


def regress_nb_doc(file_regression, sphinx_run, check_nbs):
    try:
        file_regression.check(
            sphinx_run.get_nb(),
            check_fn=check_nbs,
            extension=".ipynb",
            encoding="utf-8",
        )
    finally:
        doctree_string = sphinx_run.get_doctree().pformat()
        # TODO this is a difference in the hashing on the CI,
        # with complex_outputs_unrun.ipynb equation PNG, after execution
        # sympy
        doctree_string = doctree_string.replace(
            "91b3db0f47514d451e7c0f5a501d31c4e101b7112050634ad0788405f417782a",
            "e2dfbe330154316cfb6f3186e8f57fc4df8aee03b0303ed1345fc22cd51f66de",
        )
        doctree_string = doctree_string.replace(
            "438c56ea3dcf99d86cd64df1b23e2b436afb25846434efb1cfec7b660ef01127",
            "e2dfbe330154316cfb6f3186e8f57fc4df8aee03b0303ed1345fc22cd51f66de",
        )
        if os.name == "nt":  # on Windows image file paths are absolute
            doctree_string = doctree_string.replace(
                Path(sphinx_run.app.srcdir).as_posix() + "/", ""
            )
        file_regression.check(doctree_string, extension=".xml", encoding="utf-8")


@pytest.mark.sphinx_params("basic_unrun.ipynb", conf={"nb_execution_mode": "auto"})
def test_basic_unrun_auto(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    # print(sphinx_run.status())
    assert sphinx_run.warnings() == ""
    assert "test_name" in sphinx_run.app.env.metadata["basic_unrun"]
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    assert NbMetadataCollector.new_exec_data(sphinx_run.env)
    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "basic_unrun")
    assert data
    assert data["method"] == "auto"
    assert data["succeeded"] is True


@pytest.mark.sphinx_params("basic_unrun.ipynb", conf={"nb_execution_mode": "lazy"})
def test_basic_unrun_lazy(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    # print(sphinx_run.status())
    assert sphinx_run.warnings() == ""
    assert "test_name" in sphinx_run.app.env.metadata["basic_unrun"]
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    assert NbMetadataCollector.new_exec_data(sphinx_run.env)
    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "basic_unrun")
    assert data
    assert data["method"] == "lazy"
    assert data["succeeded"] is True


@pytest.mark.sphinx_params("basic_unrun.ipynb", conf={"nb_execution_mode": "cache"})
def test_basic_unrun_cache(sphinx_run, file_regression, check_nbs):
    """The outputs should be populated."""
    sphinx_run.build()
    assert sphinx_run.warnings() == ""
    assert "test_name" in sphinx_run.app.env.metadata["basic_unrun"]
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    assert NbMetadataCollector.new_exec_data(sphinx_run.env)
    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "basic_unrun")
    assert data
    assert data["method"] == "cache"
    assert data["succeeded"] is True


@pytest.mark.sphinx_params("basic_unrun.ipynb", conf={"nb_execution_mode": "inline"})
def test_basic_unrun_inline(sphinx_run, file_regression, check_nbs):
    """The outputs should be populated."""
    sphinx_run.build()
    assert sphinx_run.warnings() == ""
    assert "test_name" in sphinx_run.app.env.metadata["basic_unrun"]
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    assert NbMetadataCollector.new_exec_data(sphinx_run.env)
    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "basic_unrun")
    assert data
    assert data["method"] == "inline"
    assert data["succeeded"] is True


@pytest.mark.sphinx_params("basic_unrun.ipynb", conf={"nb_execution_mode": "cache"})
def test_rebuild_cache(sphinx_run):
    """The notebook should only be executed once."""
    sphinx_run.build()
    assert NbMetadataCollector.new_exec_data(sphinx_run.env)
    sphinx_run.invalidate_files()
    sphinx_run.build()
    assert "Using cached" in sphinx_run.status()


@pytest.mark.sphinx_params("basic_unrun.ipynb", conf={"nb_execution_mode": "force"})
def test_rebuild_force(sphinx_run):
    """The notebook should be executed twice."""
    sphinx_run.build()
    assert NbMetadataCollector.new_exec_data(sphinx_run.env)
    sphinx_run.invalidate_files()
    sphinx_run.build()
    assert NbMetadataCollector.new_exec_data(sphinx_run.env)


@pytest.mark.sphinx_params(
    "basic_unrun.ipynb",
    conf={
        "nb_execution_mode": "cache",
        "nb_execution_excludepatterns": ["basic_*"],
    },
)
def test_exclude_path(sphinx_run, file_regression):
    """The notebook should not be executed."""
    sphinx_run.build()
    assert not NbMetadataCollector.new_exec_data(sphinx_run.env)
    assert "Executing" not in sphinx_run.status(), sphinx_run.status()
    file_regression.check(
        sphinx_run.get_doctree().pformat(), extension=".xml", encoding="utf-8"
    )


@pytest.mark.skipif(ipy_version[0] < 8, reason="Error message changes for ipython v8")
@pytest.mark.sphinx_params("basic_failing.ipynb", conf={"nb_execution_mode": "cache"})
def test_basic_failing_cache(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    # print(sphinx_run.warnings())
    assert "Executing notebook failed" in sphinx_run.warnings()
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "basic_failing")
    assert data
    assert data["method"] == "cache"
    assert data["succeeded"] is False
    sphinx_run.get_report_file()


@pytest.mark.skipif(ipy_version[0] < 8, reason="Error message changes for ipython v8")
@pytest.mark.sphinx_params("basic_failing.ipynb", conf={"nb_execution_mode": "auto"})
def test_basic_failing_auto(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    assert "Executing notebook failed" in sphinx_run.warnings()
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "basic_failing")
    assert data
    assert data["method"] == "auto"
    assert data["succeeded"] is False
    assert data["traceback"]
    sphinx_run.get_report_file()


@pytest.mark.skipif(ipy_version[0] < 8, reason="Error message changes for ipython v8")
@pytest.mark.sphinx_params("basic_failing.ipynb", conf={"nb_execution_mode": "lazy"})
def test_basic_failing_lazy(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    assert "Executing notebook failed" in sphinx_run.warnings()
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "basic_failing")
    assert data
    assert data["method"] == "lazy"
    assert data["succeeded"] is False
    assert data["traceback"]
    sphinx_run.get_report_file()


@pytest.mark.skipif(ipy_version[0] < 8, reason="Error message changes for ipython v8")
@pytest.mark.sphinx_params("basic_failing.ipynb", conf={"nb_execution_mode": "inline"})
def test_basic_failing_inline(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    assert "Executing notebook failed" in sphinx_run.warnings()
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "basic_failing")
    assert data
    assert data["method"] == "inline"
    assert data["succeeded"] is False
    assert data["traceback"]
    sphinx_run.get_report_file()


@pytest.mark.skipif(ipy_version[0] < 8, reason="Error message changes for ipython v8")
@pytest.mark.sphinx_params(
    "basic_failing.ipynb",
    conf={"nb_execution_mode": "cache", "nb_execution_allow_errors": True},
)
def test_allow_errors_cache(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    # print(sphinx_run.status())
    assert not sphinx_run.warnings()
    regress_nb_doc(file_regression, sphinx_run, check_nbs)


@pytest.mark.skipif(ipy_version[0] < 8, reason="Error message changes for ipython v8")
@pytest.mark.sphinx_params(
    "basic_failing.ipynb",
    conf={"nb_execution_mode": "auto", "nb_execution_allow_errors": True},
)
def test_allow_errors_auto(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    # print(sphinx_run.status())
    assert not sphinx_run.warnings()
    regress_nb_doc(file_regression, sphinx_run, check_nbs)


@pytest.mark.sphinx_params(
    "basic_failing.ipynb",
    conf={"nb_execution_raise_on_error": True, "nb_execution_mode": "force"},
)
def test_raise_on_error_force(sphinx_run):
    with pytest.raises(ExecutionError, match="basic_failing.ipynb"):
        sphinx_run.build()


@pytest.mark.sphinx_params(
    "basic_failing.ipynb",
    conf={"nb_execution_raise_on_error": True, "nb_execution_mode": "cache"},
)
def test_raise_on_error_cache(sphinx_run):
    with pytest.raises(ExecutionError, match="basic_failing.ipynb"):
        sphinx_run.build()


@pytest.mark.sphinx_params(
    "complex_outputs_unrun.ipynb", conf={"nb_execution_mode": "cache"}
)
def test_complex_outputs_unrun_cache(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    # print(sphinx_run.status())
    assert sphinx_run.warnings() == ""
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    # Widget view and widget state should make it into the HTML
    scripts = sphinx_run.get_html().select("script")
    assert any(
        "application/vnd.jupyter.widget-view+json" in script.get("type", "")
        for script in scripts
    )
    assert any(
        "application/vnd.jupyter.widget-state+json" in script.get("type", "")
        for script in scripts
    )


@pytest.mark.sphinx_params(
    "complex_outputs_unrun.ipynb", conf={"nb_execution_mode": "auto"}
)
def test_complex_outputs_unrun_auto(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    # print(sphinx_run.status())
    assert sphinx_run.warnings() == ""
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    # Widget view and widget state should make it into the HTML
    scripts = sphinx_run.get_html().select("script")
    assert any(
        "application/vnd.jupyter.widget-view+json" in script.get("type", "")
        for script in scripts
    )
    assert any(
        "application/vnd.jupyter.widget-state+json" in script.get("type", "")
        for script in scripts
    )


@pytest.mark.sphinx_params("basic_unrun.ipynb", conf={"nb_execution_mode": "off"})
def test_no_execute(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    # print(sphinx_run.status())
    assert sphinx_run.warnings() == ""
    regress_nb_doc(file_regression, sphinx_run, check_nbs)


@pytest.mark.sphinx_params("basic_unrun.ipynb", conf={"nb_execution_mode": "cache"})
def test_jupyter_cache_path(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    assert "Cached executed notebook" in sphinx_run.status()
    assert sphinx_run.warnings() == ""
    regress_nb_doc(file_regression, sphinx_run, check_nbs)


# Testing relative paths within the notebook
@pytest.mark.sphinx_params("basic_relative.ipynb", conf={"nb_execution_mode": "cache"})
def test_relative_path_cache(sphinx_run):
    sphinx_run.build()
    assert "Execution Failed" not in sphinx_run.status(), sphinx_run.status()


@pytest.mark.sphinx_params("basic_relative.ipynb", conf={"nb_execution_mode": "force"})
def test_relative_path_force(sphinx_run):
    sphinx_run.build()
    assert "Execution Failed" not in sphinx_run.status(), sphinx_run.status()


@pytest.mark.sphinx_params(
    "kernel_alias.md",
    conf={"nb_execution_mode": "force", "nb_kernel_rgx_aliases": {"oth.+": "python3"}},
)
def test_kernel_rgx_aliases(sphinx_run):
    sphinx_run.build()
    assert sphinx_run.warnings() == ""


@pytest.mark.sphinx_params(
    "sleep_10.ipynb",
    conf={"nb_execution_mode": "cache", "nb_execution_timeout": 1},
)
def test_execution_timeout(sphinx_run):
    """execution should fail given the low timeout value"""
    sphinx_run.build()
    # print(sphinx_run.warnings())
    assert "Executing notebook failed" in sphinx_run.warnings()


@pytest.mark.sphinx_params(
    "sleep_10_metadata_timeout.ipynb",
    conf={"nb_execution_mode": "cache", "nb_execution_timeout": 60},
)
def test_execution_metadata_timeout(sphinx_run):
    """notebook timeout metadata has higher preference then execution_timeout config"""
    sphinx_run.build()
    # print(sphinx_run.warnings())
    assert "Executing notebook failed" in sphinx_run.warnings()


@pytest.mark.sphinx_params(
    "nb_exec_table.md",
    conf={"nb_execution_mode": "auto"},
)
def test_nb_exec_table(sphinx_run, file_regression):
    """Test that the table gets output into the HTML,
    including a row for the executed notebook.
    """
    sphinx_run.build()
    # print(sphinx_run.status())
    assert not sphinx_run.warnings()
    file_regression.check(
        sphinx_run.get_doctree().pformat(), extension=".xml", encoding="utf-8"
    )
    # print(sphinx_run.get_html())
    rows = sphinx_run.get_html().select("table.docutils tr")
    assert any("nb_exec_table" in row.text for row in rows)


@pytest.mark.sphinx_params(
    "custom-formats.Rmd",
    conf={
        "nb_execution_mode": "auto",
        "nb_custom_formats": {".Rmd": ["jupytext.reads", {"fmt": "Rmd"}]},
    },
)
def test_custom_convert_auto(sphinx_run, file_regression, check_nbs):
    sphinx_run.build()
    # print(sphinx_run.status())
    assert sphinx_run.warnings() == ""
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    assert NbMetadataCollector.new_exec_data(sphinx_run.env)
    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "custom-formats")
    assert data
    assert data["method"] == "auto"
    assert data["succeeded"] is True


@pytest.mark.sphinx_params(
    "custom-formats.Rmd",
    conf={
        "nb_execution_mode": "cache",
        "nb_custom_formats": {".Rmd": ["jupytext.reads", {"fmt": "Rmd"}]},
    },
)
def test_custom_convert_cache(sphinx_run, file_regression, check_nbs):
    """The outputs should be populated."""
    sphinx_run.build()
    assert sphinx_run.warnings() == ""
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    assert NbMetadataCollector.new_exec_data(sphinx_run.env)
    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "custom-formats")
    assert data
    assert data["method"] == "cache"
    assert data["succeeded"] is True


@pytest.mark.sphinx_params(
    "custom-formats2.extra.exnt",
    conf={
        "nb_execution_mode": "auto",
        "nb_custom_formats": {".extra.exnt": ["jupytext.reads", {"fmt": "Rmd"}]},
    },
)
def test_custom_convert_multiple_extensions_auto(
    sphinx_run, file_regression, check_nbs
):
    """The outputs should be populated."""
    sphinx_run.build()
    assert sphinx_run.warnings() == ""
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    assert NbMetadataCollector.new_exec_data(sphinx_run.env)
    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "custom-formats2")
    assert data
    assert data["method"] == "auto"
    assert data["succeeded"] is True


@pytest.mark.sphinx_params(
    "custom-formats2.extra.exnt",
    conf={
        "nb_execution_mode": "cache",
        "nb_custom_formats": {".extra.exnt": ["jupytext.reads", {"fmt": "Rmd"}]},
    },
)
def test_custom_convert_multiple_extensions_cache(
    sphinx_run, file_regression, check_nbs
):
    """The outputs should be populated."""
    sphinx_run.build()
    assert sphinx_run.warnings() == ""
    regress_nb_doc(file_regression, sphinx_run, check_nbs)

    assert NbMetadataCollector.new_exec_data(sphinx_run.env)
    data = NbMetadataCollector.get_exec_data(sphinx_run.env, "custom-formats2")
    assert data
    assert data["method"] == "cache"
    assert data["succeeded"] is True
