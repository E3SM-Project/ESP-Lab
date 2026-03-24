from importlib.metadata import PackageNotFoundError, version

from .data_access import get_monthly_data
from .data_access import preprocessor
from .stats import leadtime_skill_seas_resamp

try:
    __version__ = version("esp_lab")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"  # pragma: no cover

