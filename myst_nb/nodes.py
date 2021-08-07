"""AST nodes to designate notebook components."""
from typing import List

from docutils import nodes
from nbformat import NotebookNode


class CellNode(nodes.container):
    """Represent a cell in the Sphinx AST."""

    def __init__(self, rawsource="", *children, **attributes):
        super().__init__("", **attributes)


class CellInputNode(nodes.container):
    """Represent an input cell in the Sphinx AST."""

    def __init__(self, rawsource="", *children, **attributes):
        super().__init__("", **attributes)


class CellOutputNode(nodes.container):
    """Represent an output cell in the Sphinx AST."""

    def __init__(self, rawsource="", *children, **attributes):
        super().__init__("", **attributes)


class CellOutputBundleNode(nodes.container):
    """Represent a MimeBundle in the Sphinx AST, to be transformed later."""

    def __init__(self, outputs, renderer: str, metadata=None, **attributes):
        self._outputs = outputs
        self._renderer = renderer
        self._metadata = metadata or NotebookNode()
        attributes["output_count"] = len(outputs)  # for debugging with pformat
        super().__init__("", **attributes)

    @property
    def outputs(self) -> List[NotebookNode]:
        """The outputs associated with this cell."""
        return self._outputs

    @property
    def metadata(self) -> NotebookNode:
        """The cell level metadata for this output."""
        return self._metadata

    @property
    def renderer(self) -> str:
        """The renderer for this output cell."""
        return self._renderer

    def copy(self):
        obj = self.__class__(
            outputs=self._outputs,
            renderer=self._renderer,
            metadata=self._metadata,
            **self.attributes,
        )
        obj.document = self.document
        obj.source = self.source
        obj.line = self.line
        return obj
