shader_type spatial;
render_mode cull_back;
varying vec3 local_position;
void vertex() { local_position=VERTEX; }
void fragment() {
    float band=step(0.50,fract((local_position.x+local_position.y)*14.0));
    float wear=fract(sin(dot(floor(local_position.xy*180.0),vec2(12.9898,78.233)))*43758.5453);
    vec3 yellow=vec3(0.23,0.14,0.035);
    vec3 black=vec3(0.014,0.010,0.007);
    ALBEDO=mix(mix(yellow,black,band),vec3(0.07,0.026,0.009),step(0.86,wear)*0.70);
    ROUGHNESS=0.98;
    METALLIC=0.0;
}
