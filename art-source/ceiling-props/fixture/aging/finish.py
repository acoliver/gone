"""Pack and export the aged asset; visual acceptance uses the native game capture."""
from pathlib import Path

import bpy
R=Path(__file__).resolve().parent
EMISSION_STRENGTH=3.0
bpy.ops.wm.open_mainfile(filepath=str(R/'working.blend'));bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene
source=bpy.data.objects['SOURCE_720_generated_painted'];source.hide_render=True;source.hide_set(True)
asset=[o for o in s.objects if o.type=='MESH' and o!=source]
for name in ['DarkArmouredSteel','RecessedFrostedGlass']:
 if name in bpy.data.materials:bpy.data.materials[name].name='ROUND3_'+name
for prefix,name in [('body','Seed720_CleanedGeneratedBeam'),('grille','GeneratedUnderside_ArmouredGrille'),('hardware','RaisedRails_Rivets_GravityFasteners')]:
 o=bpy.data.objects[name];mat=bpy.data.materials.new({'body':'OliveSteel_StructuredWeather','grille':'DarkArmouredSteel','hardware':'RaisedRailSteel'}[prefix]);mat.use_nodes=True;o.data.materials.clear();o.data.materials.append(mat)
 for p in o.data.polygons:p.material_index=0
 nt=mat.node_tree;nodes=nt.nodes;links=nt.links;bs=nodes.get('Principled BSDF');textures={}
 for kind in ['albedo','orm','control','control_orm','no_rust','no_streak','no_dust']:
  im=bpy.data.images.load(str(R/(prefix+'_'+kind+'.png')));im.colorspace_settings.name='Non-Color' if 'orm' in kind else 'sRGB';im.pack();textures[kind]=im
 albedo=nodes.new('ShaderNodeTexImage');albedo.image=textures['albedo'];links.new(albedo.outputs['Color'],bs.inputs['Base Color'])
 orm=nodes.new('ShaderNodeTexImage');orm.image=textures['orm'];split=nodes.new('ShaderNodeSeparateColor');links.new(orm.outputs['Color'],split.inputs['Color']);links.new(split.outputs['Green'],bs.inputs['Roughness']);links.new(split.outputs['Blue'],bs.inputs['Metallic']);bs.inputs['Specular IOR Level'].default_value=.32
glass=bpy.data.objects['RecessedGlass_13mm'];gm=bpy.data.materials.new('RecessedFrostedGlass');gm.use_nodes=True;glass.data.materials.clear();glass.data.materials.append(gm)
for p in glass.data.polygons:p.material_index=0
bs=gm.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.045,.05,.04,1);bs.inputs['Roughness'].default_value=.83;bs.inputs['Emission Strength'].default_value=EMISSION_STRENGTH
tex=gm.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'glass_emission.png'));tex.image.pack();gm.node_tree.links.new(tex.outputs['Color'],bs.inputs['Emission Color'])
bpy.ops.object.select_all(action='DESELECT')
for o in asset:o.hide_render=False;o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=asset[0]
bpy.ops.export_scene.gltf(filepath=str(R/'fixture.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_materials='EXPORT',export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'fixture.blend'))
