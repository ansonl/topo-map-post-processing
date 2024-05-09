# Settings keys
CONFIG_GCODE_FLAVOR = 'SETTING_GCODE_FLAVOR'
CONFIG_INPUT_FILE = 'CONFIG_INPUT_FILE'
CONFIG_OUTPUT_FILE = 'CONFIG_OUTPUT_FILE'
CONFIG_TOOLCHANGE_MINIMAL_FILE = 'CONFIG_TOOLCHANGE_MINIMAL_FILE'
CONFIG_PERIODIC_COLORS = 'CONFIG_PERIODIC_COLORS'
CONFIG_REPLACEMENT_COLORS = 'CONFIG_REPLACEMENT_COLORS'
CONFIG_LINE_ENDING = 'CONFIG_LINE_ENDING'
CONFIG_APP_NAME = 'CONFIG_APP_NAME'
CONFIG_APP_VERSION = 'CONFIG_APP_VERSION'

# Gcode flavors
MARLIN_2_BAMBU_PRUSA_MARKED_GCODE = 'marlin2_bambu_prusa_markedtoolchangegcode'

# Universal MFM Gcode Tags
UNIVERSAL_TOOLCHANGE_START = '^; MFM TOOLCHANGE START'
UNIVERSAL_TOOLCHANGE_END = '^; MFM TOOLCHANGE END'
UNIVERSAL_LAYER_CHANGE_END = '^; MFM LAYER CHANGE END'

# Gcode Regex and Constants

# Movement
MOVEMENT_G0 = 'G0'
MOVEMENT_G = '^(?:G(?:0|1|2|3) )\s?(?:([XYZIJPREF])(-?\d*\.?\d*))?(?:\s+([XYZIJPREF])(-?\d*\.?\d*))?(?:\s+([XYZIJPREF])(-?\d*\.?\d*))?(?:\s+([XYZIJPREF])(-?\d*\.?\d*))?(?:\s+([XYZIJPREF])(-?\d*\.?\d*))?(?:\s+([XYZIJPREF])(-?\d*\.?\d*))?(?:\s+([XYZIJPREF])(-?\d*\.?\d*))?'

# Acceration M204
ACCELERATION_M204 = 'M204'
ACCELERATION_M = '^(?:M(?:204) )\s?(?:([PRTS])(-?\d*\.?\d*))?(?:\s+([PRTS])(-?\d*\.?\d*))?(?:\s+([PRTS])(-?\d*\.?\d*))?(?:\s+([PRTS])(-?\d*\.?\d*))?(?:\s+([PRTS])(-?\d*\.?\d*))?(?:\s+([PRTS])(-?\d*\.?\d*))?(?:\s+([PRTS])(-?\d*\.?\d*))?'

# Layer Change
LAYER_CHANGE = '^;\s?(?:CHANGE_LAYER|LAYER_CHANGE)'
LAYER_Z_HEIGHT = '^;\s?(?:Z_HEIGHT|Z):\s?(\d*\.?\d*)' # Current object layer height including current layer height
LAYER_HEIGHT = '^;\s?(?:LAYER_HEIGHT|HEIGHT):\s?(\d*\.?\d*)' # Current layer height

# Prime inserts
FULL_TOOLCHANGE_PRIME = 'G1 E.8 F1800'
MINIMAL_TOOLCHANGE_PRIME = 'G1 E2 F1800'
#FEATURE_START_DEFAULT_PRIME = 'G1 E.2 F1500'

# Filament End gcode tag - if layer starts with UNIVERSAL_TOOLCHANGE_START instead of m204 or feature. Filament end gcode appears right before UNIVERSAL_TOOLCHANGE_START LINE_WIDTH tag usually appears after FEATURE but appears appear layer_change if continuing feature.
FILAMENT_END_GCODE = '^;\s?filament end gcode'
# M204 S
M204 = '^M204\sS(?:\d*)'
# LINE_WIDTH tag
LINE_WIDTH = '^;\s?(?:LINE_WIDTH|WIDTH):'

# Feature/Line Type
FEATURE_TYPE = '^;\s?(?:FEATURE|TYPE):\s?(.*)'
PRIME_TOWER = 'Prime tower'
WIPE_TOWER = 'Wipe tower'
# MFM placeholders
TOOLCHANGE = 'Toolchange'
UNKNOWN_CONTINUED = 'Unknown continued'

# Slicer toolchange start
TOOLCHANGE_START = '^; CP TOOLCHANGE START'

# Toolchange
M620 = '^M620 S(\d*)A'
TOOLCHANGE_T = '^\s*T(?!255$|1000|1100$)(\d*)' # Do not match T255,T1000,T1100 which are nonstandard by Bambu
M621 = '^M621 S(\d*)A'

# Feature Wipe sections
WIPE_START = '^;\s?WIPE_START'
WIPE_END = '^;\s?WIPE_END'
RETAIN_WIPE_END_FEATURE_TYPES = ['Internal infill']

# Start and stop individual object
#STOP_OBJECT = '^;\s(?:stop printing object)\s?(?:, unique label|.*)\sid:?\s?(\d*)'
#START_OBJECT = '^;\s(?:start printing object|printing)\s?(?:, unique label|.*)\sid:?\s?(\d*)'

CHANGE_LAYER_CURA = '^;LAYER:\d*'
FEATURE_CURA = '^;TYPE:(.*)'