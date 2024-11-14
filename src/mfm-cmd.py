import argparse, enum, shutil

from mfm.line_ending import *
from mfm.map_post_process import *

class LineEndingCommandLineParameter(enum.Enum):
  AUTODETECT = "AUTO"
  WINDOWS = "WINDOWS"
  UNIX = "UNIX"

TEMP_OUTPUT_GCODE_FILE = 'mfm-output.gcode'

#python ./src/mfm-cmd.py ./sample_models/dual_color_dice/tests/dice_multiple_bambu_prime.gcode -o dice-export.gcode -c ./sample_models/dual_color_dice/config-dice-test.json -t ./minimal_toolchanges/bambu-p1-series.gcode

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='3D G-code Map Feature Modifier (MFM)',
        epilog='Report issues and contribute at https://github.com/ansonl/topo-map-post-processing'
    )
    parser.add_argument('input_gcode', type=str, help='Input G-code file')
    parser.add_argument('-o', '--output_gcode', help='Output G-code file. Overwrite Input G-code file if no output provided.')
    parser.add_argument('-c', '--config', required=True, help='Options configuration JSON file')
    parser.add_argument('-t', '--toolchange', required=True, help='Toolchange G-code file')

    parser.add_argument('-le', choices=[LineEndingCommandLineParameter.AUTODETECT, LineEndingCommandLineParameter.WINDOWS, LineEndingCommandLineParameter.UNIX], default=LineEndingCommandLineParameter.AUTODETECT, help='Line ending style')

    args = parser.parse_args()

    print(args)

    inputGcodeFile = args.input_gcode
    outputGcodeFile = args.output_gcode
    configFile = args.config
    toolchangeFile = args.toolchange
    lineEndingFlavor = args.le
    
    if outputGcodeFile == None:
        outputGcodeFile = TEMP_OUTPUT_GCODE_FILE

    userOptions = {}

    if readUserOptions(userOptions=userOptions, optionsFilename=configFile) != None:
        print('config file could not be read')

    print(userOptions)

    periodicColors = parsePeriodicColors(userOptions=userOptions)
    replacementColors = parseReplacementColors(userOptions=userOptions)

    if lineEndingFlavor == LineEndingCommandLineParameter.AUTODETECT: 
        lineEndingFlavor = LineEnding.AUTODETECT
    if lineEndingFlavor == LineEndingCommandLineParameter.WINDOWS:
        lineEndingFlavor = LineEnding.WINDOWS
    elif lineEndingFlavor == LineEndingCommandLineParameter.UNIX:
        lineEndingFlavor = LineEnding.UNIX
    else:
        lineEndingFlavor = LineEnding.AUTODETECT

    print(f"Selected {repr(lineEndingFlavor)} line ending.")
    if lineEndingFlavor == LineEnding.AUTODETECT:
        lineEndingFlavor = determineLineEndingTypeInFile(configFile)
        print(f"Detected {repr(lineEndingFlavor)} line ending in input G-code file.")
        if lineEndingFlavor == LineEnding.UNKNOWN:
            lineEndingFlavor = LineEnding.UNIX
        print(f"Defaulting to {LINE_ENDING_UNIX_TITLE}")

    mfmConfig = MFMConfiguration()
    mfmConfig[CONFIG_GCODE_FLAVOR] = MARLIN_2_BAMBU_PRUSA_MARKED_GCODE
    mfmConfig[CONFIG_INPUT_FILE] = inputGcodeFile
    mfmConfig[CONFIG_OUTPUT_FILE] = outputGcodeFile
    mfmConfig[CONFIG_TOOLCHANGE_MINIMAL_FILE] = toolchangeFile
    mfmConfig[CONFIG_PERIODIC_COLORS] = periodicColors
    mfmConfig[CONFIG_REPLACEMENT_COLORS] = replacementColors
    mfmConfig[CONFIG_LINE_ENDING] = lineEndingFlavor.value
    mfmConfig[CONFIG_APP_NAME] = APP_NAME
    mfmConfig[CONFIG_APP_VERSION] = APP_VERSION

    process(configuration=mfmConfig, statusQueue=None)

    print(f'Wrote output G-code to {outputGcodeFile}\n')

    # Overwrite the input G-code file if no output file was passed
    if outputGcodeFile == TEMP_OUTPUT_GCODE_FILE:
        shutil.move(TEMP_OUTPUT_GCODE_FILE, inputGcodeFile) 
        print(f'Moved output G-code to {inputGcodeFile}\n')