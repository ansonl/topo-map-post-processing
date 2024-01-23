import re, os, typing, queue, time, datetime

# Gcode flavors
MARLIN_2_BAMBUSLICER_OLD = 'marlin2bambuslicer_old'
MARLIN_2_BAMBUSLICER_MARKED_GCODE = 'marlin2bambuslicer_markedtoolchangegcode'

# Universal Gcode Constants
UNIVERSAL_TOOLCHANGE_START = '^; MFPP TOOLCHANGE START'
UNIVERSAL_TOOLCHANGE_END = '^; MFPP TOOLCHANGE END'
UNIVERSAL_LAYER_CHANGE_END = '^; MFPP LAYER CHANGE END'

# Bambu Gcode Constants
STOP_OBJECT_BAMBUSTUDIO = '^; stop printing object, unique label id:\s(\d*)'
FEATURE_BAMBUSTUDIO = '^; FEATURE: (.*)'
PRIME_TOWER = 'Prime tower'
TOOLCHANGE_START = '^; CP TOOLCHANGE START'
# Toolchange (change_filament) start
G392 = '^G392 S(\d*)' #G392 only for A1
M620 = '^M620 S(\d*)A'
# Toolchange core movement actually starts after spiral lift up. Spiral lift is useful if doing prime tower only.
WIPE_SPIRAL_LIFT = '^G2 Z\d*\.?\d* I\d*\.?\d* J\d*\.?\d* P\d*\.?\d* F\d*\.?\d* ; spiral lift a little from second lift'
TOOLCHANGE_T = '^T(?!255$|1000$)(\d*)' # Do not match T255 or T1000 which are nonstandard by Bambu
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

'''
elevIsoline = PeriodicColor(colorIndex=2, startHeight=0.3, endHeight=10, height=0.5, period=1)
'''

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

'''
replacementColors: list[ReplacementColorAtHeight] = [
  ReplacementColorAtHeight(colorIndex=3, originalColorIndex=0, startHeight=8, endHeight=float('inf'))
]
'''

def createIsoline(modelToRealWorldDefaultUnits: float, modelOneToNVerticalScale: float, modelSeaLevelBaseThickness: float, realWorldIsolineElevationInterval: float, realWorldIsolineElevationStart: float, realWorldIsolineElevationEnd: float, modelIsolineHeight: float, colorIndex: int):
  return PeriodicColor(colorIndex=colorIndex, startHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldIsolineElevationStart/modelOneToNVerticalScale, endHeight=modelToRealWorldDefaultUnits*realWorldIsolineElevationEnd/modelOneToNVerticalScale, height=modelIsolineHeight, period=modelToRealWorldDefaultUnits*realWorldIsolineElevationInterval/modelOneToNVerticalScale)

def createReplacementColor(modelToRealWorldDefaultUnits: float, modelOneToNVerticalScale: float, modelSeaLevelBaseThickness: float, realWorldElevationStart: float, realWorldElevationEnd: float, colorIndex: int, originalColorIndex: int):
  return ReplacementColorAtHeight(colorIndex=colorIndex, originalColorIndex=originalColorIndex, startHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldElevationStart/modelOneToNVerticalScale, endHeight=modelSeaLevelBaseThickness + modelToRealWorldDefaultUnits*realWorldElevationEnd/modelOneToNVerticalScale)

def shouldLayerBePeriodicLine(printState: PrintState, periodicLine: PeriodicColor):
  if printState.height >= periodicLine.startHeight and printState.height <= periodicLine.endHeight:
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

def updateReplacementColors(printState: PrintState, rcs: list[ReplacementColorAtHeight]):
  for rc in rcs:
    if printState.height > rc.startHeight and printState.height - printState.layerHeight < rc.endHeight:
      loadedColors[rc.originalColorIndex].replacementColorIndex = rc.colorIndex
    elif loadedColors[rc.originalColorIndex].replacementColorIndex == rc.colorIndex:
      loadedColors[rc.originalColorIndex].replacementColorIndex = -1

def findChangeLayer(f, lastPrintState: PrintState, gf: str, pcs: list[PeriodicColor], rcs: list[ReplacementColorAtHeight]):
  cl = f.readline()
  # Look for start of layer
  changeLayerMatchBambu = re.match(CHANGE_LAYER_BAMBUSTUDIO, cl)
  changeLayerMatchPrusa = re.match(CHANGE_LAYER_PRUSASLICER, cl)
  if changeLayerMatchBambu or changeLayerMatchPrusa:
    # Create new print state for the new found layer and carry over some state that should be preserved between layers.
    printState = PrintState()
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
    print(f"pos {f.tell()} before call findLayerFeaturePrimeTower")

    cp = f.tell()  
    printState.primeTower = findLayerFeaturePrimeTower(f, gf)
    f.seek(cp, os.SEEK_SET)
    insertionPoint = findToolchangeInsertionPoint(f, gf)
    f.seek(cp, os.SEEK_SET)

    if insertionPoint == None:
      print(f"Failed to find toolchange insertion point at layer Z_HEIGHT {printState.height}")

    isPeriodicLine = shouldLayerBePeriodicLine(printState, pcs[0]) if len(pcs) > 0 else False
    print(f"Is printing periodic color {printState.printingPeriodicColor}")
    print(f"Is periodic line {isPeriodicLine}")

    # Check if we need to switch to/from periodic color
    if printState.printingPeriodicColor == True and isPeriodicLine == True:
      # already periodic color, stay on periodic color
      # skip toolchange part on this layer. Do prime tower as usual.
      printState.skipOriginalToolchangeOnLayer = True

    elif printState.printingPeriodicColor ^ isPeriodicLine:
      # Previously no periodic color, new toolchange to periodic color
      if printState.printingPeriodicColor == False:
        # new inserted toolchange is isoline color
        printState.toolchangeNewColorIndex = pcs[0].colorIndex
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
          # if no prime block (and no toolchange), switch toolhead, no prime block. Do toolchange after M991. If toolchange did exist but no prime block, skip original toolchange.
          printState.toolchangeBareInsertionPoint = insertionPoint
          # If only toolchange exists and no prime tower was found. Skip the toolchange
          if printState.primeTower and printState.primeTower.toolchange and printState.primeTower.toolchange.start:
            printState.skipOriginalToolchangeOnLayer = True

      # Previously printing periodic color, new toolchange to original color
      else:
        # new inserted toolchange is original color
        # Check if original color has current replacement color loaded. Use original color or replacement color for toolchange new color index
        printState.toolchangeNewColorIndex = printState.originalColor if loadedColors[printState.printingColor].replacementColorIndex == -1 else loadedColors[printState.printingColor].replacementColorIndex
        # check for toolchange on this layer
        if printState.primeTower and printState.primeTower.start:
          # if toolchange exist, switch toolhead, no prime block. Do toolchange after STOPOBJ and M991
          # OR
          # if no toolchange exist on this layer and there is prime block, switch toolhead, do the prime block now and delete from later. Do toolchange after STOPOBJ and M991 (before START). Assume the prime block printing already happens after M991 so it is already in the correct place after inserting toolchange.
          printState.toolchangeBareInsertionPoint = insertionPoint
        else:
        # if no prime block (and no toolchange), switch toolhead, no prime block. Do toolchange after M991. If toolchange did exist but no prime block, same thing.
          printState.toolchangeBareInsertionPoint = insertionPoint
    
    # If we are not printing periodicColor on previous layer and current layer is not periodic color. 
    elif printState.printingPeriodicColor == False and isPeriodicLine == False:
      # Check if original active color at this point (at layer start) has a replacement color
      if loadedColors[printState.originalColor].replacementColorIndex != -1:
        # Insert toolchange (bare) at layer start to the original color's replacement color
        printState.toolchangeNewColorIndex = loadedColors[printState.originalColor].replacementColorIndex
        printState.toolchangeBareInsertionPoint = insertionPoint
  
    return printState
  return None

def findLayerFeaturePrimeTower(f: typing.TextIO, gf: str):
  primeTower = Feature()
  if gf == MARLIN_2_BAMBUSLICER_MARKED_GCODE:
    cl = True
    while cl:
      cl = f.readline()
      changeLayerMatchBambu = re.match(CHANGE_LAYER_BAMBUSTUDIO, cl)
      changeLayerMatchPrusa = re.match(CHANGE_LAYER_PRUSASLICER, cl)
      stopObjMatchBambu = re.match(STOP_OBJECT_BAMBUSTUDIO, cl)
      stopObjMatchPrusa = re.match(STOP_OBJECT_PRUSASLICER, cl)
      featureMatchBambu = re.match(FEATURE_BAMBUSTUDIO, cl)
      featureMatchPrusa = re.match(FEATURE_PRUSASLICER, cl)
      univeralToolchangeStartMatch = re.match(UNIVERSAL_TOOLCHANGE_START, cl)
      univeralToolchangeEndMatch = re.match(UNIVERSAL_TOOLCHANGE_END, cl)
      startObjMatchBambu = re.match(START_OBJECT_BAMBUSTUDIO, cl)
      startObjMatchPrusa = re.match(START_OBJECT_PRUSASLICER, cl)

      if changeLayerMatchBambu or changeLayerMatchPrusa:
        print('got new layer at ',f.tell(),'before prime tower')
        if primeTower.toolchange and primeTower.toolchange.start and primeTower.toolchange.end:
          print(f'found toolchange in this layer at {primeTower.toolchange.start}-{primeTower.toolchange.end} so will return primeTower obj with toolchange filled out')
          return primeTower
        return None
      
      #if cl.startswith("; stop printing object"):
      #  print(f"{stopObjMatchPrusa}")
      #  print(f"found stop at {f.tell()}")

      # Find prime tower start or toolchange start
      if stopObjMatchBambu or stopObjMatchPrusa:
        primeTower.start = f.tell()
        primeTower.featureType = None
        print(f"found stop at {f.tell()}")
      # toolchange starts at UNIVERSAL_TOOLCHANGE_START
      elif univeralToolchangeStartMatch: 
        primeTower.toolchange = Feature()
        primeTower.toolchange.featureType = 'Toolchange'
        primeTower.toolchange.start = f.tell() - len(cl)
        print(f"found toolchange start at {primeTower.toolchange.start}")
      # Keep looking if primetower or toolchange start have not been found
      elif primeTower.start == 0 and (primeTower.toolchange == None or primeTower.toolchange.start == 0):
        continue

      # Look for FEATURE to validate we actually found the prime tower earlier
      elif primeTower.start and primeTower.featureType == None: # Look for FEATURE tag
        if featureMatchBambu or featureMatchPrusa:
          print(f"found feature match at {f.tell()}")
          if featureMatchBambu and featureMatchBambu.groups()[0] == PRIME_TOWER:
            primeTower.featureType = PRIME_TOWER
          elif featureMatchPrusa and featureMatchPrusa.groups()[0] == WIPE_TOWER:
            print(f"feature match prusa at {f.tell()}")
            primeTower.featureType = PRIME_TOWER
          else:
            primeTower.start = 0
        else:
          continue

      # Look for UNIVERSAL_TOOLCHANGE_END if we already found the toolchange start
      elif univeralToolchangeEndMatch and primeTower.toolchange and primeTower.toolchange.start:
        primeTower.toolchange.end = f.tell()
        print(f"found toolchange end at {primeTower.toolchange.end}")
      # Look for prime tower end
      elif (startObjMatchBambu or startObjMatchPrusa) and primeTower.start:
          primeTower.end = f.tell() - len(cl)
          break
    return primeTower
  '''
  else:
    cl = True
    while cl:
      cl = f.readline()
      changeLayerMatch = re.match(CHANGE_LAYER, cl)
      stopObjMatch = re.match(STOP_OBJECT, cl)
      featureMatch = re.match(FEATURE, cl)
      toolchangeStartMatch = re.match(TOOLCHANGE_START, cl)
      g392Match = re.match(G392, cl)
      m620Match = re.match(M620, cl)
      wipeSpiralLiftMatch = re.match(WIPE_SPIRAL_LIFT, cl)
      m621Match = re.match(M621, cl)
      startObjMatch = re.match(START_OBJECT, cl)

      if changeLayerMatch:
        print('got new layer at ',f.tell(),'before prime tower')
        return None

      # Find prime tower start or toolchange start
      if stopObjMatch:
        primeTower.start = f.tell()
        primeTower.featureType = None
      # toolchange starts at TOOLCHANGE_START or before M620 (prefer in order TOOLCHANGE_START, G392, M620)
      elif toolchangeStartMatch: 
        primeTower.toolchange = Feature()
        primeTower.toolchange.featureType = 'Toolchange'
        primeTower.toolchange.start = f.tell()
      elif g392Match and (primeTower.toolchange == None or primeTower.toolchange.start == 0): 
        primeTower.toolchange = Feature()
        primeTower.toolchange.featureType = 'Toolchange'
        primeTower.toolchange.start = f.tell() - len(cl)
      elif m620Match and (primeTower.toolchange == None or primeTower.toolchange.start == 0): 
        primeTower.toolchange = Feature()
        primeTower.toolchange.featureType = 'Toolchange'
        primeTower.toolchange.start = f.tell() - len(cl)

      # Keep looking if primetower or toolchange start have not been found
      elif primeTower.start == 0 and (primeTower.toolchange == None or primeTower.toolchange.start == 0):
        continue

      # Look for FEATURE to validate we actually found the prime tower earlier
      elif primeTower.start and primeTower.featureType == None: # Look for FEATURE tag
        if featureMatch:
          if featureMatch.groups()[0] == PRIME_TOWER:
            primeTower.featureType = featureMatch.groups()[0]
          else:
            primeTower.start = 0
        else:
          continue

      # Look for toolchange end if we already found the toolchange start
      elif m621Match and primeTower.toolchange and primeTower.toolchange.start:
        primeTower.toolchange.end = f.tell()
      # Look for prime tower end
      elif startObjMatch and primeTower.start:
          primeTower.end = f.tell() - len(cl)
          break
    return primeTower

      #elif wipeSpiralLiftMatch:
      #  primeTower.toolchange.start = f.tell()
      # toolchange ends after M621
  '''
   
  
def findToolchangeInsertionPoint(f: typing.TextIO, gf: str):
  insertionPoint = Feature()
  if gf == MARLIN_2_BAMBUSLICER_MARKED_GCODE:
    insertionPoint.featureType = UNIVERSAL_LAYER_CHANGE_END
    cl = True
    while cl:
      cl = f.readline()
      universalLayerChangeEndMatch = re.match(UNIVERSAL_LAYER_CHANGE_END, cl)
      changeLayerMatchBambu = re.match(CHANGE_LAYER_BAMBUSTUDIO, cl)
      changeLayerMatchPrusa = re.match(CHANGE_LAYER_PRUSASLICER, cl)
      featureMatchBambu = re.match(FEATURE_BAMBUSTUDIO, cl)
      featureMatchPrusa = re.match(FEATURE_PRUSASLICER, cl)
      if universalLayerChangeEndMatch:
        insertionPoint.start = f.tell()
        break
      elif changeLayerMatchBambu or changeLayerMatchPrusa:
        return None
      elif featureMatchBambu or featureMatchPrusa:
        return None
    return insertionPoint
  '''
  else:
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
  '''

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

def process(gcodeFlavor: str, inputFile: str, outputFile: str, toolchangeBareFile: str, periodicColors: list[PeriodicColor], replacementColors:list[ReplacementColorAtHeight], statusQueue: queue.Queue):
  startTime = time.monotonic()
  try:
    with open(inputFile, mode='r') as f, open(outputFile, mode='w') as out:
      currentPrint: PrintState = PrintState()

      #Get total length of file
      f.seek(0, os.SEEK_END)
      lp = f.tell()
      f.seek(0, os.SEEK_SET)

      # Don't write to output
      skipWrite = False

      # Current line buffer
      cl = True
      while cl:
        # Look for start of a layer CHANGE_LAYER
        cp = f.tell()
        foundNewLayer = findChangeLayer(f,lastPrintState=currentPrint, gf=gcodeFlavor, pcs=periodicColors, rcs=replacementColors)
        if foundNewLayer:
          currentPrint = foundNewLayer
          print(f"toolchangeNewColorIndex {currentPrint.toolchangeNewColorIndex}")
          print(f"skipOriginalPrimeTowerAndToolchangeOnLayer {currentPrint.skipOriginalPrimeTowerAndToolchangeOnLayer}")
          print(f"skipOriginalToolchangeOnLayer {currentPrint.skipOriginalToolchangeOnLayer}")
          if currentPrint.primeTower:
            print(f"primetower.start {currentPrint.primeTower.start}")
            print(f"primetower.end {currentPrint.primeTower.end}")
          item = StatusQueueItem()
          item.status = f"Current Height {currentPrint.height}"
          item.progress = cp/lp * 100
          statusQueue.put(item=item)
          # join to debug thread queue reading
          #statusQueue.join()
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
            print(f"start skip {f.tell()}")
            skipWrite = True
            out.write("; MFPP Original Prime Tower and Toolchange skipped\n")
          #if currentPrint.height == 6.4 and f.tell() < currentPrint.primeTower.end and f.tell() > currentPrint.primeTower.start:
          #  print(f.tell())
          if f.tell() == currentPrint.primeTower.end:
            if skipWrite:
              print(f"end skip at {f.tell()} {currentPrint.primeTower.end}")
            skipWrite = False
        
        # Indicate current layer should skip the original toolchange found AND this layer's prime tower has a tool change section to skip
        if currentPrint.skipOriginalToolchangeOnLayer and currentPrint.primeTower and currentPrint.primeTower.toolchange:
          if f.tell() == currentPrint.primeTower.toolchange.start:
            print(f"start skip {f.tell()}")
            skipWrite = True
            out.write("; MFPP Original Toolchange skipped\n")
          if f.tell() == currentPrint.primeTower.toolchange.end:
            if skipWrite:
              print(f"end skip at {f.tell()} {currentPrint.primeTower.toolchange.end}")
            skipWrite = False

        if skipWrite == False:
          #out.write(cl)
          #print(f"test2{cp}")
          writeWithColorFilter(out, cl, loadedColors)

        # Toolchange insertion after the current line is read and written to output
        if currentPrint.toolchangeBareInsertionPoint:
          if f.tell() == currentPrint.toolchangeBareInsertionPoint.start:
            #insert toolchare bare
            printingToolchangeNewColorIndex = currentPrintingColorIndexForColorIndex(currentPrint.toolchangeNewColorIndex, loadedColors)
            out.write(f"; MFPP Toolchange (minimal) inserted to {currentPrint.toolchangeNewColorIndex} --replacement--> {printingToolchangeNewColorIndex}\n")
            # normally we would replace the color with replacement color in writeWithColorFilter() but we are replacing multiple lines so this will write directly
            with open(toolchangeBareFile, mode='r') as tc_bare:
              tc_bare_code = tc_bare.read().replace('XX', str(printingToolchangeNewColorIndex))
              out.write(tc_bare_code)
            currentPrint.printingColor = printingToolchangeNewColorIndex
            currentPrint.printingPeriodicColor = currentPrint.printingColor == periodicColors[0].colorIndex if len(periodicColors) > 0 else False
        
        if currentPrint.toolchangeFullInsertionPoint:
          if f.tell() == currentPrint.toolchangeFullInsertionPoint.start:
            #insert toolchange full
            printingToolchangeNewColorIndex = currentPrintingColorIndexForColorIndex(currentPrint.toolchangeNewColorIndex, loadedColors)
            out.write(f"; MFPP Prime Tower and Toolchange (full) inserted to {currentPrint.toolchangeNewColorIndex} --replacement--> {printingToolchangeNewColorIndex}\n")

            # Seek to original prime tower and toolchange position. Write prime tower to output. Seek back to while loop reading position.
            cp = f.tell()
            f.seek(currentPrint.primeTower.start, os.SEEK_SET)
            #print(f"test3{cp} {currentPrint.primeTower.start} {currentPrint.primeTower.end}")
            while f.tell() <= currentPrint.primeTower.end:
              #print(f"test4 {cp} {f.tell()} {currentPrint.primeTower.start} {currentPrint.primeTower.end}")
              cl = f.readline()
              #print(f"test5 {cp} {f.tell()} {currentPrint.primeTower.start} {currentPrint.primeTower.end}")
              cl = substituteNewColor(cl, currentPrint.toolchangeNewColorIndex)
              #out.write(cl)
              #print(f"test{cp}")
              writeWithColorFilter(out, cl, loadedColors)
            f.seek(cp, os.SEEK_SET)
            currentPrint.printingColor = currentPrint.toolchangeNewColorIndex
            currentPrint.printingPeriodicColor = currentPrint.printingColor == periodicColors[0].colorIndex if len(periodicColors) > 0 else False

      item = StatusQueueItem()
      item.status = f"Completed at {currentPrint.height} height in {str(datetime.timedelta(seconds=time.monotonic()-startTime))}s"
      item.progress = 99.99
      statusQueue.put(item=item)
  except PermissionError as e:
    item = StatusQueueItem()
    item.status = f"Failed to open {e}"
    statusQueue.put(item=item)