import re, os, typing, queue, time, datetime, math, enum, copy

# Gcode flavors
MARLIN_2_BAMBU_PRUSA_MARKED_GCODE = 'marlin2_bambu_prusa_markedtoolchangegcode'

# Universal Gcode Constants
UNIVERSAL_TOOLCHANGE_START = '^; MFPP TOOLCHANGE START'
UNIVERSAL_TOOLCHANGE_END = '^; MFPP TOOLCHANGE END'
UNIVERSAL_LAYER_CHANGE_END = '^; MFPP LAYER CHANGE END'

#PERIODIC_LINE_FEATURES = ["Outer wall", "Inner wall"]

# Gcode Constants
MOVEMENT_G = '^^(?:G(?:0|1|2|3) )\s?(?:([XYZEF])(-?\d*\.?\d*))?(?:\s+([XYZEF])(-?\d*\.?\d*))?(?:\s+([XYZEF])(-?\d*\.?\d*))?(?:\s+([XYZEF])(-?\d*\.?\d*))?(?:\s+([XYZEF])(-?\d*\.?\d*))?'
FULL_TOOLCHANGE_PRIME = 'G1 E.8 F1800'
MINIMAL_TOOLCHANGE_PRIME = 'G1 E2 F1800'
BAMBU_PRUSA_WIPE_END_PRIME = 'G1 E.65 F1500'

# Bambu Gcode Constants
STOP_OBJECT_BAMBUSTUDIO = '^; stop printing object, unique label id:\s(\d*)'
FEATURE_BAMBUSTUDIO = '^; FEATURE: (.*)'
FEATURE_END_BAMBUSTUDIO = '^; filament end gcode' #feature ends when this gcode is found or new feature is found
PRIME_TOWER = 'Prime tower'
TOOLCHANGE = 'Toolchange'
TOOLCHANGE_START = '^; CP TOOLCHANGE START'
WIPE_START = '^;\s?WIPE_START'
WIPE_END = '^;\s?WIPE_END'
WIPE_END_REMOVE_FEATURES = ["External perimeter", "Outer wall"]
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
#WIPE_START -skip this part
#WIPE_END
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

CHANGE_LAYER_CURA = '^;LAYER:\d*'
FEATURE_CURA = '^;TYPE:(.*)'

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
    self.height: float = -1 
    self.layerHeight: float = 0
    self.previousLayerHeight: float = 0
    self.layerStart: int = 0
    self.layerEnd: int = 0

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

    #Loop settings
    self.skipWrite: bool = False
    self.skipWriteForCurrentLine: bool = False
    
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
    self.originalColor: int = -1
    self.printingColor: int = -1
    self.startPosition: Position = Position()
    self.wipeEnd: Feature = None
    self.skipType: SkipType = None
    #self.used: bool = False #flag to show prime tower has been used already
    
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

class ToolchangeType(enum.Enum):
  NONE = enum.auto()
  MINIMAL = enum.auto()
  FULL = enum.auto()

class SkipType(enum.Enum):
  PRIME_TOWER_FEATURE = enum.auto()
  FEATURE_ORIG_TOOLCHANGE_AND_WIPE_END = enum.auto()


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
    printState.originalColor = lastPrintState.layerEndOriginalColor if lastPrintState.layerEndOriginalColor > -1 else lastPrintState.originalColor
    printState.printingColor = lastPrintState.printingColor
    printState.printingPeriodicColor = lastPrintState.printingPeriodicColor
    printState.layerStart = f.tell()

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

    if printState.height == 0.6:
      0==0

    cp = f.tell()  
    findLayerFeatures(f=f, gf=gf, printState=printState, pcs=pcs, le=le)

    #rearrange features
    if printState.isPeriodicLine:
      insertIdx = 0
      featureIdx = 0
      while featureIdx < len(printState.features):
        if printState.features[featureIdx].isPeriodicColor:
          if insertIdx != featureIdx:
            printState.features.insert(insertIdx, printState.features.pop(featureIdx))
          insertIdx += 1
        featureIdx += 1

    for feat in printState.features:
      printState.stopPositions.append(feat.start)
    for feat in printState.primeTowerFeatures:
      printState.stopPositions.append(feat.start)
    printState.stopPositions.append(printState.layerEnd) #add layer end as a stop position

    print(f"{len(printState.features)} printing features and {len(printState.primeTowerFeatures)} reusable prime towers found")

    '''
    #print rearranged features
    print(f"{len(printState.features)} printing features found")
    fi = 0
    for feat in printState.features:
      print(f"{fi} {feat.featureType} start: {feat.start} end: {feat.end} originalcolor: {feat.originalColor} isPeriodicColor:{feat.isPeriodicColor} printingColor:{feat.printingColor}")
      if feat.toolchange:
        print(f"toolchange.start: {feat.toolchange.start} end: {feat.toolchange.end} printingColor:{feat.toolchange.printingColor}")
      fi += 1

    #print prime tower features (only filled when periodic layer)
    print(f"{len(printState.primeTowerFeatures)} prime tower features found")
    for feat in printState.primeTowerFeatures:
      print(f"{feat.featureType} start: {feat.start} end: {feat.end} originalcolor: {feat.originalColor} isPeriodicColor:{feat.isPeriodicColor} printingColor:{feat.printingColor}")
      if feat.toolchange:
        print(f"toolchange.start: {feat.toolchange.start} end: {feat.toolchange.end} printingColor:{feat.toolchange.printingColor}")
      if feat.wipeEnd:
        print(f"wipeEnd.start: {feat.wipeEnd.start}")
    '''

    if printState.height == 0.6:
      0==0

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
  if gf == MARLIN_2_BAMBU_PRUSA_MARKED_GCODE:
    cl = True
    curFeature = None
    curStartPosition = printState.originalPosition #last position before entering feature
    curOriginalColor = printState.originalColor # original color at start of layer

    def addFeatureToList(ps: PrintState, cf: Feature):
      if cf.toolchange: # only add prime tower to available prime tower list if it has a toolchange
        if ps.isPeriodicLine:
          ps.primeTowerFeatures.append(cf)
        else:
          ps.features.append(cf)
      else:
        ps.features.append(cf)

    while cl:
      cl = f.readline()
      # next layer marker
      changeLayerMatchBambu = re.match(CHANGE_LAYER_BAMBUSTUDIO, cl)
      changeLayerMatchPrusa = re.match(CHANGE_LAYER_PRUSASLICER, cl)

      # start marker for prime tower feature
      #stopObjMatchBambu = re.match(STOP_OBJECT_BAMBUSTUDIO, cl)
      #stopObjMatchPrusa = re.match(STOP_OBJECT_PRUSASLICER, cl)

      # start marker for non prime tower features
      featureMatchBambu = re.match(FEATURE_BAMBUSTUDIO, cl)
      featureMatchPrusa = re.match(FEATURE_PRUSASLICER, cl)

      # toolchange start/end and index
      univeralToolchangeStartMatch = re.match(UNIVERSAL_TOOLCHANGE_START, cl)
      toolchangeMatch = re.match(TOOLCHANGE_T, cl)
      univeralToolchangeEndMatch = re.match(UNIVERSAL_TOOLCHANGE_END, cl)

      # wipe_end marker for normal printing features to skip
      wipeEndMatch = re.match(WIPE_END, cl)

      # end marker for prime tower feature
      #startObjMatchBambu = re.match(START_OBJECT_BAMBUSTUDIO, cl)
      #startObjMatchPrusa = re.match(START_OBJECT_PRUSASLICER, cl)

      # end if we find next layer marker
      if changeLayerMatchBambu or changeLayerMatchPrusa:
        printState.layerEnd = f.tell() - len(cl) - (len(le)-1)
        #print('got new layer at ',f.tell())
        curFeature.end = f.tell()
        addFeatureToList(printState, curFeature)
        curFeature = None
        printState.layerEndOriginalColor = curOriginalColor
        break
      
      # look for movement gcode and record last position before entering a feature
      movementMatch = re.match(MOVEMENT_G, cl)
      if movementMatch:
        m = 0
        while m+1 < len(movementMatch.groups()):
          if movementMatch.groups()[m] == None:
            break
          axis = str(movementMatch.groups()[m])
          axisValue = float(movementMatch.groups()[m+1])
          if axis == 'X':
            curStartPosition.X = axisValue
          elif axis == 'Y':
            curStartPosition.Y = axisValue
          elif axis == 'Z':
            curStartPosition.Z = axisValue
          elif axis == 'E':
            curStartPosition.E = axisValue
          elif axis == 'F':
            curStartPosition.F = axisValue
          else:
            print(f"Unknown axis {axis} {axisValue} at {f.tell()}")
          m += 2

      #if cl.startswith("; stop printing object"):
      #  print(f"{stopObjMatchPrusa}")
      #  print(f"found stop at {f.tell()}")

      '''
      # Find prime feature start
      if stopObjMatchBambu or stopObjMatchPrusa:
        # Look ahead one line to see if we find start object comment
        # In that case, we are still in the current feature, it just covers two objects
        cp = f.tell()
        nl = f.readline()
        f.seek(cp, os.SEEK_SET)
        if re.match(START_OBJECT_BAMBUSTUDIO, nl) or re.match(START_OBJECT_PRUSASLICER, nl):
          # Keep looking at current feature
          continue
        if curFeature and curFeature.featureType != POTENTIAL_PRIME_TOWER:
          printState.features.append(curFeature)
        curFeature = Feature()
        curFeature.featureType = POTENTIAL_PRIME_TOWER
        curFeature.start = f.tell() - len(cl) - (len(le)-1)
        #print(f"found prime tower feature start (stop obj) at {f.tell() - len(cl)}")
        continue
      '''

      # Look for FEATURE to find feature type
      if featureMatchBambu or featureMatchPrusa:
        #print(f"found FEATURE match at {f.tell() - len(cl) - (len(le)-1)}")

        # Don't end potential prime tower if we found prime tower feature for Bambu
        '''
        if curFeature and curFeature.featureType == POTENTIAL_PRIME_TOWER or curFeature and curFeature.featureType == PRIME_TOWER:
          if (featureMatchBambu and featureMatchBambu.groups()[0] == PRIME_TOWER) or (featureMatchPrusa and featureMatchPrusa.groups()[0] == WIPE_TOWER):
            print(f"turn {curFeature.featureType} to prime tower at {f.tell()}")
            curFeature.featureType = PRIME_TOWER
            continue
        # save feature if not potential prime tower
        '''
        
        if curFeature:
          curFeature.end = f.tell()
          addFeatureToList(printState, curFeature)
          curFeature = None

        # Create new feature 
        if curFeature == None or featureMatchPrusa:
          curFeature = Feature()
          curFeature.start = f.tell() - len(cl) - (len(le)-1)
          curFeature.startPosition = copy.copy(curStartPosition) # save last position state as start position for this feature
          curFeature.originalColor = curOriginalColor # save current original color as color for this feature
        if featureMatchBambu:
          curFeature.featureType = featureMatchBambu.groups()[0]
        elif featureMatchPrusa:
          if featureMatchPrusa.groups()[0] == WIPE_TOWER: #Rename wipe tower to prime tower
            curFeature.featureType = PRIME_TOWER
          else:
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
        nextTool = int(toolchangeMatch.groups()[0])
        curOriginalColor = nextTool
        curFeature.toolchange.printingColor = nextTool
        #print(f"toolchange to extruder {curFeature.toolchange.printingColor} at {f.tell()}")
        continue

      # Look for UNIVERSAL_TOOLCHANGE_END if we already found the toolchange start
      elif univeralToolchangeEndMatch:
        if curFeature.toolchange == None:
          print(f"toolchange end found before toolchange start at {f.tell()}")
          break
        curFeature.toolchange.end = f.tell()
        #print(f"found toolchange end at {curFeature.toolchange.end}")
        continue

      # Look for wipe_end on normal features. Overwrite previous found wipe end with last wipe end
      if wipeEndMatch:
          curFeature.wipeEnd = Feature()
          curFeature.wipeEnd.featureType = WIPE_END
          curFeature.wipeEnd.start = f.tell() - len(cl) - (len(le)-1)

      '''
      # Look for prime tower end (start object)
      elif startObjMatchBambu or startObjMatchPrusa:
        if curFeature.featureType != PRIME_TOWER:
          #feature may cover two objects
          print(f"found prime tower end (start obj) {f.tell()} when current feature is {curFeature.featureType}")
          continue
        # otherwise, current feature is a prime tower
        curFeature.end = f.tell()
        print(f"found prime tower end at {curFeature.end}")
        if curFeature.toolchange: # only add prime tower to available prime tower list if it has a toolchange
          if printState.isPeriodicLine:
            printState.primeTowerFeatures.append(curFeature)
          else:
            printState.features.append(curFeature)
        else:
          printState.features.append(curFeature)
        curFeature = None
      '''

    #if reach end of file
    if not cl and curFeature:
      print(f"reached end of file at {f.tell()}")
      curFeature.end = f.tell()
      addFeatureToList(printState, curFeature)

def checkAndInsertToolchange(ps: PrintState, f: typing.TextIO, out: typing.TextIO, cl: str, toolchangeBareFile: str, pcs: list[PeriodicColor]) -> ToolchangeType:
  # Check if we are at toolchange insertion point. This point could be active when no more features are remaining and before any features are found (TC can be inserted after change_layer found)
  insertedToolchangeTypeAtCurrentPosition = ToolchangeType.NONE
  if f.tell() == ps.toolchangeInsertionPoint:
    # Write out the current line read that is before the toolchange insert. We will be inserting toolchange code after this line. Temporarily set skipWrite to true for this loop
    writeWithColorFilter(out, cl, loadedColors)
    #skipWrite = True

    # find the correct color for the toolchange
    nextFeatureColor, _ = determineNextFeaturePrintingColor(ps.features, -1, -1, False)
    printingToolchangeNewColorIndex = currentPrintingColorIndexForColorIndex(nextFeatureColor, loadedColors)

    # Check if full toolchange is available
    if len(ps.primeTowerFeatures) > 0:
      insertedToolchangeTypeAtCurrentPosition = ToolchangeType.FULL
      
      #insert toolchange full
      out.write(f"; MFPP Prime Tower and Toolchange (full) inserted to {nextFeatureColor} --replacement--> {printingToolchangeNewColorIndex}\n")

      # Skip write for toolchange
      skipWriteToolchange = False
      wipeStartFoundCount = 0

      # Seek to original prime tower and toolchange position. Write prime tower to output. Seek back to while loop reading position.
      nextAvailablePrimeTowerFeature = ps.primeTowerFeatures.pop(0)
      cp = f.tell()
      f.seek(nextAvailablePrimeTowerFeature.start, os.SEEK_SET)
      while f.tell() <= nextAvailablePrimeTowerFeature.end:
        cl = f.readline()

        if skipWriteToolchange:
          # End skip on WIPE_END
          wipeEndMatch = re.match(WIPE_END, cl)
          if wipeEndMatch:
            skipWriteToolchange = False

        if wipeStartFoundCount == 0:
          # Check to skip first WIPE_START section
          # Bambu first WIPE_START section has movement commands at previous feature after FEATURE tag
          wipeStartMatch = re.match(WIPE_START, cl)
          if wipeStartMatch:
            skipWriteToolchange = True
            wipeStartFoundCount += 1

        if skipWriteToolchange == False:
          cl = substituteNewColor(cl, nextFeatureColor)
          writeWithColorFilter(out, cl, loadedColors)
      f.seek(cp, os.SEEK_SET)

      print(f"added full toolchange {nextFeatureColor} --replacement--> {printingToolchangeNewColorIndex}")
    
    else:
      insertedToolchangeTypeAtCurrentPosition = ToolchangeType.MINIMAL
      #add minimal toolchange
      out.write(f"; MFPP Toolchange (minimal) inserted to {nextFeatureColor} --replacement--> {printingToolchangeNewColorIndex}\n")
      # normally we would replace the color with replacement color in writeWithColorFilter() but we are replacing multiple lines so this will write directly
      with open(toolchangeBareFile, mode='r') as tc_bare:
        tc_bare_code = tc_bare.read().replace('XX', str(printingToolchangeNewColorIndex))
        out.write(tc_bare_code)

      print(f"added minimal toolchange {nextFeatureColor} --replacement--> {printingToolchangeNewColorIndex}")
      
    ps.printingColor = printingToolchangeNewColorIndex
    ps.printingPeriodicColor = ps.printingColor == pcs[0].colorIndex if len(pcs) > 0 else False
    
    '''
    # Restore original position state before toolchange insert
    out.write("; MFPP Post-Toolchange Restore Positions and Prime\n")
    out.write(f"G0 X{currentPrint.originalPosition.X} Y{currentPrint.originalPosition.Y} Z{currentPrint.originalPosition.Z}\n")
    if extraPrimeGcode:
      out.write(f"{extraPrimeGcode}\n") #Extrude a bit for minimal toolchange
    out.write(f"G1 F{currentPrint.originalPosition.F}\n")
    '''

    ps.toolchangeInsertionPoint = 0 # clear toolchange insertion point
  return insertedToolchangeTypeAtCurrentPosition


# Get the actual processed printing color before next printing feature (our current code recoloring state+target color)
def determineBeforeNextFeaturePrintingColor(features: list[Feature], curFeatureIdx: int, lastPrintingColor: int, passedNonTCPrimeTowers: int) -> tuple[int, bool]:
  if curFeatureIdx > -1:
    curFeature = features[curFeatureIdx]
    if curFeature.printingColor > -1: # Only set if periodic feature
      lastPrintingColor = curFeature.printingColor
    # Do not check toolchange at end of current feature because we skip all toolchanges in features and insert our own
  if curFeatureIdx+1 < len(features): # If we have additional features after this
    nextFeature = features[curFeatureIdx+1]
    if nextFeature.featureType == PRIME_TOWER: # If next feature is non-toolchange prime tower, keep looking
      return lastPrintingColor, passedNonTCPrimeTowers+1
  return lastPrintingColor, passedNonTCPrimeTowers

# Get the target printing color of next printing feature (based on original code state and next feature target printing color (if set if periodic))
def determineNextFeaturePrintingColor(features: list[Feature], curFeatureIdx: int, lastPrintingColor: int, passedNonTCPrimeTowers: int) -> tuple[int, bool]:
  if curFeatureIdx+1 < len(features): # If we have additional features after this
    nextFeature = features[curFeatureIdx+1]
    if nextFeature.featureType == PRIME_TOWER: # If next feature is non-toolchange prime tower, keep looking
      return determineNextFeaturePrintingColor(features, curFeatureIdx+1, lastPrintingColor, passedNonTCPrimeTowers)
    else:
      lastPrintingColor = nextFeature.originalColor
      if nextFeature.printingColor > -1: # Check next feature target printing color (only set if periodic feature)
        lastPrintingColor = nextFeature.printingColor
  return lastPrintingColor, passedNonTCPrimeTowers

# Check if next layer needs a toolchange and the next toolchange color
def determineIfNextFeatureNeedsToolchange(ps: PrintState, cfi: int) -> tuple[bool, int, int] :
  # the active printing color before starting the next feature
  beforeNextFeaturePrintingColor, _ = determineBeforeNextFeaturePrintingColor(features=ps.features, curFeatureIdx=cfi, lastPrintingColor=ps.printingColor, passedNonTCPrimeTowers=0)
  # the correct target printing color for the next feature
  nextFeaturePrintingColor, passedNonTCPrimeTowers = determineNextFeaturePrintingColor(features=ps.features, curFeatureIdx=cfi, lastPrintingColor=-1, passedNonTCPrimeTowers=0)
  printingToolchangeNewColorIndex = currentPrintingColorIndexForColorIndex(nextFeaturePrintingColor, loadedColors)

  #debug breakpoints
  if ps.height == 0.6:
    0==0

  return beforeNextFeaturePrintingColor != printingToolchangeNewColorIndex, printingToolchangeNewColorIndex, passedNonTCPrimeTowers

# Update states for movment POSITION and TOOL
def updatePrintState(ps: PrintState, cl: int, sw: bool):
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
        ps.originalPosition.X = axisValue
      elif axis == 'Y':
        ps.originalPosition.Y = axisValue
      elif axis == 'Z':
        ps.originalPosition.Z = axisValue
      elif axis == 'E':
        ps.originalPosition.E = axisValue
      elif axis == 'F':
        ps.originalPosition.F = axisValue
      else:
        print(f"Unknown axis {axis} {axisValue} at {cl}")
      m += 2

  # look for toolchange T
  toolchangeMatch = re.match(TOOLCHANGE_T, cl)

  if ps.height == 1.4:
    0==0

  # Only update printstatus.originalcolor until we find the first layer. Toolchanges we find after wards are out of order due to rearranged features. We should use layerendoriginalcolor after first layer.
  if toolchangeMatch:
    print(f"found toolchange to {int(toolchangeMatch.groups()[0])}")
    if ps.height == -1:
      ps.originalColor = int(toolchangeMatch.groups()[0])
    if sw == False:
      ps.printingColor = ps.originalColor
      print(f"found printing color toolchange to {int(toolchangeMatch.groups()[0])}")

def substituteNewColor(cl, newColorIndex: int):
  cl = re.sub(M620, f"M620 S{newColorIndex}A", cl)
  cl = re.sub(TOOLCHANGE_T, f"T{newColorIndex}", cl)
  cl = re.sub(M621, f"M621 S{newColorIndex}A", cl)
  return cl

def startNewFeature(gf: str, ps: PrintState, f: typing.TextIO, out: typing.TextIO, cl: str, toolchangeBareFile: str, pcs: list[PeriodicColor], curFeature: Feature, curFeatureIdx: int):
  # remember if last line from last feature was supposed to be skipped
  prevFeatureSkip = False
  if ps.skipWrite:
    prevFeatureSkip = True

  #stop any skip write when starting new feature
  #print(f"End previous feature skip at feature {f.tell()}")
  ps.skipWrite = False

  insertedToolchangeTypeAtCurrentPosition = checkAndInsertToolchange(ps=ps, f=f, out=out, cl=cl, toolchangeBareFile=toolchangeBareFile, pcs=pcs)
  if insertedToolchangeTypeAtCurrentPosition == ToolchangeType.NONE and not prevFeatureSkip:
    writeWithColorFilter(out, cl, loadedColors) # write current line read in (before seek to new feature location) before we restore position
  ps.skipWriteForCurrentLine = True
  
  # Restore pre-feature position state before entering a new feature on periodic layer (but not if it is a prime tower on periodic line) or first feature on layer anywhere and prime if toolchange was inserted at start of feature.
  if (ps.isPeriodicLine == True and not (curFeature.featureType == PRIME_TOWER and curFeature.toolchange)) or curFeatureIdx == 0:
    out.write("; MFPP Pre-Feature Restore Positions\n")
    restoreCmd = "G0"
    try:
      getattr(curFeature.startPosition, "X")
      restoreCmd += f" X{curFeature.startPosition.X}"
      getattr(curFeature.startPosition, "Y")
      restoreCmd += f" Y{curFeature.startPosition.Y}"
      getattr(curFeature.startPosition, "Z")
      restoreCmd += f" Z{curFeature.startPosition.Z}"
      getattr(curFeature.startPosition, "F")
      restoreCmd += f" F{curFeature.startPosition.F}"
    except AttributeError as e:
      print(f"Restore position did not find axis {e} yet")
    if len(restoreCmd) > 2:
      out.write(f"{restoreCmd}\n")
    #out.write(f"G0 X{curFeature.startPosition.X} Y{curFeature.startPosition.Y} Z{curFeature.startPosition.Z} F{curFeature.startPosition.F}\n")
    extraPrimeGcode = None
    if insertedToolchangeTypeAtCurrentPosition == ToolchangeType.FULL:
      extraPrimeGcode = MINIMAL_TOOLCHANGE_PRIME
    elif insertedToolchangeTypeAtCurrentPosition == ToolchangeType.MINIMAL:
      extraPrimeGcode = FULL_TOOLCHANGE_PRIME
    elif gf == MARLIN_2_BAMBU_PRUSA_MARKED_GCODE:
      extraPrimeGcode = BAMBU_PRUSA_WIPE_END_PRIME
    if extraPrimeGcode:
      out.write(f"{extraPrimeGcode}\n") #Extrude a bit for minimal toolchange

  # All other processing below is for periodic
  if not ps.isPeriodicLine:
    return 
  
  # If current feature is the prime tower with toolchange. Do not write prime tower. Skip past this prime tower feature. We may find use for prime tower later. If prime tower does not have toolchange, do not skip it.
  if curFeature.featureType == PRIME_TOWER and curFeature.toolchange:
    print(f"Current feature is prime tower (with toolchange) and it is available for use/relocation. Skipping prime tower.")
    out.write("; MFPP Original Prime Tower skipped\n")
    curFeature.skipType = SkipType.PRIME_TOWER_FEATURE
    ps.skipWrite = True
    ps.skipWriteForCurrentLine = False #don't reset skipwrite at end of loop
    print(f"start Prime Tower skip {f.tell()}")
    return
  #If prime tower is not available for relocation, it should be in the printing features list and just written as usual

  # Check if next feature needs a toolchange. Don't check on last feature because we check for the first feature in next layer when we find next layer. We do not know target printing color of first feature on next layer yet. 
  if len(ps.features) > 0:
    
    nextFeatureNeedsToolchange, _, _ = determineIfNextFeatureNeedsToolchange(ps, -1)
    if nextFeatureNeedsToolchange: #if printing color before and printing color in next feature do not match, insert a toolchange at start of next feature (or at layer end if this is the last feature)
      ps.toolchangeInsertionPoint = ps.features[0].start

  # Check if this is the last feature and all available prime towers have not been used yet. Set toolchange insert to be at layer end
  if len(ps.features) == 0 and len(ps.primeTowerFeatures) > 0:
    print(f"On last feature and {len(ps.primeTowerFeatures)} available prime towers not used. Set toolchange insert at layer end {ps.layerEnd}")
    ps.toolchangeInsertionPoint = ps.layerEnd

  if ps.height == 0.6 and curFeatureIdx == 5:
    0==0

  # skip feature original toolchanges and WIPE_END () to end of feature
  curFeature.skipType = SkipType.FEATURE_ORIG_TOOLCHANGE_AND_WIPE_END


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
      # Persistent variables for the read loop
      
      # The current print state
      currentPrint: PrintState = PrintState()

      #Get total length of file
      f.seek(0, os.SEEK_END)
      lp = f.tell()
      f.seek(0, os.SEEK_SET)
      
      curFeatureIdx = -1
      curFeature = None

      # Current line buffer
      cl = True
      while cl:
        cl = f.readline()
        #clsp = f.tell() - len(cl) - (len(lineEnding)-1) # read line start position
        cp = f.tell() # position is start of next line after read line

        currentPrint.skipWriteForCurrentLine = False

        if f.tell() == 477411:
          #print(f.tell())
          0==0

        if f.tell() >= 479645:
          0==0

        # Update current print state variables
        updatePrintState(ps=currentPrint, cl=cl, sw=currentPrint.skipWrite)
      
        # if no more features left in stack, check for new layers
        # Look for start of a layer CHANGE_LAYER
        if len(currentPrint.features) == 0:
          cp = f.tell()

          if currentPrint.height == 2.0:
            0==0

          foundNewLayer = findChangeLayer(f,lastPrintState=currentPrint, gf=gcodeFlavor, pcs=periodicColors, rcs=replacementColors, le=lineEnding)
          if foundNewLayer:
            currentPrint = foundNewLayer
            curFeature = None
            curFeatureIdx = -1
            
            currentPrint.skipWrite = False

            # Check if toolchange needed for "next" feature which is index 0
            nextFeatureNeedsToolchange, _, passedNonTCPrimeTowers = determineIfNextFeatureNeedsToolchange(ps=currentPrint, cfi=-1)
            if nextFeatureNeedsToolchange: #if printing color before and printing color in next feature do not match, insert a toolchange at start of next feature (or at layer end if this is the last feature)
              if curFeatureIdx+passedNonTCPrimeTowers+1 < len(currentPrint.features):
                currentPrint.toolchangeInsertionPoint = currentPrint.features[curFeatureIdx+passedNonTCPrimeTowers+1].start
              else:
                currentPrint.toolchangeInsertionPoint = currentPrint.layerEnd

            item = StatusQueueItem()
            item.status = f"Current Height {currentPrint.height}"
            item.progress = cp/lp * 100
            statusQueue.put(item=item)
            # join to debug thread queue reading
            #statusQueue.join()

            
          f.seek(cp, os.SEEK_SET)
        else: # look for feature stop
          if cp in currentPrint.stopPositions: # find a stop position to "start" a new feature
            currentPrint.stopPositions.remove(cp)
            curFeature = currentPrint.features.pop(0)
            curFeatureIdx += 1

            #print(f"Starting feature index {curFeatureIdx} {curFeature.featureType} seek to position {curFeature.start}")

            f.seek(curFeature.start, os.SEEK_SET) # Seek to the start of top feature in the feature list
            startNewFeature(gcodeFlavor, currentPrint, f, out, cl, toolchangeBareFile, periodicColors, curFeature, curFeatureIdx)
        
        # Start skip if feature.toolchange is reached and we marked feature as needing original toolchange skipped
        if curFeature and curFeature.skipType == SkipType.FEATURE_ORIG_TOOLCHANGE_AND_WIPE_END:
          if curFeature.toolchange and f.tell() == curFeature.toolchange.start:
            #print(f"Current feature toolchange is redundant. Skipping feature toolchange. Start skip at {f.tell()}")
            out.write("; MFPP Original Feature Toolchange skipped\n")
            currentPrint.skipWrite = True
            #print(f"start feature toolchange skip ")

          if curFeature.wipeEnd and f.tell() == curFeature.wipeEnd.start and curFeature.featureType in WIPE_END_REMOVE_FEATURES:
            writeWithColorFilter(out, cl, loadedColors)
            #print(f"Skipping feature WIPE_END. Start skip at {f.tell()}")
            out.write(";WIPE_END placeholder for PrusaSlicer Gcode Viewer")
            out.write("; MFPP Original WIPE_END skipped\n")
            currentPrint.skipWrite = True

        # Write current line
        if currentPrint.skipWrite == False and currentPrint.skipWriteForCurrentLine == False: 
          #out.write(cl)
          writeWithColorFilter(out, cl, loadedColors)

        if currentPrint.skipWriteForCurrentLine == True:
          currentPrint.skipWrite = False
          currentPrint.skipWriteForCurrentLine = False

      item = StatusQueueItem()
      item.status = f"Completed at {currentPrint.height} height in {str(datetime.timedelta(seconds=time.monotonic()-startTime))}s"
      item.progress = 99.99
      statusQueue.put(item=item)
  except PermissionError as e:
    item = StatusQueueItem()
    item.status = f"Failed to open {e}"
    statusQueue.put(item=item)