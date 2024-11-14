import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter import messagebox

import json
import os

import threading
import queue

import enum

import webbrowser

from mfm.configuration import *
from mfm.map_post_process import *

# RUNTIME Flag
TEST_MODE = False

# UI Constants
POST_PROCESS_BUTTON = 'Post Process'
POST_PROCESS_BUTTON_PROCESSING = 'Processing'

# Options keys
#CONFIG_INPUT_FILE = 'importGcodeFilename'
IMPORT_OPTIONS_FILENAME = 'importOptionsFilename'
#CONFIG_OUTPUT_FILE = 'exportGcodeFilename'



LINE_ENDING_FLAVOR = 'lineEndingFlavor'

# user options dict
userOptions = {}

def select_open_file(filetypes:tuple[str]):
  filetypes.append(('All files', '*.*'))

  filename = fd.askopenfilename(
    title='Open a file',
    initialdir='./',
    filetypes=filetypes)
  
  return filename

def select_save_file(filetypes:tuple[str]):
  filetypes.append(('All files', '*.*'))

  filename = fd.asksaveasfilename(
    title='Save as file',
    initialdir='./',
    filetypes=filetypes)
  
  return filename

def truncateMiddleLength(s, length):
  if len(s) > length:
    s = f"{s[:int(length/2)-3]}...{s[-int(length/2):]}"
  return s

def addExportToFilename(fn):
  fnSplit = os.path.splitext(fn)
  exportFn = f"{fnSplit[0]}-MFM-export"
  if len(fnSplit) > 1:
    exportFn += fnSplit[1]
  return exportFn

class App(tk.Tk):
  def __init__(self, queue: queue.Queue):
    super().__init__()

    self.title(f'{APP_NAME} {APP_VERSION}')
    self.minsize(500, 300)
    self.resizable(False, False)

    # configure the grid
    self.columnconfigure(0, weight=1)
    self.columnconfigure(1, weight=3)

    self.queue = queue
    self.postProcessThread: threading.Thread = None

    # UI strings
    self.statusLeft = tk.StringVar()
    self.statusRight = tk.StringVar()
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
      values=['Marlin 2 (PrusaSlicer/Bambu Studio/Orca Slicer)']
    )
    gcodeFlavorComboBox.current(0)
    gcodeFlavorComboBox.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=10)

    def selectImportGcodeFile():
      fn = select_open_file([('G-code file', '*.gcode')])
      if fn:
        importGcodeButton.config(text=truncateMiddleLength(fn, 50))
        exportFn = addExportToFilename(fn)
        exportGcodeButton.config(text=truncateMiddleLength(exportFn, 50))
        userOptions[CONFIG_INPUT_FILE] = fn
        userOptions[CONFIG_OUTPUT_FILE] = exportFn

    def selectOptionsFile():
      fn = select_open_file([('JSON file', '*.json')])
      if fn:
        importOptionsButton.config(text=truncateMiddleLength(fn, 50))
        userOptions[IMPORT_OPTIONS_FILENAME] = fn

    def selectToolchangeBareFile():
      fn = select_open_file([('G-code file', '*.gcode')])
      if fn:
        importToolchangeBareButton.config(text=truncateMiddleLength(fn, 50))
        userOptions[CONFIG_TOOLCHANGE_MINIMAL_FILE] = fn

    def selectExportGcodeFile():
      fn = select_save_file([('G-code file', '*.gcode')])
      if fn:
        if fn == userOptions[CONFIG_INPUT_FILE]:
          fn = addExportToFilename(fn)
          messagebox.showinfo(
            title='Invalid selection',
            message='Export file must be different from import file. The export filename has been changed to be different.'
          )
        exportGcodeButton.config(text=truncateMiddleLength(fn, 50))
        userOptions[CONFIG_OUTPUT_FILE] = fn

    def selectLineEndingFlavor(event):
      print(event)
      selectedLineEnding = None
      if lineEndingFlavorComboBox.get() == LINE_ENDING_AUTODETECT_TITLE:
        selectedLineEnding = LineEnding.AUTODETECT
      elif lineEndingFlavorComboBox.get() == LINE_ENDING_WINDOWS_TITLE:
        selectedLineEnding = LineEnding.WINDOWS
      elif lineEndingFlavorComboBox.get() == LINE_ENDING_UNIX_TITLE:
        selectedLineEnding = LineEnding.UNIX
      userOptions[LINE_ENDING_FLAVOR] = selectedLineEnding
      print("selected "+ lineEndingFlavorComboBox.get())

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

    # Line ending
    lineEndingFlavorLabel = tk.Label(
      master=self,
      text='G-code Line Ending'
    )
    lineEndingFlavorLabel.grid(row=5, column=0, sticky=tk.W, padx=10)
    lineEndingFlavorComboBox = ttk.Combobox(
      state="readonly",
      values=[LINE_ENDING_AUTODETECT_TITLE, LINE_ENDING_WINDOWS_TITLE, LINE_ENDING_UNIX_TITLE]
    )
    lineEndingFlavorComboBox.grid(row=5, column=1, sticky=tk.EW, padx=10, pady=5)
    lineEndingFlavorComboBox.bind('<<ComboboxSelected>>', selectLineEndingFlavor)
    lineEndingFlavorComboBox.current(0)

    separator = ttk.Separator(self, orient=tk.HORIZONTAL)
    separator.grid(row=6, column=0, sticky=tk.EW, columnspan=2, padx=15, pady=5)

    self.processStatusLabelLeft = tk.Label(
      master=self,
      textvariable=self.statusLeft,
      wraplength=150,
      anchor=tk.W
    )
    self.processStatusLabelLeft.grid(row=7, column=0, columnspan=1, padx=10, sticky=tk.EW)
    self.statusLeft.set("Current Layer N/A")

    self.processStatusLabelRight = tk.Label(
      master=self,
      textvariable=self.statusRight,
      wraplength=400,
      anchor=tk.E
    )
    self.processStatusLabelRight.grid(row=7, column=1, columnspan=1, padx=10, sticky=tk.EW)

    self.processStatusProgressBar = ttk.Progressbar(
      self,
      orient=tk.HORIZONTAL,
      variable=self.progress
    )
    self.processStatusProgressBar.grid(row=8, column=0, columnspan=2, padx=10, sticky=tk.EW)

    def startPostProcess():
      self.progress.set(0)
      self.progressButtonString.set(POST_PROCESS_BUTTON_PROCESSING)

      def postProcessTask():
        global userOptions
        userOptions = {
          CONFIG_INPUT_FILE : userOptions.get(CONFIG_INPUT_FILE),
          IMPORT_OPTIONS_FILENAME : userOptions.get(IMPORT_OPTIONS_FILENAME),
          CONFIG_TOOLCHANGE_MINIMAL_FILE : userOptions.get(CONFIG_TOOLCHANGE_MINIMAL_FILE),
          CONFIG_OUTPUT_FILE : userOptions.get(CONFIG_OUTPUT_FILE),
          LINE_ENDING_FLAVOR : userOptions.get(LINE_ENDING_FLAVOR)
        }

        if TEST_MODE:
          #userOptions[CONFIG_INPUT_FILE] = 'sample_models/dual_color_dice/tests/dice_multiple_bambu_prime.gcode'
          #userOptions[CONFIG_INPUT_FILE] = 'sample_models/dual_color_dice/tests/dice_multiple_bambu_no_prime.gcode'
          userOptions[CONFIG_INPUT_FILE] = 'sample_models/dual_color_dice/tests/dice_multiple_orca_prime.gcode'
          #userOptions[CONFIG_INPUT_FILE] = 'sample_models/dual_color_dice/tests/dice_multiple_orca_no_prime.gcode'
          #userOptions[CONFIG_INPUT_FILE] = 'sample_models/dual_color_dice/tests/dice_multiple_prusa_prime.gcode'
          #userOptions[CONFIG_INPUT_FILE] = 'sample_models/dual_color_dice/tests/dice_multiple_prusa_no_prime.gcode'
          userOptions[IMPORT_OPTIONS_FILENAME] = 'sample_models/dual_color_dice/config-dice-test.json'
          userOptions[CONFIG_TOOLCHANGE_MINIMAL_FILE] = 'minimal_toolchanges/bambu-x1-series.gcode'
          #userOptions[CONFIG_TOOLCHANGE_MINIMAL_FILE] = 'minimal_toolchanges/prusa-xl-series.gcode'
          userOptions[CONFIG_OUTPUT_FILE] = 'dice-export.gcode'

          #userOptions[CONFIG_INPUT_FILE] = 'sample_models/CA/ca_p3.gcode'
          #userOptions[IMPORT_OPTIONS_FILENAME] = 'sample_models/CA/config-usaofplastic-200zperc.json'
          #userOptions[CONFIG_TOOLCHANGE_MINIMAL_FILE] = 'minimal_toolchanges/bambu-x1-series.gcode'
          #userOptions[CONFIG_OUTPUT_FILE] = 'CA-export.gcode'

          #userOptions[CONFIG_INPUT_FILE] = 'longs.gcode'
          #userOptions[IMPORT_OPTIONS_FILENAME] = 'configuration-CO-z1000perc.json'
          #userOptions[CONFIG_TOOLCHANGE_MINIMAL_FILE] = 'minimal_toolchanges/bambu-p1-series.gcode'
          #userOptions[CONFIG_OUTPUT_FILE] = 'longs-export.gcode'
          
        else:
          if userOptions.get(CONFIG_INPUT_FILE) == None or userOptions.get(IMPORT_OPTIONS_FILENAME) == None or userOptions.get(CONFIG_TOOLCHANGE_MINIMAL_FILE) == None or userOptions.get(CONFIG_OUTPUT_FILE) == None:
            messagebox.showerror(
                title='Post Process Requirements',
                message='Need Print G-code, Options, Toolchange G-code, and Exported G-code to be selected.'
            )
            return
          
        if readUserOptions(userOptions=userOptions, optionsFilename=userOptions.get(IMPORT_OPTIONS_FILENAME)) != None:
          messagebox.showerror(
            title='Unable to load options',
            message='Check if options file format is JSON'
          )

        print(userOptions)

        periodicColors = parsePeriodicColors(userOptions=userOptions)
        replacementColors = parseReplacementColors(userOptions=userOptions)

        lineEndingFlavor = userOptions[LINE_ENDING_FLAVOR] if userOptions[LINE_ENDING_FLAVOR] else LineEnding.AUTODETECT
        print(f"Selected {repr(lineEndingFlavor)} line ending.")
        if lineEndingFlavor == LineEnding.AUTODETECT:
          lineEndingFlavor = determineLineEndingTypeInFile(userOptions[CONFIG_INPUT_FILE])
          print(f"Detected {repr(lineEndingFlavor)} line ending in input G-code file.")
          if lineEndingFlavor == LineEnding.UNKNOWN:
            lineEndingFlavor = LineEnding.UNIX
            print(f"Defaulting to {LINE_ENDING_UNIX_TITLE}")

        mfmConfig = MFMConfiguration()
        mfmConfig[CONFIG_GCODE_FLAVOR] = MARLIN_2_BAMBU_PRUSA_MARKED_GCODE
        mfmConfig[CONFIG_INPUT_FILE] = userOptions[CONFIG_INPUT_FILE]
        mfmConfig[CONFIG_OUTPUT_FILE] = userOptions[CONFIG_OUTPUT_FILE]
        mfmConfig[CONFIG_TOOLCHANGE_MINIMAL_FILE] = userOptions[CONFIG_TOOLCHANGE_MINIMAL_FILE]
        mfmConfig[CONFIG_PERIODIC_COLORS] = periodicColors
        mfmConfig[CONFIG_REPLACEMENT_COLORS] = replacementColors
        mfmConfig[CONFIG_LINE_ENDING] = lineEndingFlavor.value
        mfmConfig[CONFIG_APP_NAME] = APP_NAME
        mfmConfig[CONFIG_APP_VERSION] = APP_VERSION
        process(mfmConfig, statusQueue)

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
    startPostProcessButton.grid(row=9, column=0, sticky=tk.EW, columnspan=2, padx=10)

    infoButton = tk.Button(
      master=self,
      text=f'About',
      command=lambda:
        messagebox.showinfo(
          title=f"{APP_NAME} v{APP_VERSION}",
          message=f'Add isolines and elevation color change features to your 3D model g-code. Meant for use with 3D Topo Maps.\n\n{APP_NAME} is licensed under GNU Affero General Public License, version 3\n\n www.AnsonLiu.com/maps\n© 2023 Anson Liu'
        )
    )
    infoButton.grid(row=10, column=0, sticky=tk.W, columnspan=1, padx=10, pady=10)

    websiteButton = tk.Button(
      master=self,
      text='Help',
      command=lambda:
        webbrowser.open('https://github.com/ansonl/mfm')
    )
    websiteButton.grid(row=10, column=0, sticky=tk.E, columnspan=1, padx=10, pady=10)

    infoLabel = tk.Label(
      master=self,
      text=f"v{APP_VERSION}"
    )
    infoLabel.grid(row=10, column=1, sticky=tk.E, padx=10)

if __name__ == "__main__":
  statusQueue: queue.Queue[StatusQueueItem] = queue.Queue()
  app = App(queue=statusQueue)

  def worker():
    while True:
      item = statusQueue.get()
      statusQueue.task_done()
      if item.statusLeft != None:
        app.statusLeft.set(item.statusLeft)
      if item.statusRight != None:
        app.statusRight.set(item.statusRight)
      if item.progress != None:
        app.progress.set(item.progress)
      
  threading.Thread(target=worker, daemon=True).start()
  
  app.mainloop()