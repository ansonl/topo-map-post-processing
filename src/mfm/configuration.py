import typing, queue

import json

from .printing_classes import PeriodicColor, ReplacementColorAtHeight

# Only export MFMConfiguration and not any imported values
#__all__ = ['MFMConfiguration']

MODEL_TO_REAL_WORLD_DEFAULT_UNITS = 'modelToRealWorldDefaultUnits'
MODEL_ONE_TO_N_VERTICAL_SCALE = 'modelOneToNVerticalScale'
MODEL_SEA_LEVEL_BASE_THICKNESS = 'modelSeaLevelBaseThickness'

REAL_WORLD_ISOLINE_ELEVATION_INTERVAL = 'realWorldIsolineElevationInterval'
REAL_WORLD_ISOLINE_ELEVATION_START = 'realWorldIsolineElevationStart'
REAL_WORLD_ISOLINE_ELEVATION_END = 'realWorldIsolineElevationEnd'
MODEL_ISOLINE_HEIGHT = 'modelIsolineHeight' #in model units (mm)
ISOLINE_COLOR_INDEX = 'isolineColorIndex'
ISOLINE_ENABLED_FEATURES = 'isolineColorFeatureTypes'

REAL_WORLD_ELEVATION_REPLACEMENT_COLOR_START = 'realWorldElevationReplacementColorStart'
REAL_WORLD_ELEVATION_REPLACEMENT_COLOR_END = 'realWorldElevationReplacementColorEnd'
REPLACEMENT_COLOR_INDEX = 'replacementColorIndex'
REPLACEMENT_ORIGINAL_COLOR_INDEX = 'replacementOriginalColorIndex'

periodicColorRequiredOptions = [
  MODEL_TO_REAL_WORLD_DEFAULT_UNITS,
  MODEL_ONE_TO_N_VERTICAL_SCALE,
  MODEL_SEA_LEVEL_BASE_THICKNESS,
  REAL_WORLD_ISOLINE_ELEVATION_INTERVAL,
  REAL_WORLD_ISOLINE_ELEVATION_START,
  REAL_WORLD_ISOLINE_ELEVATION_END,
  MODEL_ISOLINE_HEIGHT,
  ISOLINE_COLOR_INDEX,
  ISOLINE_ENABLED_FEATURES
]

replacementColorRequiredOptions = [
  MODEL_TO_REAL_WORLD_DEFAULT_UNITS,
  MODEL_ONE_TO_N_VERTICAL_SCALE,
  MODEL_SEA_LEVEL_BASE_THICKNESS,
  REAL_WORLD_ELEVATION_REPLACEMENT_COLOR_START,
  REAL_WORLD_ELEVATION_REPLACEMENT_COLOR_END,
  REPLACEMENT_COLOR_INDEX,
  REPLACEMENT_ORIGINAL_COLOR_INDEX
]

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

def readUserOptions(userOptions:dict, optionsFilename:str) -> ValueError:
  # Read in user options
  with open(optionsFilename) as f:
    try:
      data = json.load(f)
      if isinstance(data,dict):
        for item in data.items():
          userOptions[item[0]] = item[1]
      else:
        raise ValueError()
    except ValueError:
      return ValueError
  return None

'''
periodicColors = [
  PeriodicColor(colorIndex=2, startHeight=0.3, endHeight=10, height=0.5, period=1)
]
replacementColors = [
  ReplacementColorAtHeight(colorIndex=3, originalColorIndex=0, startHeight=8, endHeight=float('inf'))
]
'''
 
def createIsoline(modelToRealWorldDefaultUnits: float, modelOneToNVerticalScale: float, modelSeaLevelBaseThickness: float, realWorldIsolineElevationInterval: float, realWorldIsolineElevationStart: float, realWorldIsolineElevationEnd: float, modelIsolineHeight: float, colorIndex: int, enabledFeatures: list[str]):
  return PeriodicColor(colorIndex=colorIndex, startHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldIsolineElevationStart/modelOneToNVerticalScale, endHeight=modelToRealWorldDefaultUnits*realWorldIsolineElevationEnd/modelOneToNVerticalScale, height=modelIsolineHeight, period=modelToRealWorldDefaultUnits*realWorldIsolineElevationInterval/modelOneToNVerticalScale, enabledFeatures=enabledFeatures)

def createReplacementColor(modelToRealWorldDefaultUnits: float, modelOneToNVerticalScale: float, modelSeaLevelBaseThickness: float, realWorldElevationStart: float, realWorldElevationEnd: float, colorIndex: int, originalColorIndex: int):
  return ReplacementColorAtHeight(colorIndex=colorIndex, originalColorIndex=originalColorIndex, startHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldElevationStart/modelOneToNVerticalScale, endHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldElevationEnd/modelOneToNVerticalScale)

def parsePeriodicColors(userOptions: dict) -> list[PeriodicColor] | bool:
  periodicColors: list[PeriodicColor] = []
  if all (opt in userOptions for opt in periodicColorRequiredOptions):
    periodicColors.append(
      createIsoline(
        modelToRealWorldDefaultUnits=userOptions[MODEL_TO_REAL_WORLD_DEFAULT_UNITS],
        modelOneToNVerticalScale=userOptions[MODEL_ONE_TO_N_VERTICAL_SCALE],
        modelSeaLevelBaseThickness=userOptions[MODEL_SEA_LEVEL_BASE_THICKNESS],
        realWorldIsolineElevationInterval=userOptions[REAL_WORLD_ISOLINE_ELEVATION_INTERVAL],
        realWorldIsolineElevationStart=userOptions[REAL_WORLD_ISOLINE_ELEVATION_START],
        realWorldIsolineElevationEnd=userOptions[REAL_WORLD_ISOLINE_ELEVATION_END],
        modelIsolineHeight=userOptions[MODEL_ISOLINE_HEIGHT],
        colorIndex=userOptions[ISOLINE_COLOR_INDEX],
        enabledFeatures=userOptions[ISOLINE_ENABLED_FEATURES]
      )
    )
    print("Added isoline based on options")
  return periodicColors

def parseReplacementColors(userOptions: dict) -> list[ReplacementColorAtHeight] | bool:
  replacementColors: list[ReplacementColorAtHeight] = []
  if all (opt in userOptions for opt in replacementColorRequiredOptions):
    replacementColors.append(
      createReplacementColor(
        modelToRealWorldDefaultUnits=userOptions[MODEL_TO_REAL_WORLD_DEFAULT_UNITS],
        modelOneToNVerticalScale=userOptions[MODEL_ONE_TO_N_VERTICAL_SCALE],
        modelSeaLevelBaseThickness=userOptions[MODEL_SEA_LEVEL_BASE_THICKNESS],
        realWorldElevationStart=userOptions[REAL_WORLD_ELEVATION_REPLACEMENT_COLOR_START],
        realWorldElevationEnd=userOptions[REAL_WORLD_ELEVATION_REPLACEMENT_COLOR_END],
        colorIndex=userOptions[REPLACEMENT_COLOR_INDEX],
        originalColorIndex=userOptions[REPLACEMENT_ORIGINAL_COLOR_INDEX]
      )
    )
    print("Added replacement color based on options")
  return replacementColors


