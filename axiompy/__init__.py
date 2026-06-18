# @!core

"""
AxiomPy - Core Python utilities
"""

from pkgutil import extend_path

# Merge subpackages from axiompy-data / axiompy-agents when they appear on sys.path
# (multiple editable installs or split wheels under the same ``axiompy`` namespace).
__path__ = extend_path(__path__, __name__)

from axiompy.result import (
    CoreResult,
    Err,
    Ok,
    Result,
    collect_results,
    partition_results,
    try_catch,
)
from axiompy.web import (
    AdapterPattern,
    HttpResponseError,
    PaginationHelper,
    ResultConverter,
    ResultErrorHandler,
    ResultValidator,
)

__version__ = "2.0.0"

__all__ = [
    "Result",
    "Ok",
    "Err",
    "CoreResult",
    "collect_results",
    "partition_results",
    "try_catch",
    "HttpResponseError",
    "ResultValidator",
    "ResultConverter",
    "ResultErrorHandler",
    "PaginationHelper",
    "AdapterPattern",
]
