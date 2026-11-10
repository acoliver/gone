"""Run the unchanged shared clothing gates with dress-local scratch paths."""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'her_jacket'))
import verify as shared

if __name__=='__main__':
    shared.SCRATCH=HERE.parents[3]/'tmp/clothes2'
    shared.main()
