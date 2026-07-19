#!/usr/bin/env python3
"""
Evaluate the MT-5M soil best checkpoint on test_final (5M reads) and save
Top-1 accuracy + per-read preds/labels to npz (parallel to the NT-v2 rctta.npz).

Based on mt_50M/eval_best_checkpoint.py (fwd-only single-read eval).

Usage (from MetaTransformer/src):
    python3 /work/ymj1123ntu/mt5m_soil/eval_test_final.py \
        --ckpt /work/ymj1123ntu/mt5m_soil/experiments/genus_5M_soil_967182/checkpoints/classification_transformer_ckpt_best.pt \
        --val  /work/ymj1123ntu/mt5m_soil/data/test_final \
        --cfg  /work/ymj1123ntu/mt5m_soil/experiments/genus_5M_soil_967182/config.yaml \
        --out  /work/ymj1123ntu/mt5m_soil/results/mt_soil_genus_5M/eval_test_final/mt5m_test_final.npz \
        --gpu 0 --batch-size 2048 --max-batches 2442
"""
import argparse, sys, os
sys.path.insert(0, '/home/ymj1123ntu/MetaTransformer/src')

import torch
import numpy as np
from omegaconf import OmegaConf
from torch.utils.data import DataLoader
from sklearn.metrics import f1_score

import utils.device_handler as DeviceHandler
from dataset.MetagenomicReadDataset import ProcessingMetagenomicReadDataset
from models.model_utils import get_label_transforms, read_transforms_for_input_layer, instantiate_model_by_str_name
from utils.torch_utils import train_collate_fn_padded
from utils.utils import load_vocabulary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--val',  required=True, help='test_final dir (contains *.fa)')
    ap.add_argument('--cfg',  required=True)
    ap.add_argument('--out',  required=True, help='output .npz path')
    ap.add_argument('--gpu',  default='0')
    ap.add_argument('--batch-size', type=int, default=2048)
    ap.add_argument('--max-batches', type=int, default=100000)
    args = ap.parse_args()

    cfg = OmegaConf.load(args.cfg)
    cfg.device_settings.gpu_ids = args.gpu
    cfg.device_settings.gpu_count = 1
    cfg.device_settings.split_gpus = False
    DeviceHandler.init_device_handler(False, 1, args.gpu, False)

    vocab, vocab_size = None, 0
    if cfg.mdl_common.input_module not in ["lsh", "hash", "one_hot", "one_hot_embed", "bpe"]:
        vocab, vocab_size = load_vocabulary(cfg.paths.vocabulary_path)

    read_transforms = read_transforms_for_input_layer(cfg.mdl_common.input_module, cfg, vocab, train=False)
    label_transform = get_label_transforms(cfg.mdl_common.class_indices)

    net = instantiate_model_by_str_name(cfg.model.name, cfg, vocab_size)
    ckpt = torch.load(args.ckpt, map_location='cpu')
    net.load_state_dict(ckpt['model_state_dict'])
    net = DeviceHandler.model_to_device(net)
    net.eval()

    val_set = ProcessingMetagenomicReadDataset(args.val, read_transforms, label_transforms=label_transform)
    val_iter = DataLoader(val_set, batch_size=args.batch_size, num_workers=4,
                          collate_fn=train_collate_fn_padded)

    all_preds, all_labels = [], []
    softmax = torch.nn.Softmax(dim=1)
    print("Running inference on test_final ...", flush=True)
    with torch.no_grad():
        for step, (data, target) in enumerate(val_iter):
            if step >= args.max_batches:
                break
            data = DeviceHandler.tensor_to_device(data)
            target = DeviceHandler.tensor_to_device(target)
            with torch.cuda.amp.autocast(enabled=cfg.training.amp):
                logits = net(data)
            preds = softmax(logits).argmax(dim=1).cpu().numpy()
            all_preds.append(preds)
            all_labels.append(target.cpu().numpy())
            if (step + 1) % 500 == 0:
                print(f"  {step+1} batches done", flush=True)

    all_preds = np.concatenate(all_preds)
    all_labels = np.concatenate(all_labels)
    top1 = (all_preds == all_labels).mean()
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    np.savez_compressed(args.out, preds=all_preds, labels=all_labels,
                        acc_top1=top1, macro_f1=macro_f1)

    print(f"\n{'='*50}")
    print(f"Checkpoint: {args.ckpt}")
    print(f"Samples evaluated: {len(all_preds):,}")
    print(f"Top-1 accuracy:    {top1:.4f}  ({top1*100:.2f}%)")
    print(f"Macro F1:          {macro_f1:.4f}")
    print(f"Saved -> {args.out}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
