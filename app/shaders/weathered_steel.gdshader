shader_type spatial;
render_mode cull_back;
#include "steel_sampling.gdshaderinc"
uniform sampler2D albedo_a : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D albedo_b : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D albedo_c : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D normal_a : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D normal_b : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D normal_c : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D orm_a : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D orm_b : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D orm_c : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D oxide_grain : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D oxide_normal : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
uniform float gain = 0.30;
uniform vec3 colour_gain = vec3(1.0);
uniform float contrast = 1.2;
uniform float macro = 0.2;
uniform float seam_strength = 0.65;
uniform bool hatch_surface = false;
uniform bool leaf_paint = false;
uniform float wheel_height = 1.15;
uniform bool raised_base = false;
uniform bool hero_wheel = false;
uniform bool leaf_hardware = false;
uniform sampler2D leaf_weather : repeat_disable, filter_linear_mipmap;
uniform bool wheel_surface = false;
uniform bool wheel_only = false;
uniform bool floor_surface = false;
uniform bool rivet_surface = false;
uniform bool edge_surface = false;
uniform bool curved_surface = false;
uniform bool baked_hatch = false;
uniform float hatch_detail_pitch = 0.20;
uniform vec3 hatch_colour_gain = vec3(1.0);
uniform sampler2D hatch_painted : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_albedo : source_color, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_normal : hint_normal, repeat_disable, filter_linear_mipmap_anisotropic;
uniform sampler2D baked_orm : repeat_disable, filter_linear_mipmap_anisotropic;
uniform vec2 panel_pitch = vec2(1.5, 1.0);
instance uniform vec4 surface_x = vec4(1,0,0,0);
instance uniform vec4 surface_y = vec4(0,1,0,0);
instance uniform vec4 surface_z = vec4(0,0,1,0);
instance uniform vec3 seed_offset = vec3(0);
instance uniform vec4 lateral_bounds = vec4(-1,1,-1,1);
instance uniform vec2 aperture = vec2(1.08,2.4);
instance uniform float floor_datum = 0.0;
varying vec3 wp;
varying vec3 wn;
float hash(vec3 p) { return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453); }
float noise(vec3 p) {
    vec3 b=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
    return mix(mix(mix(hash(b),hash(b+vec3(1,0,0)),f.x),mix(hash(b+vec3(0,1,0)),hash(b+vec3(1,1,0)),f.x),f.y),
               mix(mix(hash(b+vec3(0,0,1)),hash(b+vec3(1,0,1)),f.x),mix(hash(b+vec3(0,1,1)),hash(b+vec3(1,1,1)),f.x),f.y),f.z);
}
void vertex() {
    vec4 world = MODEL_MATRIX * vec4(VERTEX, 1.0);
    wp = vec3(dot(surface_x, world), dot(surface_y, world), dot(surface_z, world));
    vec3 normal_world = normalize(MODEL_NORMAL_MATRIX * NORMAL);
    wn = vec3(dot(surface_x.xyz, normal_world), dot(surface_y.xyz, normal_world), dot(surface_z.xyz, normal_world));
}
vec3 hatch_tone(vec3 colour, float saturation, float value) {
    colour = max(mix(vec3(max(colour.r, max(colour.g, colour.b))), colour, saturation), vec3(0.0)) * value;
    float luminance = dot(colour, vec3(0.2126, 0.7152, 0.0722));
    return colour * min(1.0, 0.105 / max(luminance, 0.0001));
}
void fragment() {
    if (baked_hatch) {
        vec3 masks = texture(baked_albedo, UV).rgb;
        vec3 weather = texture(baked_orm, UV).rgb;
        vec3 n = normalize(wn);
        vec3 signs = mix(vec3(-1.0), vec3(1.0), step(vec3(0.0), n));
        vec3 weights = pow(abs(n), vec3(4.0));
        weights /= dot(weights, vec3(1.0));
        // Scan coordinates belong to the moving leaf, wheel or fixed frame,
        // independent of atlas packing and room/world placement.
        vec3 steel = scan_sample(albedo_a, wp, signs, weights, hatch_detail_pitch, vec2(0));
        vec3 paint = scan_sample(albedo_b, wp, signs, weights, hatch_detail_pitch, vec2(0));
        vec3 oxide = scan_sample(albedo_c, wp, signs, weights, hatch_detail_pitch, vec2(0));
        vec3 base = hatch_tone(steel, 0.80, 0.78);
        vec3 colour = mix(base, hatch_tone(oxide, 1.0, 0.70), masks.g);
        colour = mix(colour, mix(base, hatch_tone(paint, 0.65, 0.70), 0.45), masks.r);
        colour = mix(colour, mix(vec3(max(steel.r, max(steel.g, steel.b))), steel, 0.20), masks.b);
        // Warning paint uses an analytic diagonal at physical scale. Mask
        // interpolation cannot erase its alternating yellow and black fields.
        float stripe = step(0.48, fract((wp.x + wp.y) / 0.12));
        float intact = smoothstep(0.035, 0.065, dot(steel, vec3(0.2126, 0.7152, 0.0722)));
        vec3 warning = mix(vec3(0.004, 0.003, 0.002), vec3(0.32, 0.20, 0.045), stripe);
        colour = mix(colour, warning * (0.80 + 0.20 * steel), weather.b * intact);
        vec2 paint_uv = clamp(UV2, vec2(0.004), vec2(0.996));
        if (COLOR.r > 0.5) {
            paint_uv = vec2(paint_uv.x * 0.5 + step(0.5, COLOR.g) * 0.5, paint_uv.y * 0.53125);
        } else {
            paint_uv = vec2(paint_uv.x, 0.53125 + paint_uv.y * 0.46875);
        }
        vec4 painted = texture(hatch_painted, paint_uv);
        float paint_owner = max(COLOR.r, COLOR.b);
        float paint_edge = min(min(UV2.x, 1.0 - UV2.x), min(UV2.y, 1.0 - UV2.y));
        float edge_wear = (1.0 - smoothstep(0.002, 0.014, paint_edge)) * COLOR.r;
        // The image already contains paint failure, oxide and grime. Only the
        // physical perimeter exposes additional steel; AO remains ambient-only.
        vec3 painted_colour = mix(painted.rgb, base, edge_wear);
        colour = max(mix(vec3(max(colour.r, max(colour.g, colour.b))), colour, mix(1.22, 1.0, weather.b)), vec3(0.0));
        colour *= 1.0 - weather.g;
        ALBEDO = mix(colour, painted_colour, paint_owner) * hatch_colour_gain;
        vec3 orm = mix(scan_sample(orm_a, wp, signs, weights, hatch_detail_pitch, vec2(0)), scan_sample(orm_c, wp, signs, weights, hatch_detail_pitch, vec2(0)), masks.g);
        orm = mix(orm, scan_sample(orm_b, wp, signs, weights, hatch_detail_pitch, vec2(0)), masks.r);
        vec3 grain = mix(scan_normal(normal_a, wp, signs, weights, hatch_detail_pitch, vec2(0)), scan_normal(normal_c, wp, signs, weights, hatch_detail_pitch, vec2(0)), masks.g);
        grain = mix(grain, scan_normal(normal_b, wp, signs, weights, hatch_detail_pitch, vec2(0)), masks.r);
        mat3 world_from_surface = mat3(surface_x.xyz, surface_y.xyz, surface_z.xyz);
        vec3 detail_normal = (VIEW_MATRIX * vec4(world_from_surface * grain, 0.0)).xyz;
        vec3 tangent_normal = bc5_normal(texture(baked_normal, UV).rg);
        NORMAL = normalize(TANGENT * tangent_normal.x + BINORMAL * tangent_normal.y + NORMAL * tangent_normal.z + detail_normal * 0.24);
        float paint_height = painted.a * 0.0015 * paint_owner * (1.0 - edge_wear);
        vec3 dx = dFdx(VERTEX), dy = dFdy(VERTEX);
        vec3 r1 = cross(dy, NORMAL), r2 = cross(NORMAL, dx);
        float determinant = dot(dx, r1);
        vec3 gradient = (dFdx(paint_height) * r1 + dFdy(paint_height) * r2) / (sign(determinant) * max(abs(determinant), 0.00000001));
        NORMAL = normalize(NORMAL - clamp(gradient, vec3(-0.5), vec3(0.5)));
        ROUGHNESS = mix(clamp(orm.g - masks.g * 0.12, 0.24, 0.97), mix(0.91, 0.69, painted.a), paint_owner);
        METALLIC = orm.b * (1.0 - masks.g) * 0.55;
        AO = weather.r;
        AO_LIGHT_AFFECT = 0.0;
        SPECULAR = 0.32;
    } else {
    vec3 n=normalize(wn), an=abs(n);
    vec3 signs=mix(vec3(-1.0), vec3(1.0), step(vec3(0.0),n));
    int axis=an.y>max(an.x,an.z)?1:(an.x>an.z?0:2);
    vec3 weights=axis==0?vec3(1,0,0):(axis==1?vec3(0,1,0):vec3(0,0,1));
    if (curved_surface) { weights=pow(an,vec3(4.0)); weights/=dot(weights,vec3(1.0)); }
    vec2 q=plane_uv(wp,signs,axis);
    vec3 field_position=wp+seed_offset;
    float broad=noise(field_position/3.4+vec3(3,8,1));
    float residual=0.10+0.09*noise(field_position/5.2+vec3(2,4,9));
    float wa=residual*0.64, wb=residual*0.36, wc=1.0-residual;
    vec3 scan=scan_sample(albedo_c,field_position,signs,weights,2.8,vec2(0))*wc
        +scan_sample(albedo_a,field_position,signs,weights,4.7,vec2(0.31,0.67))*wa
        +scan_sample(albedo_b,field_position,signs,weights,3.9,vec2(0.72,0.19))*wb;
    vec3 pn=scan_normal(normal_c,field_position,signs,weights,2.8,vec2(0))*wc
        +scan_normal(normal_a,field_position,signs,weights,4.7,vec2(0.31,0.67))*wa
        +scan_normal(normal_b,field_position,signs,weights,3.9,vec2(0.72,0.19))*wb;
    vec3 orm=scan_sample(orm_c,field_position,signs,weights,2.8,vec2(0))*wc
        +scan_sample(orm_a,field_position,signs,weights,4.7,vec2(0.31,0.67))*wa
        +scan_sample(orm_b,field_position,signs,weights,3.9,vec2(0.72,0.19))*wb;
    float lum=dot(scan,vec3(0.2126,0.7152,0.0722));
    vec3 chroma=scan/max(lum,0.003);
    vec3 steel_chroma=vec3(1.10,1.015,0.91);
    vec3 colour=0.12*pow(clamp(lum/0.12,0.06,4.0),contrast)*steel_chroma;
    colour*=1.0+macro*(broad-0.5)*2.0;
    float plate=hash(vec3(floor(q/panel_pitch),sign(n.x)+sign(n.z)*7.0));
    colour*=hatch_surface?1.0:0.55+plate*0.90;
    vec2 dims=panel_pitch, f=mod(q,dims), border=min(f,dims-f);
    float d=min(border.x,border.y);
    float aa=max(fwidth(q.x),fwidth(q.y))*0.6;
    float seam=1.0-smoothstep(0.003-aa,0.009+aa,d);
    float rusty_edge=exp(-d*30.0);
    float worn=(smoothstep(0.012,0.020,d)-smoothstep(0.030,0.052,d));
    float dx=abs(mod(q.x+0.11,0.22)-0.11), dy=abs(f.y-0.065);
    float rivet_d=length(vec2(dx,dy));
    float rivet=1.0-smoothstep(0.010,0.019+aa,rivet_d);
    float rivet_halo=exp(-rivet_d*40.0);
    float below=mod(0.065-f.y+1.0,1.0);
    float drip_seed=hash(vec3(floor(q.x/0.22),floor(q.y),7.0));
    float runs=exp(-dx*70.0)*exp(-below*(2.7+drip_seed*4.0));
    runs*=0.45+0.55*noise(vec3(q.x*14.0,wp.y*1.1,4));
    float lower=1.0-smoothstep(0.05,0.90,wp.y-floor_datum);
    float corner=1.0-smoothstep(0.02,0.30,min(min(wp.x-lateral_bounds.x,lateral_bounds.y-wp.x),min(wp.z-lateral_bounds.z,lateral_bounds.w-wp.z)));
    float relief=0.0;
    if(hatch_surface) {
        vec2 p=wp.xy;
        float leaf_width=aperture.x, leaf_height=aperture.y;
        float perimeter=min(min(abs(p.x-0.09),abs(p.x-(leaf_width-0.09))),min(abs(p.y-0.19),abs(p.y-(leaf_height-0.10))));
        float span_y=leaf_height-0.43;
        float slope=(leaf_width-0.28)/span_y;
        float center_y=(leaf_height+0.13)*0.5;
        float diagonal=min(abs((p.x-leaf_width*0.5)-(p.y-center_y)*slope),abs((p.x-leaf_width*0.5)+(p.y-center_y)*slope));
        float step_y=span_y/22.0;
        float rivet_y=0.28+ceil((p.y-0.28)/step_y)*step_y;
        float ry=rivet_y-p.y;
        float rx=min(abs((p.x-leaf_width*0.5)-(rivet_y-center_y)*slope),abs((p.x-leaf_width*0.5)+(rivet_y-center_y)*slope));
        seam=0.0; worn=exp(-perimeter*180.0)*0.32;
        rusty_edge=max(exp(-perimeter*30.0),exp(-diagonal*40.0)*0.65);
        rivet=0.0; rivet_halo=exp(-length(vec2(rx,ry))*45.0);
        runs=exp(-rx*70.0)*exp(-ry*6.0)*(0.5+0.5*noise(vec3(p.x*37.0,p.y*1.1,3)));
        float fittings=0.0;
        for(int i=0;i<2;i++) {
            vec2 hinge=vec2(0.215,i==0?0.48:leaf_height-0.40);
            vec2 offset=p-hinge;
            float contact=exp(-length(offset/vec2(0.23,0.095))*3.0);
            float trail=exp(-abs(offset.x)*35.0)*smoothstep(0.02,0.06,-offset.y)*exp(min(offset.y,0.0)*9.0);
            fittings=max(fittings,max(contact,trail*0.70));
        }
        for(int i=0;i<3;i++) {
            vec2 latch=vec2(leaf_width-0.12,i==0?0.40:(i==1?1.17:leaf_height-0.33));
            vec2 offset=p-latch;
            float contact=exp(-length(offset/vec2(0.11,0.08))*3.0);
            float trail=exp(-abs(offset.x)*45.0)*smoothstep(0.015,0.04,-offset.y)*exp(min(offset.y,0.0)*11.0);
            fittings=max(fittings,max(contact,trail*0.65));
        }
        rusty_edge=max(rusty_edge*0.35,fittings);
        runs*=smoothstep(0.48,0.79,noise(field_position/2.3+vec3(11,2,7)));
    }
    vec3 grain_sample=scan_sample(oxide_grain,field_position,signs,weights,1.20,vec2(0));
    float grain_value=dot(grain_sample,vec3(0.2126,0.7152,0.0722));
    float pits=smoothstep(0.030,0.10,grain_value);
    colour*=hatch_surface?mix(0.95,1.05,pits):mix(0.78,1.18,pits);
    vec3 grain_normal=scan_normal(oxide_normal,field_position,signs,weights,1.20,vec2(0));
    // Broad 2.3/4.6 m fields select only some wet seams and fasteners.
    float wet_area=0.42+0.58*smoothstep(0.30,0.68,noise(field_position/2.3+vec3(4,2,8)));
    float seam_choice=smoothstep(0.34,0.64,noise(field_position/4.6+vec3(7,1,3)));
    float fastener_choice=smoothstep(0.48,0.72,drip_seed);
    float short_runs=runs*exp(-below*11.0)*fastener_choice;
    if(hatch_surface) { short_runs=runs*0.32; }
    float geometry_mask=rusty_edge*0.80*(hatch_surface?1.0:seam_choice)+rivet_halo*0.78*fastener_choice+short_runs*0.85+lower*0.12;
    if(wheel_surface) { geometry_mask=max(geometry_mask,0.78); }
    float oxide=clamp(geometry_mask*wet_area*1.8,0.0,0.86);
    vec3 rust_chroma=mix(vec3(1.85,0.85,0.47),clamp(chroma,vec3(0.7),vec3(1.8)),0.12);
    rust_chroma/=dot(rust_chroma,vec3(0.2126,0.7152,0.0722));
    vec3 accent=dot(colour,vec3(0.2126,0.7152,0.0722))*rust_chroma*0.94;
    colour=mix(colour,accent,oxide);
    colour*=1.0-lower*(hatch_surface?0.85:0.27)-corner*0.09;
    colour*=1.0-seam*seam_strength;
    colour*=1.0+worn*0.45;
    colour=mix(colour,colour*vec3(1.20,1.12,0.90)*1.4,rivet*0.7);
    relief=-seam*0.0014+rivet*0.0018;
    if(wheel_surface) { colour*=1.45; }
    if(wheel_only) { colour*=0.52; }
    if(floor_surface) { colour*=0.65; }
    if(rivet_surface) { colour*=1.65; }
    if(edge_surface) { colour=mix(colour,dot(colour,vec3(0.2126,0.7152,0.0722))*vec3(1.03,1.05,0.93),0.60)*1.80; }
    if(hatch_surface) {
        vec3 local_p=wp;
        vec2 p=local_p.xy;
        vec3 seed=local_p*5.3+vec3(0,0,13.7);
        float coarse=noise(seed);
        float torn=coarse*0.67+noise(seed*2.7+vec3(7,2,3))*0.24+noise(seed*9.1)*0.09;
        vec4 weather=texture(leaf_weather,p/vec2(aperture.x,aperture.y));
        float paint=weather.r;
        float patina=mix(noise(vec3(p*37.0,7)),weather.g,0.6);
        float patch=noise(vec3(p.x*7.1,p.y*4.3,2))+noise(vec3(p*19.0,8))*0.22;
        vec3 dark_steel=vec3(0.053,0.051,0.043)*(0.82+0.34*patina);
        vec3 dark_paint=vec3(0.061,0.073,0.060)*(0.85+0.22*patina);
        vec3 dry_rust=mix(vec3(0.075,0.040,0.021),vec3(0.145,0.074,0.034),patina);
        float edge_distance=min(min(p.x,aperture.x-p.x),min(p.y-0.08,aperture.y-p.y));
        float edge_oxide=exp(-max(edge_distance,0.0)*22.0);
        if(leaf_paint) {
            float rust_patch=smoothstep(0.55,0.78,patch)*0.76;
            colour=mix(dark_steel,dry_rust,rust_patch);
            colour=mix(colour,dry_rust*0.70,max(weather.a*0.70,edge_oxide*0.72));
            colour=mix(colour,dark_paint,paint);
            float runoff=weather.b;
            for(int i=0;i<8;i++) {
                vec2 source=vec2(0.19,2.0);
                if(i==1) source=vec2(0.35,2.0);
                if(i==2) source=vec2(0.19,0.48);
                if(i==3) source=vec2(0.35,0.48);
                if(i==4) source=vec2(0.87,2.07);
                if(i==5) source=vec2(0.87,1.17);
                if(i==6) source=vec2(0.87,0.40);
                if(i==7) source=vec2(aperture.x*0.5,wheel_height);
                float drop=source.y-p.y;
                float length_run=i==7?0.98:0.72+0.12*sin(float(i)*7.3);
                float width_run=i==7?0.035:0.020+0.006*sin(float(i)*3.7);
                float run=exp(-pow((p.x-source.x+0.003*sin(p.y*13.0+float(i)))/width_run,2.0));
                run*=step(0.0,drop)*pow(clamp(1.0-drop/length_run,0.0,1.0),0.55);
                runoff=max(runoff,run);
            }
            colour=mix(colour,vec3(0.145,0.063,0.029),smoothstep(0.015,0.14,runoff)*0.78);
            colour=mix(colour,vec3(0.32,0.125,0.043)*(0.84+0.32*patina),smoothstep(0.15,0.65,runoff)*0.95);
            colour=mix(colour,vec3(0.070,0.032,0.014),smoothstep(0.86,0.99,runoff)*0.32);
            float wheel_shadow=1.0-smoothstep(0.36,0.50,length((p-vec2(aperture.x*0.5,wheel_height))/vec2(1.0,0.95)));
            colour*=1.0-wheel_shadow*0.72;
            colour=mix(colour,vec3(0.29,0.118,0.047)*(0.85+0.25*patina),smoothstep(0.12,0.64,runoff)*0.80);
            relief+=paint*0.00065-weather.a*0.0006+(weather.g-0.5)*0.00045;
        } else {
            vec3 deep_rust=mix(vec3(0.070,0.026,0.010),vec3(0.23,0.086,0.025),0.32+0.68*noise(vec3(p.x*4.8,p.y*1.8,2)));
            deep_rust*=mix(0.65,1.20,pits);
            vec3 frame_steel=vec3(0.105,0.106,0.087)*(0.80+0.30*noise(local_p*2.0+vec3(3,1,7)));
            float frame_oxide=0.45+0.35*noise(local_p*6.5+vec3(11,4,2));
            colour=mix(frame_steel,deep_rust*0.85,frame_oxide);
            if(wheel_surface) colour*=0.62;
            float base=1.0-smoothstep(0.05,0.30,p.y);
            float corner_grime=exp(-min(abs(p.x+0.11),abs(p.x-1.19))*12.0)*(1.0-smoothstep(0.12,0.52,p.y));
            colour*=1.0-max(base*0.72,corner_grime*0.85)*(0.80+0.20*noise(local_p*41.0));
        }
        colour*=mix(raised_base?0.48:(leaf_paint?0.18:0.20),1.0,smoothstep(0.035,0.52,p.y));
        if(leaf_hardware) {
            float crust=noise(local_p*21.0)*0.58+noise(local_p*93.0)*0.42;
            colour=mix(vec3(0.060,0.035,0.018),vec3(0.21,0.084,0.029),smoothstep(0.24,0.75,crust));
            relief+=(crust-0.5)*0.0025;
        }
        if(hero_wheel) {
            float crust=noise(local_p*19.0)*0.52+noise(local_p*63.0)*0.30+noise(local_p*191.0)*0.18;
            colour=mix(vec3(0.058,0.029,0.013),vec3(0.25,0.125,0.051),smoothstep(0.24,0.74,crust));
            colour*=0.80+0.30*pits;
            relief+=(crust-0.5)*0.0030;
        }
    }
    vec3 normal_surface=normalize(n+pn*(hatch_surface?0.10:0.26)+grain_normal*(hatch_surface?0.05:0.14));
    mat3 world_from_surface=mat3(surface_x.xyz,surface_y.xyz,surface_z.xyz);
    vec3 view_n=normalize((VIEW_MATRIX*vec4(world_from_surface*normal_surface,0)).xyz);
    vec3 dpdx=dFdx(VERTEX), dpdy=dFdy(VERTEX);
    vec3 r1=cross(dpdy,view_n), r2=cross(view_n,dpdx);
    float det=dot(dpdx,r1);
    vec3 gradient=(dFdx(relief)*r1+dFdy(relief)*r2)/(sign(det)*max(abs(det),0.00000001));
    NORMAL=normalize(view_n-clamp(gradient,vec3(-0.3),vec3(0.3)));
    ALBEDO=max(colour*gain*colour_gain,vec3(0.0001));
    ROUGHNESS=clamp(0.84+orm.g*0.10,0.88,0.97);
    METALLIC=mix(0.20,0.025,oxide);
    SPECULAR=0.32;
    AO=mix(0.86,1.0,orm.r)*mix(0.90,1.0,pits);
    }
}
