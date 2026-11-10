"""Append follow-up cloth measurements without discarding the pilot's trials."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCRATCH = ROOT / 'tmp/fit/sofa/cloth2'
NOTES = {
    'seat-m': 'Softer shell with pressure 3 overinflated: crown 94.80 mm and side bulges 112.5 to 153.5 mm.',
    'seat-n': 'Crown passed after fitting, but three side bulges exceeded 30 mm. Initial assembly and piping also exceeded their limits.',
    'seat-o': 'Larger radius at lower pressure still produced irregular shoulders and side bulges above 30 mm.',
    'seat-p': 'The thinner coarse shell had shallow crowns and unequal side bulges.',
    'seat-q': 'Denser grid reduced shoulder asymmetry. Crown remained below 35 mm.',
    'seat-r': 'Higher bending resistance held the crown below 35 mm.',
    'seat-s': 'Pressure 3 on the dense shell produced excessive crowns and side bulges.',
    'seat-t': 'A taller shell produced a 49.46 mm raw crown but still excessive side bulges.',
    'seat-u': 'Inset upper shoulders let the side-wall belly and rounded top edge inflate separately. Fitted crowns, bulges, edge radii, corners and contacts pass.',
    'throw-i': 'Single gathered sheet passed folds and coverage. One thickness self-crossing remained at the inner rear hem, and motion was 2.785 mm over the last five frames.',
    'throw-j': 'Longer settle reduced motion to 0.138 mm. One inner-hem crossing remained. Transfer to the inset-shoulder cushions exposed a 0.898 mm contact penetration, so this transferred assembly was rejected.',
    'throw-k': 'Greater bending resistance and the actual fitted colliders removed crossings, but motion remained 6.348 mm over the last five frames. The inside rear hem started against the back cushion.',
    'throw-l': 'Moved the sheet forward 65 mm to clear the back cushion and held the 35 mm rolled cap strip. Motion fell to 0.0231 mm. All geometry gates pass after orphan mesh names are cleared. The circle measurement was corrected to use geometric residuals for the two skins of the thick sheet.',
}


def main():
    path = HERE / 'cloth-trials.json'
    data = json.loads(path.read_text())
    previous=data.get('followup',{})
    followup = {'baseline_commit':'1547cad',
                'pilot_assembly':previous.get('pilot_assembly',data['assembly']),
                'pilot_selected':previous.get('pilot_selected',data['selected']),
                'cushion_trials':[], 'throw_trials':[], 'assembly_trials':[]}
    for folder in sorted(SCRATCH.glob('seat-*')) + sorted(SCRATCH.glob('throw-*')):
        numbers = folder/'numbers.json'
        if not numbers.exists():
            continue
        record = json.loads(numbers.read_text())
        record['assessment'] = NOTES[folder.name]
        if folder.name=='throw-l':
            record['settings']['cap_clearance_adjustment_m']=-.001
        verification = folder/'verify.json'
        if verification.exists():
            record['export_gates'] = json.loads(verification.read_text())
        key = 'cushion_trials' if folder.name.startswith('seat-') else 'throw_trials'
        followup[key].append(record)
    for name in ('candidate-u','candidate-final'):
        path_to_report = SCRATCH/(name+'-verify.json')
        if path_to_report.exists():
            followup['assembly_trials'].append({'name':name, 'export_gates':json.loads(path_to_report.read_text())})
    before = SCRATCH/'before.json'
    if before.exists():
        followup['before'] = json.loads(before.read_text())
    final=json.loads((HERE/'verify.json').read_text())
    followup['after']=final
    data['assembly']={'seat_fit_dimensions_blender_m':[.66,.70,.18],
                      'seat_center_x_m':[-.67,0,.67],'seat_center_yz_m':[-.035,.480],
                      'back_fit_dimensions_game_xyz_m':[.66,.42,.20],
                      'back_lower_return_depth_m':.04,
                      'back_depth_transition_normalized_height':[.38,.58],
                      'body_triangle_targets':{'seats':1440,'backs':1210},
                      'welt_offsets_m':{'seats':.0047,'backs':.00458},
                      'foot_mounting_plate_width_depth_m':[.19,.11],
                      'foot_mounting_plate_top_m':.131,'foot_mounting_gap_m':.00015,
                      'rivets_per_plate':4,'rivet_diameter_m':.012,'rivet_dome_height_m':.003,
                      'rivet_material':{'name':'BareSteel','base_color':[.48,.52,.54],
                                        'metallic':.85,'roughness':.32}}
    data['selected']={'cushion':'seat-u','throw':'throw-l','baked_source':'sofa-working.blend',
                      'export_checks':'verify.json','triangles':final['triangle_budget']['triangles'],
                      'byte_identical_reexport':final.get('byte_identical_reexport',False)}
    data['followup'] = followup
    path.write_text(json.dumps(data,indent=2)+'\n')


if __name__ == '__main__':
    main()
