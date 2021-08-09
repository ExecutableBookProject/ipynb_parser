import copy
import json
from pathlib import Path
from typing import Dict, List, cast

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.domains import Domain
from sphinx.domains.math import MathDomain
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective

from myst_nb.nb_glue import GLUE_PREFIX
from myst_nb.nb_glue.utils import find_all_keys
from myst_nb.nodes import CellOutputBundleNode, CellOutputNode

SPHINX_LOGGER = logging.getLogger(__name__)


class PasteNode(nodes.container):
    """Represent a MimeBundle in the Sphinx AST, to be transformed later."""

    def __init__(self, key, **attributes):
        attributes["key"] = key
        super().__init__("", **attributes)

    @property
    def key(self):
        return self.attributes["key"]

    def copy(self):
        obj = self.__class__(
            self.key, **{k: v for k, v in self.attributes.items() if k != "key"}
        )
        obj.document = self.document
        obj.source = self.source
        obj.line = self.line
        return obj

    def create_node(self, output: dict, document, env):
        """Create the output node, give the cell output."""
        # the whole output chunk is deposited and rendered later
        # TODO move these nodes to separate module, to avoid cyclic imports
        output_node = CellOutputBundleNode([output], "default")
        out_node = CellOutputNode(classes=["cell_output"])
        out_node.source, out_node.line = self.source, self.line
        out_node += output_node
        return out_node


class PasteInlineNode(PasteNode):
    def create_node(self, output: dict, document, env):
        """Create the output node, give the cell output."""
        # the whole output chunk is deposited and rendered later
        bundle_node = CellOutputBundleNode([output], "inline")
        inline_node = nodes.inline("", "", bundle_node, classes=["pasted-inline"])
        inline_node.source, inline_node.line = self.source, self.line
        return inline_node


class PasteTextNode(PasteNode):
    """A subclass of ``PasteNode`` that only supports plain text."""

    @property
    def formatting(self):
        return self.attributes["formatting"]

    def create_node(self, output: dict, document, env):
        """Create the output node, give the cell output."""
        mimebundle = output["data"]
        if "text/plain" in mimebundle:
            text = mimebundle["text/plain"].strip("'")
            # If formatting is specified, see if we have a number of some kind
            if self.formatting:
                try:
                    newtext = float(text)
                    text = f"{newtext:>{self.formatting}}"
                except ValueError:
                    pass
            node = nodes.inline(text, text, classes=["pasted-text"])
            node.source, node.line = self.source, self.line
            return node
        return None


class PasteMathNode(PasteNode):
    """A subclass of ``PasteNode`` that only supports plain text.

    Code mainly copied from sphinx.directives.patches.MathDirective
    """

    def create_node(self, output: dict, document, env):
        """Create the output node, give the cell output."""
        mimebundle = output["data"]
        if "text/latex" in mimebundle:
            text = mimebundle["text/latex"].strip("$")
            node = nodes.math_block(
                text,
                text,
                classes=["pasted-math"],
                docname=env.docname,
                number=self["math_number"],
                nowrap=self["math_nowrap"],
                label=self["math_label"],
            )
            node.line, node.source = self.line, self.source
            if "math_class" in self and self["math_class"]:
                node["classes"].append(self["math_class"])
            return node
        return None


# Role and directive for pasting
class Paste(SphinxDirective):
    required_arguments = 1
    final_argument_whitespace = True
    has_content = False

    option_spec = {"id": directives.unchanged}

    def run(self):
        node = PasteNode(self.arguments[0])
        self.set_source_info(node)
        return [node]


class PasteMath(Paste):

    option_spec = Paste.option_spec.copy()
    option_spec["class"] = directives.class_option
    option_spec["label"] = directives.unchanged
    option_spec["nowrap"] = directives.flag
    has_content = False

    def run(self):
        paste_node = PasteMathNode(self.arguments[0])
        self.set_source_info(paste_node)
        paste_node["math_class"] = self.options.pop("class", None)
        paste_node["math_label"] = self.options.pop("label", None)
        paste_node["math_nowrap"] = "nowrap" in self.options
        target = self.add_target(paste_node)
        if target:
            return [target, paste_node]
        return [paste_node]

    def add_target(self, node):
        if not node["math_label"]:
            return None
        # register label to domain
        domain = cast(MathDomain, self.env.get_domain("math"))
        domain.note_equation(self.env.docname, node["math_label"], location=node)
        node["math_number"] = domain.get_equation_number_for(node["math_label"])

        # add target node
        node_id = nodes.make_id("equation-%s" % node["math_label"])
        target = nodes.target("", "", ids=[node_id])
        self.state.document.note_explicit_target(target)
        return target


class PasteFigure(Paste):
    def align(argument):
        return directives.choice(argument, ("left", "center", "right"))

    def figwidth_value(argument):
        return directives.length_or_percentage_or_unitless(argument, "px")

    option_spec = Paste.option_spec.copy()
    option_spec["figwidth"] = figwidth_value
    option_spec["figclass"] = directives.class_option
    option_spec["align"] = align
    option_spec["name"] = directives.unchanged
    has_content = True

    def run(self):
        figwidth = self.options.pop("figwidth", None)
        figclasses = self.options.pop("figclass", None)
        align = self.options.pop("align", None)
        # On the Paste node we should add an attribute to specify that only image
        # type mimedata is allowed, then this would be used by
        # PasteNodesToDocutils -> CellOutputsToNodes to alter the render priority
        # and/or log warnings if that type of mimedata is not available
        (paste_node,) = Paste.run(self)
        if isinstance(paste_node, nodes.system_message):
            return [paste_node]
        figure_node = nodes.figure("", paste_node)
        figure_node.line = paste_node.line
        figure_node.source = paste_node.source
        if figwidth is not None:
            figure_node["width"] = figwidth
        if figclasses:
            figure_node["classes"] += figclasses
        if align:
            figure_node["align"] = align
        self.add_name(figure_node)
        # note: this is copied directly from sphinx.Figure
        if self.content:
            node = nodes.Element()  # anonymous container for parsing
            self.state.nested_parse(self.content, self.content_offset, node)
            first_node = node[0]
            if isinstance(first_node, nodes.paragraph):
                caption = nodes.caption(first_node.rawsource, "", *first_node.children)
                caption.source = first_node.source
                caption.line = first_node.line
                figure_node += caption
            elif not (isinstance(first_node, nodes.comment) and len(first_node) == 0):
                error = self.state_machine.reporter.error(
                    "Figure caption must be a paragraph or empty comment.",
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno,
                )
                return [figure_node, error]
            if len(node) > 1:
                figure_node += nodes.legend("", *node[1:])
        return [figure_node]


def paste_any_role(name, rawtext, text, lineno, inliner, options=None, content=()):
    """This role will simply add the cell output"""
    path = inliner.document.current_source
    # Remove line number if we have a notebook because it is unreliable
    if path.endswith(".ipynb"):
        lineno = None
    path = str(Path(path).with_suffix(""))
    return [PasteInlineNode(text, location=(path, lineno))], []


def paste_text_role(name, rawtext, text, lineno, inliner, options=None, content=()):
    """This role will be parsed as text, with some formatting fanciness.

    The text can have a final ``:``,
    whereby everything to the right will be treated as a formatting string, e.g.
    ``key:.2f``
    """
    # First check if we have both key:format in the key
    parts = text.rsplit(":", 1)
    if len(parts) == 2:
        key, formatting = parts
    else:
        key = parts[0]
        formatting = None

    path = inliner.document.current_source
    # Remove line number if we have a notebook because it is unreliable
    if path.endswith(".ipynb"):
        lineno = None
    path = str(Path(path).with_suffix(""))
    return [PasteTextNode(key, formatting=formatting, location=(path, lineno))], []


class NbGlueDomain(Domain):
    """A sphinx domain for handling glue data"""

    name = "glue"
    label = "NotebookGlue"
    # data version, bump this when the format of self.data changes
    data_version = 0.1
    # data value for a fresh environment
    # - cache is the mapping of all keys to outputs
    # - docmap is the mapping of docnames to the set of keys it contains
    initial_data = {"cache": {}, "docmap": {}}

    directives = {"": Paste, "any": Paste, "figure": PasteFigure, "math": PasteMath}

    roles = {"": paste_any_role, "any": paste_any_role, "text": paste_text_role}

    @property
    def cache(self) -> dict:
        return self.env.domaindata[self.name]["cache"]

    @property
    def docmap(self) -> dict:
        return self.env.domaindata[self.name]["docmap"]

    def __contains__(self, key):
        return key in self.cache

    def get(self, key, view=True, replace=True):
        """Grab the output for this key and replace `glue` specific prefix info."""
        output = self.cache.get(key)
        if view:
            output = copy.deepcopy(output)
        if replace:
            output["data"] = {
                key.replace(GLUE_PREFIX, ""): val for key, val in output["data"].items()
            }
        return output

    @classmethod
    def from_env(cls, env) -> "NbGlueDomain":
        return env.domains[cls.name]

    def write_cache(self, path=None):
        """If None, write to doctreedir"""
        if path is None:
            path = Path(self.env.doctreedir).joinpath("glue_cache.json")
        if isinstance(path, str):
            path = Path(path)
        with path.open("w", encoding="utf8") as handle:
            json.dump(
                {
                    d: {k: self.cache[k] for k in vs if k in self.cache}
                    for d, vs in self.docmap.items()
                    if vs
                },
                handle,
                indent=2,
            )

    def add_notebook(self, ntbk, docname):
        """Find all glue keys from the notebook and add to the cache."""
        new_keys = find_all_keys(
            ntbk,
            existing_keys={v: k for k, vs in self.docmap.items() for v in vs},
            path=str(docname),
            logger=SPHINX_LOGGER,
        )
        self.docmap[str(docname)] = set(new_keys)
        self.cache.update(new_keys)

    def clear_doc(self, docname: str) -> None:
        """Remove traces of a document in the domain-specific inventories."""
        for key in self.docmap.get(docname, []):
            self.cache.pop(key, None)
        self.docmap.pop(docname, None)

    def merge_domaindata(self, docnames: List[str], otherdata: Dict) -> None:
        """Merge in data regarding *docnames* from a different domaindata
        inventory (coming from a subprocess in parallel builds).
        """
        # TODO need to deal with key clashes
        raise NotImplementedError(
            "merge_domaindata must be implemented in %s "
            "to be able to do parallel builds!" % self.__class__
        )
