"""Ask the installed local image-comparer to score matched material sheets."""
import argparse
import base64
import json
import shutil
import urllib.request

from PIL import Image, ImageDraw, ImageFont

from steel_library import ROOT, LIBRARY
from map_library import PROPS

VIEWS = ('hero', 'front', 'top', 'detail')
BASE_RATINGS = ('candidate_as_built', 'candidate_aged', 'locker_as_built', 'locker_aged')


def archive_review(directory):
    if not (directory / 'review-response.json').exists():
        return
    archive = directory / 'history' / str(len(list((directory / 'history').glob('*')))+1)
    archive.mkdir(parents=True, exist_ok=True)
    for name in ('material-review.json', 'review-response.json', 'review-prompt.txt'):
        if (directory / name).exists():
            shutil.move(directory / name, archive / name)
    for path in directory.glob('matched-*.png'):
        shutil.copyfile(path, archive / path.name)


def compose_review(prop, directory, render=ROOT / 'tmp/mat2/render'):
    block = (1536, 1024) if prop == 'wardrobe' else (2048, 2048)
    canvas = Image.new('RGB', (block[0]*2, (block[1]+48)*2), '#151c20')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=36)
    for index, view in enumerate(VIEWS):
        x, y = (index%2)*block[0], (index//2)*(block[1]+48)
        draw.text((x+16, y+4), view, fill='white', font=font)
        if prop == 'wardrobe':
            sheet = Image.new('RGB', (3072, 2048))
            for column, identity in enumerate((prop, 'legacy', 'locker')):
                for row, state in enumerate(('as_built', 'aged')):
                    image = Image.open(render / f'{prop}-{identity}-{state}-{view}.png').convert('RGB')
                    sheet.paste(image, (column*1024, row*1024))
            sheet.save(directory / f'matched-legacy-{view}.png')
            sheet = sheet.resize(block, Image.Resampling.LANCZOS)
        else:
            sheet = Image.open(directory / f'matched-{view}.png').convert('RGB')
        canvas.paste(sheet, (x, y+48))
    master = directory / 'matched-review.png'
    canvas.save(master)
    return master


def acceptance(report, prop, numeric_failed):
    keys = BASE_RATINGS+('legacy_as_built', 'legacy_aged') if prop == 'wardrobe' else BASE_RATINGS
    scores = {key: report['ratings'][key]['score'] for key in keys}
    if any(type(value) not in (int, float) or not 1 <= value <= 10 for value in scores.values()):
        raise ValueError('visual ratings must be numbers from 1 to 10')
    aged, locker = scores['candidate_aged'], scores['locker_aged']
    complete = set(report['images_seen']) == set(VIEWS)
    result = dict(accepted=aged >= locker and numeric_failed == 0 and complete,
                  candidate_aged=aged, locker_aged=locker, numeric_failed=numeric_failed,
                  scope_complete=complete,
                  rule='candidate aged >= locker aged in this review, numeric gates pass, all four view blocks inspected')
    if prop == 'wardrobe':
        result['legacy_aged'] = scores['legacy_aged']
        result['accepted'] = result['accepted'] and aged >= scores['legacy_aged']
        result['rule'] += '; wardrobe must also match or exceed its per-face finish in this review'
    return result


def review(prop):
    directory = LIBRARY / 'props' / prop
    archive_review(directory)
    master = compose_review(prop, directory)
    layout = ('Within EACH block is a 3 by 2 grid: shared-library candidate LEFT, per-face wardrobe finish MIDDLE, '
              'finished reference locker RIGHT. AS-BUILT is the TOP row and AGED the BOTTOM row.'
              if prop == 'wardrobe' else
              'Within EACH block is a 2 by 2 grid: candidate LEFT, finished reference locker RIGHT, '
              'AS-BUILT on TOP, AGED on BOTTOM.')
    keys = BASE_RATINGS+('legacy_as_built', 'legacy_aged') if prop == 'wardrobe' else BASE_RATINGS
    prompt = f'''You are the image-comparer visual reviewer. Inspect the supplied image directly.
This is ONE composite of four labelled neutral-light matched view blocks for the Godot game's {prop} furniture finish.
The four large blocks are HERO at upper left, FRONT at upper right, TOP at lower left,
and DETAIL at lower right. {layout}
All material columns share white lighting, orthographic physical image scale and view direction;
cameras are translated to each object's centre. Geometry differs. Judge materials, not matching silhouettes.
The material brief is grey-green painted warship steel, with bare hardware and dark trim when new.
Aged means 1000 years aboard a sealed sterile dry oxygenated ship: most broad paint retained,
irregular edge/corner/fixture corrosion, a few narrow downward rust runs on vertical faces,
corroded hardware, and fine soft settled dust on upward faces. No biological growth or new bright green.
Fabric pads, if present, should be faded woven fabric. Displays and glass retain their original finish.
Evaluate the complete material/rendering result, including stretching, repeating marks, seams,
blocky or blurry wear, lighting, relief, dust softness and material-role clarity. Distinguish
observations from hypotheses. Report cropping and visibility limitations instead of assuming unseen features.
Rate every shown finish in BOTH states on the SAME 1-10 scale in this review.
Use 1 for unusable/material failure and 10 for a convincing finished presentation.
Do not infer ratings from numeric checks. Explain each score with locations in the images.
Return JSON only with keys: images_seen (exact labels hero, front, top, detail for blocks you can actually inspect;
omit unreadable blocks); ratings ({', '.join(keys)}, each an object with score and explanation);
features (each requested feature with achieved and observations); findings (ordered by severity with concrete fixes);
ready (boolean); limitations. Be concise, using one sentence per score and feature.
Assess all four view blocks. Do not edit images or source files.'''
    (directory / 'review-prompt.txt').write_text(prompt+'\n')
    content = [{'type': 'text', 'text': prompt},
               {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,'+base64.b64encode(master.read_bytes()).decode()}}]
    payload = dict(model='qwen3.8-27b', messages=[
        {'role': 'system', 'content': 'You are image-comparer, an independent visual QA agent. Inspect the supplied pixels. Return JSON only.'},
        {'role': 'user', 'content': content}], max_tokens=2600, temperature=.1,
        chat_template_kwargs={'enable_thinking': False})
    request = urllib.request.Request('http://127.0.0.1:8308/v1/chat/completions', data=json.dumps(payload).encode(),
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=900) as response:
        result = json.load(response)
    (directory / 'review-response.json').write_text(json.dumps(result, indent=2)+'\n')
    text = result['choices'][0]['message']['content'].strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    report = json.loads(text)
    numeric = json.loads((directory / 'gates.json').read_text())
    report['acceptance'] = acceptance(report, prop, numeric['failed'])
    (directory / 'material-review.json').write_text(json.dumps(report, indent=2)+'\n')
    print(prop, json.dumps(report['acceptance']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prop', choices=PROPS, action='append')
    args = parser.parse_args()
    for prop in args.prop or PROPS:
        review(prop)
