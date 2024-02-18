# MFPP Minimal Toolchange G-code File

You must supply MFPP a file containing a minimal toolchange G-code sequence for your printer.

This toolchange is used when a toolchange is needed but the existing Prime Tower and toolchange G-code cannot be located or used.

## Requirements

1. The location for next extruder index (the tool/filament/color being switched to) **must** be replaced with `XX` in this text file. MFPP will replace all instances of `XX` with the next extruder index. *E.g. When switching to extruder 1, `TXX` will become `T1`*

2. It is recommended to convert moves that change depending on the current print progress from absolute to relative.

Premade minimal toolchange files are located in the [`minimal_toolchanges`](minimal_toolchanges/) directory. Every 3D printer is different and you should manually verify that the provided G-code is compatible with your printer.

## Toolchange G-code in Firmware or Slicer?

The movement commands to perform the toolchange can be set within firmware or the slicer.

I recommend setting your toolchange G-code within firmware as a macro in Marlin or Klipper. The firmware will handle both the hotend offset and toolchange which simplifies the process. Then all you need to do to perform a toolchange write/send the [`T` command](https://marlinfw.org/docs/gcode/T.html) with the extruder index after it like `T0` or `T1`.

If you would like to contribute your tested toolchange G-Code, please make a pull request on this Github repo.
