"""A Sphinx post-transform, to convert notebook outpus to AST nodes."""
import os
from abc import ABC, abstractmethod
from typing import List, Optional
from unittest import mock

import nbconvert
from docutils import nodes
from docutils.parsers.rst import directives
from importlib_metadata import entry_points
from jupyter_sphinx.ast import JupyterWidgetViewNode, strip_latex_delimiters
from jupyter_sphinx.utils import sphinx_abs_dir
from myst_parser.docutils_renderer import make_document
from myst_parser.main import MdParserConfig, default_parser
from nbformat import NotebookNode
from sphinx.environment import BuildEnvironment
from sphinx.environment.collectors.asset import ImageCollector
from sphinx.errors import SphinxError
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util import logging

from .nodes import CellOutputBundleNode

LOGGER = logging.getLogger(__name__)

WIDGET_VIEW_MIMETYPE = "application/vnd.jupyter.widget-view+json"


def get_default_render_priority(builder: str) -> Optional[List[str]]:
    priority = {
        builder: (
            WIDGET_VIEW_MIMETYPE,
            "application/javascript",
            "text/html",
            "image/svg+xml",
            "image/png",
            "image/jpeg",
            "text/markdown",
            "text/latex",
            "text/plain",
        )
        for builder in (
            "html",
            "readthedocs",
            "singlehtml",
            "dirhtml",
            "linkcheck",
            "readthedocsdirhtml",
            "readthedocssinglehtml",
            "readthedocssinglehtmllocalmedia",
            "epub",
        )
    }
    # TODO: add support for "image/svg+xml"
    priority["latex"] = (
        "application/pdf",
        "image/png",
        "image/jpeg",
        "text/latex",
        "text/markdown",
        "text/plain",
    )
    return priority.get(builder, None)


class MystNbEntryPointError(SphinxError):
    category = "MyST NB Renderer Load"


def load_renderer(name: str) -> "CellOutputRendererBase":
    """Load a renderer,
    given a name within the ``myst_nb.mime_render`` entry point group
    """
    all_eps = entry_points()
    if hasattr(all_eps, "select"):
        # importlib_metadata >= 3.6 or importlib.metadata in python >=3.10
        eps = all_eps.select(group="myst_nb.mime_render", name=name)
        found = name in eps.names
    else:
        eps = {ep.name: ep for ep in all_eps.get("myst_nb.mime_render", [])}
        found = name in eps
    if found:
        klass = eps[name].load()
        if not issubclass(klass, CellOutputRendererBase):
            raise MystNbEntryPointError(
                f"Entry Point for myst_nb.mime_render:{name} "
                f"is not a subclass of `CellOutputRendererBase`: {klass}"
            )
        return klass

    raise MystNbEntryPointError(f"No Entry Point found for myst_nb.mime_render:{name}")


class CellOutputsToNodes(SphinxPostTransform):
    """Use the builder context to transform a CellOutputNode into Sphinx nodes."""

    # process very early, before CitationReferenceTransform (5), ReferencesResolver (10)
    # https://www.sphinx-doc.org/en/master/extdev/appapi.html#sphinx.application.Sphinx.add_transform
    default_priority = 4

    def run(self):
        abs_dir = sphinx_abs_dir(self.env)
        renderers = {}  # cache renderers
        for node in self.document.traverse(CellOutputBundleNode):
            try:
                renderer_cls = renderers[node.renderer]
            except KeyError:
                renderer_cls = load_renderer(node.renderer)
                renderers[node.renderer] = renderer_cls
            renderer = renderer_cls(self.document, node, abs_dir)
            output_nodes = renderer.cell_output_to_nodes(self.env.nb_render_priority)
            node.replace_self(output_nodes)

        # Image collect extra nodes from cell outputs that we need to process
        # this normally gets called as a `doctree-read` event
        for node in self.document.traverse(nodes.image):
            # If the image node has `candidates` then it's already been processed
            # as in-line markdown, so skip it
            if "candidates" in node:
                continue
            col = ImageCollector()

            # use the node docname, where possible, to deal with single document builds
            docname = (
                self.app.env.path2doc(node.source)
                if node.source
                else self.app.env.docname
            )
            with mock.patch.dict(self.app.env.temp_data, {"docname": docname}):
                col.process_doc(self.app, node)


class CellOutputRendererBase(ABC):
    """An abstract base class for rendering Notebook outputs to docutils nodes.

    Subclasses should implement the ``render`` method.
    """

    def __init__(
        self, document: nodes.document, node: CellOutputBundleNode, sphinx_dir: str
    ):
        """
        :param sphinx_dir: Sphinx "absolute path" to the output folder,
            so it is a relative path to the source folder prefixed with ``/``.
        """
        self.document = document
        self.env = document.settings.env  # type: BuildEnvironment
        self.node = node
        self.sphinx_dir = sphinx_dir

    def cell_output_to_nodes(self, data_priority: List[str]) -> List[nodes.Node]:
        """Convert a jupyter cell with outputs and filenames to doctree nodes.

        :param outputs: a list of outputs from a Jupyter cell
        :param data_priority: media type by priority.

        :returns: list of docutils nodes

        """
        output_nodes = []
        for idx, output in enumerate(self.node.outputs):
            output_type = output["output_type"]
            if output_type == "stream":
                if output["name"] == "stderr":
                    output_nodes.extend(self.render("stderr", output, idx))
                else:
                    output_nodes.extend(self.render("stdout", output, idx))
            elif output_type == "error":
                output_nodes.extend(self.render("traceback", output, idx))

            elif output_type in ("display_data", "execute_result"):
                try:
                    # First mime_type by priority that occurs in output.
                    mime_type = next(x for x in data_priority if x in output["data"])
                except StopIteration:
                    # TODO this is incompatible with glue outputs
                    # perhaps have sphinx config to turn on/off this error reporting?
                    # and/or only warn if "scrapbook" not in output.metadata
                    # (then enable tests/test_render_outputs.py::test_unknown_mimetype)
                    # LOGGER.warning(
                    #     "MyST-NB: output contains no MIME type in priority list: %s",
                    #     list(output["data"].keys()),
                    #     location=location,
                    # )
                    continue
                output_nodes.extend(self.render(mime_type, output, idx))

        return output_nodes

    def add_source_and_line(self, *nodes: List[nodes.Node]):
        """Add the source and line recursively to all nodes."""
        location = self.node.source, self.node.line
        for node in nodes:
            node.source, node.line = location
            for child in node.traverse():
                child.source, child.line = location

    def make_warning(self, error_msg: str) -> nodes.system_message:
        """Raise an exception or generate a warning if appropriate,
        and return a system_message node"""
        return self.document.reporter.warning(
            "output render: {}".format(error_msg),
            line=self.node.line,
        )

    def make_error(self, error_msg: str) -> nodes.system_message:
        """Raise an exception or generate a warning if appropriate,
        and return a system_message node"""
        return self.document.reporter.error(
            "output render: {}".format(error_msg),
            line=self.node.line,
        )

    def make_severe(self, error_msg: str) -> nodes.system_message:
        """Raise an exception or generate a warning if appropriate,
        and return a system_message node"""
        return self.document.reporter.severe(
            "output render: {}".format(error_msg),
            line=self.node.line,
        )

    def add_name(self, node: nodes.Node, name: str):
        """Append name to node['names'].

        Also normalize the name string and register it as explicit target.
        """
        name = nodes.fully_normalize_name(name)
        if "name" in node:
            del node["name"]
        node["names"].append(name)
        self.document.note_explicit_target(node, node)
        return name

    def parse_markdown(
        self, text: str, parent: Optional[nodes.Node] = None
    ) -> List[nodes.Node]:
        """Parse text as CommonMark, in a new document."""
        parser = default_parser(MdParserConfig(commonmark_only=True))

        # setup parent node
        if parent is None:
            parent = nodes.container()
            self.add_source_and_line(parent)
        parser.options["current_node"] = parent

        # setup containing document
        new_doc = make_document(self.node.source)
        new_doc.settings = self.document.settings
        new_doc.reporter = self.document.reporter
        parser.options["document"] = new_doc

        # use the node docname, where possible, to deal with single document builds
        with mock.patch.dict(
            self.env.temp_data, {"docname": self.env.path2doc(self.node.source)}
        ):
            subsequent_nodes = parser.render(text)

        # TODO is there any transforms we should retroactively carry out?
        return parent.children + subsequent_nodes

    @abstractmethod
    def render(
        self, mime_type: str, output: NotebookNode, index: int
    ) -> List[nodes.Node]:
        """Take a MIME bundle and MIME type, and return zero or more nodes."""
        pass


class CellOutputRenderer(CellOutputRendererBase):
    def __init__(
        self, document: nodes.document, node: CellOutputBundleNode, sphinx_dir: str
    ):
        """
        :param sphinx_dir: Sphinx "absolute path" to the output folder,
            so it is a relative path to the source folder prefixed with ``/``.
        """
        super().__init__(document, node, sphinx_dir)
        self._render_map = {
            "stderr": self.render_stderr,
            "stdout": self.render_stdout,
            "traceback": self.render_traceback,
            "text/plain": self.render_text_plain,
            "text/markdown": self.render_text_markdown,
            "text/html": self.render_text_html,
            "text/latex": self.render_text_latex,
            "application/javascript": self.render_application_javascript,
            WIDGET_VIEW_MIMETYPE: self.render_widget,
        }

    def render(
        self, mime_type: str, output: NotebookNode, index: int
    ) -> List[nodes.Node]:
        """Take a MIME bundle and MIME type, and return zero or more nodes."""
        if mime_type.startswith("image"):
            nodes = self.create_render_image(mime_type)(output, index)
            self.add_source_and_line(*nodes)
            return nodes
        if mime_type in self._render_map:
            nodes = self._render_map[mime_type](output, index)
            self.add_source_and_line(*nodes)
            return nodes

        LOGGER.warning(
            "MyST-NB: No renderer found for output MIME: %s",
            mime_type,
            location=(self.node.source, self.node.line),
        )
        return []

    def render_stderr(self, output: NotebookNode, index: int):
        """Output a container with an unhighlighted literal block."""
        text = output["text"]

        if self.env.config.nb_output_stderr == "show":
            pass
        elif self.env.config.nb_output_stderr == "remove-warn":
            self.make_warning(f"stderr was found in the cell outputs: {text}")
            return []
        elif self.env.config.nb_output_stderr == "warn":
            self.make_warning(f"stderr was found in the cell outputs: {text}")
        elif self.env.config.nb_output_stderr == "error":
            self.make_error(f"stderr was found in the cell outputs: {text}")
        elif self.env.config.nb_output_stderr == "severe":
            self.make_severe(f"stderr was found in the cell outputs: {text}")

        if (
            "remove-stderr" in self.node.metadata.get("tags", [])
            or self.env.config.nb_output_stderr == "remove"
        ):
            return []

        node = nodes.literal_block(
            text=output["text"],
            rawsource=output["text"],
            language=self.env.config.nb_render_text_lexer,
            classes=["output", "stderr"],
        )
        return [node]

    def render_stdout(self, output: NotebookNode, index: int):

        if "remove-stdout" in self.node.metadata.get("tags", []):
            return []

        return [
            nodes.literal_block(
                text=output["text"],
                rawsource=output["text"],
                language=self.env.config.nb_render_text_lexer,
                classes=["output", "stream"],
            )
        ]

    def render_traceback(self, output: NotebookNode, index: int):
        traceback = "\n".join(output["traceback"])
        text = nbconvert.filters.strip_ansi(traceback)
        return [
            nodes.literal_block(
                text=text,
                rawsource=text,
                language="ipythontb",
                classes=["output", "traceback"],
            )
        ]

    def render_text_markdown(self, output: NotebookNode, index: int):
        text = output["data"]["text/markdown"]
        return self.parse_markdown(text)

    def render_text_html(self, output: NotebookNode, index: int):
        text = output["data"]["text/html"]
        return [nodes.raw(text=text, format="html", classes=["output", "text_html"])]

    def render_text_latex(self, output: NotebookNode, index: int):
        text = output["data"]["text/latex"]
        self.env.get_domain("math").data["has_equations"][self.env.docname] = True
        return [
            nodes.math_block(
                text=strip_latex_delimiters(text),
                nowrap=False,
                number=None,
                classes=["output", "text_latex"],
            )
        ]

    def render_text_plain(self, output: NotebookNode, index: int):
        text = output["data"]["text/plain"]
        return [
            nodes.literal_block(
                text=text,
                rawsource=text,
                language=self.env.config.nb_render_text_lexer,
                classes=["output", "text_plain"],
            )
        ]

    def render_application_javascript(self, output: NotebookNode, index: int):
        data = output["data"]["application/javascript"]
        return [
            nodes.raw(
                text='<script type="{mime_type}">{data}</script>'.format(
                    mime_type="application/javascript", data=data
                ),
                format="html",
            )
        ]

    def render_widget(self, output: NotebookNode, index: int):
        data = output["data"][WIDGET_VIEW_MIMETYPE]
        return [JupyterWidgetViewNode(view_spec=data)]

    def create_render_image(self, mime_type: str):
        def _render_image(output: NotebookNode, index: int):
            # Sphinx treats absolute paths as being rooted at the source
            # directory, so make a relative path, which Sphinx treats
            # as being relative to the current working directory.
            filename = os.path.basename(output.metadata["filenames"][mime_type])

            # checks if file dir path is inside a subdir of dir
            filedir = os.path.dirname(output.metadata["filenames"][mime_type])
            subpaths = filedir.split(self.sphinx_dir)
            final_dir = self.sphinx_dir
            if subpaths and len(subpaths) > 1:
                subpath = subpaths[1]
                final_dir += subpath

            uri = os.path.join(final_dir, filename)
            # TODO I'm not quite sure why, but as soon as you give it a width,
            # it becomes clickable?! (i.e. will open the image in the browser)
            image_node = nodes.image(uri=uri)

            myst_meta_img = self.node.metadata.get(
                self.env.config.nb_render_key, {}
            ).get("image", {})

            for key, spec in [
                ("classes", directives.class_option),
                ("alt", directives.unchanged),
                ("height", directives.length_or_unitless),
                ("width", directives.length_or_percentage_or_unitless),
                ("scale", directives.percentage),
                ("align", align),
            ]:
                if key in myst_meta_img:
                    value = myst_meta_img[key]
                    try:
                        image_node[key] = spec(value)
                    except (ValueError, TypeError) as error:
                        error_msg = (
                            "Invalid image attribute: "
                            "(key: '{}'; value: {})\n{}".format(key, value, error)
                        )
                        return [self.make_error(error_msg)]

            myst_meta_fig = self.node.metadata.get(
                self.env.config.nb_render_key, {}
            ).get("figure", {})
            if "caption" not in myst_meta_fig:
                return [image_node]

            figure_node = nodes.figure("", image_node)
            caption = nodes.caption(myst_meta_fig["caption"], "")
            figure_node += caption
            # TODO only contents of one paragraph? (and second should be a legend)
            self.parse_markdown(myst_meta_fig["caption"], caption)
            if "name" in myst_meta_fig:
                name = myst_meta_fig["name"]
                self.add_source_and_line(figure_node)
                self.add_name(figure_node, name)
                # The target should have already been processed by now, with
                # sphinx.transforms.references.SphinxDomains, which calls
                # sphinx.domains.std.StandardDomain.process_doc,
                # so we have to replicate that here
                std = self.env.get_domain("std")
                nametypes = self.document.nametypes.items()
                self.document.nametypes = {name: True}
                try:
                    std.process_doc(self.env, self.env.docname, self.document)
                finally:
                    self.document.nametypes = nametypes

            return [figure_node]

        return _render_image


def align(argument):
    return directives.choice(argument, ("left", "center", "right"))


class CellOutputRendererInline(CellOutputRenderer):
    """Replaces literal/math blocks with non-block versions"""

    def render_stderr(self, output: NotebookNode, index: int):
        """Output a container with an unhighlighted literal"""
        return [
            nodes.literal(
                text=output["text"],
                rawsource="",  # disables Pygment highlighting
                language="none",
                classes=["stderr"],
            )
        ]

    def render_stdout(self, output: NotebookNode, index: int):
        """Output a container with an unhighlighted literal"""
        return [
            nodes.literal(
                text=output["text"],
                rawsource="",  # disables Pygment highlighting
                language="none",
                classes=["output", "stream"],
            )
        ]

    def render_traceback(self, output: NotebookNode, index: int):
        traceback = "\n".join(output["traceback"])
        text = nbconvert.filters.strip_ansi(traceback)
        return [
            nodes.literal(
                text=text,
                rawsource=text,
                language="ipythontb",
                classes=["output", "traceback"],
            )
        ]

    def render_text_latex(self, output: NotebookNode, index: int):
        data = output["data"]["text/latex"]
        self.env.get_domain("math").data["has_equations"][self.env.docname] = True
        return [
            nodes.math(
                text=strip_latex_delimiters(data),
                nowrap=False,
                number=None,
                classes=["output", "text_latex"],
            )
        ]

    def render_text_plain(self, output: NotebookNode, index: int):
        data = output["data"]["text/plain"]
        return [
            nodes.literal(
                text=data,
                rawsource=data,
                language="none",
                classes=["output", "text_plain"],
            )
        ]
