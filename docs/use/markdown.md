---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: '0.8'
    jupytext_version: '1.4.1'
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---
# MyST Markdown Notebooks

MyST Markdown Notebooks allow you to write your Jupyter Notebook
entirely in markdown using the
[MyST Markdown format](https://jupytext.readthedocs.io/en/latest/formats.html#myst-markdown).
This allows you to store notebook metadata,
markdown, and cell inputs in a text-based format that is easy
to read and use with text-based tools.

MyST Notebooks can be [parsed directly into Sphinx](myst-nb/sphinx)
with the `myst_nb` Sphinx extension, and are similarly-supported as
[Jupyter Book inputs as well](myst-nb/jupyter-book). [^download]

MyST Notebooks have a 1-to-1 mapping with the notebook, so can be
[converted to `.ipynb` files](converting-ipynb) and
[opened as notebooks in Jupyter interfaces](myst-nb/jupyter-interfaces) (with jupytext installed).
When used with Sphinx, MyST Notebooks are also integrated
directly into the {ref}`Execution and Caching <execute/cache>` machinery!

[^download]: This notebook can be downloaded as
            **{nb-download}`markdown.py`** and {download}`markdown.md`

## The MyST Notebook Structure

MyST Markdown Notebooks (or MyST Notebooks for short) have
three main types of content: **markdown** (that can be written as
CommonMark or MyST Markdown), **code cells** (that are written
with MyST Markdown `code-cell` directive syntax), and cell/notebook
metadata (that are written as YAML wrapped in `---`). Here is an
example with these main syntax pieces:

````md
---
kernelspec:
  display_name: Python 3
  name: python3
notebookmetadatakey: val
notebookmetadatakey2: val2
---

# Markdown content is written as regular markdown

You can also write {ref}`MyST Markdown <myst>`.

```{code-cell}
---
cellmetadatakey: val1
---
print("Here is a Python cell")
```

And here is more markdown.

+++

Separate markdown cells with `+++` lines.

```{code-cell}
:cellmetadatakey: val1
print("Another code cell with a second optional metadata syntax")
```
````

:::{note}
The kernel that your code cells use is determined by the notebook-level
metadata for your MyST Notebook file. If no kernel is given, then the default kernel
will be used.
:::

### Syntax for code cells

When writing MyST Notebooks, use the following syntax to define a code cell:

````md
```{code-cell} ipython3
a = "This is some"
b = "Python code!"
print(f"{a} {b}")
```
````

The argument after `{code-cell}` (above, `ipython3`) is optional, and is used for
readability purposes. The content inside `{code-cell}` makes up the content of the cell,
and will be executed at build time.

This will result in the following output after building your site:

```{code-cell} ipython3
a = "This is some"
b = "Python code!"
print(f"{a} {b}")
```

**Code from Files:**

`myst_nb` provides a convenience feature for importing executable code into a `{code-cell}`
from a file. This can be useful when you want to share code between documents. To do this
you specify a `load` metadata attribute such as:

````md
```{code-cell} ipython3
:load: <path>
```
````

```{warning}
This is an experimental feature that is **not** part of the core `MyST` markup specification, and may be removed in the future. Using `:load:` will also overwrite any code written into the directive.
```

### Syntax for markdown

Anything in-between code cells will be treated as markdown. You can use any markdown
that is valid MyST Markdown. If you are using MyST Notebooks with the `myst_nb` Sphinx
extension, you can write Sphinx directives and roles. However, note that most Jupyter
Notebook environments may not be able to render MyST Markdown syntax.

**To denote a break between two markdown cells**, use the following syntax:

```
Some markdown
+++ {"optionalkey": "val"}
More markdown
```

This will result in two markdown cells in the resulting notebook. The key:val pairs
specified in the `{}` brackets will be cell-level metadata in the second markdown cell.

### Notebook-level metadata

You can begin the MyST Notebook file with front-matter metadata. These will be used
as **notebook-level metadata** for the resulting Jupyter Notebook. This metadata takes
the following form:

```md
---
key1: val1
key2: val2
---
# Notebook title
...
```

### Cell-level metadata

You can begin `code-cell` blocks with front-matter metadata. These will be used
as **cell-level metadata** in the resulting notebook cell.
The same metadata tags can be used as you would in a normal notebook,
for example those discussed in {ref}`use/hiding/code`:

````md
```{code-cell} ipython3
---
tags: [hide-output]
---
for i in range(20):
    print("Millhouse did not test cootie positive")
```
````

Yields the following:

```{code-cell} ipython3
---
tags: [hide-output]
---
for i in range(20):
    print("Millhouse did not test cootie positive")
```

There is also an **alternative short-hand syntax** for cell-level metadata. This takes
the following form:

````md
```{code-cell}
:key: val
print("hi")
```
````

For example, the following syntax adds a `raises-exception` tag to the cell, which
means our code will execute without halting the kernel:

````md
```{code-cell} ipython3
:tags: [raises-exception]

raise ValueError("oopsie!")
```
````

```{code-cell} ipython3
:tags: [raises-exception]

raise ValueError("oopsie!")
```

(converting-ipynb)=
## Convert between `ipynb` and MyST Notebooks

MyST Notebooks can be converted back-and-forth from `ipynb` files using
[jupytext](https://jupytext.readthedocs.io), a Python library for two-way
conversion of `ipynb` files with many text-based formats.

* To convert `.ipynb` to MyST-markdown, run: `jupytext notebook.ipynb --to myst`
* To convert MyST-markdown to `.ipynb`, run: `jupytext mystfile.md --to ipynb`

For more information, see the [Jupytext Documentation](https://jupytext.readthedocs.io).

(myst-nb/sphinx)=
## MyST Notebooks in Sphinx

In order to signal MyST-NB that it should treat your markdown file as a notebook,
add the following Jupytext configuration to your notebook-level metadata (by adding it to
the YAML front-matter at the beginning of the file).

```md
---
jupytext:
  text_representation:
    format_name: myst
kernelspec:
  display_name: Python 3
  name: python3
---
```

Note that `kernelspec:` should map on to the kernel you wish to use to run your
notebook's code. It must be installed on the machine and registered with Jupyter to
be used.

Here's an example of a simple MyST Notebook written for Jupytext and the `myst_nb`
Sphinx extension:

````md
---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: '0.8'
    jupytext_version: 1.4.1+dev
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# My simple notebook

Some **intro markdown**!

```{code-cell} ipython3
:tags: [mytag]

print("A python cell")
```

## A section

And some more markdown...
````

For more information, see [the MyST-NB Sphinx extension documentation](start.md).

(myst-nb/jupyter-book)=
## MyST Notebooks in Jupyter Book

In addition to using MyST Notebooks with Sphinx, you may also use them with the
Jupyter Book project. See {doc}`jb:file-types/myst-notebooks`.


(myst-nb/jupyter-interfaces)=
## MyST Notebooks in Jupyter interfaces

You can use MyST Notebooks in Jupyter interfaces by using Jupytext extensions. This
allows you to open a MyST Markdown Notebook as a "regular" Jupyter Notebook in
Jupyter Lab and the Classic Notebook interface. For more information, see
[the Jupytext documentation](https://jupytext.readthedocs.io).
