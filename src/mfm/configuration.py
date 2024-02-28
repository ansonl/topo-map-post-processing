import typing, queue

from .printing_classes import PeriodicColor, ReplacementColorAtHeight

# Only export MFMConfiguration and not any imported values
__all__ = ['MFMConfiguration']

class MFMConfiguration(typing.TypedDict):
  CONFIG_GCODE_FLAVOR: str
  CONFIG_INPUT_FILE: str
  CONFIG_OUTPUT_FILE: str
  CONFIG_TOOLCHANGE_MINIMAL_FILE: str
  CONFIG_PERIODIC_COLORS: list[PeriodicColor]
  CONFIG_REPLACEMENT_COLORS: list[ReplacementColorAtHeight]
  CONFIG_LINE_ENDING: str
  CONFIG_APP_NAME: str
  CONFIG_APP_VERSION: str
