import re, os, typing

# Constants
STOP_OBJECT = '^; stop printing object, unique label id:\s(\d*)'
FEATURE = '^; FEATURE:\s(.*)'
PRIME_TOWER = 'Prime tower'
TOOLCHANGE_START = '^; CP TOOLCHANGE START'
M620 = '^M620 S(\d*)A'
# Toolchange movement actually starts after spiral lift up. Spiral lift is useful if doing prime tower only.
WIPE_SPIRAL_LIFT = '^G2 Z\d*\.?\d* I\d*\.?\d* J\d*\.?\d* P\d*\.?\d* F\d*\.?\d* ; spiral lift a little from second lift'
TOOLCHANGE_T = '^T(?!255$|1000$)(\d*)' # Do not match T255 or T1000 which are nonstandard by Bambu
# Prime tower printing actually starts after M621
M621 = '^M621 S(\d*)A'
START_OBJECT = '^; start printing object, unique label id:\s(\d*)'

CHANGE_LAYER = '^; CHANGE_LAYER'
Z_HEIGHT = '^; Z_HEIGHT:\s(\d*\.?\d*)' # Current object layer height including current layer height
LAYER_HEIGHT = '^; LAYER_HEIGHT:\s(\d*\.?\d*)' # Current layer height

M991 = '^M991 S0 P(\d*)' # process indicator. Indicate layer insertion point.

#inputFile = 'dicetest.gcode'
#outputFile = 'dicetestout.gcode'
toolchangeBareFile = 'toolchange-bare.gcode'

# State of current Print FILE
class PrintState:
  def __init__(self):
    self.height: float = 0 
    self.layerHeight: float = 0
    self.originalColor: int = 0 # last color changed to in original print
    self.printingColor: int = 0 # current modified color
    self.printingPeriodicColor: bool = False

    # Prime tower / Toolchange values for current layer
    self.primeTower: Feature = None
    self.toolchangeBareInsertionPoint: Feature = None
    self.toolchangeFullInsertionPoint: Feature = None
    self.toolchangeNewColorIndex: int = -1
    self.skipOriginalPrimeTowerAndToolchangeOnLayer: bool = False
    self.skipOriginalToolchangeOnLayer: bool = False

class PeriodicColor:
  def __init__(self, colorIndex = -1, startHeight = -1, endHeight = -1, height = -1, period = -1):
    self.colorIndex: int = colorIndex
    self.startHeight: float = startHeight
    self.endHeight: float = endHeight
    self.height: float = height
    self.period: float = period

elevIsoline = PeriodicColor(colorIndex=2, startHeight=0.3, endHeight=10, height=0.5, period=1)

class Feature:
  def __init__(self):
    self.featureType: str = None
    self.start: int = 0
    self.end: int = 0
    self.toolchange: Feature = None

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

replacementColors: list[ReplacementColorAtHeight] = [
  ReplacementColorAtHeight(colorIndex=3, originalColorIndex=0, startHeight=8, endHeight=float('inf'))
]

# Options keys
IMPORT_GCODE_FILENAME = 'importGcodeFilename'
IMPORT_OPTIONS_FILENAME = 'importOptionsFilename'
EXPORT_GCODE_FILENAME = 'exportGcodeFilename'

MODEL_TO_REAL_WORLD_DEFAULT_UNITS = 'modelToRealWorldDefaultUnits'
MODEL_ONE_TO_N_VERTICAL_SCALE = 'modelOneToNVerticalScale'
MODEL_SEA_LEVEL_BASE_THICKNESS = 'modelSeaLevelBaseThickness'

REAL_WORLD_ISOLINE_ELEVATION_INTERVAL = 'realWorldIsolineElevationInterval'
REAL_WORLD_ISOLINE_ELEVATION_START = 'realWorldIsolineElevationStart'
REAL_WORLD_ISOLINE_ELEVATION_END = 'realWorldIsolineElevationEnd'
MODEL_ISOLINE_HEIGHT = 'modelIsolineHeight' #in model units

REAL_WORLD_ELEVATION_START = 'realWorldElevationStart'
REAL_WORLD_ELEVATION_END = 'realWorldElevationEnd'

COLOR_INDEX = 'colorIndex'
ORIGINAL_COLOR_INDEX = 'originalColorIndex'

def createIsoline(modelToRealWorldDefaultUnits: float, modelOneToNVerticalScale: float, modelSeaLevelBaseThickness: float, realWorldIsolineElevationInterval: float, realWorldIsolineElevationStart: float, realWorldIsolineElevationEnd: float, modelIsolineHeight: float, colorIndex: int):
  return PeriodicColor(colorIndex=colorIndex, startHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldIsolineElevationStart/modelOneToNVerticalScale, endHeight=modelToRealWorldDefaultUnits*realWorldIsolineElevationEnd/modelOneToNVerticalScale, height=modelIsolineHeight, period=modelToRealWorldDefaultUnits*realWorldIsolineElevationInterval/modelOneToNVerticalScale)

def createReplacementColor(modelToRealWorldDefaultUnits: float, modelOneToNVerticalScale: float, modelSeaLevelBaseThickness: float, realWorldElevationStart: float, realWorldElevationEnd: float, colorIndex: int, originalColorIndex: int):
  return ReplacementColorAtHeight(colorIndex=colorIndex, originalColorIndex=originalColorIndex, startHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldElevationStart/modelOneToNVerticalScale, endHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldElevationEnd/modelOneToNVerticalScale)

def shouldLayerBePeriodicLine(printState: PrintState, periodicLine: PeriodicColor):
  if printState.height >= periodicLine.startHeight and printState.height <= periodicLine.endHeight:
    print('height within isoline active range')
    # current layer top is inside an isoline
    if (printState.height - periodicLine.startHeight) % periodicLine.period <= periodicLine.height:
      #start isoline
      return True
    #current layer envelopes an isoline
    #is thicker than 1 isoline AND top is above isoline end and bottom is below isoline start (or above isoline end)
    elif printState.layerHeight > periodicLine.height and ((printState.height - periodicLine.startHeight) - printState.layerHeight) % periodicLine.period > periodicLine.height:
      #start isoline
      return True
  return False

def updateReplacementColors(printState: PrintState):
  for rc in replacementColors:
    if printState.height > rc.startHeight and printState.height - printState.layerHeight < rc.endHeight:
      loadedColors[rc.originalColorIndex].replacementColorIndex = rc.colorIndex
    elif loadedColors[rc.originalColorIndex].replacementColorIndex == rc.colorIndex:
      loadedColors[rc.originalColorIndex].replacementColorIndex = -1

def findChangeLayer(f, lastPrintState: PrintState):
  cl = f.readline()
  # Look for start of layer
  changeLayerMatch = re.match(CHANGE_LAYER, cl)
  if changeLayerMatch:
    # Create new print state for the new found layer and carry over some state that should be preserved between layers.
    printState = PrintState()
    printState.originalColor = lastPrintState.originalColor
    printState.printingColor = lastPrintState.printingColor
    printState.printingPeriodicColor = lastPrintState.printingPeriodicColor

    # Find Z_HEIGHT value
    cl = f.readline()
    cl = re.match(Z_HEIGHT, cl)
    if cl:
      printState.height = float(cl.groups()[0])
      #print(f"{Z_HEIGHT} {cl.groups()[0]}")
      print(f"\nProcessing height {printState.height}")

    # Find LAYER_HEIGHT value
    cl = f.readline()
    cl = re.match(LAYER_HEIGHT, cl)
    if cl:
      printState.layerHeight = float(cl.groups()[0])

    #update loaded colors replacement color data based on current height
    updateReplacementColors(printState)

    cp = f.tell()  
    printState.primeTower = findLayerFeaturePrimeTower(f)
    f.seek(cp, os.SEEK_SET)
    insertionPoint = findToolchangeInsertionPoint(f)
    f.seek(cp, os.SEEK_SET)

    if insertionPoint == None:
      print(f"Failed to find toolchange insertion point at layer Z_HEIGHT {printState.height}")

    isPeriodicLine = shouldLayerBePeriodicLine(printState, elevIsoline)
    print("is periodic line")

    # Check if we need to switch to/from periodic color
    if printState.printingPeriodicColor == True and isPeriodicLine == True:
      # already periodic color, stay on periodic color
      # skip toolchange part on this layer. Do prime tower as usual.
      printState.skipOriginalToolchangeOnLayer = True

    elif printState.printingPeriodicColor ^ isPeriodicLine:
      # Previously no periodic color, new toolchange to periodic color
      if printState.printingPeriodicColor == False:
        # new inserted toolchange is isoline color
        printState.toolchangeNewColorIndex = elevIsoline.colorIndex
        # check for existing toolchange on this layer
        #print(printState.primeTower)     
        if printState.primeTower and printState.primeTower.start:
          # if toolchange exist, switch toolhead, do prime block. Do toolchange after STOPOBJ and M991. Relocate prime block. Skip found toolchange/primeblock on this layer.
          if printState.primeTower.toolchange:
            printState.toolchangeFullInsertionPoint = insertionPoint
            printState.skipOriginalPrimeTowerAndToolchangeOnLayer = True
          # if no toolchange exist on this layer and there is prime block, switch toolhead, do the prime block now and delete from later. Do toolchange after STOPOBJ and M991 (before START). Assume the prime block printing already happens after M991 so it is already in the correct place after inserting toolchange.
          else: 
            printState.toolchangeBareInsertionPoint = insertionPoint
        else:
          # if no prime block (and no toolchange), switch toolhead, no prime block. Do toolchange after M991. If toolchange did exist but no prime block, same thing.
          printState.toolchangeBareInsertionPoint = insertionPoint

      # Previously printing periodic color, new toolchange to original color
      else:
        # new inserted toolchange is original color
        printState.toolchangeNewColorIndex = printState.originalColor
        # check for toolchange on this layer
        if printState.primeTower and printState.primeTower.start:
          # if toolchange exist, switch toolhead, no prime block. Do toolchange after STOPOBJ and M991
          # OR
          # if no toolchange exist on this layer and there is prime block, switch toolhead, do the prime block now and delete from later. Do toolchange after STOPOBJ and M991 (before START). Assume the prime block printing already happens after M991 so it is already in the correct place after inserting toolchange.
          printState.toolchangeBareInsertionPoint = insertionPoint
        else:
        # if no prime block (and no toolchange), switch toolhead, no prime block. Do toolchange after M991. If toolchange did exist but no prime block, same thing.
          printState.toolchangeBareInsertionPoint = insertionPoint
    return printState
  return None

def findLayerFeaturePrimeTower(f: typing.TextIO):
  primeTower = Feature()
  cl = True
  while cl:
    cl = f.readline()
    changeLayerMatch = re.match(CHANGE_LAYER, cl)
    stopObjMatch = re.match(STOP_OBJECT, cl)
    featureMatch = re.match(FEATURE, cl)
    toolchangeStartMatch = re.match(TOOLCHANGE_START, cl)
    wipeSpiralLiftMatch = re.match(WIPE_SPIRAL_LIFT, cl)
    m692Match = re.match(M621, cl)
    startObjMatch = re.match(START_OBJECT, cl)

    if changeLayerMatch:
      print('got new layer at ',f.tell(),'before prime tower')
      return None

    if stopObjMatch:
      primeTower.start = f.tell()
      primeTower.featureType = None
    elif primeTower.start == 0:
      continue
    elif primeTower.featureType == None: # Look for FEATURE tag
      if featureMatch:
        if featureMatch.groups()[0] == PRIME_TOWER:
          primeTower.featureType = featureMatch.groups()[0]
        else:
          primeTower.start = 0
      else:
        continue
    # Look for start object and toolchange
    elif toolchangeStartMatch: 
      primeTower.toolchange = Feature()
      primeTower.toolchange.featureType = 'Toolchange'
    elif wipeSpiralLiftMatch:
      primeTower.toolchange.start = f.tell()
    elif m692Match:
      primeTower.toolchange.end = f.tell()
    elif startObjMatch:
        primeTower.end = f.tell() - len(cl)
        break
  return primeTower
  
def findToolchangeInsertionPoint(f: typing.TextIO):
  insertionPoint = Feature()
  insertionPoint.featureType = M991
  cl = True
  while cl:
    cl = f.readline()
    m991Match = re.match(M991, cl)
    changeLayerMatch = re.match(CHANGE_LAYER, cl)
    featureMatch = re.match(FEATURE, cl)
    if m991Match:
      insertionPoint.start = f.tell()
      break
    elif changeLayerMatch:
      return None
    elif featureMatch:
      return None
  return insertionPoint

def substituteNewColor(cl, newColorIndex: int):
  cl = re.sub(M620, f"M620 S{newColorIndex}A", cl)
  cl = re.sub(TOOLCHANGE_T, f"T{newColorIndex}", cl)
  cl = re.sub(M621, f"M621 S{newColorIndex}A", cl)
  return cl

# return the current printing color index that should be used for a given color index. Returns the replacement color index for a color index if there is a replacement assigned.
def currentPrintingColorIndexForColorIndex(colorIndex: int, lc: list[PrintColor]):
  print(colorIndex)
  if lc[colorIndex].replacementColorIndex != -1:
    return lc[colorIndex].replacementColorIndex
  else:
    return colorIndex

def writeWithColorFilter(out: typing.TextIO, cl: str, lc: list[PrintColor]):
  cmdColorIndex = -1

  #look for color specific matches to find the original color to check for replacement colors
  m620Match = re.match(M620, cl)
  toolchangeMatch = re.match(TOOLCHANGE_T, cl)
  m621Match = re.match(M621, cl)

  if m620Match:
    cmdColorIndex = int(m620Match.groups()[0])
  elif toolchangeMatch:
    cmdColorIndex = int(toolchangeMatch.groups()[0])
  elif m621Match:
    cmdColorIndex = int(m621Match.groups()[0])

  if cmdColorIndex != -1:
    cl = substituteNewColor(cl, currentPrintingColorIndexForColorIndex(cmdColorIndex,lc))
  
  out.write(cl)

def process(inputFile, outputFile):
  with open(inputFile, mode='r') as f, open(outputFile, mode='w') as out:
    currentPrint: PrintState = PrintState()

    # Don't write to output
    skipWrite = False

    # Current line buffer
    cl = True
    while cl:
      # Look for start of a layer CHANGE_LAYER
      cp = f.tell()
      foundNewLayer = findChangeLayer(f,currentPrint)
      if foundNewLayer:
        currentPrint = foundNewLayer
      f.seek(cp, os.SEEK_SET)

      cl = f.readline()
      #print(".",end='')

      # look for toolchange T
      toolchangeMatch = re.match(TOOLCHANGE_T, cl)
      if toolchangeMatch:
        currentPrint.originalColor = int(toolchangeMatch.groups()[0])
        if skipWrite == False:
          currentPrint.printingColor = currentPrint.originalColor
      
      # Indicate current layer should skip the original prime tower and toolchange found
      if currentPrint.skipOriginalPrimeTowerAndToolchangeOnLayer and currentPrint.primeTower:
        if f.tell() == currentPrint.primeTower.start:
          skipWrite = True
          out.write("; Original Prime Tower and Toolchange skipped\n")
        if f.tell() == currentPrint.primeTower.end:
          skipWrite = False
      
      # Indicate current layer should skip the original toolchange found AND this layer's prime tower has a tool change section to skip
      if currentPrint.skipOriginalToolchangeOnLayer and currentPrint.primeTower and currentPrint.primeTower.toolchange:
        if f.tell() == currentPrint.primeTower.toolchange.start:
          skipWrite = True
          out.write("; Original Toolchange skipped\n")
        if f.tell() == currentPrint.primeTower.toolchange.end:
          skipWrite = False

      if skipWrite == False:
        #out.write(cl)
        writeWithColorFilter(out, cl, loadedColors)

      # Toolchange insertion after the current line is read and written to output
      if currentPrint.toolchangeBareInsertionPoint:
        if f.tell() == currentPrint.toolchangeBareInsertionPoint.start:
          #insert toolchare bare
          printingToolchangeNewColorIndex = currentPrintingColorIndexForColorIndex(currentPrint.toolchangeNewColorIndex, loadedColors)
          out.write(f"; Toolchange (minimal) inserted to {currentPrint.toolchangeNewColorIndex} --replacement--> {printingToolchangeNewColorIndex}\n")
          # normally we would replace the color with replacement color in writeWithColorFilter() but we are replacing multiple lines so this will write directly
          with open(toolchangeBareFile, mode='r') as tc_bare:
            tc_bare_code = tc_bare.read().replace('XX', str(printingToolchangeNewColorIndex))
            out.write(tc_bare_code)
          currentPrint.printingColor = printingToolchangeNewColorIndex
          currentPrint.printingPeriodicColor = currentPrint.printingColor == elevIsoline.colorIndex
      
      if currentPrint.toolchangeFullInsertionPoint:
        if f.tell() == currentPrint.toolchangeFullInsertionPoint.start:
          #insert toolchange full
          printingToolchangeNewColorIndex = currentPrintingColorIndexForColorIndex(currentPrint.toolchangeNewColorIndex, loadedColors)
          out.write(f"; Prime Tower and Toolchange (full) inserted to {currentPrint.toolchangeNewColorIndex} --replacement--> {printingToolchangeNewColorIndex}\n")

          # Seek to original prime tower and toolchange position. Write prime tower to output. Seek back to while loop reading position.
          cp = f.tell()
          f.seek(currentPrint.primeTower.start, os.SEEK_SET)
          while f.tell() != currentPrint.primeTower.end:
            cl = f.readline()
            cl = substituteNewColor(cl, currentPrint.toolchangeNewColorIndex)
            #out.write(cl)
            writeWithColorFilter(out, cl, loadedColors)
          f.seek(cp, os.SEEK_SET)
          currentPrint.printingColor = currentPrint.toolchangeNewColorIndex
          currentPrint.printingPeriodicColor = currentPrint.printingColor == elevIsoline.colorIndex