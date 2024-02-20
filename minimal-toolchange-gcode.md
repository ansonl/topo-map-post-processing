# MFPP Minimal Toolchange G-code File

You must supply MFPP a file containing a minimal toolchange G-code sequence for your printer.

This toolchange is used when a toolchange is needed but the existing Prime Tower and toolchange G-code cannot be located or used.

## Premade Minimal Toolchanges

> **Note:** Premade minimal toolchanges' temperatures are set up for PLA material. Modify the `M104`, `M109`, and `M620.1` command temperature parameters with your material temperature settings.

Premade minimal toolchange files can be downloaded from the [`minimal_toolchanges`](minimal_toolchanges/) directory.

Current premade printer toolchanges:

- Generic (firmware managed tool change)
- Bambu X1 series
- Bambu P1 series
- Bambu A1
- Bambu A1 mini
- Prusa XL

Every 3D printer is different and you should manually verify that the provided G-code is compatible with your printer.

## Requirements to Create a Minimal Toolchange

1. The location for next extruder index (the tool/filament/color being switched to) **must** be replaced with `XX` in this text file. MFPP will replace all instances of `XX` with the next extruder index. *E.g. When switching to extruder 1, `TXX` will become `T1`*

2. It is recommended to convert moves that change depending on the current print progress from absolute to relative.

3. All movements that are specific to a specific model must be removed or generalized to not interfere with printed models possibly being located anywhere in the print volume.

## Toolchange Movements in Firmware or Slicer?

The movement commands to perform the toolchange can be set and managed within firmware or the slicer.

I highly recommend setting your toolchange G-code within firmware as a macro in Marlin or Klipper. The firmware will handle both the hotend offset and toolchange which simplifies the process. Then all you need to do to perform a toolchange write/send the [`T` command](https://marlinfw.org/docs/gcode/T.html) with the extruder index after it like `T0` or `T1`.

With toolchange movements properly setup in firmware, a toolchange becomes as simple as the below.

```gcode
; Single-extruder Toolchange
TXX

; Multi-extruder Toolchange
M104 S170     ; Set the active hotend to the standby temperature
M104 S210 TXX ; Set the next hotend index to the print/purge temperature
TXX           ; Execute the tool change
M109 S210     ; Wait for next (now active) hotend to warm up 
```

A properly set up tool change g-code in firmware example for a multi-extruder 3D printer can be seen for the Ultimaker DXUv2 [here](https://github.com/ansonl/DXU/blob/master/Firmware/README.md#toolchange-g-code).

## Contributing

If you would like to contribute your tested toolchange G-Code, please make a pull request on this Github repo.
