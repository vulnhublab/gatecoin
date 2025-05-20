import os
import sys
from typing import Any, Dict

import gatecoin
from gatecoin import constants


def get_project_root() -> str:
    return os.path.dirname(gatecoin.__file__)


def get_system_spec() -> Dict[str, Any]:
    """Collect information about the system and installation."""
    import platform

    import pkg_resources

    if sys.platform == "darwin":
        system_info = "macOS {} {}".format(platform.mac_ver()[0], platform.architecture()[0])
    else:
        system_info = "{} {} {}".format(
            platform.system(),
            "_".join(part for part in platform.architecture() if part),
            platform.release(),
        )

    try:
        version = pkg_resources.require(gatecoin.__name__)[0].version
    except (pkg_resources.VersionConflict, pkg_resources.DistributionNotFound):
        raise RuntimeError(
            "Cannot detect Gatecoin version. Did you do python setup.py?  "
            "Refer to https://gatecoin.readthedocs.io/en/latest/"
            "overview_and_guide.html#for-developers"
        )

    system_spec = {
        "gatecoin": version,
        "gatecoin_db_version": constants.GATECOIN_DB_VERSION,
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "system": system_info,
        "architecture": platform.machine(),
        "distribution": "bundled" if getattr(sys, "frozen", False) else "source",
    }
    return system_spec
