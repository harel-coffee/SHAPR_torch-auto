#!/bin/bash
#
# Create jobs for a specific sweep.

NAME="topo_shapr_sweep"
SWEEP=$1

if [ -z "$1" ]; then
  exit -1
fi

for i in `seq 27`; do
  sbatch -p interactive_gpu_p   \
         -J ${NAME}             \
         -o "${NAME}_%j.out"    \
         --gres=gpu:1           \
         --qos=interactive_gpu  \
         --cpus-per-task=4      \
         --mem=4G               \
         --nice=10000           \
         --wrap "poetry run wandb agent --count 1 $1"
done