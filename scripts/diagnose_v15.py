#!/usr/bin/env python
"""Read-only diagnostic of v15 clean-test predictions: where does the 42.64% fail?"""
import numpy as np, pandas as pd, json, collections

PRED = "/work/ymj1123ntu/checkpoints/cleantest_eval_v15/predictions.npz"
TESTLB = "/work/ymj1123ntu/data/clean_test_genus/labels.tsv"
COV = "/work/ymj1123ntu/data/leftover_coverage/coverage_per_genus.tsv"

d = np.load(PRED)
preds, labels = d["preds"], d["labels"]
acc = (preds == labels).mean()
print(f"overall acc = {acc*100:.2f}%  (n={len(labels):,})")

# genus_class -> name (from clean test labels; assumes label index == genus_class)
tl = pd.read_csv(TESTLB, sep="\t")
gc2name = dict(zip(tl["genus_class"], tl["genus_name"]))
# training read count per genus_class
cov = pd.read_csv(COV, sep="\t")
gc2used = dict(zip(cov["genus_class"], cov["used"]))

# per-true-genus stats
rows = []
for g in np.unique(labels):
    m = labels == g
    n = int(m.sum()); corr = int((preds[m] == g).sum())
    rows.append({"genus_class": int(g), "name": gc2name.get(int(g), "?"),
                 "support": n, "correct": corr, "acc": corr/n,
                 "train_used": gc2used.get(int(g), -1)})
df = pd.DataFrame(rows).sort_values("acc")

print("\n=== per-genus accuracy 分布 ===")
for lo, hi in [(0,0.1),(0.1,0.3),(0.3,0.5),(0.5,0.7),(0.7,0.9),(0.9,1.01)]:
    c = ((df.acc>=lo)&(df.acc<hi)).sum()
    print(f"  acc [{lo:.1f},{hi:.1f}): {c} genera")
print(f"  中位數 per-genus acc = {df.acc.median()*100:.1f}%")

print("\n=== 最差 12 個 genus ===")
print(df.head(12)[["name","support","acc","train_used"]].to_string(index=False))
print("\n=== 最好 8 個 genus ===")
print(df.tail(8)[["name","support","acc","train_used"]].to_string(index=False))

# accuracy vs training amount correlation
sub = df[df.train_used>0]
if len(sub)>2:
    r = np.corrcoef(np.log10(sub.train_used), sub.acc)[0,1]
    print(f"\n=== acc vs log10(train_used) 相關係數 = {r:.3f} ===")
    # split by training volume tertiles
    sub2 = sub.sort_values("train_used")
    t = len(sub2)//3
    for name,grp in [("低訓練量",sub2.iloc[:t]),("中",sub2.iloc[t:2*t]),("高",sub2.iloc[2*t:])]:
        print(f"  {name}(used~{int(grp.train_used.median()):>10,}): 平均 acc {grp.acc.mean()*100:.1f}%")

# top confusions: true -> most common wrong pred
print("\n=== 最常見的 12 個混淆 (true -> 誤判成) ===")
conf = collections.Counter()
for t_, p_ in zip(labels, preds):
    if t_ != p_:
        conf[(int(t_), int(p_))] += 1
for (t_, p_), c in conf.most_common(12):
    print(f"  {gc2name.get(t_,'?'):>22} -> {gc2name.get(p_,'?'):<22} : {c} 次")

# how concentrated are errors
tot_err = (preds!=labels).sum()
top12 = sum(c for _,c in conf.most_common(12))
print(f"\n  總錯誤 {tot_err:,};前 12 混淆佔 {top12/tot_err*100:.1f}%")
