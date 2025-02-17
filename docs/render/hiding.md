---
file_format: mystnb
kernelspec:
  name: python3
---

# Hide cell contents

You can use Jupyter Notebook **cell tags** to control some of the behavior of
the rendered notebook.[^download]
If you are using cell tags for the first time, you can read more about them in this tutorial <https://jupyterbook.org/en/stable/content/metadata.html#add-metadata-to-notebooks>

[^download]: This notebook can be downloaded as
            **{nb-download}`hiding.ipynb`** and {download}`hiding.md`

(use/hiding/code)=

## Hide code cells

You can use **cell tags** to control the content hidden with code cells at the cell level.
Add the following tags to a cell's metadata to control
what to hide in code cells:

* **`hide-input`** tag to hide the cell inputs
* **`hide-output`** to hide the cell outputs
* **`hide-cell`** to hide the entire cell

For example, we'll show cells with each below.

```{code-cell} ipython3
:tags: [remove-cell]

import matplotlib.pyplot as plt
import numpy as np
data = np.random.rand(2, 100) * 100
```

Here is a cell with a `hide-input` tag.

```{code-cell} ipython3
:tags: [hide-input]

# This cell has a hide-input tag
fig, ax = plt.subplots()
points =ax.scatter(*data, c=data[0], s=data[0])
```

Here's a cell with a `hide-output` tag:

```{code-cell} ipython3
:tags: [hide-output]

# This cell has a hide-output tag
fig, ax = plt.subplots()
points =ax.scatter(*data, c=data[0], s=data[0])
```

Here's a cell with both `hide-input` and `hide-output` tags:

```{code-cell} ipython3
:tags: [hide-input, hide-output]

# This cell has a hide-output tag
fig, ax = plt.subplots()
points =ax.scatter(*data, c=data[0], s=data[0])
```

Here's a cell with a `hide-cell` tag:

```{code-cell} ipython3
:tags: [hide-cell]

# This cell has a hide-cell tag
fig, ax = plt.subplots()
points =ax.scatter(*data, c=data[0], s=data[0])
```

Finally, a cell with both `remove-input` (see below) and `hide-output` tags:

```{code-cell} ipython3
:tags: [remove-input, hide-output]

fig, ax = plt.subplots()
points = ax.scatter(*data, c=data[0], s=data[0])
```

You can control the hide/show prompts by using the `code_prompt_show` and `code_prompt_hide` configuration options.
The optional `{type}` placeholder will be replaced with `content`, `source`, or `outputs`, depending on the hide tag.
See the {ref}`config/intro` section for more details.

````markdown

```{code-cell} ipython3
:tags: [hide-cell]
:mystnb:
:  code_prompt_show: "My show prompt for {type}"
:  code_prompt_hide: "My hide prompt for {type}"

print("hallo world")
```
````

```{code-cell} ipython3
:tags: [hide-cell]
:mystnb:
:  code_prompt_show: "My show prompt for {type}"
:  code_prompt_hide: "My hide prompt for {type}"

print("hallo world")
```

### LaTeX output

Hiding cells in LaTeX output does nothing, unless further tweaks on the LaTeX side are in place.

Cell tags are helpfully propagated to the LaTeX source (e.g. `hide-cell` tag will wrap the cell inside the `\begin{sphinxuseclass}{tag_hide-cell}…\end{sphinxuseclass}`), but those classes, by default, do nothing. Adjust LaTeX preamble (in `conf.py`, editing `latex_elements` option and its `preamble` field) by adding e.g.

```{code-cell} latex

\NewDocumentEnvironment{HIDDEN}{+b}{}{}                                  % defines a new environment HIDDEN which ignores its contents (no output)
\newenvironment{sphinxclasstag_hide-cell}{\begin{HIDDEN}}{\end{HIDDEN}}  % this will be used by \begin{sphinxuseclass}{tag_hide-cell}…\end{sphinxuseclass}
```

to completely hide all cells with the `hide-cell` tag.


(use/hiding/markdown)=

## Hide markdown cells

You cannot hide an entire markdown cell, but you can hide sections of markdown **content** by using roles and directives.

For information on how to hide / toggle markdown content in Sphinx, see either [the `sphinx-togglebutton` documentation](https://sphinx-togglebutton.readthedocs.io/en/latest/) or the [`sphinx-design` dropdowns documentation](https://sphinx-design.readthedocs.io/en/latest/dropdowns.html).

(use/removing)=

## Remove parts of cells

Sometimes, you want to entirely remove parts of a cell so that it doesn't make it into the output at all.

To do this at the global level, use the `nb_remove_code_source` or `nb_remove_code_outputs` configuration options, or at a per-file level, e.g.

```yaml
---
mystnb:
  remove_code_source: true
  remove_code_outputs: true
---
```

See the [configuration section](config/intro) for more details.

At a per-cell level you can use the same tag pattern described above,
but with the word `remove_` instead of `hide_`. Use the following tags:

* **`remove-input`** tag to remove the cell inputs
* **`remove-output`** to remove the cell outputs
* **`remove-cell`** to remove the entire cell

+++

Here is a cell with a `remove-input` tag. The inputs will not make it into
the page at all.

```{code-cell} ipython3
:tags: [remove-input]

fig, ax = plt.subplots()
points =ax.scatter(*data, c=data[0], s=data[0])
```

Here's a cell with a `remove-output` tag:

```{code-cell} ipython3
:tags: [remove-output]

fig, ax = plt.subplots()
points = ax.scatter(*data, c=data[0], s=data[0])
```

And the following cell has a `remove-cell` tag (there should be nothing
below, since the cell will be gone).

```{code-cell} ipython3
:tags: [remove-cell]

fig, ax = plt.subplots()
points = ax.scatter(*data, c=data[0], s=data[0])
```
