from pathlib import Path
O=Path(__file__).resolve().parent;A=O.parent/'assembly3'
bake=(A/'bake.py').read_text().replace("'Finish4 object-space paint bake'","'Standing object-space paint bake'").replace("'Console worn olive paint finish4'","'Console standing worn olive paint'")
(O/'bake.py').write_text(bake)
tex=(A/'textures.py').read_text()
tex=tex.replace("O=Path(__file__).resolve().parent;S=O;N=2048","O=Path(__file__).resolve().parent;S=O;N=2048\nstanding=json.loads((O/'geometry-report.json').read_text())['standing'];delta=standing['delta_m'];stretch=standing['lower_body_vertical_scale']")
tex=tex.replace("(points[:,2]>.615)&(points[:,2]<.705)","(points[:,2]>.615+delta)&(points[:,2]<.705+delta)")
tex=tex.replace(" z=points[:,2];drift=", " start+=delta;length*=stretch\n z=points[:,2];drift=")
(O/'textures.py').write_text(tex)
# Reuse the assembly3 rusty-wall and steel-floor staging, excluding its refit.
build=(A/'build.py').read_text();start=build.index("scene.cycles.device='CPU'\nscene.cycles.samples=64")
staging=build[start:];staging=staging[:staging.index("views=[")]
(O/'stage.py').write_text(staging)
