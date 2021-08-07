# Get started

This section covers how to get started with the `MyST-NB` Sphinx extension.
The Sphinx extension allows you to read markdown (`.md`) and Jupyter Notebook (`.ipynb`)
files into your Sphinx site. It also enables you to write [MyST Markdown](myst.md)
in your pages.

## Install and activate

To install `myst-nb`, do the following:

* **Install** `myst-nb` with the following command:

  ```bash
  pip install myst-nb
  ```

* **Activate** the `myst_nb` extension in your Sphinx site by adding it to your list of
  Sphinx extensions in `conf.py`:

  ```python
  extensions = [
      ...,
      "myst_nb"
  ]
  ```

Once you do this, MyST-NB will now parse both markdown (`.md`), Jupyter notebooks (`.ipynb`), and even [text-based Notebooks](markdown.md) (`.md`) into your Sphinx site
(see also [custom notebook formats](examples/custom_formats)).

(start/error-reporting)=

## Sphinx Error Reporting

For `.md` files, sphinx will correctly report the line number that the error or warning is associated with:

```
source/path:4: (WARNING/2) Duplicate reference definition: abc
```

For `.ipynb` files, these errors also correspond to a cell index.
To allow for this, we use a special format of line number corresponding to: `<CELL_INDEX> * 10000 + LINE_NUMBER`, for example:

```
source/path:10004: (WARNING/2) Duplicate reference definition: abc
```

(start/config-options)=

## MyST-NB configuration options

The MyST-NB parser derives from {ref}`the base MyST-Parser <myst:intro/get-started>`, and so all the same configuration options are available.
See the {ref}`MyST configuration options <myst:sphinx/config-options>` for the full set of options.

MyST-NB then adds some additional configuration, specific to notebooks.
Firstly for execution:

`````{list-table}
:header-rows: 1

* - Option
  - Default
  - Description
* - `jupyter_cache`
  - ""
  - Path to jupyter_cache, [see here](execute/cache) for details.
* - `execution_excludepatterns`
  - ()
  - Exclude certain file patterns from execution, [see here](execute/config) for details.
* - `jupyter_execute_notebooks`
  - "auto"
  - The logic for executing notebooks, [see here](execute/config) for details.
* - `execution_in_temp`
  - `False`
  - If `True`, then a temporary directory will be created and used as the command working directory (cwd), if `False` then the notebook's parent directory will be the cwd.
* - `execution_allow_errors`
  - `False`
  - If `False`, when a code cell raises an error the execution is stopped, if `True` then all cells are always run.
    This can also be overridden by metadata in a notebook, [see here](execute/allow_errors) for details.
* - `execution_fail_on_error`
  - `False`
  - If `False`, disallowed errors will result in a sphinx warnings.
    If `True`, then disallowed errors result in a failed build. [See here](execute/fail_on_error) for details.
* - `execution_timeout`
  - 30
  - The maximum time (in seconds) each notebook cell is allowed to run.
    This can also be overridden by metadata in a notebook, [see here](execute/timeout) for details.
* - `execution_show_tb`
  - `False`
  - Show failed notebook tracebacks in stdout (in addition to writing to file).
`````

Then for parsing and output rendering:

`````{list-table}
:header-rows: 1

* - Option
  - Default
  - Description
* - `nb_custom_formats`
  - `{}`
  - Define custom functions for conversion of files to notebooks, [see here](examples/custom_formats) for details.
* - `nb_render_priority`
  - `{}`
  - Dict override for MIME type render priority, [see here](use/format/priority) for details.
* - `nb_render_plugin`
  - `default`
  - Entry point pointing toward a code cell output renderer, [see here](use/format/cutomise) for details.
* - `nb_render_text_lexer`
  - `myst-ansi`
  - pygments lexer for rendering text outputs, [see here](use/format/ansi) for details.
* - `nb_render_key`
  - `render`
  - The top-level cell metadata key, to store render control data, [see here](use/format/images) for examples.
* - `nb_output_stderr`
  - `show`
  - One of 'show', 'remove', 'warn', 'error' or 'severe', [see here](use/format/stderr) for details.
`````
