"""Compose labelled review JPEGs without making an image judgment."""
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def sheets(out):
    render=out/'renders'
    font=ImageFont.load_default(size=18)
    concept=ROOT/'docs/art/quarters/sheets/medal/c-machined-rim-seed130303.png'
    def panel(path,label,width,height):
        image=Image.open(path).convert('RGB')
        image.thumbnail((width,height-36),Image.Resampling.LANCZOS)
        result=Image.new('RGB',(width,height),(160,160,160))
        result.paste(image,((width-image.width)//2,36+(height-36-image.height)//2))
        ImageDraw.Draw(result).text((10,8),label,font=font,fill=(20,20,20))
        return result
    sheet=Image.new('RGB',(1398,1000),(160,160,160))
    entries=[(concept,'Selected concept'),(render/'high-clay-three-quarter.jpg','High: neutral clay'),
             (render/'low-clay-three-quarter.jpg','Low: neutral clay'),
             (concept,'Selected concept'),(render/'high-preview-three-quarter.jpg','High: simple brass/enamel'),
             (render/'low-preview-three-quarter.jpg','Low: simple brass/enamel')]
    for i,(path,label) in enumerate(entries):
        sheet.paste(panel(path,label,466,500),((i%3)*466,(i//3)*500))
    target=render/'concept-high-low-three-quarter-sheet.jpg'
    sheet.save(target,quality=94)
    lineage=Image.new('RGB',(1400,420),(160,160,160))
    for i,(path,label) in enumerate([(concept,'Concept'),(render/'raw-clay-three-quarter.jpg','Raw generated guide'),
              (render/'high-clay-three-quarter.jpg','Corrected high'),(render/'low-clay-three-quarter.jpg','Bounded low')]):
        lineage.paste(panel(path,label,350,420),(350*i,0))
    lineage_path=render/'concept-raw-high-low-clay-sheet.jpg'
    lineage.save(lineage_path,quality=94)
    inventory=[]
    for path in sorted(render.glob('*.jpg')):
        with Image.open(path) as image:
            assert max(image.size)<=1400
            inventory.append(dict(path=str(path.resolve()),dimensions=list(image.size)))
    (out/'review-jpegs.json').write_text(json.dumps(inventory,indent=2))
    print(target,lineage_path,sep='\n')


if __name__=='__main__':
    sheets(Path(sys.argv[1]))
