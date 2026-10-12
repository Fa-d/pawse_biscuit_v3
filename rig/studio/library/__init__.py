"""The sticker library: every motion, prop, effect, worn item, face and mascot the studio can use.

Importing this package registers everything in studio.registry.REG.  Modules are imported in a fixed order so
the registry (and so the editor's chips) always lists items in the same order.
"""
from . import looks  # noqa: F401  faces, mascots, stances, tails, arm poses
from . import motions_core  # noqa: F401
from . import motions_gesture  # noqa: F401
from . import motions_body  # noqa: F401
from . import motions_act  # noqa: F401
from . import props_core  # noqa: F401
from . import props_food  # noqa: F401
from . import props_things  # noqa: F401
from . import effects_core  # noqa: F401
from . import effects_more  # noqa: F401
from . import wear_core  # noqa: F401
from . import wear_more  # noqa: F401
