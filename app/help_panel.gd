class_name HelpPanel
extends CanvasLayer

const ACTION_LABELS := {
	&"move_forward": "Avanzar", &"move_back": "Retroceder",
	&"move_left": "Moverse a la izquierda", &"move_right": "Moverse a la derecha",
	&"activate": "Levantarse de la cápsula", &"interact": "Usar / subir o bajar de la escalera",
	&"look_left": "Mirar a la izquierda", &"look_right": "Mirar a la derecha",
	&"look_up": "Mirar arriba", &"look_down": "Mirar abajo",
	&"climb_up": "Subir por la escalera", &"climb_down": "Bajar por la escalera",
	&"release_cursor": "Liberar el cursor mientras se mantiene pulsado",
	&"help": "Abrir / cerrar esta ayuda",
}

const KEY_NAMES := {
	KEY_SPACE: "Espacio", KEY_COMMA: ",", KEY_PERIOD: ".",
	KEY_UP: "Flecha arriba", KEY_DOWN: "Flecha abajo",
	KEY_LEFT: "Flecha izquierda", KEY_RIGHT: "Flecha derecha",
	KEY_TAB: "Tab", KEY_ESCAPE: "Esc",
}
const MOUSE_NAMES := {
	MOUSE_BUTTON_LEFT: "Clic izquierdo", MOUSE_BUTTON_RIGHT: "Clic derecho",
	MOUSE_BUTTON_MIDDLE: "Clic central", MOUSE_BUTTON_WHEEL_UP: "Rueda arriba",
	MOUSE_BUTTON_WHEEL_DOWN: "Rueda abajo",
}

var player: Player
var close_button: Button
var _overlay: Control
var _opened := false

static func key_name(code: Key) -> String:
	return KEY_NAMES.get(code, OS.get_keycode_string(code))

static func binding_name(event: InputEvent) -> String:
	if event is InputEventKey:
		return key_name(event.physical_keycode if event.physical_keycode != KEY_NONE else event.keycode)
	if event is InputEventMouseButton:
		assert(MOUSE_NAMES.has(event.button_index), "mouse binding needs a Spanish display name")
		return MOUSE_NAMES[event.button_index]
	assert(false, "gameplay binding needs a display-name mapping")
	return ""

static func build(rig: Player) -> HelpPanel:
	var help := HelpPanel.new()
	help.name = "ControlsHelp"
	help.player = rig
	help.layer = 200
	help.process_mode = Node.PROCESS_MODE_ALWAYS
	return help

static func controls() -> Dictionary:
	var rows: Dictionary = {}
	for action: StringName in InputMap.get_actions():
		if String(action).begins_with("ui_"): continue
		var bindings: PackedStringArray = []
		for event: InputEvent in InputMap.action_get_events(action): bindings.append(binding_name(event))
		rows[action] = "%s: %s" % [ACTION_LABELS.get(action, String(action).capitalize()), " / ".join(bindings)]
	rows[&"mouse_look"] = "Mover el ratón: mirar alrededor"
	var click := InputEventMouseButton.new()
	click.button_index = Player.PICK_BUTTON
	rows[&"mouse_pick"] = "%s: caminar al punto elegido o usar el objeto" % binding_name(click)
	rows[&"escape"] = "%s: liberar el cursor / cerrar esta ayuda" % key_name(Player.RELEASE_KEY)
	return rows

func _ready() -> void:
	_overlay = Control.new()
	_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_overlay.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(_overlay)
	var shade := ColorRect.new()
	shade.color = Color(0, 0, 0, 0.72)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_overlay.add_child(shade)
	var center := CenterContainer.new()
	_overlay.add_child(center)
	var resize := func() -> void:
		var viewport := get_viewport().get_visible_rect().size
		var factor := minf(viewport.x / 1152, viewport.y / 648)
		center.scale = Vector2.ONE * factor
		center.size = viewport / factor
	get_viewport().size_changed.connect(resize)
	resize.call()
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(660, 0)
	var steel := StyleBoxFlat.new()
	steel.bg_color = Color(0.065, 0.075, 0.085)
	steel.border_color = Color(0.32, 0.35, 0.37)
	steel.set_border_width_all(2)
	steel.content_margin_left = 24
	steel.content_margin_right = 24
	steel.content_margin_top = 18
	steel.content_margin_bottom = 18
	panel.add_theme_stylebox_override("panel", steel)
	center.add_child(panel)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 6)
	panel.add_child(column)
	var heading := Label.new()
	heading.text = "Controles"
	heading.add_theme_font_size_override("font_size", 26)
	column.add_child(heading)
	var note := Label.new()
	note.text = "Juego en pausa. F1 o Esc para volver."
	note.add_theme_font_size_override("font_size", 16)
	column.add_child(note)
	var list := VBoxContainer.new()
	list.add_theme_constant_override("separation", 3)
	column.add_child(list)
	for line: String in controls().values():
		var label := Label.new()
		label.text = line
		label.add_theme_font_size_override("font_size", 17)
		label.add_theme_color_override("font_color", Color(0.90, 0.92, 0.93))
		list.add_child(label)
	close_button = Button.new()
	close_button.text = "Cerrar"
	close_button.custom_minimum_size.y = 36
	close_button.pressed.connect(close)
	column.add_child(close_button)
	_overlay.hide()

func _input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo: return
	if event.is_action_pressed("help"):
		if _opened: close()
		else: open()
		get_viewport().set_input_as_handled()
	elif _opened and event.physical_keycode == Player.RELEASE_KEY:
		close()
		get_viewport().set_input_as_handled()

func open() -> void:
	assert(not _opened, "help opens once per key edge")
	_opened = true
	player.clear_device_input(false)
	get_tree().paused = true
	_overlay.show()
	close_button.grab_focus()

func close() -> void:
	assert(_opened, "only an open help panel can close")
	_overlay.hide()
	_opened = false
	player.clear_device_input(true)
	get_tree().paused = false
