import re, os, typing, queue, time, datetime, math, enum, copy

from .app_constants import *
from .printing_constants import *
from .printing_classes import *
from .line_ending import *
from .configuration import *

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
  changeLayerMatch = re.match(LAYER_CHANGE, cl)
  if changeLayerMatch:
    # Create new print state for the new found layer and carry over some state that should be preserved between layers.
    printState = PrintState()
    printState.previousLayerHeight = lastPrintState.layerHeight
    printState.originalColor = lastPrintState.layerEndOriginalColor if lastPrintState.layerEndOriginalColor > -1 else lastPrintState.originalColor
    printState.printingColor = lastPrintState.printingColor
    printState.printingPeriodicColor = lastPrintState.printingPeriodicColor
    printState.layerStart = f.tell()

    printState.prevLayerLastFeature = lastPrintState.lastFeature
    printState.featureWipeEndPrime = lastPrintState.featureWipeEndPrime

    # Find Z_HEIGHT value
    cl = f.readline()
    zHeightMatch = re.match(LAYER_Z_HEIGHT, cl)
    if zHeightMatch:
      if zHeightMatch:
        printState.height = float(zHeightMatch.groups()[0])
        #print(f"{Z_HEIGHT} {cl.groups()[0]}")
      print(f"\nProcessing height {printState.height}")

    # Find LAYER_HEIGHT value
    cl = f.readline()
    layerHeightMatch = re.match(LAYER_HEIGHT, cl)
    if layerHeightMatch:
      if layerHeightMatch:
        printState.layerHeight = float(layerHeightMatch.groups()[0])

    #update loaded colors replacement color data based on current height
    updateReplacementColors(printState, rcs)
    print(f"pos {f.tell()} before call findLayerFeatures")

    # determine periodic line status
    printState.isPeriodicLine = shouldLayerBePeriodicLine(printState, pcs[0]) if len(pcs) > 0 else False
    print(f"Is printing periodic color {printState.printingPeriodicColor}")
    print(f"Is periodic line {printState.isPeriodicLine}")
    
    return printState
  return None

def findLayerFeatures(f: typing.TextIO, gf: str, printState: PrintState, pcs: list[PeriodicColor], le: str):
  if gf == MARLIN_2_BAMBU_PRUSA_MARKED_GCODE:
    cl = True
    curFeature = None
    curStartPosition = printState.originalPosition #last position before entering feature
    curOriginalColor = printState.originalColor # original color at start of layer

    def addFeatureToList(ps: PrintState, cf: Feature):
      if cf.featureType == PRIME_TOWER and cf.toolchange: # only add prime tower to available prime tower list if it has a toolchange
        if ps.isPeriodicLine:
          ps.primeTowerFeatures.append(cf)
        else:
          ps.features.append(cf)
      else:
        ps.features.append(cf)

    # Enable after lookahead if a feature spans a layer change
    useFirstSpecialGcodeAsFeature = None

    while cl:
      cl = f.readline()
      # next layer marker
      changeLayerMatch = re.match(LAYER_CHANGE, cl)

      # end of layer_change
      layerChangeEndMatch = re.match(UNIVERSAL_LAYER_CHANGE_END, cl)

      # start marker for non prime tower features
      featureTypeMatch = re.match(FEATURE_TYPE, cl)

      # FILAMENT_END_GCODE signals TC after layer_change or M204 S signals start of printing moves after layer_change. FILAMENT_END_GCODE comes before the early toolchange start. M204 S may come on line before FEATURE if FEATURE exists at start
      specialGcodeMatch = None
      if useFirstSpecialGcodeAsFeature:
        specialGcodeMatch = re.match(useFirstSpecialGcodeAsFeature, cl)

      # toolchange start/end and index
      univeralToolchangeStartMatch = re.match(UNIVERSAL_TOOLCHANGE_START, cl)
      toolchangeMatch = re.match(TOOLCHANGE_T, cl)
      univeralToolchangeEndMatch = re.match(UNIVERSAL_TOOLCHANGE_END, cl)

      # wipe_end marker for normal printing features to skip
      wipeEndMatch = re.match(WIPE_END, cl)

      #Debug
      if f.tell() == 155194:
        0==0

      # end if we find next layer marker
      if changeLayerMatch:
        printState.layerEnd = f.tell() - len(cl) - (len(le)-1)
        #print('got new layer at ',f.tell())
        curFeature.end = f.tell() - len(cl) - (len(le)-1)
        addFeatureToList(printState, curFeature)
        curFeature = None
        printState.layerEndOriginalColor = curOriginalColor
        break
      
      checkAndUpdatePosition(cl=cl, pp=curStartPosition)

      # If UNIVERSAL LAYER CHANGE END found first, look ahead to see if a new feature is the first thing on this layer or previous feature is continued.
      if len(printState.features) == 0 and layerChangeEndMatch:
        cp = f.tell()
        lookaheadLines = 200
        foundFeatureInLookahead = False
        i = 0
        fl = True
        while fl:
          fl = f.readline()
          i += 1
          if re.match(FEATURE_TYPE, fl):
            foundFeatureInLookahead = True
            print(f'found feature during lookahead line distance {i} {f.tell()}')
            break
          if re.match(M204, fl): #secondary check for M204 S to look for continued feature
            print(f'found M204 S during lookahead line distance {i} {f.tell()}')
            fl = f.readline()
            # If no FEATURE found right after M204, treat M204 as the first feature
            if re.match(FEATURE_TYPE, fl):
              foundFeatureInLookahead = True
              print(f'found feature after M204 S during lookahead line distance {i} {f.tell()}')
              break
            else:
              useFirstSpecialGcodeAsFeature = M204
            break
          if re.match(FILAMENT_END_GCODE, fl):
            print(f'found FILAMENT_END_GCODE during lookahead line distance {i} {f.tell()}')
            useFirstSpecialGcodeAsFeature = FILAMENT_END_GCODE
            break
          if re.match(LINE_WIDTH, fl):
            print(f'found LINE_WIDTH during lookahead line distance {i} {f.tell()}')
            useFirstSpecialGcodeAsFeature = LINE_WIDTH
            break
          if re.match(LAYER_CHANGE, fl):
            #No feature found before next layer!
            break
        f.seek(cp, os.SEEK_SET)
        if foundFeatureInLookahead or useFirstSpecialGcodeAsFeature:
          # a new feature is found soon so continue looking for features like normal
          # a line width tag was found so look for line width tag as if it is a feature tag
          continue
        else:
          print(f'Found no feature or M204 tag in lookahead of {lookaheadLines} at start of layer at {f.tell()}')
          break

      # Look for FEATURE to find feature type
      if featureTypeMatch or (len(printState.features) == 0 and useFirstSpecialGcodeAsFeature and specialGcodeMatch):
        print(f"found FEATURE match {featureTypeMatch.groups()[0] if featureTypeMatch else 'None'} at {f.tell() - len(cl) - (len(le)-1)}")

        # Don't end prime tower if we found prime tower feature for Bambu
        if curFeature and curFeature.featureType == PRIME_TOWER and featureTypeMatch and (featureTypeMatch.groups()[0] == PRIME_TOWER or featureTypeMatch.groups()[0] == WIPE_TOWER):
          continue

        if curFeature:
          curFeature.end = f.tell() - len(cl) - (len(le)-1)
          addFeatureToList(printState, curFeature)
          curFeature = None

        # Create new feature 
        if curFeature == None:
          curFeature = Feature()
          curFeature.start = f.tell() - len(cl) - (len(le)-1)
          curFeature.startPosition = copy.copy(curStartPosition) # save last position state as start position for this feature
          curFeature.originalColor = curOriginalColor # save current original color as color for this feature
        if featureTypeMatch:
          curFeature.featureType = featureTypeMatch.groups()[0]
          if featureTypeMatch.groups()[0] == WIPE_TOWER: #Rename wipe tower to prime tower
            curFeature.featureType = PRIME_TOWER
        # If not a feature Type Match, try to see if line width matches
        elif specialGcodeMatch:
          useFirstSpecialGcodeAsFeature = False
          if printState.prevLayerLastFeature:
            curFeature.featureType = printState.prevLayerLastFeature.featureType
            printState.prevLayerLastFeature = None # clear reference to prev layer last feature
          else:
            curFeature.featureType = UNKNOWN_CONTINUED

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
          print(f"toolchange end found before toolchange start at {f.tell()} set .end to {f.tell() - len(cl) - (len(le)-1)}")
          1==0 # assert crash
          break
        curFeature.toolchange.end = f.tell() - len(cl) - (len(le)-1)
        #print(f"found toolchange end at {curFeature.toolchange.end}")
        continue

      # Look for wipe_end on normal features. Overwrite previous found wipe end with last wipe end
      if wipeEndMatch:
          curFeature.wipeEnd = Feature()
          curFeature.wipeEnd.featureType = WIPE_END
          curFeature.wipeEnd.start = f.tell() - len(cl) - (len(le)-1)

    #if reach end of file
    if not cl and curFeature:
      print(f"reached end of file at {f.tell()}")
      curFeature.end = f.tell()
      addFeatureToList(printState, curFeature)

def reorderFeatures(ps: PrintState):
  #Debug breakpoint before layer feature cataloging
  if ps.height == 12.0:
    0==0

  #rearrange features
  if ps.isPeriodicLine:
    insertIdx = 0
    featureIdx = 0
    while featureIdx < len(ps.features):
      if ps.features[featureIdx].isPeriodicColor:
        if insertIdx != featureIdx:
          ps.features.insert(insertIdx, ps.features.pop(featureIdx))
        insertIdx += 1
      featureIdx += 1

  for feat in ps.features:
    ps.stopPositions.append(feat.start)
  for feat in ps.primeTowerFeatures:
    ps.stopPositions.append(feat.start)
  ps.stopPositions.append(ps.layerEnd) #add layer end as a stop position

  print(f"{len(ps.features)} printing features and {len(ps.primeTowerFeatures)} reusable prime towers found")

  
  #print rearranged features
  print(f"{len(ps.features)} printing features found")
  fi = 0
  for feat in ps.features:
    print(f"{fi} {feat.featureType} start: {feat.start} end: {feat.end} originalcolor: {feat.originalColor} isPeriodicColor:{feat.isPeriodicColor} printingColor:{feat.printingColor}")
    if feat.toolchange:
      print(f"toolchange.start: {feat.toolchange.start} end: {feat.toolchange.end} printingColor:{feat.toolchange.printingColor}")
    if feat.wipeEnd:
      print(f"wipeEnd.start: {feat.wipeEnd.start}")
    fi += 1

  #print prime tower features (only filled when periodic layer)
  print(f"{len(ps.primeTowerFeatures)} prime tower features found")
  for feat in ps.primeTowerFeatures:
    print(f"{feat.featureType} start: {feat.start} end: {feat.end} originalcolor: {feat.originalColor} isPeriodicColor:{feat.isPeriodicColor} printingColor:{feat.printingColor}")
    if feat.toolchange:
      print(f"toolchange.start: {feat.toolchange.start} end: {feat.toolchange.end} printingColor:{feat.toolchange.printingColor}")
    if feat.wipeEnd:
      print(f"wipeEnd.start: {feat.wipeEnd.start}")
  
  #Debug breakpoint after layer feature cataloging
  if ps.height == 7.8:
    0==0

def checkAndInsertToolchange(ps: PrintState, f: typing.TextIO, out: typing.TextIO, cl: str, toolchangeBareFile: str, pcs: list[PeriodicColor]) -> ToolchangeType:
  # Check if we are at toolchange insertion point. This point could be active when no more features are remaining and before any features are found (TC can be inserted after change_layer found)
  insertedToolchangeTypeAtCurrentPosition = ToolchangeType.NONE
  if f.tell() == ps.toolchangeInsertionPoint:
    # Write out the current line read that is before the toolchange insert. We will be inserting toolchange code after this line. Temporarily set skipWrite to true for this loop
    writeWithFilters(out, cl, loadedColors)
    #skipWrite = True

    # find the correct color for the toolchange
    nextFeatureColor, _ = determineNextFeaturePrintingColor(ps.features, -1, -1, False)
    printingToolchangeNewColorIndex = currentPrintingColorIndexForColorIndex(nextFeatureColor, loadedColors)

    # Check if full toolchange is available
    if len(ps.primeTowerFeatures) > 0:
      insertedToolchangeTypeAtCurrentPosition = ToolchangeType.FULL
      
      #insert toolchange full
      out.write(f"; MFM Prime Tower and Toolchange (full) inserted to {nextFeatureColor} --replacement--> {printingToolchangeNewColorIndex}\n")

      # Skip write for toolchange
      skipWriteToolchange = False
      wipeStartFoundCount = 0

      # Seek to original prime tower and toolchange position. Write prime tower to output. Seek back to while loop reading position.
      nextAvailablePrimeTowerFeature = ps.primeTowerFeatures.pop(0)
      cp = f.tell()
      f.seek(nextAvailablePrimeTowerFeature.start, os.SEEK_SET)
      # We check if the position is != instead of <= because readline() with the next line being empty meaning it looks like double line endings leads to high tell() values that do not make sense but still seek to the correct position anyways.
      while f.tell() != nextAvailablePrimeTowerFeature.end:
        cl = f.readline()

        if f.tell() == 155194:
          0==0

        # Skip WIPE_END of the nserted prime tower
        if nextAvailablePrimeTowerFeature.wipeEnd and f.tell() == nextAvailablePrimeTowerFeature.wipeEnd.start:
          writeWithFilters(out, cl, loadedColors)
          out.write(";WIPE_END placeholder for PrusaSlicer Gcode Viewer\n")
          out.write("; WIPE_END placeholder for BambuStudio Gcode Preview\n")
          out.write("; MFM Original WIPE_END skipped for inserted Prime Tower\n")
          skipWriteToolchange = True

        if skipWriteToolchange == False:
          cl = substituteNewColor(cl, nextFeatureColor)
          writeWithFilters(out, cl, loadedColors)
      f.seek(cp, os.SEEK_SET)

      print(f"added full toolchange {nextFeatureColor} --replacement--> {printingToolchangeNewColorIndex}")
    
    else:
      insertedToolchangeTypeAtCurrentPosition = ToolchangeType.MINIMAL
      #add minimal toolchange
      out.write(f"; MFM Toolchange (minimal) inserted to {nextFeatureColor} --replacement--> {printingToolchangeNewColorIndex}\n")
      # normally we would replace the color with replacement color in writeWithColorFilter() but we are replacing multiple lines so this will write directly
      with open(toolchangeBareFile, mode='r') as tc_bare:
        tc_bare_code = tc_bare.read().replace('XX', str(printingToolchangeNewColorIndex))
        out.write(tc_bare_code)

      print(f"added minimal toolchange {nextFeatureColor} --replacement--> {printingToolchangeNewColorIndex}")
      
    ps.printingColor = printingToolchangeNewColorIndex
    ps.printingPeriodicColor = ps.printingColor == pcs[0].colorIndex if len(pcs) > 0 else False

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

# Update position state
def checkAndUpdatePosition(cl: str, pp: Position):
  # look for movement gcode and record last position before entering a feature
  movementMatch = re.match(MOVEMENT_G, cl)
  if movementMatch:
    m = 0
    travelMove = True
    while m+1 < len(movementMatch.groups()):
      if movementMatch.groups()[m] == None:
        break
      axis = str(movementMatch.groups()[m])
      axisValue = float(movementMatch.groups()[m+1])
      m += 2
      if axis == 'X':
        pp.X = axisValue
      elif axis == 'Y':
        pp.Y = axisValue
      elif axis == 'Z':
        pp.Z = axisValue
      elif axis == 'I' or axis == 'J' or axis == 'P' or axis == 'R':
        continue
      elif axis == 'E':
        pp.E = axisValue
        travelMove = False
      elif axis == 'F':
        pp.F = axisValue
      else:
        print(f"Unknown movement/feedrate axis {axis} {axisValue} for input {cl}")
      
    # If this move did not have extrusion, save the Feedrate as last travel speed
    if travelMove:
      if hasattr(pp, 'F'):
        pp.FTravel = pp.F

  else:
    #look for acceleration gcode
    accelerationMatch = re.match(ACCELERATION_M, cl)
    if accelerationMatch:
      m = 0
      while m+1 < len(accelerationMatch.groups()):
        if accelerationMatch.groups()[m] == None:
          break
        axis = str(accelerationMatch.groups()[m])
        axisValue = float(accelerationMatch.groups()[m+1])
        m += 2
        if axis == 'P':
          pp.P = axisValue
        elif axis == 'R':
          pp.R = axisValue
        elif axis == 'T':
          pp.T = axisValue
        elif axis == 'S':
          pp.P = pp.T = axisValue
        else:
          print(f"Unknown accleration axis {axis} {axisValue} for input {cl}")
  
# Update states for movment POSITION and TOOL
def updatePrintState(ps: PrintState, cl: str, sw: bool):
  # look for movement gcode and record last position
  checkAndUpdatePosition(cl=cl, pp=ps.originalPosition)
  # look for toolchange T
  toolchangeMatch = re.match(TOOLCHANGE_T, cl)

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
  #re-enable extrude
  #print(f"End previous feature skip at feature {f.tell()}")
  ps.skipWrite = False

  insertedToolchangeTypeAtCurrentPosition = checkAndInsertToolchange(ps=ps, f=f, out=out, cl=cl, toolchangeBareFile=toolchangeBareFile, pcs=pcs)
  if insertedToolchangeTypeAtCurrentPosition == ToolchangeType.NONE and not prevFeatureSkip:
    writeWithFilters(out, cl, loadedColors) # write current line read in (before seek to new feature location) before we restore position
  ps.skipWriteForCurrentLine = True
  
  # Restore pre-feature position state before entering a new feature on periodic layer (but not if it is a prime tower on periodic line) or first feature on layer anywhere and prime if toolchange was inserted at start of feature.
  if (ps.isPeriodicLine == True and not (curFeature.featureType == PRIME_TOWER and curFeature.toolchange)) or curFeatureIdx == 0:
    out.write("; MFM Pre-Feature Restore Positions\n")

    # Restore acceleration
    restoreCmd = ACCELERATION_M204
    try:
      getattr(curFeature.startPosition, "P")
      restoreCmd += f" P{curFeature.startPosition.P}"
      getattr(curFeature.startPosition, "R")
      restoreCmd += f" R{curFeature.startPosition.R}"
      getattr(curFeature.startPosition, "T")
      restoreCmd += f" T{curFeature.startPosition.T}"
    except AttributeError as e:
      print(f"Restore acceleration did not find axis {e} yet")
    if len(restoreCmd) > len(ACCELERATION_M204):
      out.write(f"{restoreCmd}\n")

    # Restore position and feedrate
    restoreCmd = MOVEMENT_G0
    try:
      getattr(curFeature.startPosition, "X")
      restoreCmd += f" X{curFeature.startPosition.X}"
      getattr(curFeature.startPosition, "Y")
      restoreCmd += f" Y{curFeature.startPosition.Y}"
      getattr(curFeature.startPosition, "Z")
      restoreCmd += f" Z{curFeature.startPosition.Z}"
      getattr(curFeature.startPosition, "F")
      restoreCmd += f" F{curFeature.startPosition.FTravel}"
    except AttributeError as e:
      print(f"Restore position did not find axis {e} yet")
    if len(restoreCmd) > len(MOVEMENT_G0):
      out.write(f"{restoreCmd}\n")
    #out.write(f"G0 X{curFeature.startPosition.X} Y{curFeature.startPosition.Y} Z{curFeature.startPosition.Z} F{curFeature.startPosition.F}\n")
    # Restore any prime needed
    extraPrimeGcode = None
    if insertedToolchangeTypeAtCurrentPosition == ToolchangeType.FULL:
      extraPrimeGcode = FULL_TOOLCHANGE_PRIME
    elif insertedToolchangeTypeAtCurrentPosition == ToolchangeType.MINIMAL:
      extraPrimeGcode = MINIMAL_TOOLCHANGE_PRIME
    elif ps.featureWipeEndPrime:
      extraPrimeGcode = f"G1 E{ps.featureWipeEndPrime.E} F{ps.featureWipeEndPrime.F}"
      ps.featureWipeEndPrime = None # clear feature wipe end prime position which had prev feature wipe values
    #elif gf == MARLIN_2_BAMBU_PRUSA_MARKED_GCODE:
    #  extraPrimeGcode = FEATURE_START_DEFAULT_PRIME
    if extraPrimeGcode:
      out.write(f"{extraPrimeGcode}\n") #Extrude a bit for minimal toolchange

  # All other processing below is for periodic
  if not ps.isPeriodicLine:
    return 
  
  # We should not run into this older prime tower check because we separate prime towers into another feature list for periodic lines
  # If current feature is the prime tower with toolchange. Do not write prime tower. Skip past this prime tower feature. We may find use for prime tower later. If prime tower does not have toolchange, do not skip it.
  if curFeature.featureType == PRIME_TOWER and curFeature.toolchange:
    print(f"Current feature is prime tower (with toolchange) and it is available for use/relocation. Skipping prime tower.")
    out.write("; MFM Original Prime Tower skipped\n")
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

def writeWithFilters(out: typing.TextIO, cl: str, lc: list[PrintColor]):
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

#def process(gcodeFlavor: str, inputFile: str, outputFile: str, toolchangeBareFile: str, periodicColors: list[PeriodicColor], replacementColors:list[ReplacementColorAtHeight], lineEnding: str, statusQueue: queue.Queue):
def process(configuration: MFMConfiguration, statusQueue: queue.Queue):
  startTime = time.monotonic()
  try:
    with open(configuration[CONFIG_INPUT_FILE], mode='r') as f, open(configuration[CONFIG_OUTPUT_FILE], mode='w') as out:
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
        cp = f.tell() # position is start of next line after read line. We define in lower scope function as needed for retention.

        currentPrint.skipWriteForCurrentLine = False

        if f.tell() == 30440:
          0==0

        # Update current print state variables
        updatePrintState(ps=currentPrint, cl=cl, sw=currentPrint.skipWrite)
      
        # If no more features left in stackcheck for new layers
        # Look for start of a layer CHANGE_LAYER
        if len(currentPrint.features) == 0:
          # If no more features and we are at a stop position write the read line and jump to layer end (cursor at start of CHANGE_LAYER line). This is needed required for the case where the last feature original position is not last in the original file. But we write the current last line and seek to layer end everytime so that we can continue the loop without figuring out if write the previous line found after found new layer because we did it here.
          if f.tell() in currentPrint.stopPositions:
            if not currentPrint.skipWrite:
              writeWithFilters(out, cl, loadedColors)
            f.seek(currentPrint.layerEnd, os.SEEK_SET)

          # Save current pos for restore since findChangeLayer() will change pos
          cp = f.tell()

          if currentPrint.height == 2.0:
            0==0

          foundNewLayer = findChangeLayer(f,lastPrintState=currentPrint, gf=configuration[CONFIG_GCODE_FLAVOR], pcs=configuration[CONFIG_PERIODIC_COLORS], rcs=configuration[CONFIG_REPLACEMENT_COLORS], le=configuration[CONFIG_LINE_ENDING])
          if foundNewLayer:
            currentPrint = foundNewLayer

            if statusQueue:
              item = StatusQueueItem()
              item.statusLeft = f"Current Layer {currentPrint.height}"
              item.statusRight = f"Analyzing"
              item.progress = cp/lp * 100
              statusQueue.put(item=item)

            findLayerFeatures(f=f, gf=configuration[CONFIG_GCODE_FLAVOR], printState=currentPrint, pcs=configuration[CONFIG_PERIODIC_COLORS], le=configuration[CONFIG_LINE_ENDING])
            # Save reference to last original feature in case it originally continues to next layer
            if len(currentPrint.features) > 0:
              currentPrint.lastFeature = currentPrint.features[len(currentPrint.features)-1]
            reorderFeatures(ps=currentPrint)

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

            if statusQueue:
              item = StatusQueueItem()
              item.statusRight = f"Writing"
              item.progress = (currentPrint.layerStart+((currentPrint.layerEnd-currentPrint.layerStart)/2))/lp * 100
              statusQueue.put(item=item)
            # join to debug thread queue reading
            #statusQueue.join()
            
          f.seek(cp, os.SEEK_SET)

          # We wrote last line in previous layer (readline for this loop) already if the last feature. 
          if foundNewLayer:
            continue

        else: # look for feature stop
          if cp in currentPrint.stopPositions: # find a stop position to "start" a new feature
            currentPrint.stopPositions.remove(cp)
            curFeature = currentPrint.features.pop(0)
            curFeatureIdx += 1

            #print(f"Starting feature index {curFeatureIdx} {curFeature.featureType} seek to position {curFeature.start}")

            if statusQueue:
              item = StatusQueueItem()
              item.statusRight = f"{curFeature.featureType} Writing"
              statusQueue.put(item=item)

            f.seek(curFeature.start, os.SEEK_SET) # Seek to the start of top feature in the feature list
            startNewFeature(configuration[CONFIG_GCODE_FLAVOR], currentPrint, f, out, cl, configuration[CONFIG_TOOLCHANGE_MINIMAL_FILE], configuration[CONFIG_PERIODIC_COLORS], curFeature, curFeatureIdx)
        
        # Start skip if feature.toolchange is reached and we marked feature as needing original toolchange skipped
        if curFeature and curFeature.skipType == SkipType.FEATURE_ORIG_TOOLCHANGE_AND_WIPE_END:
          if curFeature.toolchange and f.tell() == curFeature.toolchange.start:
            #print(f"Current feature toolchange is redundant. Skipping feature toolchange. Start skip at {f.tell()}")
            out.write("; MFM Original Feature Toolchange skipped\n")
            currentPrint.skipWrite = True
            #print(f"start feature toolchange skip ")
          
          if curFeature.wipeEnd and f.tell() == curFeature.wipeEnd.start and curFeature.featureType not in RETAIN_WIPE_END_FEATURE_TYPES:
            writeWithFilters(out, cl, loadedColors)
            #print(f"Skipping feature WIPE_END. Start skip at {f.tell()}")
            out.write(";WIPE_END placeholder for PrusaSlicer Gcode Viewer\n")
            out.write("; WIPE_END placeholder for BambuStudio Gcode Preview\n")
            out.write("; MFM Original WIPE_END skipped\n")
            currentPrint.skipWrite = True
            # Reference original pos as last wipe end pos for next layer
            currentPrint.featureWipeEndPrime = currentPrint.originalPosition
            

        # Write current line
        if currentPrint.skipWrite == False and currentPrint.skipWriteForCurrentLine == False: 
          #out.write(cl)
          writeWithFilters(out, cl, loadedColors)

        if currentPrint.skipWriteForCurrentLine == True:
          currentPrint.skipWrite = False
          currentPrint.skipWriteForCurrentLine = False

      out.write(f'Post Processed with {configuration[CONFIG_APP_NAME]} {configuration[CONFIG_APP_VERSION]}')

      if statusQueue:
        item = StatusQueueItem()
        item.statusLeft = f"Current Layer {currentPrint.height}"
        item.statusRight = f"Completed in {str(datetime.timedelta(seconds=time.monotonic()-startTime))}s"
        item.progress = 99.99
        statusQueue.put(item=item)
  except PermissionError as e:
    if statusQueue:
      item = StatusQueueItem()
      item.statusRight = f"Failed to open {e}"
      statusQueue.put(item=item)