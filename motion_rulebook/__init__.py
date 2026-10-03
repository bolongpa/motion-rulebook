"""motion-rulebook: expansion rules for panel-to-animation.

Panel pins WHAT. The rulebook constrains HOW: every rule governs an
*expansion point* -- a place where turning a panel into animation forces the
generator to invent information (motion breakdown, between-panel fill,
vocalization, off-frame content). Rules are user-editable data (YAML), the
engine is generic; Pokemon Gen-1 ships as the reference rulebook.
"""

__version__ = "0.1.0"

from .rulebook import Rule, Rulebook, EXPANSION_POINT_TYPES  # noqa: F401
from .prompt_pack import compile_prompt_pack, load_panel, PromptPack  # noqa: F401
from .type_chart import effectiveness, multiplier  # noqa: F401
