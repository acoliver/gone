shader_type spatial;
render_mode cull_back;
varying vec3 local_position;
float hash(vec2 p) { return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
float noise(vec2 p) {
    vec2 b=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
    return mix(mix(hash(b),hash(b+vec2(1,0)),f.x),mix(hash(b+vec2(0,1)),hash(b+vec2(1,1)),f.x),f.y);
}
void vertex() { local_position=VERTEX; }
void fragment() {
    vec2 p=local_position.xy;
    float band=step(0.50,fract((p.x+p.y)*8.0));
    float torn=noise(p*43.0+vec2(4,17))*0.65+noise(p*181.0)*0.35;
    float peel=smoothstep(0.48,0.67,torn);
    float edge=smoothstep(0.045,0.080,abs(p.y))*(0.4+0.6*noise(p*87.0));
    vec3 yellow=vec3(0.19,0.125,0.038)*(0.78+0.27*noise(p*113.0));
    vec3 black=vec3(0.015,0.012,0.008);
    ALBEDO=mix(mix(yellow,black,band),vec3(0.075,0.032,0.012),max(peel*0.85,edge));
    ROUGHNESS=0.98;
    METALLIC=0.0;
    SPECULAR=0.2;
}
