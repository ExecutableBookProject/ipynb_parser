---
jupytext:
  cell_metadata_filter: -all
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: '0.8'
    jupytext_version: 1.4.2
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Executing and caching your content

MyST-NB can automatically run and cache notebooks contained in your project using [jupyter-cache].
Notebooks can either be run each time the documentation is built, or cached locally so that re-runs occur only when code cells have changed.

Caching behaviour is controlled with configuration in your `conf.py` file.
See the sections below for each configuration option and its effect.

(execute/config)=

## Triggering notebook execution

To trigger the execution of notebook pages, use the following configuration in `conf.py`:

```python
jupyter_execute_notebooks = "auto"
```

By default, this will only execute notebooks that are missing at least one output.
If a notebook has *all* of its outputs populated, then it will not be executed.

**To force the execution of all notebooks, regardless of their outputs**, change the above configuration value to:

```python
jupyter_execute_notebooks = "force"
```

**To cache execution outputs with [jupyter-cache]**, change the above configuration value to:

```python
jupyter_execute_notebooks = "cache"
```

See {ref}`execute/cache` for more information.

**To turn off notebook execution**, change the above configuration value to:

```python
jupyter_execute_notebooks = "off"
```

**To exclude certain file patterns from execution**, use the following configuration:

```python
execution_excludepatterns = ['list', 'of', '*patterns']
```

Any file that matches one of the items in `execution_excludepatterns` will not be executed.

(execute/cache)=
## Caching the notebook execution

As mentioned above, you can **cache the results of executing a notebook page** by setting:

```python
jupyter_execute_notebooks = "cache"
```

in your conf.py file.

In this case, when a page is executed, its outputs will be stored in a local database.
This allows you to be sure that the outputs in your documentation are up-to-date, while saving time avoiding unnecessary re-execution.
It also allows you to store your `.ipynb` files (or their `.md` equivalent) in your `git` repository *without their outputs*, but still leverage a cache to save time when building your site.

When you re-build your site, the following will happen:

* Notebooks that have not seen changes to their **code cells** or **metadata** since the last build will not be re-executed.
  Instead, their outputs will be pulled from the cache and inserted into your site.
* Notebooks that **have any change to their code cells** will be re-executed, and the cache will be updated with the new outputs.

By default, the cache will be placed in the parent of your build folder.
Generally, this is in `_build/.jupyter_cache`.

You may also specify a path to the location of a jupyter cache you'd like to use:

```python
jupyter_cache = "path/to/mycache"
```

The path should point to an **empty folder**, or a folder where a **jupyter cache already exists**.

[jupyter-cache]: https://github.com/executablebooks/jupyter-cache "the Jupyter Cache Project"

## Executing in temporary folders

By default, the command working directory (cwd) that a notebook runs in will be the directory it is located in.
However, you can set `execution_in_temp=True` in your `conf.py`, to change this behaviour such that, for each execution, a temporary directory will be created and used as the cwd.

(execute/timeout)=
## Execution Timeout

The execution of notebooks is managed by {doc}`nbclient <nbclient:client>`.

The `execution_timeout` sphinx option defines the maximum time (in seconds) each notebook cell is allowed to run.
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
## Dealing with code that raises errors

In some cases, you may want to intentionally show code that doesn't work (e.g., to show the error message).
You can achieve this at "three levels":

Globally, by setting `execution_allow_errors=True` in your `conf.py`.

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

(execute/fail_on_error)=
### Error Reporting: Warning vs. Failure
When an error occurs in a context where `allow_errors=False`, the default behaviour is for this to be reported as a warning. This warning will simply be logged and not cause the build to fail unless `sphinx-build` is run with the [`-W` option](https://www.sphinx-doc.org/en/master/man/sphinx-build.html#cmdoption-sphinx-build-W).

If you would like unexpected execution errors to cause a build failure rather than a warning regardless of the `-W` option, you can achieve this by setting `execution_fail_on_error=True` in your `conf.py`.

(execute/statistics)=
## Execution statistics

As notebooks are executed, certain statistics are stored in a dictionary (`{docname:data}`), and saved on the [sphinx environment object](https://www.sphinx-doc.org/en/master/extdev/envapi.html#sphinx.environment.BuildEnvironment) as `env.nb_execution_data`.

You can access this in a post-transform in your own sphinx extensions, or use the built-in `nb-exec-table` directive:

````md
```{nb-exec-table}
```
````

which produces:

```{nb-exec-table}
```
