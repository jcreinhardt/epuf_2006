#!/bin/bash
# TikTak estimation of the nonemployment block on the SOM cluster. Needs no database: the inputs come from
# processed_data/nonemp_inputs_yob<YOB>.npz (estimate_nonemp.Problem), built once on a machine with the DuckDB.
#
# One-time setup on a login node (uv: single tool for the interpreter and the packages; see the hpc skills):
#   curl -LsSf https://astral.sh/uv/install.sh | sh
#   mkdir -p ~/epuf_2006 && cd ~/epuf_2006          # home (/gpfs/home); there is no per-user /gpfs/project directory
#   uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python numpy pandas scipy
#   mkdir -p logs
# From the laptop, the two data files (both untracked; the second is optional -- without it the job rebuilds the
# data moments and their bootstrap, about a minute):
#   rsync -az code/dynamics code/cross_sections <netid>@hpc.som.yale.edu:epuf_2006/code/
#   scp processed_data/nonemp_inputs_yob1932.npz <netid>@hpc.som.yale.edu:epuf_2006/processed_data/
#   scp output/dynamics/nonemp_moments_yob1932.csv <netid>@hpc.som.yale.edu:epuf_2006/output/dynamics/
#
# Submit FROM THE REPO ROOT (extra arguments go to estimate_nonemp.py, e.g. --spec sexlag --tiktak 1024 --budget 1200):
#   sbatch --cpus-per-task=16 code/dynamics/estimate_nonemp.sbatch --spec sexlag_absq --tiktak 512 --keep 32
# Workers = SLURM_CPUS_PER_TASK (estimate_nonemp's default). Measured 2026-10-07: 16 cores on cpunormal ran 21
# evaluations/s (a laptop with 9 workers: 9/s); the 512-point run above converged in 7.3 minutes. The CPU partitions
# are small (10 nodes x 32 cores) and usually nearly full, so ask for the cores a part-used node has free
# (sinfo -N -o '%P %N %T %C') rather than a whole node.

#SBATCH --job-name=nonemp-tiktak
#SBATCH --partition=default_queue
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=32
#SBATCH --mem=16G
#SBATCH --output=logs/%x_%j.out

set -euo pipefail

# the optimizer forks one single-threaded process per core; BLAS threads on top would oversubscribe
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

cd "${SLURM_SUBMIT_DIR:?submit from the repo root}"   # sbatch copies the script, so $0 is useless here
srun .venv/bin/python code/dynamics/estimate_nonemp.py --root /nonexistent --tiktak 512 --budget 600 "$@"
