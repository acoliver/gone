"""Generate one standalone clothing guide after waiting for the shared GPU."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT=Path(__file__).resolve().parents[4]
TOOL='/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-z-image-turbo'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('prop',choices=['her_jacket','her_dresses'])
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    data=json.loads((ROOT/'docs/art/quarters/prompts/batch2.json').read_text())
    entry=next(v for v in data['props'] if v['id']==a.prop)
    out=a.output or ROOT/'docs/art/quarters/sheets'/a.prop/'hero.png'
    if out.exists():raise FileExistsError(f'Choose a new --output to preserve {out}')
    out.parent.mkdir(parents=True,exist_ok=True)
    pattern=re.compile(r'(?:/| )mflux-\S+|(?:/| )generate\.py(?: |$)')
    while True:
        processes=subprocess.run(['ps','-axo','pid,command'],check=True,capture_output=True,text=True).stdout
        busy=[line for line in processes.splitlines() if pattern.search(line)]
        if not busy:break
        print('Waiting for shared GPU: '+'; '.join(busy),flush=True)
        time.sleep(15)
    spec=entry['generation']
    command=[TOOL,'--model',spec['model'],'--quantize',str(spec['quantize']),
             '--steps',str(spec['steps']),'--width',str(spec['width']),'--height',str(spec['height']),
             '--seed',str(entry['seeds'][0]),'--output',str(out),'--prompt',entry['prompt']]
    subprocess.run(command,check=True,env={**os.environ,'HF_HOME':'/Volumes/XS1000/hf-cache','HF_HUB_OFFLINE':'1'})
    out.with_suffix('.json').write_text(json.dumps({'command':command,'prompt':entry['prompt'],
        'seed':entry['seeds'][0],'model':spec['model'],'purpose':'clothing sewn-pattern design guide'},indent=2)+'\n')


if __name__=='__main__':main()
