extends SceneTree
## Headless machine check of the issue #45 probe captures: decodes
## tmp/pipeline/probe-capsule.png (red lane) and
## tmp/pipeline/probe-capsule-neutral.png (neutral lane) and measures
## per-pixel brightness (mean of the r8/g8/b8 channels, the repo capture
## lanes' convention): overall mean, the fraction of pixels that differ
## strongly from near-black, and the fraction of structured bright pixels.
## Each lane also carries a hue gate: the red lane's bright pixels must be
## red-dominant (the red OmniLight reaching the pod), the neutral lane's
## bright pixels must be near-neutral (the off-white shell under white
## light). Exits 0 only when both captures are non-black (mean > 8/255),
## structured (at least 1.5% of pixels above 60/255 brightness, i.e. a
## pod-sized lit region), and hue-correct.
## Run: godot --headless --path . -s assets/props/probe/probe_check.gd

const RED_CAPTURE_PATH: String = "tmp/pipeline/probe-capsule.png"
const NEUTRAL_CAPTURE_PATH: String = "tmp/pipeline/probe-capsule-neutral.png"
const NEAR_BLACK_BRIGHTNESS: float = 30.0
const BRIGHT_BRIGHTNESS: float = 60.0
const MIN_MEAN: float = 8.0
const MIN_STRUCTURE_FRACTION: float = 0.015
const MIN_BRIGHT_FRACTION: float = 0.005
const RED_DOMINANCE: float = 20.0
const NEUTRAL_SPREAD_FRACTION: float = 0.30

func _init() -> void:
	var ok := true
	ok = _check(RED_CAPTURE_PATH, "red", true) and ok
	ok = _check(NEUTRAL_CAPTURE_PATH, "neutral", false) and ok
	if ok:
		print("RESULT OK")
	quit(0 if ok else 1)

func _check(path: String, label: String, expect_red: bool) -> bool:
	var image := Image.new()
	var resolved := ProjectSettings.globalize_path(path)
	if image.load(resolved) != OK:
		print("RESULT FAIL cannot load %s" % resolved)
		return false
	image.convert(Image.FORMAT_RGBA8)
	var pixels := image.get_width() * image.get_height()
	var data := image.get_data()
	var brightness_sum: float = 0.0
	var non_near_black: int = 0
	var bright: int = 0
	var hue_ok: int = 0
	for index: int in range(pixels):
		var offset := index * 4
		var r := float(data[offset])
		var g := float(data[offset + 1])
		var b := float(data[offset + 2])
		var brightness := (r + g + b) / 3.0
		brightness_sum += brightness
		if brightness > NEAR_BLACK_BRIGHTNESS:
			non_near_black += 1
		if brightness > BRIGHT_BRIGHTNESS:
			bright += 1
			# Bright-pixel hue gate: red lane needs r clearly above g/b;
			# neutral lane needs the channel spread small against
			# brightness (off-white shell, not a colored wash).
			if expect_red:
				if r - maxf(g, b) > RED_DOMINANCE:
					hue_ok += 1
			elif maxf(maxf(r, g), b) - minf(minf(r, g), b) <= NEUTRAL_SPREAD_FRACTION * brightness:
				hue_ok += 1
	var mean := brightness_sum / float(pixels)
	var non_near_black_fraction := float(non_near_black) / float(pixels)
	var bright_fraction := float(bright) / float(pixels)
	var hue_ok_fraction := float(hue_ok) / float(pixels)
	print("STAT lane=%s pixels=%d mean=%.2f/255 non_near_black=%.4f bright=%.4f hue_ok=%.4f" % [
		label, pixels, mean, non_near_black_fraction, bright_fraction, hue_ok_fraction])
	if mean <= MIN_MEAN:
		print("RESULT FAIL %s lane mean %.2f <= %.1f/255: capture is black" % [
			label, mean, MIN_MEAN])
		return false
	if bright_fraction < MIN_STRUCTURE_FRACTION:
		print("RESULT FAIL %s lane bright fraction %.4f < %.4f: no pod-sized lit region" % [
			label, bright_fraction, MIN_STRUCTURE_FRACTION])
		return false
	if hue_ok_fraction < MIN_BRIGHT_FRACTION:
		print("RESULT FAIL %s lane hue_ok fraction %.4f < %.4f: lit region is the wrong hue" % [
			label, hue_ok_fraction, MIN_BRIGHT_FRACTION])
		return false
	return true
