#!/bin/bash
cd /Users/francois/git/symmetry-project-202512/symmetry-unified-backend/app
source /Users/francois/git/symmetry-project-202512/symmetry-unified-backend/venv/bin/activate
export PYTHONPATH="/Users/francois/git/symmetry-project-202512/symmetry-unified-backend:${PYTHONPATH}"
python main.py
