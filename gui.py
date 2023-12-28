import tkinter as tk
from tkinter import filedialog as fd
from tkinter.messagebox import showinfo

import json
import os

from map_post_process import *

window = tk.Tk()
window.columnconfigure(0, minsize=100)

window.title('Tkinter Open File Dialog')

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
  with open(fn) as f:
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

labelFrame = tk.Frame(
  master=window,
  borderwidth=1
)
labelFrame.grid(row=0, column=0)
importLabel = tk.Label(
    master=labelFrame,
    text='Print Gcode '
)
importLabel.pack(side=tk.TOP)
optionsLabel = tk.Label(
    master=labelFrame,
    text='Options'
)
optionsLabel.pack(side=tk.TOP)
exportLabel = tk.Label(
    master=labelFrame,
    text='Export Gcode'
)
exportLabel.pack(side=tk.TOP)

actionsFrame = tk.Frame(
  master=window,
  borderwidth=1
)
actionsFrame.grid(row=0, column=1)
importGcodeButton = tk.Button(
    master=actionsFrame,
    text='Select file',
    command=selectImportGcodeFile
)
importGcodeButton.pack(side=tk.TOP)
importOptionsButton = tk.Button(
    master=actionsFrame,
    text='Select file',
    command=selectOptionsFile
)
importOptionsButton.pack(side=tk.TOP)
exportGcodeButton = tk.Button(
    master=actionsFrame,
    text='Select file',
    command=selectExportGcodeFile
)
exportGcodeButton.pack(side=tk.TOP)

def startPostProcess():
  createIsoline()
  createReplacementColor()
  process(inputFile=userOptions[IMPORT_GCODE_FILENAME], outputFile=userOptions[EXPORT_GCODE_FILENAME])

startPostProcessButton = tk.Button(
    master=actionsFrame,
    text='Post Process',
    command=startPostProcess
)
startPostProcessButton.pack(side=tk.TOP)

window.mainloop()