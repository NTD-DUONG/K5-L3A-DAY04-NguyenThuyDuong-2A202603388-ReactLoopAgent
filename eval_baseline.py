"""Run the unchanged evaluator with the saved pre-validation agent.

All CLI arguments are forwarded to evals/run_evals.py.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'evals'))

import run_evals
from versions.agent_before_source_validation import run_agent


if __name__ == '__main__':
    run_evals.run_agent = run_agent
    sys.exit(run_evals.main())
