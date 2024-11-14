import enum

class StatusQueueItem:
  "Status Queue Item properties to send to the user."
  def __init__(self):
    self.statusLeft = None
    self.statusRight = None
    self.progress = None

# Position
class Position:
  """Position, Feedrate, and Acceleration values for printing"""
  def __init__(self):
    # Position
    self.X: float
    self.Y: float
    self.Z: float
    self.E: float

    # Feedrate
    self.F: float
    self.FTravel: float

    # Acceleration
    self.P: float
    """Printing acceleration"""
    self.R: float
    """Retract acceleration"""
    self.T: float
    """Travel acceleration for moves with no extrusion."""

class ToolchangeType(enum.Enum):
  NONE = enum.auto()
  """No toolchange"""
  MINIMAL = enum.auto()
  """Minimal toolchange is a generic toolchange procedure."""
  FULL = enum.auto()
  """Full toolchange is derived from an existing toolchange in the original G-code."""

# Reason for skip when looping that is set when first starting a feature
class SkipType(enum.Enum):
  PRIME_TOWER_FEATURE = enum.auto()
  """Prime Tower or Wipe Tower"""
  FEATURE_ORIG_TOOLCHANGE_AND_WIPE_END = enum.auto()
  """The original toolchange and Wipe End within a feature."""

# State of current Print FILE
class PrintState:
  """The current state of the processed G-code file."""

  def __init__(self):
    """Constructor method
    """
    super().__init__()

    self.height: float = -1 
    """The current printing height relative to the buildplate."""
    self.layerHeight: float = 0
    """The layer height of an individual layer relative to the top of the last layer. E.g. 0.12, 0.2"""
    self.previousLayerHeight: float = 0
    """The previous layer's layer height."""
    self.layerStart: int = 0
    """The character position of the layer start."""
    self.layerEnd: int = 0
    """The character position of the layer end."""
    self.lastFeature: Feature = None
    """Reference to last original feature of the previous layer. Used in case it originally continues to next layer."""
    self.prevLayerLastFeature: Feature = None
    """Reference to last original feature of the layer before the previous layer."""

    # Color info
    self.originalColor: int = -1
    """last color changed to in original print at the start of the layer"""
    self.layerEndOriginalColor: int = -1
    """last color changed to in the original print at the end of the current layer"""
    self.printingColor: int = -1
    """current modified color"""
    self.printingPeriodicColor: bool = False
    """last layer was PeriodicColor?"""
    self.isPeriodicLine: bool = False
    """is this layer supposed to have periodic lines?"""

    # Movement info
    self.originalPosition: Position = Position() # Restore original XYZ position after inserting a TC. Then do E2 for minimal TC. Full Prime tower TC already does E.8
    """The position of the extruder in the original print file."""

    # Prime tower / Toolchange values for current layer
    self.features: list[Feature] = []
    """Printing features found on the current layer"""
    self.primeTowerFeatures: list[Feature] = [] # The available prime tower features.
    """Prime Tower features found on the current layer"""
    self.stopPositions: list[int] = []
    """Stop Positions for process() loop to stop and process next printing feature"""
    self.toolchangeInsertionPoint: int = 0
    """The next toolchange insertion point"""
    self.featureWipeEndPrime: Position = None
    """prime values at end of wipe_end"""

    #Loop settings
    self.skipWrite: bool = False
    """Skip writing at the end of process loop."""
    self.skipWriteForCurrentLine: bool = False
    """Skip writing the current line at the end of process loop. Reset at the end of the loop."""
    
    #self.toolchangeBareInsertionPoint: Feature = None
    #self.toolchangeFullInsertionPoint: Feature = None
    #self.toolchangeNewColorIndex: int = -1
    #self.skipOriginalPrimeTowerAndToolchangeOnLayer: bool = False
    #self.skipOriginalToolchangeOnLayer: bool = False

class Feature:
  """Printing Feature properties"""

  def __init__(self):
    """Constructor"""
    super().__init__()
    self.featureType: str = None
    self.start: int = 0
    self.end: int = 0
    self.toolchange: Feature = None
    self.isPeriodicColor: bool = False
    self.originalColor: int = -1
    self.printingColor: int = -1
    self.startPosition: Position = Position()
    self.wipeStart: Feature = None
    self.wipeEnd: Feature = None
    self.skipType: SkipType = None

class PeriodicColor:
  """A repeating Periodic Color (isoline) properties"""
  def __init__(self, colorIndex = -1, startHeight = -1, endHeight = -1, height = -1, period = -1, enabledFeatures=[]):
    self.colorIndex: int = colorIndex
    self.startHeight: float = startHeight
    self.endHeight: float = endHeight
    self.height: float = height
    self.period: float = period
    self.enabledFeatures: list[str] = enabledFeatures

class PrintColor:
  """Tracks an individual tool and the replacement tool (color) index."""
  def __init__(self, index=-1, replacementColorIndex=-1, humanColor=None):
    self.index: int = index
    self.replacementColorIndex: int = replacementColorIndex #the current replacement color
    self.humanColor: str = humanColor

loadedColors: list[PrintColor] = [
  PrintColor(0, -1, 'Base Color'),
  PrintColor(1, -1, 'River Color'),
  PrintColor(2, -1, 'Isoline Color'),
  PrintColor(3, -1, 'High Elevation Color')
]
"""All loaded tools (colors)"""

class ReplacementColorAtHeight:
  """A replacement color at height properties"""
  def __init__(self, colorIndex, originalColorIndex, startHeight, endHeight):
    self.colorIndex: int = colorIndex
    self.originalColorIndex: int = originalColorIndex
    self.startHeight: float = startHeight
    self.endHeight: float = endHeight