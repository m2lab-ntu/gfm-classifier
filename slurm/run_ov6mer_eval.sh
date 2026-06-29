#!/bin/bash
#SBATCH -A MST114550 -p dev --gres=gpu:1 --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 --mem=64G -t 02:00:00
#SBATCH -o /work/ymj1123ntu/logs/ov6mer_eval-%j.out
#SBATCH -e /work/ymj1123ntu/logs/ov6mer_eval-%j.err
set -uo pipefail
REPO=/work/ymj1123ntu/gfm-classifier; SC=$REPO/scripts
CFG=$REPO/configs/nt_token_genus_ov6mer_17M.yaml
CK=/work/ymj1123ntu/checkpoints/nt_token_genus_ov6mer_17M/best.pt
TRLB=/work/ymj1123ntu/data/balanced_species_17M/labels.tsv
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export HF_HOME=/work/ymj1123ntu/.cache/huggingface HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface PYTHONUNBUFFERED=1
cd $SC
# clean_common (Top-1 + sample-level) and leftover (Top-1)
python run_genus_rctta.py --config $CFG --checkpoint $CK --train_labels $TRLB --batch_size 256   --test_fasta /work/ymj1123ntu/taiwania2_testset/reads_clean_common.fa   --test_labels /work/ymj1123ntu/taiwania2_testset/labels_clean_common.tsv   --out_dir /work/ymj1123ntu/benchmark_results/common_preds/ov6mer 2>&1 | grep -aiE 'RC-TTA|forward'
python run_genus_rctta.py --config $CFG --checkpoint $CK --train_labels $TRLB --batch_size 256   --test_fasta /work/ymj1123ntu/data/clean_pool_5M/reads.fa   --test_labels /work/ymj1123ntu/data/clean_pool_5M/labels.tsv   --out_dir /work/ymj1123ntu/benchmark_results/sample_pool_preds/ov6mer 2>&1 | grep -aiE 'RC-TTA|forward'
python evaluate_sample.py --predictions /work/ymj1123ntu/benchmark_results/common_preds/ov6mer/rctta.npz   --out_dir /work/ymj1123ntu/benchmark_results/sample_common_eval/ov6mer --exp_name ov6mer   --n_partition_samples 9 --reads_per_sample 10000 2>&1 | grep -aiE 'Read-level|Pearson'
echo "=== ov6mer eval done $(date) ==="
