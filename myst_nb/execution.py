"""Control notebook outputs generation, caching and retrieval

The primary methods in this module are:

- ``update_execution_cache``, which is called when sphinx detects outdated files.
  When caching is enabled, this will execute the files if necessary and update the cache
- ``generate_notebook_outputs`` which is called during the parsing of each notebook.
  If caching is enabled, this will attempt to pull the outputs from the cache,
  or if 'auto' / 'force' is set, will execute the notebook.

"""
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Set

import nbformat as nbf
from jupyter_cache import get_cache
from jupyter_cache.executors import load_executor
from jupyter_cache.executors.utils import single_nb_execution
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.environment import BuildEnvironment
from sphinx.util import logging, progress_message

from .converter import get_nb_converter

LOGGER = logging.getLogger(__name__)


class ExecutionError(Exception):
    pass


def update_execution_cache(
    app: Sphinx, builder: Builder, added: Set[str], changed: Set[str], removed: Set[str]
):
    """If caching is required, stage and execute the added or modified notebooks,
    and cache them for later retrieval.

    This is called by sphinx as an `env-get-outdated` event,
    which is emitted when the environment determines which source files have changed
    and should be re-read.

    """
    # all the added and changed notebooks should be operated on.
    # note docnames are paths relative to the sphinx root folder, with no extensions
    altered_docnames = added.union(changed)

    exec_docnames = [
        docname for docname in altered_docnames if is_valid_exec_file(app.env, docname)
    ]
    LOGGER.verbose("MyST-NB: Potential docnames to execute: %s", exec_docnames)

    if app.config["jupyter_execute_notebooks"] == "cache":

        app.env.nb_path_to_cache = str(
            app.config["jupyter_cache"]
            or Path(app.outdir).parent.joinpath(".jupyter_cache")
        )

        cache_base = get_cache(app.env.nb_path_to_cache)
        for path in removed:

            if path in app.env.nb_execution_data:
                app.env.nb_execution_data_changed = True
                app.env.nb_execution_data.pop(path, None)

            docpath = app.env.doc2path(path)
            # there is an issue in sphinx doc2path, whereby if the path does not
            # exist then it will be assigned the default source_suffix (usually .rst)
            # therefore, to be safe here, we run through all possible suffixes
            for suffix in app.env.nb_allowed_exec_suffixes:
                docpath = os.path.splitext(docpath)[0] + suffix
                if not os.path.exists(docpath):
                    cache_base.discard_staged_notebook(docpath)

        _stage_and_execute(
            env=app.env,
            exec_docnames=exec_docnames,
            path_to_cache=app.env.nb_path_to_cache,
            timeout=app.config["execution_timeout"],
            allow_errors=app.config["execution_allow_errors"],
            fail_on_error=app.config["execution_fail_on_error"],
            exec_in_temp=app.config["execution_in_temp"],
        )

    return []


def generate_notebook_outputs(
    env: BuildEnvironment,
    ntbk: nbf.NotebookNode,
    file_path: Optional[str] = None,
    show_traceback: bool = False,
) -> nbf.NotebookNode:
    """
    Add outputs to a NotebookNode by pulling from cache.

    Function to get the database instance. Get the cached output of the notebook
    and merge it with the original notebook. If there is no cached output,
    checks if there was error during execution, then saves the traceback to a log file.
    """

    # check if the file is of a format that may be associated with outputs
    if not is_valid_exec_file(env, env.docname):
        return ntbk

    # If we have a jupyter_cache, see if there's a cache for this notebook
    file_path = file_path or env.doc2path(env.docname)

    execution_method = env.config["jupyter_execute_notebooks"]  # type: str

    path_to_cache = env.nb_path_to_cache if "cache" in execution_method else None

    if not path_to_cache and "off" in execution_method:
        return ntbk

    if not path_to_cache:

        if execution_method == "auto" and nb_has_all_output(file_path):
            LOGGER.info(
                "Did not execute %s. "
                "Set jupyter_execute_notebooks to `force` to execute",
                env.docname,
            )
        else:
            if env.config["execution_in_temp"]:
                with tempfile.TemporaryDirectory() as tmpdirname:
                    LOGGER.info("Executing: %s in temporary directory", env.docname)
                    result = single_nb_execution(
                        ntbk,
                        cwd=tmpdirname,
                        timeout=env.config["execution_timeout"],
                        allow_errors=env.config["execution_allow_errors"],
                    )
            else:
                cwd = Path(file_path).parent
                LOGGER.info("Executing: %s in: %s", env.docname, cwd)
                result = single_nb_execution(
                    ntbk,
                    cwd=cwd,
                    timeout=env.config["execution_timeout"],
                    allow_errors=env.config["execution_allow_errors"],
                )

            report_path = None
            if result.err:
                if env.config["execution_fail_on_error"]:
                    raise ExecutionError(
                        f"Execution failed for file: {file_path}\n{str(result.err)}"
                    )
                else:
                    report_path, message = _report_exec_fail(
                        env,
                        Path(file_path).name,
                        result.exc_string,
                        show_traceback,
                        "Execution Failed with traceback saved in {}",
                    )
                    LOGGER.error(message)

            ntbk = result.nb

            env.nb_execution_data_changed = True
            env.nb_execution_data[env.docname] = {
                "mtime": datetime.now().timestamp(),
                "runtime": result.time,
                "method": execution_method,
                "succeeded": False if result.err else True,
            }
            if report_path:
                env.nb_execution_data[env.docname]["error_log"] = report_path

        return ntbk

    cache_base = get_cache(path_to_cache)
    # Use relpath here in case Sphinx is building from a non-parent folder
    r_file_path = Path(os.path.relpath(file_path, Path().resolve()))

    # default execution data
    runtime = None
    succeeded = False
    report_path = None

    try:
        pk, ntbk = cache_base.merge_match_into_notebook(ntbk)
    except KeyError:
        message = (
            f"Couldn't find cache key for notebook file {str(r_file_path)}. "
            "Outputs will not be inserted."
        )
        try:
            stage_record = cache_base.get_staged_record(file_path)
        except KeyError:
            stage_record = None
        if stage_record and stage_record.traceback:
            report_path, suffix = _report_exec_fail(
                env,
                r_file_path.name,
                stage_record.traceback,
                show_traceback,
                "\n  Last execution failed with traceback saved in {}",
            )
            message += suffix

        if env.config["execution_fail_on_error"]:
            raise ExecutionError(message)
        else:
            LOGGER.error(message)

    else:
        LOGGER.verbose("Merged cached outputs into %s", str(r_file_path))
        succeeded = True
        try:
            runtime = cache_base.get_cache_record(pk).data.get(
                "execution_seconds", None
            )
        except Exception:
            pass

    env.nb_execution_data_changed = True
    env.nb_execution_data[env.docname] = {
        "mtime": datetime.now().timestamp(),
        "runtime": runtime,
        "method": execution_method,
        "succeeded": succeeded,
    }
    if report_path:
        env.nb_execution_data[env.docname]["error_log"] = report_path

    return ntbk


def is_valid_exec_file(env: BuildEnvironment, docname: str) -> bool:
    """Check if the docname refers to a file that should be executed."""
    doc_path = env.doc2path(docname)
    if doc_path in env.nb_excluded_exec_paths:
        return False
    matches = tuple(
        re.search(re.escape(suffix) + "$", doc_path)
        for suffix in env.nb_allowed_exec_suffixes
    )
    if not any(matches):
        return False
    return True


def _report_exec_fail(
    env,
    file_name: str,
    traceback: str,
    show_traceback: bool,
    template: str,
):
    """Save the traceback to a log file, and create log message."""
    reports_dir = Path(env.app.outdir).joinpath("reports")
    reports_dir.mkdir(exist_ok=True)
    full_path = reports_dir.joinpath(os.path.splitext(file_name)[0] + ".log")
    full_path.write_text(traceback, encoding="utf8")
    message = template.format(full_path)
    if show_traceback:
        message += "\n" + traceback
    return str(full_path), message


def _stage_and_execute(
    env: BuildEnvironment,
    exec_docnames: List[str],
    path_to_cache: str,
    timeout: Optional[int],
    allow_errors: bool,
    fail_on_error: bool,
    exec_in_temp: bool,
):
    pk_list = []
    cache_base = get_cache(path_to_cache)

    for nb in exec_docnames:
        source_path = env.doc2path(nb)
        with open(source_path, encoding="utf8") as handle:
            # here we pass an iterator, so that only the required lines are read
            converter = get_nb_converter(source_path, env, (line for line in handle))
        if converter is not None:
            stage_record = cache_base.stage_notebook_file(source_path)
            pk_list.append(stage_record.pk)

    # can leverage parallel execution implemented in jupyter-cache here
    try:
        with progress_message("executing outdated notebooks"):
            execute_staged_nb(
                cache_base,
                pk_list or None,
                timeout=timeout,
                exec_in_temp=exec_in_temp,
                allow_errors=allow_errors,
                fail_on_error=fail_on_error,
                env=env,
            )
    except OSError as err:
        # This is a 'fix' for obscure cases, such as if you
        # remove name.ipynb and add name.md (i.e. same name, different extension)
        # and then name.ipynb isn't flagged for removal.
        # Normally we want to keep the stage records available, so that we can retrieve
        # execution tracebacks at the `generate_notebook_outputs` stage,
        # but we need to flush if it becomes 'corrupted'
        message = (
            f"Execution failed in an unexpected way, clearing staged notebooks: {err}"
        )
        if fail_on_error:
            raise ExecutionError(message)
        else:
            LOGGER.error(message)
        for record in cache_base.list_staged_records():
            cache_base.discard_staged_notebook(record.pk)


def execute_staged_nb(
    cache_base,
    pk_list,
    timeout: Optional[int],
    exec_in_temp: bool,
    allow_errors: bool,
    fail_on_error: bool,
    env: BuildEnvironment,
):
    """Executing the staged notebook."""
    try:
        executor = load_executor("basic", cache_base, logger=LOGGER)
    except ImportError as error:
        if fail_on_error:
            raise ExecutionError(str(error))
        else:
            LOGGER.error(str(error))
        return 1

    def _converter(path):
        text = Path(path).read_text(encoding="utf8")
        return get_nb_converter(path, env).func(text)

    result = executor.run_and_cache(
        filter_pks=pk_list or None,
        converter=_converter,
        timeout=timeout,
        allow_errors=allow_errors,
        run_in_temp=exec_in_temp,
    )
    return result


def nb_has_all_output(
    source_path: str, nb_extensions: Iterable[str] = (".ipynb",)
) -> bool:
    """Determine if the path contains a notebook with at least one output."""
    has_outputs = False
    ext = os.path.splitext(source_path)[1]

    if ext in nb_extensions:
        with open(source_path, "r", encoding="utf8") as f:
            ntbk = nbf.read(f, as_version=4)
            has_outputs = all(
                len(cell.outputs) != 0
                for cell in ntbk.cells
                if cell["cell_type"] == "code"
            )
    return has_outputs
