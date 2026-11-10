"""Validate exported bounds, named parts, pivots, shells, UVs and stable export."""
import argparse
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'wardrobe'))
from verify_common import verify


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=HERE.parents[3]/'assets/props/quarters/bedside.glb')
    parser.add_argument('--reexport',type=Path,required=True)
    args=parser.parse_args()
    verify(args.input,HERE/'construction.json',HERE/'verify.json',args.reexport)


if __name__=='__main__':main()
