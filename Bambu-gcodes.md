# Bambu G-code list

Non-standard Bambu G-code that has undocumented parameters or deviates from [Marlin G-code](https://marlinfw.org/docs/gcode).

Please contribute edits and corrections with a [pull request](https://github.com/ansonl/mfm/pulls) or [issue](https://github.com/ansonl/mfm/issues).

More guesses can be found on this [thread](https://forum.bambulab.com/t/bambu-lab-x1-specific-g-code/666).

## M106 - Set Fan Speed

| Parameter    | Notes | Related flags |
| -------- | ------- | ------- |
| none | Part cooling fan | |
| P1 | Hotend cooling fan | |
| P2 | Remote part cooling/big fan | |
| P3 | Chamber fan | `support_air_filtration` |
| S | speed |

## M620 - AMS Toolchange

Bambu AMS Toolchange

| Parameter    | Notes |
| -------- | ------- |
| SXXA | Switch to XX filament. `M620 M` previous line and four spaces on next lines for conditional execution if AMS exists and material switched.  |
| S255 | pull back filament to AMS |
| .1 E F523 T240 | Switch to XX filament |

## M620.1 - AMS Do Toolchange

| Parameter    | Notes |
| -------- | ------- |
| E | |
| F523 | Filament extrude feedrate |
| TXX | Extruder temperature XX |

## M621 - AMS Toolchange

Bambu AMS Toolchange

| Parameter    | Notes |
| -------- | ------- |
| SXXA | Switch to XX filament |

## M622 conditional after M1002

Gcode between `M622`` and `M623`` runs if timelapse is on.

| Parameter    | Values | Notes |
| -------- | ------- | ------- |
| J | 0 1 | conditional |

## M623 jump location for conditional

## M624 - Stop main part

| Parameter    | Values | Notes |
| -------- | ------- | ------- |
| AQAAAAAAAAA= | | |

## M625 - Start main part

## M900 - Set flow

| Parameter    | Values |  Notes |
| -------- | ------- | ------- |
| K | |
| M | `outer_wall_volumetric_speed/(1.75*1.75/4*3.14)*0.02` |

## M901 end smooth timelapse at safe pos

| Parameter    | Values |  Notes |
| -------- | ------- | ------- |
| S | 0 |
| P | -1 |  |

## M960 - laser

See [thread](https://forum.bambulab.com/t/bambu-lab-x1-specific-g-code/666) for `M960``

| Parameter    | Values |  Notes |
| -------- | ------- | ------- |
| S | | |
| P | |

## M969 - scanning

| Parameter    | Values |  Notes |
| -------- | ------- | ------- |
| S | 0 1 2 |
| P | 0 1 |

## M971 - scanning

| Parameter    | Values |  Notes |
| -------- | ------- | ------- |
| S | 5 |
| P | 2 |

## M973

| Parameter    | Values |  Notes |
| -------- | ------- | ------- |
| S | 4 | turn off scanner |

## M975

| Parameter    | Values |  Notes |
| -------- | ------- | ------- |
| S | 1 | `turn on mech mode supression` |

## M991 - notify layer change

`M991` notifies printer display of layer change.

| Parameter | Values |  Notes |
| -------- | ------- | ------- |
| S | 0 | |
| P | 0 | |

## M1002 - judge_last_extrude_cali_success / gcode_claim_action : 0

See [thread](https://forum.bambulab.com/t/bambu-lab-x1-specific-g-code/666)

| Parameter | Values |  Notes |
| -------- | ------- | ------- |
| set_gcode_claim_speed_level | 0 | showhide message on screen |

## T - ~~Select~~ or Report Tool

`T` command tells the printer which filament (tool) is now selected.

Bambu firmware does not do the toolchange with `T` command. The actual toolchange with AMS uses the M620 command.

| Parameter    | Notes |
| -------- | ------- |
| 255 | Switch to empty tool |
| 1000 | change to nozzle space |
| 1100 | change to scanning space on X1 |

