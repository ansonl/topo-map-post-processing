import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter import messagebox

import json
import os
import time

import threading
import queue

from map_post_process import *

# RUNTIME Flag
TEST_MODE = True

# UI Constants
APP_NAME = 'Map Features G-code Post Processing'
APP_VERSION = '0.4.2'
POST_PROCESS_BUTTON = 'Post Process'
POST_PROCESS_BUTTON_PROCESSING = 'Processing'

# Options keys
IMPORT_GCODE_FILENAME = 'importGcodeFilename'
IMPORT_OPTIONS_FILENAME = 'importOptionsFilename'
IMPORT_TOOLCHANGE_BARE_FILENAME = 'importToolchangeBareFilename'
EXPORT_GCODE_FILENAME = 'exportGcodeFilename'

MODEL_TO_REAL_WORLD_DEFAULT_UNITS = 'modelToRealWorldDefaultUnits'
MODEL_ONE_TO_N_VERTICAL_SCALE = 'modelOneToNVerticalScale'
MODEL_SEA_LEVEL_BASE_THICKNESS = 'modelSeaLevelBaseThickness'

REAL_WORLD_ISOLINE_ELEVATION_INTERVAL = 'realWorldIsolineElevationInterval'
REAL_WORLD_ISOLINE_ELEVATION_START = 'realWorldIsolineElevationStart'
REAL_WORLD_ISOLINE_ELEVATION_END = 'realWorldIsolineElevationEnd'
MODEL_ISOLINE_HEIGHT = 'modelIsolineHeight' #in model units
ISOLINE_COLOR_INDEX = 'isolineColorIndex'

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
  ISOLINE_COLOR_INDEX
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

# user options dict
userOptions = {}

def select_file(filetypes:[tuple]):
  filetypes.append(('All files', '*.*'))

  filename = fd.askopenfilename(
    title='Open a file',
    initialdir='/',
    filetypes=filetypes)
  
  return filename

def truncateMiddleLength(s, length):
  if len(s) > length:
    s = f"{s[:int(length/2)-3]}...{s[-int(length/2):]}"
  return s

def addExportToFilename(fn):
  fnSplit = os.path.splitext(fn)
  exportFn = f"{fnSplit[0]}-export"
  if len(fnSplit) > 1:
    exportFn += fnSplit[1]
  return exportFn

class App(tk.Tk):
  def __init__(self, queue: queue.Queue):
    super().__init__()

    self.title(APP_NAME)
    self.minsize(500, 275)
    self.resizable(False, False)

    # configure the grid
    self.columnconfigure(0, weight=1)
    self.columnconfigure(1, weight=3)

    self.queue = queue
    self.postProcessThread: threading.Thread = None

    # UI strings
    self.status = tk.StringVar()
    self.progress = tk.DoubleVar()
    self.progressButtonString = tk.StringVar(value=POST_PROCESS_BUTTON)

    self.create_widgets()

  def create_widgets(self):

    gcodeFlavorLabel = tk.Label(
      master=self,
      text='G-code Flavor'
    )
    gcodeFlavorLabel.grid(row=0, column=0, sticky=tk.W, padx=10)
    gcodeFlavorComboBox = ttk.Combobox(
      state="readonly",
      values=['Marlin 2 (PrusaSlicer/Bambu Studio)']
    )
    gcodeFlavorComboBox.current(0)
    gcodeFlavorComboBox.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=10)

    def selectImportGcodeFile():
      fn = select_file([('G-code file', '*.gcode')])
      importGcodeButton.config(text=truncateMiddleLength(fn, 50))
      exportFn = addExportToFilename(fn)
      exportGcodeButton.config(text=truncateMiddleLength(exportFn, 50))
      userOptions[IMPORT_GCODE_FILENAME] = fn
      userOptions[EXPORT_GCODE_FILENAME] = exportFn

    def selectOptionsFile():
      fn = select_file([('JSON file', '*.json')])
      importOptionsButton.config(text=truncateMiddleLength(fn, 50))
      userOptions[IMPORT_OPTIONS_FILENAME] = fn

    def selectToolchangeBareFile():
      fn = select_file([('G-code file', '*.gcode')])
      importToolchangeBareButton.config(text=truncateMiddleLength(fn, 50))
      userOptions[IMPORT_TOOLCHANGE_BARE_FILENAME] = fn

    def selectExportGcodeFile():
      fn = select_file([('G-code file', '*.gcode')])
      if fn == userOptions[IMPORT_GCODE_FILENAME]:
        fn = addExportToFilename(fn)
        messagebox.showinfo(
          title='Invalid selection',
          message='Export file must be different from import file. The export filename has been changed to be different.'
        )
      exportGcodeButton.config(text=truncateMiddleLength(fn, 50))
      userOptions[EXPORT_GCODE_FILENAME] = fn

    importLabel = tk.Label(
      master=self,
      text='Print G-code '
    )
    importLabel.grid(row=1, column=0, sticky=tk.W, padx=10)
    importGcodeButton = tk.Button(
      master=self,
      text='Select file',
      command=selectImportGcodeFile
    )
    importGcodeButton.grid(row=1, column=1, sticky=tk.EW, padx=10, pady=5)

    optionsLabel = tk.Label(
      master=self,
      text='Options'
    )
    optionsLabel.grid(row=2, column=0, sticky=tk.W, padx=10)
    importOptionsButton = tk.Button(
      master=self,
      text='Select file',
      command=selectOptionsFile
    )
    importOptionsButton.grid(row=2, column=1, sticky=tk.EW, padx=10, pady=5)

    toolchangeBareLabel = tk.Label(
      master=self,
      text='Toolchange G-code'
    )
    toolchangeBareLabel.grid(row=3, column=0, sticky=tk.W, padx=10)
    importToolchangeBareButton = tk.Button(
      master=self,
      text='Select file',
      command=selectToolchangeBareFile
    )
    importToolchangeBareButton.grid(row=3, column=1, sticky=tk.EW, padx=10, pady=5)

    exportLabel = tk.Label(
      master=self,
      text='Export G-code'
    )
    exportLabel.grid(row=4, column=0, sticky=tk.W, padx=10)
    exportGcodeButton = tk.Button(
      master=self,
      text='Select file',
      command=selectExportGcodeFile
    )
    exportGcodeButton.grid(row=4, column=1, sticky=tk.EW, padx=10, pady=5)

    separator = ttk.Separator(self, orient=tk.HORIZONTAL)
    separator.grid(row=5, column=0, sticky=tk.EW, columnspan=2, padx=15, pady=5)

    self.processStatusLabel = tk.Label(
      master=self,
      textvariable=self.status,
      wraplength=450
    )
    self.processStatusLabel.grid(row=6, column=0, columnspan=2, padx=10, sticky=tk.EW)
    self.processStatusProgressBar = ttk.Progressbar(
      self,
      orient=tk.HORIZONTAL,
      variable=self.progress
    )
    self.processStatusProgressBar.grid(row=7, column=0, columnspan=2, padx=10, sticky=tk.EW)

    def startPostProcess():
      self.progress.set(0)
      self.progressButtonString.set(POST_PROCESS_BUTTON_PROCESSING)

      def postProcessTask():
        global userOptions
        userOptions = {
          IMPORT_GCODE_FILENAME : userOptions.get(IMPORT_GCODE_FILENAME),
          IMPORT_OPTIONS_FILENAME : userOptions.get(IMPORT_OPTIONS_FILENAME),
          IMPORT_TOOLCHANGE_BARE_FILENAME : userOptions.get(IMPORT_TOOLCHANGE_BARE_FILENAME),
          EXPORT_GCODE_FILENAME : userOptions.get(EXPORT_GCODE_FILENAME)
        }
        periodicColors: list[PeriodicColor] = []
        replacementColors: list[ReplacementColorAtHeight] = []

        if TEST_MODE:
          userOptions[IMPORT_GCODE_FILENAME] = 'sample_models/dice_x1c.gcode'
          userOptions[IMPORT_TOOLCHANGE_BARE_FILENAME] = 'minimal_toolchanges/toolchange-bare-bambu-x1-series.gcode'
          userOptions[EXPORT_GCODE_FILENAME] = 'dice-export.gcode'
          periodicColors = [
            PeriodicColor(colorIndex=2, startHeight=0.3, endHeight=10, height=0.5, period=1)
          ]
          replacementColors = [
            ReplacementColorAtHeight(colorIndex=3, originalColorIndex=0, startHeight=8, endHeight=float('inf'))
          ]
        else:
          if userOptions.get(IMPORT_GCODE_FILENAME) == None or userOptions.get(IMPORT_OPTIONS_FILENAME) == None or userOptions.get(IMPORT_TOOLCHANGE_BARE_FILENAME) == None or userOptions.get(EXPORT_GCODE_FILENAME) == None:
            messagebox.showerror(
                title='Post Process Requirements',
                message='Need Print G-code, Options, Toolchange G-code, and Exported G-code to be  selected.'
            )
            return
          
          # Read in user options
          with open(userOptions.get(IMPORT_OPTIONS_FILENAME)) as f:
            try:
              data = json.load(f)
              if isinstance(data,dict):
                for item in data.items():
                  userOptions[item[0]] = item[1]
              else:
                raise ValueError()
            except ValueError:
              messagebox.showerror(
                title='Unable to load options',
                message='Check if options file format is JSON'
              )
              return

          print(userOptions)
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
                colorIndex=userOptions[ISOLINE_COLOR_INDEX]
              )
            )
            print("Added isoline based on options")

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
          
        process(gcodeFlavor=MARLIN_2_BAMBUSLICER_MARKED_GCODE, inputFile=userOptions[IMPORT_GCODE_FILENAME], outputFile=userOptions[EXPORT_GCODE_FILENAME], toolchangeBareFile=userOptions[IMPORT_TOOLCHANGE_BARE_FILENAME], periodicColors=periodicColors, replacementColors=replacementColors, statusQueue=self.queue)

      startPostProcessButton["state"] = "disabled"

      postProcessThread = threading.Thread(target=postProcessTask)
      postProcessThread.start()

      # Wait on post process thread in another thread to reset UI
      def resetButton():
        postProcessThread.join()
        startPostProcessButton["state"] = "normal"
        self.progressButtonString.set(POST_PROCESS_BUTTON)
      threading.Thread(target=resetButton).start()

    startPostProcessButton = tk.Button(
      master=self,
      textvariable=self.progressButtonString,
      command=startPostProcess
    )
    startPostProcessButton.grid(row=8, column=0, sticky=tk.EW, columnspan=2, padx=10)

    infoButton = tk.Button(
      master=self,
      text='About',
      command=lambda:
        messagebox.showinfo(
          title=f"{APP_NAME} v{APP_VERSION}",
          message='Add isolines and elevation color change features to your 3D Topo Maps when printed.\n\n www.AnsonLiu.com/maps'
        )
    )
    infoButton.grid(row=9, column=0, sticky=tk.EW, columnspan=1, padx=10, pady=10)

    infoLabel = tk.Label(
      master=self,
      text=f"v{APP_VERSION}"
    )
    infoLabel.grid(row=9, column=1, sticky=tk.E, padx=10)

    

if __name__ == "__main__":
  statusQueue: queue.Queue[StatusQueueItem] = queue.Queue()
  app = App(queue=statusQueue)

  def worker():
    while True:
      item = statusQueue.get()
      statusQueue.task_done()
      if item.status != None:
        app.status.set(item.status)
      if item.progress != None:
        app.progress.set(item.progress)
      
  threading.Thread(target=worker, daemon=True).start()
  
  app.mainloop()