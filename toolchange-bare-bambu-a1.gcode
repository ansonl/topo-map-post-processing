; stop printing object, unique label id: X
M625
; LAYER_HEIGHT: X
; FEATURE: Prime tower
; LINE_WIDTH: 0.500000
;--------------------
; CP TOOLCHANGE START
; toolchange #X
; material : PLA -> PLA
;--------------------
M220 S100
; WIPE_TOWER_START
; filament end gcode 
M106 P3 S0

G1 E-1.2 F1800
;===== machine: A1 =========================
;===== date: 20231012 =======================
G392 S0
M620 SXXA
M204 S9000

G17
; lift by 2.6mm
;G2 Z7 I0.86 J0.86 P1 F10000 ; spiral lift a little from second lift
G2 I0.86 J0.86 P1 F10000
G91
G1 Z2.6
G90

M400
M106 P1 S0
M106 P2 S0

M104 S220


G1 X267 F18000
;
M620.1 E F523 T240
TXX
M620.1 E F523 T240

G1 Y128 F9000


M400

G92 E0

; FLUSH_START
; always use highest temperature to flush
M400
M1002 set_filament_type:UNKNOWN
M109 S240
M106 P1 S60

G1 E23.7 F523 ; do not need pulsatile flushing for start part
G1 E0.690105 F50
G1 E7.9362 F523
G1 E0.690105 F50
G1 E7.9362 F523
G1 E0.690105 F50
G1 E7.9362 F523
G1 E0.690105 F50
G1 E7.9362 F523

; FLUSH_END
G1 E-2 F1800
G1 E2 F300
M400
M1002 set_filament_type:UNKNOWN



; WIPE
M400
M106 P1 S178
M400 S3
M73 P20 R120
G1 X-38.5 F18000
G1 X-48.5 F3000
G1 X-38.5 F18000
G1 X-48.5 F3000
G1 X-38.5 F18000
G1 X-48.5 F3000
M400
M106 P1 S0



M106 P1 S60
; FLUSH_START
G1 E10.4769 F523
G1 E1.1641 F50
G1 E10.4769 F523
G1 E1.1641 F50
G1 E10.4769 F523
G1 E1.1641 F50
G1 E10.4769 F523
G1 E1.1641 F50
G1 E10.4769 F523
G1 E1.1641 F50
; FLUSH_END
G1 E-2 F1800
G1 E2 F300










M400
M106 P1 S60
M109 S220
G1 E6 F523 ;Compensate for filament spillage during waiting temperature
M400
G92 E0
G1 E-2 F1800
M400
M106 P1 S178
M400 S3
G1 X-38.5 F18000
G1 X-48.5 F3000
G1 X-38.5 F18000
G1 X-48.5 F3000
G1 X-38.5 F18000
G1 X-48.5 F3000
M73 P21 R120
G1 X-38.5 F18000
M400
;G1 Z9.6 F3000
M106 P1 S0

M204 S6000


M621 SXXA
G392 S1
M106 S173.4
M106 P2 S178

; filament start gcode
M106 P3 S200

; CP TOOLCHANGE WIPE

; WIPE_TOWER_END
G92 E0
; CP TOOLCHANGE END
;------------------



; WIPE_START
; WIPE_END
G1 E-.04 F1800
; start printing object, unique label id: 90
M624 AQAAAAAAAAA=
;G1 X183.591 Y232.687 Z7 F42000
;G1 X118.138 Y127.553 Z7
G91
G1 Z-2.6 F30000
G90

;G1 Z6.6 ;restore Z
G1 E.8 F1800