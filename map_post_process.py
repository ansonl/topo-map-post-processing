import re, os, typing, queue, time, datetime, math

# Gcode flavors
MARLIN_2_BAMBUSLICER_OLD = 'marlin2bambuslicer_old'
MARLIN_2_BAMBUSLICER_MARKED_GCODE = 'marlin2bambuslicer_markedtoolchangegcode'

# Universal Gcode Constants
UNIVERSAL_TOOLCHANGE_START = '^; MFPP TOOLCHANGE START'
UNIVERSAL_TOOLCHANGE_END = '^; MFPP TOOLCHANGE END'
UNIVERSAL_LAYER_CHANGE_END = '^; MFPP LAYER CHANGE END'

#PERIODIC_LINE_FEATURES = ["Outer wall", "Inner wall"]

# Gcode Constants
MOVEMENT_G = '^(?:G(?:0|1|2|3) )(?:([XYZEF])(-?\d*\.?\d*))?(?: ([XYZEF])(-?\d*\.?\d*))?(?: ([XYZEF])(-?\d*\.?\d*))?(?: ([XYZEF])(-?\d*\.?\d*))?(?: ([XYZEF])(-?\d*\.?\d*))?'
MINIMAL_TOOLCHANGE_PRIME = 'G1 E2 F1800'

# Bambu Gcode Constants
STOP_OBJECT_BAMBUSTUDIO = '^; stop printing object, unique label id:\s(\d*)'
FEATURE_BAMBUSTUDIO = '^; FEATURE: (.*)'
FEATURE_END_BAMBUSTUDIO = '^; filament end gcode' #feature ends when this gcode is found or new feature is found
POTENTIAL_PRIME_TOWER = 'Potential Prime tower'
PRIME_TOWER = 'Prime tower'
TOOLCHANGE = 'Toolchange'
TOOLCHANGE_START = '^; CP TOOLCHANGE START'
# Toolchange (change_filament) start
G392 = '^G392 S(\d*)' #G392 only for A1
M620 = '^M620 S(\d*)A'
# Toolchange core movement actually starts after spiral lift up. Spiral lift is useful if doing prime tower only.
WIPE_SPIRAL_LIFT = '^G2 Z\d*\.?\d* I\d*\.?\d* J\d*\.?\d* P\d*\.?\d* F\d*\.?\d* ; spiral lift a little from second lift'
TOOLCHANGE_T = '^T(?!255$|1000|1100$)(\d*)' # Do not match T255 or T1000 which are nonstandard by Bambu
# Prime tower printing actually starts after M621
M621 = '^M621 S(\d*)A'
#; CP TOOLCHANGE WIPE
# wipe/prime tower here
#; WIPE_TOWER_END
#G92 E0
#; CP TOOLCHANGE END
START_OBJECT_BAMBUSTUDIO = '^; start printing object, unique label id:\s(\d*)'

# Prusa Gcode Constants
STOP_OBJECT_PRUSASLICER = '^; stop printing object'
# wipe off object
FEATURE_PRUSASLICER = '^;TYPE:(.*)'
WIPE_TOWER = 'Wipe tower'
#TOOLCHANGE_START
# prime tower line with old tool
#UNIVERSAL_TOOLCHANGE_START
#UNIVERSAL_TOOLCHANGE_END
#; CP TOOLCHANGE WIPE
# prime tower lines in new tool
#; CP TOOLCHANGE END
#;Type:Wipe tower
# prime tower more lines
START_OBJECT_PRUSASLICER = '^; printing object'

CHANGE_LAYER_BAMBUSTUDIO = '^; CHANGE_LAYER'
Z_HEIGHT_BAMBUSTUDIO = '^; Z_HEIGHT: (\d*\.?\d*)' # Current object layer height including current layer height
LAYER_HEIGHT_BAMBUSTUDIO = '^; LAYER_HEIGHT: (\d*\.?\d*)' # Current layer height

CHANGE_LAYER_PRUSASLICER = '^;LAYER_CHANGE'
Z_HEIGHT_PRUSASLICER = '^;Z:(\d*\.?\d*)' # Current object layer height including current layer height
LAYER_HEIGHT_PRUSASLICER = '^;HEIGHT:(\d*\.?\d*)' # Current layer height

M991 = '^M991 S0 P(\d*)' # process indicator. Indicate layer insertion point.

class StatusQueueItem:
  def __init__(self):
    self.status = None
    self.progress = None

# Position
class Position:
  def __init__(self):
    self.X: float
    self.Y: float
    self.Z: float
    self.E: float
    self.F: float

# State of current Print FILE
class PrintState:
  def __init__(self):
    self.height: float = 0 
    self.layerHeight: float = 0
    self.previousLayerHeight: float = 0
    self.layerEnd: int = 0

    # Color info
    self.originalColor: int = -1 # last color changed to in original print
    self.printingColor: int = -1 # current modified color
    self.printingPeriodicColor: bool = False # last layer wasPeriodicColor?
    self.isPeriodicLine: bool = False # is this layer supposed to have periodic lines?

    # Movement info
    self.originalPosition: Position = Position() # Restore original XYZ position after inserting a TC. Then do E2 for minimal TC. Full Prime tower TC already does E.8

    # Prime tower / Toolchange values for current layer
    self.features: list[Feature] = []
    self.primeTowerFeatureIndex: int = -1 # The available prime tower toolchange index in the feature list. -1 means prime tower does not exist or has been used already.
    self.toolchangeInsertionPoint: int = 0
    
    #self.toolchangeBareInsertionPoint: Feature = None
    #self.toolchangeFullInsertionPoint: Feature = None
    #self.toolchangeNewColorIndex: int = -1
    #self.skipOriginalPrimeTowerAndToolchangeOnLayer: bool = False
    #self.skipOriginalToolchangeOnLayer: bool = False

class PeriodicColor:
  def __init__(self, colorIndex = -1, startHeight = -1, endHeight = -1, height = -1, period = -1, enabledFeatures=[]):
    self.colorIndex: int = colorIndex
    self.startHeight: float = startHeight
    self.endHeight: float = endHeight
    self.height: float = height
    self.period: float = period
    self.enabledFeatures: list[str] = enabledFeatures

class Feature:
  def __init__(self):
    self.featureType: str = None
    self.start: int = 0
    self.end: int = 0
    self.toolchange: Feature = None
    self.isPeriodicColor: bool = False
    self.printingColor: int = -1
    self.skipType: str = None
    
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

def createIsoline(modelToRealWorldDefaultUnits: float, modelOneToNVerticalScale: float, modelSeaLevelBaseThickness: float, realWorldIsolineElevationInterval: float, realWorldIsolineElevationStart: float, realWorldIsolineElevationEnd: float, modelIsolineHeight: float, colorIndex: int, enabledFeatures: list[str]):
  return PeriodicColor(colorIndex=colorIndex, startHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldIsolineElevationStart/modelOneToNVerticalScale, endHeight=modelToRealWorldDefaultUnits*realWorldIsolineElevationEnd/modelOneToNVerticalScale, height=modelIsolineHeight, period=modelToRealWorldDefaultUnits*realWorldIsolineElevationInterval/modelOneToNVerticalScale, enabledFeatures=enabledFeatures)

def createReplacementColor(modelToRealWorldDefaultUnits: float, modelOneToNVerticalScale: float, modelSeaLevelBaseThickness: float, realWorldElevationStart: float, realWorldElevationEnd: float, colorIndex: int, originalColorIndex: int):
  return ReplacementColorAtHeight(colorIndex=colorIndex, originalColorIndex=originalColorIndex, startHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldElevationStart/modelOneToNVerticalScale, endHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldElevationEnd/modelOneToNVerticalScale)

def shouldLayerBePeriodicLine(printState: PrintState, periodicLine: PeriodicColor):
  if printState.height >= periodicLine.startHeight and printState.height <= periodicLine.endHeight:
    # current layer top is inside an isoline
    if (printState.height - periodicLine.startHeight) % periodicLine.period <= periodicLine.height:
      #start isoline
      #print(f"({printState.height} - {periodicLine.startHeight}) % {periodicLine.period} so start isoline")
      return True
    #current layer envelopes an isoline
    #is thicker than 1 isoline AND bottom is in isoline OR top is above next isoline (top of next isoline)
    elif printState.layerHeight > periodicLine.height:
      #If previous layer was periodic line and previous layer height was greater than periodic line height then this layer should not a periodic color even if periodic layer range is sandwiched between current layer and previous layer boundary. Previous layer being periodic color and greather than periodic line height already exceeded total periodic line height so we don't need a double thick periodic line.
      if printState.printingPeriodicColor == True and printState.previousLayerHeight > periodicLine.height:
        return False

      if ((printState.height - periodicLine.startHeight) - printState.layerHeight) % periodicLine.period < periodicLine.height:
        #print(f"{printState.layerHeight} > {periodicLine.height} and (({printState.height} - {periodicLine.startHeight}) - {printState.layerHeight}) % {periodicLine.period} < {periodicLine.height} so start isoline")
        #start isoline
        return True
      elif printState.height - periodicLine.startHeight > math.ceil(((printState.height - periodicLine.startHeight) - printState.layerHeight) / periodicLine.period) * periodicLine.period + periodicLine.height:
      #start isoline
        return True
  return False

def updateReplacementColors(printState: PrintState, rcs: list[ReplacementColorAtHeight]):
  for rc in rcs:
    if printState.height > rc.startHeight and printState.height - printState.layerHeight < rc.endHeight:
      loadedColors[rc.originalColorIndex].replacementColorIndex = rc.colorIndex
    elif loadedColors[rc.originalColorIndex].replacementColorIndex == rc.colorIndex:
      loadedColors[rc.originalColorIndex].replacementColorIndex = -1

def findChangeLayer(f: typing.TextIO, lastPrintState: PrintState, gf: str, pcs: list[PeriodicColor], rcs: list[ReplacementColorAtHeight], le: str):
  cl = f.readline()
  # Look for start of layer
  changeLayerMatchBambu = re.match(CHANGE_LAYER_BAMBUSTUDIO, cl)
  changeLayerMatchPrusa = re.match(CHANGE_LAYER_PRUSASLICER, cl)
  if changeLayerMatchBambu or changeLayerMatchPrusa:
    # Create new print state for the new found layer and carry over some state that should be preserved between layers.
    printState = PrintState()
    printState.previousLayerHeight = lastPrintState.layerHeight
    printState.originalColor = lastPrintState.originalColor
    printState.printingColor = lastPrintState.printingColor
    printState.printingPeriodicColor = lastPrintState.printingPeriodicColor

    # Find Z_HEIGHT value
    cl = f.readline()
    zHeightMatchBambu = re.match(Z_HEIGHT_BAMBUSTUDIO, cl)
    zHeightMatchPrusa = re.match(Z_HEIGHT_PRUSASLICER, cl)
    if zHeightMatchBambu or zHeightMatchPrusa:
      if zHeightMatchBambu:
        printState.height = float(zHeightMatchBambu.groups()[0])
      if zHeightMatchPrusa:
        printState.height = float(zHeightMatchPrusa.groups()[0])
        #print(f"{Z_HEIGHT} {cl.groups()[0]}")
      print(f"\nProcessing height {printState.height}")

    # Find LAYER_HEIGHT value
    cl = f.readline()
    layerHeightMatchBambu = re.match(LAYER_HEIGHT_BAMBUSTUDIO, cl)
    layerHeightMatchPrusa = re.match(LAYER_HEIGHT_PRUSASLICER, cl)
    if layerHeightMatchBambu or layerHeightMatchPrusa:
      if layerHeightMatchBambu:
        printState.layerHeight = float(layerHeightMatchBambu.groups()[0])
      if layerHeightMatchPrusa:
        printState.layerHeight = float(layerHeightMatchPrusa.groups()[0])

    #update loaded colors replacement color data based on current height
    updateReplacementColors(printState, rcs)
    print(f"pos {f.tell()} before call findLayerFeatures")

    # determine periodic line status
    printState.isPeriodicLine = shouldLayerBePeriodicLine(printState, pcs[0]) if len(pcs) > 0 else False
    print(f"Is printing periodic color {printState.printingPeriodicColor}")
    print(f"Is periodic line {printState.isPeriodicLine}")

    cp = f.tell()  
    findLayerFeatures(f=f, gf=gf, printState=printState, pcs=pcs, le=le)

    #print features
    print(f"{len(printState.features)} features found")
    for feat in printState.features:
      print(f"{feat.featureType} start: {feat.start} end: {feat.end} isPeriodicColor:{feat.isPeriodicColor} printingColor:{feat.printingColor}")
      if feat.toolchange:
        print(f"toolchange.start: {feat.toolchange.start} end: {feat.toolchange.start} printingColor:{feat.toolchange.printingColor}")

    f.seek(cp, os.SEEK_SET)

    firstNonePrimeTowerFeatureIndex = 0
    while firstNonePrimeTowerFeatureIndex < len(printState.features):
      if printState.features[firstNonePrimeTowerFeatureIndex].featureType != PRIME_TOWER:
        break
      firstNonePrimeTowerFeatureIndex += 1
    if firstNonePrimeTowerFeatureIndex == len(printState.features):
      firstNonePrimeTowerFeatureIndex = -1

    return printState
  return None

def findLayerFeatures(f: typing.TextIO, gf: str, printState: PrintState, pcs: list[PeriodicColor], le: str):
  if gf == MARLIN_2_BAMBUSLICER_MARKED_GCODE:
    cl = True
    curFeature = None
    while cl:
      cl = f.readline()
      # next layer marker
      changeLayerMatchBambu = re.match(CHANGE_LAYER_BAMBUSTUDIO, cl)
      changeLayerMatchPrusa = re.match(CHANGE_LAYER_PRUSASLICER, cl)

      # start marker for prime tower feature
      stopObjMatchBambu = re.match(STOP_OBJECT_BAMBUSTUDIO, cl)
      stopObjMatchPrusa = re.match(STOP_OBJECT_PRUSASLICER, cl)

      # start marker for non prime tower features
      featureMatchBambu = re.match(FEATURE_BAMBUSTUDIO, cl)
      featureMatchPrusa = re.match(FEATURE_PRUSASLICER, cl)

      # toolchange start/end and index
      univeralToolchangeStartMatch = re.match(UNIVERSAL_TOOLCHANGE_START, cl)
      toolchangeMatch = re.match(TOOLCHANGE_T, cl)
      univeralToolchangeEndMatch = re.match(UNIVERSAL_TOOLCHANGE_END, cl)

      # end marker for prime tower feature
      startObjMatchBambu = re.match(START_OBJECT_BAMBUSTUDIO, cl)
      startObjMatchPrusa = re.match(START_OBJECT_PRUSASLICER, cl)

      # end if we find next layer marker
      if changeLayerMatchBambu or changeLayerMatchPrusa:
        printState.layerEnd = f.tell() - len(cl) - (len(le)-1)
        #print('got new layer at ',f.tell())
        if curFeature and curFeature.featureType != POTENTIAL_PRIME_TOWER:
          printState.features.append(curFeature)
          curFeature = None
        break
      
      #if cl.startswith("; stop printing object"):
      #  print(f"{stopObjMatchPrusa}")
      #  print(f"found stop at {f.tell()}")

      # Find prime feature start
      if stopObjMatchBambu or stopObjMatchPrusa:
        if curFeature and curFeature.featureType != POTENTIAL_PRIME_TOWER:
          printState.features.append(curFeature)
        curFeature = Feature()
        curFeature.featureType = POTENTIAL_PRIME_TOWER
        curFeature.start = f.tell() - len(cl) - (len(le)-1)
        #print(f"found prime tower feature start (stop obj) at {f.tell() - len(cl)}")
        continue

      # Look for FEATURE to find feature type
      elif featureMatchBambu or featureMatchPrusa:
        #print(f"found FEATURE match at {f.tell() - len(cl) - (len(le)-1)}")

        if curFeature and curFeature.featureType != POTENTIAL_PRIME_TOWER: # If we were looking at a feature already, end it and save it. Don't end potential prime tower
          if curFeature.featureType == PRIME_TOWER:
            if (featureMatchBambu and featureMatchBambu.groups()[0] == PRIME_TOWER) or (featureMatchPrusa and featureMatchPrusa.groups()[0] == PRIME_TOWER):
              #print(f"found next prime tower before current prime tower end")
              continue
            else:
              #print(f"found new feature before end of prime tower at {f.tell()}")
              break
          printState.features.append(curFeature)
        
        curFeature = None

        if curFeature == None:
          curFeature = Feature()
          curFeature.start = f.tell() - len(cl) - (len(le)-1)
        if featureMatchBambu:
          curFeature.featureType = featureMatchBambu.groups()[0]
        elif featureMatchPrusa:
          curFeature.featureType = featureMatchPrusa.groups()[0]

        # mark feature as periodic color if needed
        if printState.isPeriodicLine and (curFeature.featureType in pcs[0].enabledFeatures or len(pcs[0].enabledFeatures) == 0):
          curFeature.isPeriodicColor = True
          curFeature.printingColor = pcs[0].colorIndex

        #print(f"feature is of type {curFeature.featureType}")
        continue

      # Keep looking for feature if we didn't find one yet
      elif curFeature == None:
        continue

      # A toolchange is found UNIVERSAL_TOOLCHANGE_START
      elif univeralToolchangeStartMatch: 
        curFeature.toolchange = Feature()
        curFeature.toolchange.featureType = TOOLCHANGE
        curFeature.toolchange.start = f.tell() - len(cl) - (len(le)-1)
        #print(f"found toolchange start at {curFeature.toolchange.start}")
        continue

      # Look for TXX if we already found the toolchange start
      elif toolchangeMatch:
        curFeature.toolchange.printingColor = int(toolchangeMatch.groups()[0])
        #print(f"toolchange to extruder {curFeature.toolchange.printingColor} at {f.tell()}")
        continue

      # Look for UNIVERSAL_TOOLCHANGE_END if we already found the toolchange start
      elif univeralToolchangeEndMatch:
        if curFeature.toolchange == None:
          #print(f"toolchange end found before toolchange start at {f.tell()}")
          break
        curFeature.toolchange.end = f.tell()
        #print(f"found toolchange end at {curFeature.toolchange.end}")
        continue

      # Look for prime tower end
      elif startObjMatchBambu or startObjMatchPrusa:
        if curFeature.featureType != PRIME_TOWER:
          #print(f"found prime tower end even though current feature is not prime tower and is type {curFeature.featureType}")
          curFeature = None
          continue
        curFeature.end = f.tell() - len(cl) - (len(le)-1)
        printState.features.append(curFeature)
        printState.primeTowerFeatureIndex = len(printState.features)-1
        #print(f"found prime tower end at {curFeature.end}")
        curFeature = None

    if curFeature:
      printState.features.append(curFeature)

# Get the actual processed printing color before next printing feature
def determineBeforeNextFeaturePrintingColor(features: list[Feature], curFeatureIdx: int, lastPrintingColor: int, passedPrimeTowerCount: int) -> tuple[int, bool]:
  if curFeatureIdx > -1:
    curFeature = features[curFeatureIdx]
    if curFeature.printingColor > -1: # Only set if periodic feature
      lastPrintingColor = curFeature.printingColor
    if curFeature.toolchange: # Check toolchange that may be at end of current feature
      lastPrintingColor = curFeature.toolchange.printingColor
  if curFeatureIdx+1 < len(features): # If we have additional features after this
    nextFeature = features[curFeatureIdx+1]
    if nextFeature.featureType == PRIME_TOWER: # If next feature is prime tower, keep looking
      return determineNextFeaturePrintingColor(features, curFeatureIdx+1, lastPrintingColor, passedPrimeTowerCount+1)
  return lastPrintingColor, passedPrimeTowerCount

# Get the target printing color of next printing feature
def determineNextFeaturePrintingColor(features: list[Feature], curFeatureIdx: int, lastPrintingColor: int, passedPrimeTowerCount: int) -> tuple[int, bool]:
  if curFeatureIdx > -1:
    curFeature = features[curFeatureIdx]
    if curFeature.toolchange: # Check toolchange that may be at end of current feature
      lastPrintingColor = curFeature.toolchange.printingColor
  if curFeatureIdx+1 < len(features): # If we have additional features after this
    nextFeature = features[curFeatureIdx+1]
    if nextFeature.featureType == PRIME_TOWER: # If next feature is prime tower, keep looking
      return determineNextFeaturePrintingColor(features, curFeatureIdx+1, lastPrintingColor, passedPrimeTowerCount+1)
    else:
      if nextFeature.printingColor > -1: # Check next feature printing color (only set if periodic feature)
        lastPrintingColor = nextFeature.printingColor
  return lastPrintingColor, passedPrimeTowerCount

def substituteNewColor(cl, newColorIndex: int):
  cl = re.sub(M620, f"M620 S{newColorIndex}A", cl)
  cl = re.sub(TOOLCHANGE_T, f"T{newColorIndex}", cl)
  cl = re.sub(M621, f"M621 S{newColorIndex}A", cl)
  return cl

# return the current printing color index that should be used for a given color index. Returns the replacement color index for a color index if there is a replacement assigned.
def currentPrintingColorIndexForColorIndex(colorIndex: int, lc: list[PrintColor]):
  #print(colorIndex)
  if lc[colorIndex].replacementColorIndex != -1:
    return lc[colorIndex].replacementColorIndex
  else:
    return colorIndex

def writeWithColorFilter(out: typing.TextIO, cl: str, lc: list[PrintColor]):
  cmdColorIndex = -1
  #print(f"writewithcolorfilter {cl}")
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

def process(gcodeFlavor: str, inputFile: str, outputFile: str, toolchangeBareFile: str, periodicColors: list[PeriodicColor], replacementColors:list[ReplacementColorAtHeight], lineEnding: str, statusQueue: queue.Queue):
  startTime = time.monotonic()
  try:
    with open(inputFile, mode='r') as f, open(outputFile, mode='w') as out:
      currentPrint: PrintState = PrintState()

      #Get total length of file
      f.seek(0, os.SEEK_END)
      lp = f.tell()
      f.seek(0, os.SEEK_SET)

      # Don't write to output if True
      skipWrite = False

      curFeatureIdx = -1

      # Check if next layer needs a toolchange and the next toolchange color
      def determineIfNextFeatureNeedsToolchange(ps: PrintState, cfi: int) -> tuple[bool, int, int] :
        # the active printing color before starting the next feature
        beforeNextFeaturePrintingColor, passedPrimeTowerCount = determineBeforeNextFeaturePrintingColor(features=ps.features, curFeatureIdx=cfi, lastPrintingColor=ps.printingColor, passedPrimeTowerCount=0)
        # the correct target printing color for the next feature (pass in original color as initial color to get correct original color index if needed)
        nextFeaturePrintingColor, _ = determineNextFeaturePrintingColor(features=ps.features, curFeatureIdx=cfi, lastPrintingColor=ps.originalColor, passedPrimeTowerCount=0)
        printingToolchangeNewColorIndex = currentPrintingColorIndexForColorIndex(nextFeaturePrintingColor, loadedColors)

        if ps.height == 14.4:
          0==0
        #if curFeatureIdx == 3:
        #  0==0

        return beforeNextFeaturePrintingColor != printingToolchangeNewColorIndex, printingToolchangeNewColorIndex, passedPrimeTowerCount

      # Current line buffer
      cl = True
      while cl:
        # Look for start of a layer CHANGE_LAYER
        cp = f.tell()
        foundNewLayer = findChangeLayer(f,lastPrintState=currentPrint, gf=gcodeFlavor, pcs=periodicColors, rcs=replacementColors, le=lineEnding)
        if foundNewLayer:
          currentPrint = foundNewLayer
          #print(f"toolchangeNewColorIndex {currentPrint.toolchangeNewColorIndex}")
          #print(f"skipOriginalPrimeTowerAndToolchangeOnLayer {currentPrint.skipOriginalPrimeTowerAndToolchangeOnLayer}")
          #print(f"skipOriginalToolchangeOnLayer {currentPrint.skipOriginalToolchangeOnLayer}")
          #if currentPrint.primeTower:
          #  print(f"primetower.start {currentPrint.primeTower.start}")
          #  print(f"primetower.end {currentPrint.primeTower.end}")
          curFeatureIdx = -1

          # Check if toolchange needed for "next" feature which is index 0
          nextFeatureNeedsToolchange, printingToolchangeNewColorIndex, passedPrimeTower = determineIfNextFeatureNeedsToolchange(currentPrint, curFeatureIdx)
          if nextFeatureNeedsToolchange: #if printing color before and printing color in next feature do not match, insert a toolchange at start of next feature (or at layer end if this is the last feature)
            if curFeatureIdx+1 < len(currentPrint.features):
              currentPrint.toolchangeInsertionPoint = currentPrint.features[curFeatureIdx+1].start
            else:
              currentPrint.toolchangeInsertionPoint = currentPrint.layerEnd
          else:
              if passedPrimeTower: 
                currentPrint.primeTowerFeatureIndex = -1


          item = StatusQueueItem()
          item.status = f"Current Height {currentPrint.height}"
          item.progress = cp/lp * 100
          statusQueue.put(item=item)
          # join to debug thread queue reading
          #statusQueue.join()
        f.seek(cp, os.SEEK_SET)

        cl = f.readline()
        #print(".",end='')

        # look for movement gcode and record last position
        movementMatch = re.match(MOVEMENT_G, cl)
        if movementMatch:
          m = 0
          while m+1 < len(movementMatch.groups()):
            if movementMatch.groups()[m] == None:
              break
            axis = str(movementMatch.groups()[m])
            axisValue = float(movementMatch.groups()[m+1])
            if axis == 'X':
              currentPrint.originalPosition.X = axisValue
            elif axis == 'Y':
              currentPrint.originalPosition.Y = axisValue
            elif axis == 'Z':
              currentPrint.originalPosition.Z = axisValue
            elif axis == 'E':
              currentPrint.originalPosition.E = axisValue
            elif axis == 'F':
              currentPrint.originalPosition.F = axisValue
            else:
              print(f"Unknown axis {axis} {axisValue} at {f.tell()}")
            m += 2

        # look for toolchange T
        toolchangeMatch = re.match(TOOLCHANGE_T, cl)
        if toolchangeMatch:
          currentPrint.originalColor = int(toolchangeMatch.groups()[0])
          if skipWrite == False:
            currentPrint.printingColor = currentPrint.originalColor

        insertedToolchangeAtCurrentPosition = False
        # Check if we are at toolchange insertion point. This point can be set while parsing the layer (if first printing layer needs TC). This point can also be set while reading a feature in the loop.
        if f.tell() == currentPrint.toolchangeInsertionPoint:
          # Write out the current line read that is before the toolchange insert. We will be inserting toolchange code after this line.
          writeWithColorFilter(out, cl, loadedColors)
          insertedToolchangeAtCurrentPosition = True
          skipWrite = True

          extraPrimeGcode = None

          # find the correct color for the toolchange
          nextFeatureColor, _ = determineNextFeaturePrintingColor(currentPrint.features, curFeatureIdx, currentPrint.originalColor, False)
          printingToolchangeNewColorIndex = currentPrintingColorIndexForColorIndex(nextFeatureColor, loadedColors)

          # Check if full toolchange is available
          if currentPrint.primeTowerFeatureIndex > -1 and currentPrint.features[currentPrint.primeTowerFeatureIndex].toolchange:
            
            #insert toolchange full
            out.write(f"; MFPP Prime Tower and Toolchange (full) inserted to {nextFeatureColor} --replacement--> {printingToolchangeNewColorIndex}\n")

            # Seek to original prime tower and toolchange position. Write prime tower to output. Seek back to while loop reading position.
            cp = f.tell()
            f.seek(currentPrint.features[currentPrint.primeTowerFeatureIndex].start, os.SEEK_SET)
            while f.tell() <= currentPrint.features[currentPrint.primeTowerFeatureIndex].end:
              cl = f.readline()
              cl = substituteNewColor(cl, nextFeatureColor)
              writeWithColorFilter(out, cl, loadedColors)
            f.seek(cp, os.SEEK_SET)
          
            currentPrint.primeTowerFeatureIndex = -1 # clear prime tower feature index now that we used it
          else:
            #add minimal toolchange
            #insert toolchare bare
            out.write(f"; MFPP Toolchange (minimal) inserted to {nextFeatureColor} --replacement--> {printingToolchangeNewColorIndex}\n")
            # normally we would replace the color with replacement color in writeWithColorFilter() but we are replacing multiple lines so this will write directly
            with open(toolchangeBareFile, mode='r') as tc_bare:
              tc_bare_code = tc_bare.read().replace('XX', str(printingToolchangeNewColorIndex))
              out.write(tc_bare_code)
            
            extraPrimeGcode = MINIMAL_TOOLCHANGE_PRIME
            
          currentPrint.printingColor = printingToolchangeNewColorIndex
          currentPrint.printingPeriodicColor = currentPrint.printingColor == periodicColors[0].colorIndex if len(periodicColors) > 0 else False
          
          # Restore original position state before toolchange insert
          out.write("; MFPP Post-Toolchange Restore Positions and Prime\n")
          out.write(f"G0 X{currentPrint.originalPosition.X} Y{currentPrint.originalPosition.Y} Z{currentPrint.originalPosition.Z}\n")
          if extraPrimeGcode:
            out.write(f"{extraPrimeGcode}\n") #Extrude a bit for minimal toolchange
          out.write(f"G1 F{currentPrint.originalPosition.F}\n")

          currentPrint.toolchangeInsertionPoint = 0 # clear toolchange insertion point

        curFeature = None
        # Check if we are at current feature index start
        if len(currentPrint.features) > 0:
          if curFeatureIdx+1 < len(currentPrint.features) and f.tell() == currentPrint.features[curFeatureIdx+1].start:
            curFeature = currentPrint.features[curFeatureIdx+1]
            curFeatureIdx += 1 #next loop will check for next feature start
            
            # End skip (when skipping prime tower that is the previous feature) because we ended the previous prime tower feature by detecting the next feature.
            if skipWrite and insertedToolchangeAtCurrentPosition == False:
              print(f"End previous feature skip at feature {curFeatureIdx} {f.tell()}")
              skipWrite = False

            # Check this is the last feature and prime tower has not been used yet. Set toolchange insert to be at layer end
            if curFeatureIdx == len(currentPrint.features) - 1 and currentPrint.primeTowerFeatureIndex > -1:
              print(f"On last feature and prime tower not used. Set insert at layer end {currentPrint.primeTowerFeatureIndex}")
              currentPrint.toolchangeInsertionPoint = currentPrint.layerEnd

            # If current feature is the prime tower. Do not write prime tower. Skip past this prime tower feature. We may find use for prime tower later.
            if curFeature.featureType == PRIME_TOWER and currentPrint.primeTowerFeatureIndex > -1:
              print(f"Current feature {curFeatureIdx} is prime tower. Skipping prime tower.")
              out.write("; MFPP Original Prime Tower skipped\n")
              curFeature.skipType = PRIME_TOWER
              skipWrite = True
              print(f"start Prime Tower skip {f.tell()}")
              continue

            # Check if next layer needs a toolchange
            nextFeatureNeedsToolchange, printingToolchangeNewColorIndex, passedPrimeTowerCount = determineIfNextFeatureNeedsToolchange(currentPrint, curFeatureIdx)
            if nextFeatureNeedsToolchange: #if printing color before and printing color in next feature do not match, insert a toolchange at start of next feature (or at layer end if this is the last feature)
              if curFeatureIdx+1+passedPrimeTowerCount < len(currentPrint.features):
                currentPrint.toolchangeInsertionPoint = currentPrint.features[curFeatureIdx+1+passedPrimeTowerCount].start
              else:
                currentPrint.toolchangeInsertionPoint = currentPrint.layerEnd
            else: # if printing color before and in next feature match and prime tower played a part in the color, clear the prime tower index and write prime tower in original position
              if passedPrimeTowerCount: 
                currentPrint.primeTowerFeatureIndex = -1
            
            # Check if feature toolchange can be omitted. If feature toolchange is redundant.
            if curFeature.toolchange and ((currentPrint.printingColor == curFeature.toolchange.printingColor) or (curFeature.toolchange.printingColor == printingToolchangeNewColorIndex)):
              curFeature.skipType = TOOLCHANGE
          
          if curFeature:
            # Skip feature toolchange if needed
            if curFeature.skipType == TOOLCHANGE and f.tell() == curFeature.toolchange.start:
              print(f"Current feature {curFeatureIdx} toolchange is redundant. Skipping feature toolchange.")
              out.write("; MFPP Original Feature Toolchange skipped\n")
              skipWrite = True
              print(f"start feature toolchange skip {f.tell()}")

            # End skip if we are skipping toolchange and got to toolchange end
            if curFeature.skipType == TOOLCHANGE and f.tell() == curFeature.toolchange.end:
              print(f"end feature toolchange skip at {f.tell()}")
              skipWrite = False
              curFeature.skipType = None

        if skipWrite == False: 
          #out.write(cl)
          writeWithColorFilter(out, cl, loadedColors)

        # If we are at toolchange insertion point, we wrote the current line read earlier before inserting the toolchange. So we set skipWrite to not write it again. We can turn off skipWrite now so that next lines are written again.
        if skipWrite and insertedToolchangeAtCurrentPosition:
          skipWrite = False

      item = StatusQueueItem()
      item.status = f"Completed at {currentPrint.height} height in {str(datetime.timedelta(seconds=time.monotonic()-startTime))}s"
      item.progress = 99.99
      statusQueue.put(item=item)
  except PermissionError as e:
    item = StatusQueueItem()
    item.status = f"Failed to open {e}"
    statusQueue.put(item=item)