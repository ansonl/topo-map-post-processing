import argparse, enum, shutil, os, logging, sys, threading

from mfm.line_ending import *
from mfm.map_post_process import *

class LineEndingCommandLineParameter(enum.Enum):
  AUTODETECT = "AUTO"
  WINDOWS = "WINDOWS"
  UNIX = "UNIX"

TEMP_OUTPUT_GCODE_FILE = 'mfm-output.gcode'

#python ./src/mfm_cmd.py ./sample_models/dual_color_dice/tests/dice_multiple_bambu_prime.gcode -o dice-export.gcode -c ./sample_models/dual_color_dice/config-dice-test.json -t ./minimal_toolchanges/bambu-p1-series.gcode

#python ./src/mfm_cmd.py "C:\Users\ansonl\Downloads\Die and Dots_PLA_3h21m.gcode" -o dice-export.gcode -c ./sample_models/dual_color_dice/config-dice-test.json -t ./minimal_toolchanges/bambu-p1-series.gcode

# Slicer Post-processing Scripts (general)
#"PYTHONPATH/python3.11.exe" "SCRIPTPATH/mfm_cmd.py" -c "OPTIONSPATH/options.json" -t "TOOLCHANGEPATH/toolchange.gcode";

# Slicer Post-processing Scripts (windows) (put project folder in user home folder)
#"C:\Users\USERNAME\AppData\Local\Microsoft\WindowsApps\python3.11.exe" "C:\Users\USERNAME\topo-map-post-processing\src\mfm_cmd.py" -c "C:\Users\USERNAME\topo-map-post-processing\sample_models\dual_color_dice\config-dice-test.json" -t "C:\Users\USERNAME\topo-map-post-processing\minimal_toolchanges\bambu-p1-series.gcode";

if __name__ == "__main__":

    redirectSTDERR = open(os.path.join(os.path.expanduser('~'), 'mfm-script-stderr.log'), "w")
    sys.stderr.write = redirectSTDERR.write

    '''
    redirectSTDOUT = open(os.path.join(os.path.expanduser('~'), 'mfm-script-stdout.log'), "w")
    sys.stdout.write = redirectSTDOUT.write
    '''

    log_file_path = os.path.join(os.path.expanduser('~'), 'mfm-script.log')
    try:
        logging.basicConfig(level=logging.DEBUG, 
            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', filename=log_file_path, filemode='w')
        console = logging.StreamHandler(stream=sys.stdout)
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        logging.getLogger('').setLevel(logging.DEBUG)
    except Exception as e:
        print(f"Failed to create log file: {e}")

    logging.info(f"Logging started")

    # Set up status queue
    statusQueue: queue.Queue[StatusQueueItem] = queue.Queue()
    def worker():
        while True:
            item = statusQueue.get()
            statusQueue.task_done()
            status = None
            if item.statusLeft != None:
                status = item.statusLeft
            if item.statusRight != None:
                status = item.statusRight
            if item.progress != None:
                status = f'Progress {item.progress}'
            logging.info(status)
    threading.Thread(target=worker, daemon=True).start()

    # Setup arguments to parse
    parser = argparse.ArgumentParser(
        description='3D G-code Map Feature Modifier (MFM)',
        epilog='Report issues and contribute at https://github.com/ansonl/mfm'
    )
    parser.add_argument('input_gcode', type=str, help='Input G-code file')
    parser.add_argument('-o', '--output_gcode', help='Output G-code file. Overwrite Input G-code file if no output provided.')
    parser.add_argument('-c', '--config', required=True, help='Options configuration JSON file')
    parser.add_argument('-t', '--toolchange', required=True, help='Toolchange G-code file')
    parser.add_argument('-le', choices=[LineEndingCommandLineParameter.AUTODETECT, LineEndingCommandLineParameter.WINDOWS, LineEndingCommandLineParameter.UNIX], default=LineEndingCommandLineParameter.AUTODETECT, help='Line ending style')
    
    args =  parser.parse_args()
    logging.info(f'Parsed args {args}')

    inputGcodeFile = args.input_gcode
    outputGcodeFile = args.output_gcode
    configFile = args.config
    toolchangeFile = args.toolchange
    lineEndingFlavor = args.le
    
    if outputGcodeFile == None:     
        outputGcodeFile = TEMP_OUTPUT_GCODE_FILE
        status = f"No Output G-code file provided. Temp output at {outputGcodeFile}. input file will be replaced by temp file."
        logging.info(status)

    status = f"Input G-code file is {inputGcodeFile}"
    logging.info(status)

    # Load Options from JSON file
    userOptions = {}
    loadOptionsError = readUserOptions(userOptions=userOptions, optionsFilename=configFile)
    if loadOptionsError != None:
        status = f'Config JSON file could not be parsed. {loadOptionsError}'
        logging.error(status)
    status = f'UserOptions are {userOptions}'
    logging.info(status)

    # Parse colors
    periodicColors = parsePeriodicColors(userOptions=userOptions)
    replacementColors = parseReplacementColors(userOptions=userOptions)

    # Determine line ending
    if lineEndingFlavor == LineEndingCommandLineParameter.AUTODETECT: 
        lineEndingFlavor = LineEnding.AUTODETECT
    if lineEndingFlavor == LineEndingCommandLineParameter.WINDOWS:
        lineEndingFlavor = LineEnding.WINDOWS
    elif lineEndingFlavor == LineEndingCommandLineParameter.UNIX:
        lineEndingFlavor = LineEnding.UNIX
    else:
        lineEndingFlavor = LineEnding.AUTODETECT

    status = f"User selected {repr(lineEndingFlavor)} line ending."
    logging.info(status)
    if lineEndingFlavor == LineEnding.AUTODETECT:
        lineEndingFlavor = determineLineEndingTypeInFile(inputGcodeFile)
        status = f"Detected {repr(lineEndingFlavor)} line ending in input G-code file."
        logging.info(status)
        if lineEndingFlavor == LineEnding.UNKNOWN:
            lineEndingFlavor = LineEnding.UNIX
            status = f"Defaulting to {LINE_ENDING_UNIX_TITLE}"
            logging.warning(status)

    # Create config dict that is sent to process loop
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

    process(configuration=mfmConfig, statusQueue=statusQueue)

    status = f'Wrote output G-code to {outputGcodeFile}\n'
    logging.info(status)

    # Overwrite the input G-code file if no output file was passed
    if outputGcodeFile == TEMP_OUTPUT_GCODE_FILE:
        shutil.move(TEMP_OUTPUT_GCODE_FILE, inputGcodeFile)
        status = f'Moved temp output G-code to {inputGcodeFile}\n'
        logging.info(status)