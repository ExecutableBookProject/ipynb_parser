import json
from os.path import splitext
from pathlib import Path

# import jupytext
import nbformat as nbf
import yaml

CODE_DIRECTIVE = "{code-cell}"
RAW_DIRECTIVE = "{raw-cell}"


def string_to_notebook(inputstring, env):
    """de-serialize a notebook or text-based representation"""
    extension = splitext(env.doc2path(env.docname))[1]
    if extension == ".ipynb":
        return nbf.reads(inputstring, nbf.NO_CONVERT)
    elif is_myst_notebook(inputstring):
        # return jupytext.reads(inputstring, fmt="myst")
        return myst_to_notebook(inputstring)
    return None


def path_to_notebook(path):
    extension = splitext(path)[1]
    if extension == ".ipynb":
        return nbf.read(path, nbf.NO_CONVERT)
    else:
        return myst_to_notebook(Path(path).read_text())


def is_myst_notebook(inputstring):
    """Is the text file a MyST based notebook representation?"""
    # we need to distinguish between markdown representing notebooks
    # and standard notebooks.
    # Therefore, for now we require that, at a mimimum we can find some top matter
    # containing the jupytext format_name
    lines = inputstring.splitlines()
    if (not lines) or (not lines[0].startswith("---")):
        return False

    yaml_lines = []
    for line in lines[1:]:
        if line.startswith("---") or line.startswith("..."):
            break
        yaml_lines.append(line)

    front_matter = yaml.safe_load("\n".join(yaml_lines))
    if (
        front_matter.get("jupytext", {})
        .get("text_representation", {})
        .get("format_name", None)
        != "myst"
    ):
        return False

    if "name" not in front_matter.get("kernelspec", {}):
        raise IOError(
            "A myst notebook text-representation requires " "kernelspec/name metadata"
        )
    if "display_name" not in front_matter.get("kernelspec", {}):
        raise IOError(
            "A myst notebook text-representation requires "
            "kernelspec/display_name metadata"
        )
    return True


class MystMetadataParsingError(Exception):
    """Error when parsing metadata from myst formatted text"""


def strip_blank_lines(text):
    text = text.rstrip()
    while text and text.startswith("\n"):
        text = text[1:]
    return text


class MockDirective:
    option_spec = {"options": True}
    required_arguments = 0
    optional_arguments = 1
    has_content = True


def read_fenced_cell(token, cell_index, cell_type):
    from myst_parser.parse_directives import DirectiveParsingError, parse_directive_text

    try:
        _, options, body_lines = parse_directive_text(
            directive_class=MockDirective,
            argument_str="",
            content=token.content,
            validate_options=False,
        )
    except DirectiveParsingError as err:
        raise MystMetadataParsingError(
            "{0} cell {1} at line {2} could not be read: {3}".format(
                cell_type, cell_index, token.map[0] + 1, err
            )
        )
    return options, body_lines


def read_cell_metadata(token, cell_index):
    metadata = {}
    if token.content:
        try:
            metadata = json.loads(token.content.strip())
        except Exception as err:
            raise MystMetadataParsingError(
                "Markdown cell {0} at line {1} could not be read: {2}".format(
                    cell_index, token.map[0] + 1, err
                )
            )
        if not isinstance(metadata, dict):
            raise MystMetadataParsingError(
                "Markdown cell {0} at line {1} is not a dict".format(
                    cell_index, token.map[0] + 1
                )
            )

    return metadata


def myst_to_notebook(
    text,
    code_directive=CODE_DIRECTIVE,
    raw_directive=RAW_DIRECTIVE,
    store_line_numbers=False,
):
    """Convert text written in the myst format to a notebook.

    :param text: the file text
    :param code_directive: the name of the directive to search for containing code cells
    :param raw_directive: the name of the directive to search for containing raw cells
    :param store_line_numbers: add a `_source_lines` key to cell metadata,
        mapping to the source text.

    :raises MystMetadataParsingError if the metadata block is not valid JSON/YAML

    NOTE: we assume here that all of these directives are at the top-level,
    i.e. not nested in other directives.
    """
    from myst_parser.main import default_parser

    # parse markdown file up to the block level (i.e. don't worry about inline text)
    parser = default_parser("html", disable_syntax=["inline"])
    tokens = parser.parse(text + "\n")
    lines = text.splitlines()
    md_start_line = 0

    # get the document metadata
    metadata_nb = {}
    if tokens[0].type == "front_matter":
        metadata = tokens.pop(0)
        md_start_line = metadata.map[1]
        try:
            metadata_nb = yaml.safe_load(metadata.content)
        except (yaml.parser.ParserError, yaml.scanner.ScannerError) as error:
            raise MystMetadataParsingError("Notebook metadata: {}".format(error))

    # create an empty notebook
    nbf_version = nbf.v4
    kwargs = {"metadata": nbf.from_dict(metadata_nb)}
    notebook = nbf_version.new_notebook(**kwargs)

    def _flush_markdown(start_line, token, md_metadata):
        """When we find a cell we check if there is preceding text.o"""
        endline = token.map[0] if token else len(lines)
        md_source = strip_blank_lines("\n".join(lines[start_line:endline]))
        meta = nbf.from_dict(md_metadata)
        if store_line_numbers:
            meta["_source_lines"] = [start_line, endline]
        if md_source:
            notebook.cells.append(
                nbf_version.new_markdown_cell(source=md_source, metadata=meta)
            )

    # iterate through the tokens to identify notebook cells
    nesting_level = 0
    md_metadata = {}

    for token in tokens:

        nesting_level += token.nesting

        if nesting_level != 0:
            # we ignore fenced block that are nested, e.g. as part of lists, etc
            continue

        if token.type == "fence" and token.info.startswith(code_directive):
            _flush_markdown(md_start_line, token, md_metadata)
            options, body_lines = read_fenced_cell(token, len(notebook.cells), "Code")
            meta = nbf.from_dict(options)
            if store_line_numbers:
                meta["_source_lines"] = [token.map[0] + 1, token.map[1]]
            notebook.cells.append(
                nbf_version.new_code_cell(source="\n".join(body_lines), metadata=meta)
            )
            md_metadata = {}
            md_start_line = token.map[1]

        elif token.type == "fence" and token.info.startswith(raw_directive):
            _flush_markdown(md_start_line, token, md_metadata)
            options, body_lines = read_fenced_cell(token, len(notebook.cells), "Raw")
            meta = nbf.from_dict(options)
            if store_line_numbers:
                meta["_source_lines"] = [token.map[0] + 1, token.map[1]]
            notebook.cells.append(
                nbf_version.new_raw_cell(source="\n".join(body_lines), metadata=meta)
            )
            md_metadata = {}
            md_start_line = token.map[1]

        elif token.type == "myst_block_break":
            _flush_markdown(md_start_line, token, md_metadata)
            md_metadata = read_cell_metadata(token, len(notebook.cells))
            md_start_line = token.map[1]

    _flush_markdown(md_start_line, None, md_metadata)

    return notebook
