# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os

# -- Project information -----------------------------------------------------

project = "MyST-NB"
copyright = "2023, Executable Book Project"
author = "Executable Book Project"

master_doc = "index"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_nb",
    "sphinx_copybutton",
    "sphinx_book_theme",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx_design",
]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints"]

myst_enable_extensions = [
    "amsmath",
    "colon_fence",
    "deflist",
    "dollarmath",
    "html_image",
]

nb_custom_formats = {".Rmd": ["jupytext.reads", {"fmt": "Rmd"}]}
nb_execution_mode = "cache"
nb_execution_show_tb = "READTHEDOCS" in os.environ
nb_execution_timeout = 60  # Note: 30 was timing out on RTD
nb_ipywidgets_js = {
    "https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.4/require.min.js": {
        "integrity": "sha256-Ae2Vz/4ePdIu6ZyI/5ZGsYnb+m0JlOmKPjt6XZ9JJkA=",
        "crossorigin": "anonymous",
    },
    "https://cdn.jsdelivr.net/npm/@jupyter-widgets/html-manager@*/dist/embed-amd.js": {
        "data-jupyter-widgets-cdn": "https://cdn.jsdelivr.net/npm/",
        "crossorigin": "anonymous",
    },
}
# nb_render_image_options = {"width": "200px"}
# application/vnd.plotly.v1+json and application/vnd.bokehjs_load.v0+json
suppress_warnings = ["mystnb.unknown_mime_type"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3.8", None),
    "jb": ("https://jupyterbook.org/", None),
    "myst": ("https://myst-parser.readthedocs.io/en/latest/", None),
    "markdown_it": ("https://markdown-it-py.readthedocs.io/en/latest", None),
    "nbclient": ("https://nbclient.readthedocs.io/en/latest", None),
    "nbformat": ("https://nbformat.readthedocs.io/en/latest", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
}
intersphinx_cache_limit = 5

# ignore these type annotations
nitpick_ignore = [
    ("py:class", klass)
    for klass in [
        "Path",
        "docutils.nodes.document",
        "docutils.nodes.Node",
        "docutils.nodes.Element",
        "nodes.Element",
        "docutils.nodes.container",
        "docutils.nodes.system_message",
        "DocutilsNbRenderer",
        "SphinxNbRenderer",
        "nbformat.notebooknode.NotebookNode",
        "nbf.NotebookNode",
        "NotebookNode",
        "pygments.lexer.RegexLexer",
        "LoggerType",
        "ExecutionResult",
        "MdParserConfig",
        "NbParserConfig",
        "NbReader",
        # Literal values are not supported
        "typing_extensions.Literal",
        "typing_extensions.Literal[show, remove, remove - warn, warn, error, severe]",
        "off",
        "force",
        "auto",
        "lazy",
        "cache",
        "commonmark",
        "gfm",
        "myst",
    ]
]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_title = ""
html_theme = "sphinx_book_theme"
html_logo = "_static/logo-wide.svg"
html_favicon = "_static/logo-square.svg"
html_theme_options = {
    "github_url": "https://github.com/executablebooks/myst-nb",
    "repository_url": "https://github.com/executablebooks/myst-nb",
    "repository_branch": "master",
    "home_page_in_toc": True,
    "path_to_docs": "docs",
    "show_navbar_depth": 1,
    "use_edit_page_button": True,
    "use_repository_button": True,
    "use_download_button": True,
    "launch_buttons": {
        "binderhub_url": "https://mybinder.org",
        "notebook_interface": "classic",
    },
    "navigation_with_keys": False,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_css_files = ["custom.css"]

copybutton_selector = "div:not(.output) > div.highlight pre"


def setup(app):
    """Add functions to the Sphinx setup."""
    import subprocess
    from typing import cast

    from docutils import nodes
    from docutils.parsers.rst import directives
    from myst_parser.config.main import MdParserConfig
    from sphinx.application import Sphinx
    from sphinx.util.docutils import SphinxDirective

    from myst_nb.core.config import NbParserConfig, Section

    app = cast(Sphinx, app)

    # this is required to register the coconut kernel with Jupyter,
    # to execute docs/examples/coconut-lang.md
    subprocess.check_call(["coconut", "--jupyter"])

    class _ConfigBase(SphinxDirective):
        """Directive to automate printing of the configuration."""

        @staticmethod
        def table_header():
            return [
                "```````{list-table}",
                ":header-rows: 1",
                "",
                "* - Name",
                "  - Type",
                "  - Default",
                "  - Description",
            ]

        @staticmethod
        def field_default(value):
            default = " ".join(f"{value!r}".splitlines())
            if len(default) > 20:
                default = default[:20] + "..."
            return default

        @staticmethod
        def field_type(field):
            ctype = " ".join(str(field.type).splitlines())
            ctype = ctype.replace("typing.", "")
            ctype = ctype.replace("typing_extensions.", "")
            for tname in ("str", "int", "float", "bool"):
                ctype = ctype.replace(f"<class '{tname}'>", tname)
            return ctype

    class MystNbConfigDirective(_ConfigBase):
        required_arguments = 1
        option_spec = {
            "sphinx": directives.flag,
            "section": lambda x: directives.choice(
                x, ["config", "read", "execute", "render"]
            ),
        }

        def run(self):
            """Run the directive."""
            level_name = directives.choice(
                self.arguments[0], ["global_lvl", "file_lvl", "cell_lvl"]
            )
            level = Section[level_name]

            config = NbParserConfig()
            text = self.table_header()
            count = 0
            for name, value, field in config.as_triple():
                # filter by sphinx options
                if "sphinx" in self.options and field.metadata.get("sphinx_exclude"):
                    continue
                # filter by level
                sections = field.metadata.get("sections") or []
                if level not in sections:
                    continue
                # filter by section
                if "section" in self.options:
                    section = Section[self.options["section"]]
                    if section not in sections:
                        continue

                if level == Section.global_lvl:
                    name = f"nb_{name}"
                elif level == Section.cell_lvl:
                    name = field.metadata.get("cell_key", name)

                description = " ".join(field.metadata.get("help", "").splitlines())
                default = self.field_default(value)
                ctype = self.field_type(field)
                text.extend(
                    [
                        f"* - `{name}`",
                        f"  - `{ctype}`",
                        f"  - `{default}`",
                        f"  - {description}",
                    ]
                )

                count += 1

            if not count:
                return []

            text.append("```````")
            node = nodes.Element()
            self.state.nested_parse(text, 0, node)
            return node.children

    class MystConfigDirective(_ConfigBase):
        option_spec = {
            "sphinx": directives.flag,
        }

        def run(self):
            """Run the directive."""
            config = MdParserConfig()
            text = self.table_header()
            count = 0
            for name, value, field in config.as_triple():
                # filter by sphinx options
                if "sphinx" in self.options and field.metadata.get("sphinx_exclude"):
                    continue

                name = f"myst_{name}"
                description = " ".join(field.metadata.get("help", "").splitlines())
                default = self.field_default(value)
                ctype = self.field_type(field)
                text.extend(
                    [
                        f"* - `{name}`",
                        f"  - `{ctype}`",
                        f"  - `{default}`",
                        f"  - {description}",
                    ]
                )

                count += 1

            if not count:
                return []

            text.append("```````")
            node = nodes.Element()
            self.state.nested_parse(text, 0, node)
            return node.children

    class DocutilsCliHelpDirective(SphinxDirective):
        """Directive to print the docutils CLI help."""

        has_content = False
        required_arguments = 0
        optional_arguments = 0
        final_argument_whitespace = False
        option_spec = {}

        def run(self):
            """Run the directive."""
            import io

            from docutils import nodes
            from docutils.frontend import OptionParser

            from myst_nb.docutils_ import Parser as DocutilsParser

            stream = io.StringIO()
            OptionParser(
                components=(DocutilsParser,),
                usage="mystnb-docutils-<writer> [options] [<source> [<destination>]]",
            ).print_help(stream)
            return [nodes.literal_block("", stream.getvalue())]

    app.add_directive("myst-config", MystConfigDirective)
    app.add_directive("mystnb-config", MystNbConfigDirective)
    app.add_directive("docutils-cli-help", DocutilsCliHelpDirective)
