---
file_format: mystnb
kernelspec:
  name: python3
---

(execute/intro)=
# Execute and cache

MyST-NB can automatically run and cache notebooks contained in your project using [jupyter-cache].
Notebooks can either be run each time the documentation is built, or cached locally so that re-runs occur only when code cells have changed.

Execution and caching behaviour is controlled with configuration at a global or per-file level, as outlined in the [configuration section](config/intro).
See the sections below for a description of each configuration option and their effect.

(execute/modes)=

## Notebook execution modes

To trigger the execution of notebook pages, use the global `nb_execution_mode` configuration key, or per-file `execution_mode` key:

|   Mode   |                             Description                              |
| -------- | -------------------------------------------------------------------- |
| `off`    | Do not execute the notebook                                          |
| `force`  | Always execute the notebook (before parsing)                         |
| `auto`   | Execute notebooks with any missing outputs (before parsing)          |
| `lazy`   | Execute notebooks without any existing outputs (before parsing)      |
| `cache`  | Execute notebook and store/retrieve outputs from a cache             |
| `inline` | Execute the notebook during parsing (allows for variable evaluation) |

By default this is set to:

```python
nb_execution_mode = "auto"
```

This will only execute notebooks that are missing at least one output.
If a notebook has *all* of its outputs populated, then it will not be executed.

To only execute notebooks that do not have *any* of its outputs populated, change the above configuration value to:

```python
nb_execution_mode = "lazy"
```

To force the execution of all notebooks, regardless of their outputs, change the above configuration value to:

```python
nb_execution_mode = "force"
```

To cache execution outputs with [jupyter-cache], change the above configuration value to:

```python
nb_execution_mode = "cache"
```

See {ref}`execute/cache` for more information.

To execute notebooks inline during parsing, change the above configuration value to:

```python
nb_execution_mode = "inline"
```

This allows for the use of `eval` roles/directives to embed variables, evaluated from the execution kernel, inline of the Markdown.

See {ref}`render/eval` for more information.

To turn off notebook execution, change the above configuration value to:

```python
nb_execution_mode = "off"
```

## Exclude notebooks from execution

To exclude certain file patterns from execution, use the following configuration:

```python
nb_execution_excludepatterns = ['list', 'of', '*patterns']
```

Any file that matches one of the items in `nb_execution_excludepatterns` will not be executed.

(execute/cache)=
## Cache execution outputs

As mentioned above, you can cache the results of executing a notebook page by setting:

```python
nb_execution_mode = "cache"
```

In this case, when a page is executed, its outputs will be stored in a local database.
This allows you to be sure that the outputs in your documentation are up-to-date, while saving time avoiding unnecessary re-execution.
It also allows you to store your `.ipynb` files (or their `.md` equivalent) in your `git` repository *without their outputs*, but still leverage a cache to save time when building your site.

:::{tip}
You should only use this option when notebooks have deterministic execution outputs:

- You use the same environment to run them (e.g. the same installed packages)
- They run no non-deterministic code (e.g. random numbers)
- They do not depend on external resources (e.g. files or network connections) that change over time
:::

When you re-build your site, the following will happen:

- Notebooks that have not seen changes to their **code cells** or **metadata** since the last build will not be re-executed.
  Instead, their outputs will be pulled from the cache and inserted into your site.
- Notebooks that **have any change to their code cells** will be re-executed, and the cache will be updated with the new outputs.

By default, the cache will be placed in the parent of your build folder.
Generally, this is in `_build/.jupyter_cache`, and it will also be specified in the build log, e.g.

```
Using jupyter-cache at: ./docs/_build/.jupyter_cache
```

You may also specify a path to the location of a jupyter cache you'd like to use:

```python
nb_execution_cache_path = "path/to/mycache"
```

The path should point to an **empty folder**, or a folder where a **jupyter cache already exists**.

Once you have run the documentation build, you can inspect the contents of the cache with the following command:

```console
$ jcache notebook -p docs/_build/.jupyter_cache list
```

See [jupyter-cache] for more information.

[jupyter-cache]: https://github.com/executablebooks/jupyter-cache "the Jupyter Cache Project"

## Execute with a different kernel name

If you require your notebooks to run with a different kernel, to those specified in the actual files, you can set global aliases with e.g.

```python
nb_kernel_rgx_aliases = {"oth.*": "python3"}
```

The mapping keys are [regular expressions](https://www.regular-expressions.info/) so, for example `oth.*` will match any kernel name starting with `oth`.

## Executing in temporary folders

By default, the command working directory (cwd) that a notebook runs in will be the directory it is located in.
However, you can set `nb_execution_in_temp=True` in your `conf.py`, to change this behaviour such that, for each execution, a temporary directory will be created and used as the cwd.

(execute/timeout)=
## Execution timeout

The execution of notebooks is managed by {doc}`nbclient <nbclient:client>`.

The `nb_execution_timeout` sphinx option defines the maximum time (in seconds) each notebook cell is allowed to run.
If the execution takes longer an exception will be raised.
The default is 30 s, so in cases of long-running cells you may want to specify an higher value.
The timeout option can also be set to `None` or -1 to remove any restriction on execution time.

This global value can also be overridden per notebook by adding this to you notebooks metadata:

```json
{
 "metadata": {
  "execution": {
      "timeout": 30
  }
}
```

(execute/allow_errors)=
## Raise errors in code cells

In some cases, you may want to intentionally show code that doesn't work (e.g., to show the error message).
You can achieve this at "three levels":

Globally, by setting `nb_execution_allow_errors=True` in your `conf.py`.

Per notebook (overrides global), by adding this to you notebooks metadata:

```json
{
"metadata": {
  "execution": {
      "allow_errors": true
  }
}
```

Per cell, by adding a `raises-exception` tag to your code cell.
This can be done via a Jupyter interface, or via the `{code-cell}` directive like so:

````md
```{code-cell}
:tags: [raises-exception]

print(thisvariabledoesntexist)
```
````

Which produces:

```{code-cell}
---
tags: [raises-exception]
---
print(thisvariabledoesntexist)
```

(execute/raise_on_error)=
## Error reporting: Warning vs. Failure

When an error occurs in a context where `nb_execution_allow_errors=False`,
the default behaviour is for this to be reported as a warning.
This warning will simply be logged and not cause the build to fail unless `sphinx-build` is run with the [`-W` option](https://www.sphinx-doc.org/en/master/man/sphinx-build.html#cmdoption-sphinx-build-W).
If you would like unexpected execution errors to cause a build failure rather than a warning regardless of the `-W` option, you can achieve this by setting `nb_execution_raise_on_error=True` in your `conf.py`.

(execute/statistics)=
## Execution statistics

As notebooks are executed, certain statistics are stored in a dictionary, and saved on the [sphinx environment object](https://www.sphinx-doc.org/en/master/extdev/envapi.html#sphinx.environment.BuildEnvironment) in `env.metadata[docname]`.

You can access this in a post-transform in your own sphinx extensions, or use the built-in `nb-exec-table` directive:

````md
```{nb-exec-table}
```
````

which produces:

```{nb-exec-table}
```
