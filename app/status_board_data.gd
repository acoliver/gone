class_name StatusBoardData
extends RefCounted

const SYSTEMS: Array[Dictionary] = [
	{"native": "te na nawa lina", "perceived_es": "ENERGÍA PRINCIPAL", "state": "palo"},
	{"native": "te mu nawa lina", "perceived_es": "ENERGÍA SECUNDARIA", "state": "shenu"},
	{"native": "chena lina", "perceived_es": "RED DE LA NAVE", "state": "palo"},
	{"native": "taka chena lina", "perceived_es": "RED DE EMERGENCIA", "state": "palo"},
	{"native": "kimela lina", "perceived_es": "COMPUTADORAS DE LA NAVE", "state": "palo"},
	{"native": "te mu kimela lina", "perceived_es": "COMPUTADORAS SECUNDARIAS", "state": "palo"},
	{"native": "wesha kama", "perceived_es": "MOTOR S", "state": "palo"},
	{"native": "chalu kama", "perceived_es": "MOTOR H", "state": "palo"},
	{"native": "pama shoketa", "perceived_es": "SENSORES INTERNOS", "state": "palo"},
	{"native": "te mu pama shoketa", "perceived_es": "SENSORES INTERNOS SECUNDARIOS", "state": "palo"},
	{"native": "showi shoketa", "perceived_es": "SENSORES EXTERNOS", "state": "palo"},
	{"native": "te mu showi shoketa", "perceived_es": "SENSORES EXTERNOS SECUNDARIOS", "state": "palo"},
	{"native": "kelawa pasha lina", "perceived_es": "EXTINCIÓN DE INCENDIOS", "state": "palo"},
	{"native": "talu lina", "perceived_es": "SOPORTE VITAL", "state": "palo"},
]
const HEADER := {"native": "malu mishela", "perceived_es": "MAPA DE LA NAVE"}
const DAMAGE := {"native": "mo lokemi malu", "perceived_es": "SIN DAÑOS EN LA NAVE"}
const HERE := {"native": "wupo to lometa [16] pama", "perceived_es": "CUBIERTA 14 · USTED ESTÁ AQUÍ"}

static func running_system_count() -> int:
	var count := 0
	for system: Dictionary in SYSTEMS:
		if system.state == "shenu":
			count += 1
	return count

static func native_text() -> PackedStringArray:
	var lines := PackedStringArray([HEADER.native, DAMAGE.native, HERE.native])
	for system: Dictionary in SYSTEMS:
		lines.append(system.native)
	return lines
