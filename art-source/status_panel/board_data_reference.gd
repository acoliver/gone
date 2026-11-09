extends RefCounted

const SIZE := Vector2i(2560, 1080)
const SYSTEMS := [
	{"category":"POWER", "native":"te na nawa lina", "es":"ENERGÍA PRINCIPAL", "state":"palo", "source":"docs/design/biblia.md §§10, 30; docs/design/ship-systems-and-security.md §4"},
	{"category":"POWER", "native":"te mu nawa lina", "es":"ENERGÍA SECUNDARIA", "state":"shenu", "source":"docs/design/language/nalesha-reference.md glossary 464; app/power_room.gd built secondary generator powers this room"},
	{"category":"COMPUTING / NETWORK", "native":"chena lina", "es":"RED DE LA NAVE", "state":"palo", "source":"docs/design/biblia.md §10; docs/design/ship-systems-and-security.md §7"},
	{"category":"COMPUTING / NETWORK", "native":"taka chena lina", "es":"RED DE EMERGENCIA", "state":"palo", "source":"docs/design/biblia.md §10; docs/design/ship-systems-and-security.md §7"},
	{"category":"COMPUTING / NETWORK", "native":"kimela lina", "es":"COMPUTADORAS DE LA NAVE", "state":"palo", "source":"docs/design/biblia.md §§10–11, 30"},
	{"category":"COMPUTING / NETWORK", "native":"te mu kimela lina", "es":"COMPUTADORAS SECUNDARIAS", "state":"palo", "source":"docs/design/biblia.md §§10, 30; nalesha-reference.md §Compounds"},
	{"category":"PROPULSION", "native":"wesha kama", "es":"MOTOR S", "state":"palo", "source":"docs/design/language/nalesha-reference.md glossary 221; docs/design/biblia.md §7; duplicate S-drive row merged"},
	{"category":"PROPULSION", "native":"chalu kama", "es":"MOTOR H", "state":"palo", "source":"docs/design/language/nalesha-reference.md glossary 222; docs/design/biblia.md §7"},
	{"category":"SENSORS", "native":"pama shoketa", "es":"SENSORES INTERNOS", "state":"palo", "source":"docs/design/biblia.md §34; docs/design/ship-systems-and-security.md §7"},
	{"category":"SENSORS", "native":"te mu pama shoketa", "es":"SENSORES INTERNOS SECUNDARIOS", "state":"palo", "source":"docs/design/biblia.md §34; secondary sensor compound proposed"},
	{"category":"SENSORS", "native":"showi shoketa", "es":"SENSORES EXTERNOS", "state":"palo", "source":"docs/design/biblia.md §10; docs/art/ship/README.md"},
	{"category":"SENSORS", "native":"te mu showi shoketa", "es":"SENSORES EXTERNOS SECUNDARIOS", "state":"palo", "source":"docs/design/biblia.md §10; secondary sensor compound proposed"},
	{"category":"SAFETY", "native":"kelawa pasha lina", "es":"EXTINCIÓN DE INCENDIOS", "state":"palo", "source":"docs/design/language/nalesha-reference.md §Project additions: fire vocabulary; docs/design/biblia.md §§8, 36; docs/design/ship-systems-and-security.md §9"},
	{"category":"LIFE SUPPORT", "native":"talu lina", "es":"SOPORTE VITAL", "state":"palo", "source":"docs/design/language/nalesha-reference.md glossary 129; docs/design/biblia.md §§10, 31"}
]
const CATEGORIES := [
	{"name":"ENERGÍA", "native":"nawa", "systems":[0, 1]},
	{"name":"CÓMPUTO / RED", "native":"kimela chena", "systems":[2, 3, 4, 5]},
	{"name":"SENSORES", "native":"shoketa", "systems":[8, 9, 10, 11]},
	{"name":"PROPULSIÓN", "native":"kama", "systems":[6, 7]},
	{"name":"SEGURIDAD", "native":"tewe", "systems":[12]},
	{"name":"SOPORTE VITAL / ENTORNO", "native":"talu", "systems":[13]}
]
const HEADER := {"native":"malu mishela", "es":"MAPA DE LA NAVE"}
const DAMAGE := {"native":"mo lokemi malu", "es":"SIN DAÑOS EN LA NAVE"}
const EXTERNAL_SENSORS := {"native":"showi shoketa palo", "es":"SENSORES EXTERNOS INACTIVOS"}
const HERE := {"native":"wupo to lometa [16] pama", "es":"CUBIERTA 14 · USTED ESTÁ AQUÍ"}
const DECK_LABELS := [
	{"deck":1, "native":"lometa [1]", "es":"1"},
	{"deck":5, "native":"lometa [5]", "es":"5"},
	{"deck":10, "native":"lometa [12]", "es":"10"},
	{"deck":14, "native":"lometa [16]", "es":"14"},
	{"deck":20, "native":"lometa [24]", "es":"20"},
	{"deck":25, "native":"lometa [31]", "es":"25"},
	{"deck":30, "native":"lometa [36]", "es":"30"}
]
const BOARD := {"native":"te mu nawa lina shenu", "es":"SISTEMA SECUNDARIO ACTIVO"}
