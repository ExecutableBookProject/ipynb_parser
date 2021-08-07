import IPython
from IPython.display import display as ipy_display

GLUE_PREFIX = "application/papermill.record/"


def glue(name, variable, display=True):
    """Glue a variable into the notebook's cell metadata.

    Parameters
    ----------
    name: string
        A unique name for the variable. You can use this name to refer to the variable
        later on.
    variable: Python object
        A variable in Python for which you'd like to store its display value. This is
        not quite the same as storing the object itself - the stored information is
        what is *displayed* when you print or show the object in a Jupyter Notebook.
    display: bool
        Display the object you are gluing. This is helpful in sanity-checking the
        state of the object at glue-time.
    """
    mimebundle, metadata = IPython.core.formatters.format_display_data(variable)
    mime_prefix = "" if display else GLUE_PREFIX
    metadata["scrapbook"] = dict(name=name, mime_prefix=mime_prefix)
    ipy_display(
        {mime_prefix + k: v for k, v in mimebundle.items()}, raw=True, metadata=metadata
    )
