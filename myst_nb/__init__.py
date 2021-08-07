__version__ = "0.13.0"

import os
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from docutils import nodes as docnodes
from IPython.lib.lexers import IPython3Lexer, IPythonTracebackLexer
from ipywidgets.embed import DEFAULT_EMBED_REQUIREJS_URL, DEFAULT_EMBED_SCRIPT_URL
from jupyter_sphinx import REQUIRE_URL_DEFAULT
from jupyter_sphinx.ast import JupyterWidgetStateNode, JupyterWidgetViewNode
from jupyter_sphinx.utils import sphinx_abs_dir
from myst_parser import setup_sphinx as setup_myst_parser
from sphinx.addnodes import download_reference
from sphinx.application import Sphinx
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.environment import BuildEnvironment
from sphinx.errors import SphinxError
from sphinx.util import import_object, logging
from sphinx.util.docutils import ReferenceRole, SphinxDirective

from .exec_table import setup_exec_table
from .execution import update_execution_cache
from .nb_glue import glue  # noqa: F401
from .nb_glue.domain import (
    NbGlueDomain,
    PasteInlineNode,
    PasteMathNode,
    PasteNode,
    PasteTextNode,
)
from .nb_glue.transform import PasteNodesToDocutils
from .nodes import CellInputNode, CellNode, CellOutputBundleNode, CellOutputNode
from .parser import NotebookParser
from .render_outputs import (
    CellOutputsToNodes,
    get_default_render_priority,
    load_renderer,
)

LOGGER = logging.getLogger(__name__)


def setup(app: Sphinx):
    """Initialize Sphinx extension."""
    # Allow parsing ipynb files
    app.add_source_suffix(".md", "myst-nb")
    app.add_source_suffix(".ipynb", "myst-nb")
    app.add_source_parser(NotebookParser)
    app.setup_extension("sphinx_togglebutton")

    # Helper functions for the registry, pulled from jupyter-sphinx
    def skip(self, node):
        raise docnodes.SkipNode

    # Used to render an element node as HTML
    def visit_element_html(self, node):
        self.body.append(node.html())
        raise docnodes.SkipNode

    # Shortcut for registering our container nodes
    render_container = (
        lambda self, node: self.visit_container(node),
        lambda self, node: self.depart_container(node),
    )

    # Register our container nodes, these should behave just like a regular container
    for node in [CellNode, CellInputNode, CellOutputNode]:
        app.add_node(
            node,
            override=True,
            html=(render_container),
            latex=(render_container),
            textinfo=(render_container),
            text=(render_container),
            man=(render_container),
        )

    # Register the output bundle node.
    # No translators should touch this node because we'll replace it in a post-transform
    app.add_node(
        CellOutputBundleNode,
        override=True,
        html=(skip, None),
        latex=(skip, None),
        textinfo=(skip, None),
        text=(skip, None),
        man=(skip, None),
    )

    # these nodes hold widget state/view JSON,
    # but are only rendered properly in HTML documents.
    for node in [JupyterWidgetStateNode, JupyterWidgetViewNode]:
        app.add_node(
            node,
            override=True,
            html=(visit_element_html, None),
            latex=(skip, None),
            textinfo=(skip, None),
            text=(skip, None),
            man=(skip, None),
        )

    # Register our inline nodes so they can be parsed as a part of titles
    # No translators should touch these nodes because we'll replace them in a transform
    for node in [PasteMathNode, PasteNode, PasteTextNode, PasteInlineNode]:
        app.add_node(
            node,
            override=True,
            html=(skip, None),
            latex=(skip, None),
            textinfo=(skip, None),
            text=(skip, None),
            man=(skip, None),
        )

    # Add configuration for the cache
    app.add_config_value("jupyter_cache", "", "env")
    app.add_config_value("execution_excludepatterns", [], "env")
    app.add_config_value("jupyter_execute_notebooks", "auto", "env")
    app.add_config_value("execution_timeout", 30, "env")
    app.add_config_value("execution_allow_errors", False, "env")
    app.add_config_value("execution_in_temp", False, "env")
    # show traceback in stdout (in addition to writing to file)
    # this is useful in e.g. RTD where one cannot inspect a file
    app.add_config_value("execution_show_tb", False, "")
    app.add_config_value("nb_custom_formats", {}, "env")

    # render config
    app.add_config_value("nb_render_key", "render", "env")
    app.add_config_value("nb_render_priority", {}, "env")
    app.add_config_value("nb_render_plugin", "default", "env")
    app.add_config_value("nb_render_text_lexer", "myst-ansi", "env")
    app.add_config_value("nb_output_stderr", "show", "env")

    # Register our post-transform which will convert output bundles to nodes
    app.add_post_transform(PasteNodesToDocutils)
    app.add_post_transform(CellOutputsToNodes)

    # Add myst-parser transforms and configuration
    setup_myst_parser(app)

    # Events
    app.connect("config-inited", validate_config_values)
    app.connect("builder-inited", static_path)
    app.connect("builder-inited", set_valid_execution_paths)
    app.connect("builder-inited", set_up_execution_data)
    app.connect("builder-inited", set_render_priority)
    app.connect("env-purge-doc", remove_execution_data)
    app.connect("env-get-outdated", update_execution_cache)
    app.connect("config-inited", add_exclude_patterns)
    app.connect("config-inited", update_togglebutton_classes)
    app.connect("env-updated", save_glue_cache)
    app.connect("config-inited", add_nb_custom_formats)
    app.connect("env-updated", load_ipywidgets_js)

    from myst_nb.ansi_lexer import AnsiColorLexer

    # For syntax highlighting
    app.add_lexer("ipythontb", IPythonTracebackLexer)
    app.add_lexer("ipython", IPython3Lexer)
    app.add_lexer("myst-ansi", AnsiColorLexer)

    # Add components
    app.add_directive("code-cell", CodeCell)
    app.add_role("nb-download", JupyterDownloadRole())
    app.add_css_file("mystnb.css")
    app.add_domain(NbGlueDomain)

    # execution statistics table
    setup_exec_table(app)

    # TODO need to deal with key clashes in NbGlueDomain.merge_domaindata
    # before this is parallel_read_safe
    return {"version": __version__, "parallel_read_safe": False}


class MystNbConfigError(SphinxError):
    """Error specific to MyST-NB."""

    category = "MyST NB Configuration Error"


def validate_config_values(app: Sphinx, config):
    """Validate configuration values."""
    execute_mode = app.config["jupyter_execute_notebooks"]
    if execute_mode not in ["force", "auto", "cache", "off"]:
        raise MystNbConfigError(
            "'jupyter_execute_notebooks' can be: "
            f"`force`, `auto`, `cache` or `off`, but got: {execute_mode}",
        )

    if app.config["jupyter_cache"] and execute_mode != "cache":
        raise MystNbConfigError(
            "'jupyter_cache' is set, "
            f"but 'jupyter_execute_notebooks' is not `cache`: {execute_mode}"
        )

    if app.config["jupyter_cache"] and not os.path.isdir(app.config["jupyter_cache"]):
        raise MystNbConfigError(
            f"'jupyter_cache' is not a directory: {app.config['jupyter_cache']}",
        )

    if not isinstance(app.config["nb_custom_formats"], dict):
        raise MystNbConfigError(
            "'nb_custom_formats' should be a dictionary: "
            f"{app.config['nb_custom_formats']}"
        )
    for name, converter in app.config["nb_custom_formats"].items():
        if not isinstance(name, str):
            raise MystNbConfigError(
                f"'nb_custom_formats' keys should be a string: {name}"
            )
        if isinstance(converter, str):
            app.config["nb_custom_formats"][name] = (converter, {})
        elif not (isinstance(converter, Sequence) and len(converter) in [2, 3]):
            raise MystNbConfigError(
                "'nb_custom_formats' values must be "
                f"either strings or 2/3-element sequences, got: {converter}"
            )

        converter_str = app.config["nb_custom_formats"][name][0]
        caller = import_object(
            converter_str,
            f"MyST-NB nb_custom_formats: {name}",
        )
        if not callable(caller):
            raise MystNbConfigError(
                f"`nb_custom_formats.{name}` converter is not callable: {caller}"
            )
        if len(app.config["nb_custom_formats"][name]) == 2:
            app.config["nb_custom_formats"][name].append(None)
        elif not isinstance(app.config["nb_custom_formats"][name][2], bool):
            raise MystNbConfigError(
                f"`nb_custom_formats.{name}.commonmark_only` arg is not boolean"
            )

        if not isinstance(app.config["nb_render_key"], str):
            raise MystNbConfigError("`nb_render_key` is not a string")

        if app.config["nb_output_stderr"] not in [
            "show",
            "remove",
            "remove-warn",
            "warn",
            "error",
            "severe",
        ]:
            raise MystNbConfigError(
                "`nb_output_stderr` not one of: "
                "'show', 'remove', 'remove-warn', 'warn', 'error', 'severe'"
            )

    # try loading notebook output renderer
    load_renderer(app.config["nb_render_plugin"])


def static_path(app: Sphinx):
    static_path = Path(__file__).absolute().with_name("_static")
    app.config.html_static_path.append(str(static_path))


def load_ipywidgets_js(app: Sphinx, env: BuildEnvironment) -> None:
    """Add ipywidget JavaScript to HTML pages.

    We adapt the code in sphinx.ext.mathjax,
    to only add this JS if widgets have been found in any notebooks.
    (ideally we would only add it to the pages containing widgets,
    but this is not trivial in sphinx)

    There are 2 cases:

    - ipywidgets 7, with require
    - ipywidgets 7, no require

    We reuse settings, if available, for jupyter-sphinx
    """
    if app.builder.format != "html" or not app.env.nb_contains_widgets:
        return
    builder = cast(StandaloneHTMLBuilder, app.builder)

    require_url_default = (
        REQUIRE_URL_DEFAULT
        if "jupyter_sphinx_require_url" not in app.config
        else app.config.jupyter_sphinx_require_url
    )
    embed_url_default = (
        None
        if "jupyter_sphinx_embed_url" not in app.config
        else app.config.jupyter_sphinx_embed_url
    )

    if require_url_default:
        builder.add_js_file(require_url_default)
        embed_url = embed_url_default or DEFAULT_EMBED_REQUIREJS_URL
    else:
        embed_url = embed_url_default or DEFAULT_EMBED_SCRIPT_URL
    if embed_url:
        builder.add_js_file(embed_url)


def set_render_priority(app: Sphinx):
    """Set the render priority for the particular builder."""
    builder = app.builder.name
    if app.config.nb_render_priority and builder in app.config.nb_render_priority:
        app.env.nb_render_priority = app.config.nb_render_priority[builder]
    else:
        app.env.nb_render_priority = get_default_render_priority(builder)

    if app.env.nb_render_priority is None:
        raise MystNbConfigError(f"`nb_render_priority` not set for builder: {builder}")
    try:
        for item in app.env.nb_render_priority:
            assert isinstance(item, str)
    except Exception:
        raise MystNbConfigError(
            f"`nb_render_priority` is not a list of str: {app.env.nb_render_priority}"
        )


def set_valid_execution_paths(app: Sphinx):
    """Set files excluded from execution, and valid file suffixes

    Patterns given in execution_excludepatterns conf variable from executing.
    """
    app.env.nb_excluded_exec_paths = {
        str(path)
        for pat in app.config["execution_excludepatterns"]
        for path in Path().cwd().rglob(pat)
    }
    LOGGER.verbose("MyST-NB: Excluded Paths: %s", app.env.nb_excluded_exec_paths)
    app.env.nb_allowed_exec_suffixes = {
        suffix
        for suffix, parser_type in app.config["source_suffix"].items()
        if parser_type in ("myst-nb",)
    }
    app.env.nb_contains_widgets = False


def set_up_execution_data(app: Sphinx):
    if not hasattr(app.env, "nb_execution_data"):
        app.env.nb_execution_data = {}
    if not hasattr(app.env, "nb_execution_data_changed"):
        app.env.nb_execution_data_changed = False
    app.env.nb_execution_data_changed = False


def remove_execution_data(app: Sphinx, env, docname):
    if docname in app.env.nb_execution_data:
        app.env.nb_execution_data.pop(docname)
        app.env.nb_execution_data_changed = True


def add_nb_custom_formats(app: Sphinx, config):
    """Add custom conversion formats."""
    for suffix in config.nb_custom_formats:
        app.add_source_suffix(suffix, "myst-nb")


def add_exclude_patterns(app: Sphinx, config):
    """Add default exclude patterns (if not already present)."""
    if "**.ipynb_checkpoints" not in config.exclude_patterns:
        config.exclude_patterns.append("**.ipynb_checkpoints")


def update_togglebutton_classes(app: Sphinx, config):
    to_add = [
        ".tag_hide_input div.cell_input",
        ".tag_hide-input div.cell_input",
        ".tag_hide_output div.cell_output",
        ".tag_hide-output div.cell_output",
        ".tag_hide_cell.cell",
        ".tag_hide-cell.cell",
    ]
    for selector in to_add:
        config.togglebutton_selector += f", {selector}"


def save_glue_cache(app: Sphinx, env):
    NbGlueDomain.from_env(env).write_cache()


class JupyterDownloadRole(ReferenceRole):
    def run(self):
        reftarget = sphinx_abs_dir(self.env, self.target)
        node = download_reference(self.rawtext, reftarget=reftarget)
        self.set_source_info(node)
        title = self.title if self.has_explicit_title else self.target
        node += docnodes.literal(
            self.rawtext, title, classes=["xref", "download", "myst-nb"]
        )
        return [node], []


class CodeCell(SphinxDirective):
    """Raises a warning if it is triggered, it should not make it to the doctree."""

    optional_arguments = 1
    final_argument_whitespace = True
    has_content = True

    def run(self):
        LOGGER.warning(
            (
                "Found an unexpected `code-cell` directive. "
                "Either this file was not converted to a notebook, "
                "because Jupytext header content was missing, "
                "or the `code-cell` was not converted, because it is nested. "
                "See https://myst-nb.readthedocs.io/en/latest/use/markdown.html "
                "for more information."
            ),
            location=(self.env.docname, self.lineno),
        )
        return []
