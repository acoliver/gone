"""Compose the small-prop batch without changing the fixed capture framing."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[4]
ITEMS=['photo_frame','mug','plate','data_tablet','medal_case','jewellery_box','hairbrush','boots']


def main():
    cell=384; row_height=420
    sheet=Image.new('RGB',(cell*4,row_height*4),'#e5e5e5')
    draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',18)
    for index,item in enumerate(ITEMS):
        for state_index,state in enumerate(['remembered','aged']):
            column=(index%2)*2+state_index; row=index//2
            image=Image.open(ROOT/f'docs/art/quarters/sheets/{item}/{state}/hero.png').convert('RGB')
            image=image.resize((cell,cell),Image.Resampling.LANCZOS)
            x,y=column*cell,row*row_height
            sheet.paste(image,(x,y))
            label=item+(' / remembered' if state=='remembered' else ' / 1000 years')
            draw.text((x+8,y+cell+8),label,fill='black',font=font)
    output=ROOT/'docs/art/quarters/sheets/photo_frame/batch3-small-items.png'
    sheet.save(output)
    print(output)


if __name__=='__main__':
    main()
