import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.messagebox import showinfo

import json
import os
import time

import threading
import queue

from map_post_process import *

# RUNTIME Flag
TEST_MODE = True

userOptions = {}

def select_file(filetypes):
  filetypes = (
    ('text files', '*.txt'),
    ('All files', '*.*')
  )

  filename = fd.askopenfilename(
    title='Open a file',
    initialdir='/',
    filetypes=filetypes)
  
  return filename

def truncateMiddleLength(s, length):
  if len(s) > length:
    s = f"{s[:length/2-3]}...{s[-length/2:]}"
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

    self.title('Map Feature Gcode Post Processing')
    self.minsize(200, 200)

    # configure the grid
    self.columnconfigure(0, weight=1)
    self.columnconfigure(1, weight=3)

    self.queue = queue
    self.status = tk.StringVar()
    self.status.set('---')
    self.progress = tk.DoubleVar()
    self.postProcessThread: threading.Thread = None
    self.create_widgets()

  def create_widgets(self):

    def selectImportGcodeFile():
      fn = select_file(('Gcode file', '*.gcode'))
      importGcodeButton.config(text=truncateMiddleLength(fn, 50))
      exportFn = addExportToFilename(fn)
      exportGcodeButton.config(text=truncateMiddleLength(exportFn, 50))
      userOptions[IMPORT_GCODE_FILENAME] = fn
      userOptions[EXPORT_GCODE_FILENAME] = fn

    def selectOptionsFile():
      fn = select_file(('JSON file', '*.json'))
      importOptionsButton.config(text=truncateMiddleLength(fn, 50))
      userOptions[IMPORT_OPTIONS_FILENAME] = fn

    def selectExportGcodeFile():
      fn = select_file(('JSON file', '*.json'))
      if fn == userOptions[IMPORT_GCODE_FILENAME]:
        fn = addExportToFilename(fn)
        showinfo(
          title='Invalid selection',
          message='Export file must be different from import file. The export filename has been changed to be different.'
        )
      exportGcodeButton.config(text=truncateMiddleLength(fn, 50))
      userOptions[EXPORT_GCODE_FILENAME] = fn

    importLabel = tk.Label(
      master=self,
      text='Print Gcode '
    )
    importLabel.grid(row=0, column=0, sticky=tk.W)
    importGcodeButton = tk.Button(
      master=self,
      text='Select file',
      command=selectImportGcodeFile
    )
    importGcodeButton.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

    optionsLabel = tk.Label(
      master=self,
      text='Options'
    )
    optionsLabel.grid(row=1, column=0, sticky=tk.W)
    importOptionsButton = tk.Button(
      master=self,
      text='Select file',
      command=selectOptionsFile
    )
    importOptionsButton.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)

    exportLabel = tk.Label(
      master=self,
      text='Export Gcode'
    )
    exportLabel.grid(row=2, column=0, sticky=tk.W)
    exportGcodeButton = tk.Button(
      master=self,
      text='Select file',
      command=selectExportGcodeFile
    )
    exportGcodeButton.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)

    separator = ttk.Separator(self, orient=tk.HORIZONTAL)
    separator.grid(row=3, column=0, sticky=tk.EW, columnspan=2, padx=5, pady=5)

    self.processStatusLabel = tk.Label(
      master=self,
      textvariable=self.status
    )
    self.processStatusLabel.grid(row=4, column=0, columnspan=2, padx=10, sticky=tk.EW)
    self.processStatusProgressBar = ttk.Progressbar(
      self,
      orient=tk.HORIZONTAL,
      variable=self.progress
    )
    self.processStatusProgressBar.grid(row=5, column=0, columnspan=2, padx=10, sticky=tk.EW)

    def startPostProcess():

      def postProcessTask():
        periodicColors = []
        replacementColors = []

        if TEST_MODE:
          userOptions[IMPORT_GCODE_FILENAME] = 'dicetest.gcode'
          userOptions[EXPORT_GCODE_FILENAME] = 'dicetest-export.gcode'
          periodicColors = [
            PeriodicColor(colorIndex=2, startHeight=0.3, endHeight=10, height=0.5, period=1)
          ]
          replacementColors = [
            ReplacementColorAtHeight(colorIndex=3, originalColorIndex=0, startHeight=8, endHeight=float('inf'))
          ]
        else:
          if userOptions.get(IMPORT_GCODE_FILENAME) == None or userOptions.get(IMPORT_OPTIONS_FILENAME) == None or userOptions.get(EXPORT_GCODE_FILENAME) == None:
            showinfo(
                title='Post Process Requirements',
                message='Need import, options, and exports specified'
            )
            return
          
          with open(userOptions.get(IMPORT_OPTIONS_FILENAME)) as f:
            try:
              data = json.load(f)
              if isinstance(data,dict):
                for item in data.items():
                  userOptions[item[0]] = userOptions[item[1]]
            except ValueError:
              showinfo(
                title='Unable to load options',
                message='Check if options file format is JSON'
              )
              return

          periodicColors: list[PeriodicColor] = [
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
          ]
          replacementColors: list[ReplacementColorAtHeight] = [
            createReplacementColor(
              modelToRealWorldDefaultUnits=userOptions[MODEL_TO_REAL_WORLD_DEFAULT_UNITS],
              modelOneToNVerticalScale=userOptions[MODEL_ONE_TO_N_VERTICAL_SCALE],
              modelSeaLevelBaseThickness=userOptions[MODEL_SEA_LEVEL_BASE_THICKNESS],
              realWorldElevationStart=userOptions[REAL_WORLD_ELEVATION_START],
              realWorldElevationEnd=userOptions[REAL_WORLD_ELEVATION_END],
              colorIndex=userOptions[REPLACEMENT_COLOR_INDEX],
              originalColorIndex=userOptions[REPLACEMENT_ORIGINAL_COLOR_INDEX]
            )
          ]
          
        process(inputFile=userOptions[IMPORT_GCODE_FILENAME], outputFile=userOptions[EXPORT_GCODE_FILENAME], periodicColors=periodicColors, replacementColors=replacementColors, statusQueue=self.queue)

        print('process ended')
        return

      startPostProcessButton["state"] = "disabled"

      print('post process thread start')

      postProcessThread = threading.Thread(target=postProcessTask)
      postProcessThread.start()

      # Wait on post process thread in another thread to reset UI
      def resetButton():
        postProcessThread.join()
        startPostProcessButton["state"] = "normal"
      threading.Thread(target=resetButton).start()

    startPostProcessButton = tk.Button(
      master=self,
      text='Post Process',
      command=startPostProcess
    )
    startPostProcessButton.grid(row=6, column=0, sticky=tk.EW, columnspan=2, padx=10)

    infoButton = tk.Button(
      master=self,
      text='About',
      command=lambda:
        showinfo(
          title='Map Feature Gcode Post Processing',
          message='Add isolines and elevation color changes to your 3D Topo Maps when printed.\n\nVisit www.AnsonLiu.com/maps for more info.'
        )
    )
    infoButton.grid(row=7, column=1, sticky=tk.EW, columnspan=1, padx=10, pady=10)

    

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