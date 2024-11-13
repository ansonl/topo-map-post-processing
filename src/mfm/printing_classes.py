import enum

class StatusQueueItem:
  def __init__(self):
    self.statusLeft = None
    self.statusRight = None
    self.progress = None

# Position
class Position:
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
    self.P: float # Printing acceleration
    self.R: float # Retract acceleration
    self.T: float # Travel acceleration for moves with no extrusion.

class ToolchangeType(enum.Enum):
  NONE = enum.auto()
  MINIMAL = enum.auto()
  FULL = enum.auto()

# Reason for skip when looping that is set when first starting a feature
class SkipType(enum.Enum):
  PRIME_TOWER_FEATURE = enum.auto()
  FEATURE_ORIG_TOOLCHANGE_AND_WIPE_END = enum.auto()

# State of current Print FILE
class PrintState:
  """The current state of the processed G-code file."""

  def __init__(self):
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
    self.originalColor: int = -1 # last color changed to in original print at the start of the layer
    self.layerEndOriginalColor: int = -1 #last color changed to in the original print at the end of the current layer
    self.printingColor: int = -1 # current modified color
    self.printingPeriodicColor: bool = False # last layer wasPeriodicColor?
    self.isPeriodicLine: bool = False # is this layer supposed to have periodic lines?

    # Movement info
    self.originalPosition: Position = Position() # Restore original XYZ position after inserting a TC. Then do E2 for minimal TC. Full Prime tower TC already does E.8

    # Prime tower / Toolchange values for current layer
    self.features: list[Feature] = [] # Printing features
    self.primeTowerFeatures: list[Feature] = [] # The available prime tower features.
    self.stopPositions: list[int] = []
    self.toolchangeInsertionPoint: int = 0
    self.featureWipeEndPrime: Position = None # prime values at end of wipe_end

    #Loop settings
    self.skipWrite: bool = False
    self.skipWriteForCurrentLine: bool = False
    self.prevLayerSkipWrite: bool = False
    
    #self.toolchangeBareInsertionPoint: Feature = None
    #self.toolchangeFullInsertionPoint: Feature = None
    #self.toolchangeNewColorIndex: int = -1
    #self.skipOriginalPrimeTowerAndToolchangeOnLayer: bool = False
    #self.skipOriginalToolchangeOnLayer: bool = False

class Feature:
  def __init__(self):
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
    #self.used: bool = False #flag to show prime tower has been used already

class PeriodicColor:
  def __init__(self, colorIndex = -1, startHeight = -1, endHeight = -1, height = -1, period = -1, enabledFeatures=[]):
    self.colorIndex: int = colorIndex
    self.startHeight: float = startHeight
    self.endHeight: float = endHeight
    self.height: float = height
    self.period: float = period
    self.enabledFeatures: list[str] = enabledFeatures

class PrintColor:
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
class ReplacementColorAtHeight:
  def __init__(self, colorIndex, originalColorIndex, startHeight, endHeight):
    self.colorIndex: int = colorIndex
    self.originalColorIndex: int = originalColorIndex
    self.startHeight: float = startHeight
    self.endHeight: float = endHeight