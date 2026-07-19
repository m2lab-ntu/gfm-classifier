#!/usr/bin/env python3
"""Cross-setting sample-level abundance comparison (clean 573K pool, 11x50K
random-partition). MT-250M to be appended when its prediction is ready."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
NAVY,TEAL,GREEN,PURPLE,ORANGE,GRAY="#0A2540","#1E6091","#2E7D32","#6A1B9A","#E65100","#5A6068"
# (tag, label, read_acc, pearson_r, bray_curtis, color)
rows=[
 ("MT50M","MT 13-mer 50M\n(~5M params)",0.830,0.9901,0.0696,PURPLE),
 ("MT250M","MT 13-mer 250M\n(~5M params)",0.985,0.9999,0.0064,"#4A148C"),
 ("v9","NT-v2 50M",0.581,0.9276,0.2227,TEAL),
 ("v15","NT-v2 250M warm",0.583,0.9281,0.2218,TEAL),
 ("v14","NT-v2 250M scratch",0.555,0.9159,0.2447,TEAL),
 ("sbal","NT-v2 17.6M species-bal",0.502,0.8941,0.2829,GREEN),
 ("gbal","NT-v2 17.6M genus-bal",0.359,0.6250,0.4284,ORANGE),
]
rows=sorted(rows,key=lambda r:r[3])
labels=[r[1] for r in rows]; rr=[r[3] for r in rows]; bc=[r[4] for r in rows]
acc=[r[2] for r in rows]; cols=[r[5] for r in rows]; y=np.arange(len(rows))
fig,ax=plt.subplots(1,2,figsize=(13,5.2))
fig.suptitle("Sample-Level Abundance Estimation — clean train-disjoint pool (573K reads, 11×50K random-partition)",
             fontsize=12.5,fontweight="bold",color=NAVY,y=0.99)
# Pearson r
a=ax[0]
a.barh(y,rr,color=cols,edgecolor="white")
for yi,(r,ac) in zip(y,zip(rr,acc)):
    a.text(r+0.005,yi,f"{r:.3f}  (read-acc {ac*100:.0f}%)",va="center",fontsize=9,color=NAVY)
a.set_yticks(y); a.set_yticklabels(labels,fontsize=9); a.set_xlim(0.55,1.06)
a.set_xlabel("Pearson r (true vs predicted relative abundance) — higher better")
a.set_title("Abundance accuracy (Pearson r)",fontsize=11.5,fontweight="bold",color=NAVY)
a.axvline(1.0,color=GRAY,ls=":",lw=1,alpha=0.6)
# Bray-Curtis
b=ax[1]
b.barh(y,bc,color=cols,edgecolor="white")
for yi,v in zip(y,bc): b.text(v+0.008,yi,f"{v:.3f}",va="center",fontsize=9,color=NAVY)
b.set_yticks(y); b.set_yticklabels([]); b.set_xlim(0,0.5)
b.set_xlabel("Bray-Curtis dissimilarity — lower better")
b.set_title("Community-composition error (Bray-Curtis)",fontsize=11.5,fontweight="bold",color=NAVY)
fig.text(0.5,0.015,"MT 13-mer's tokenization advantage propagates to the sample level (r=0.990); NT-v2 settings land ~0.89–0.93. "
         "Genus-balancing collapses real-abundance estimation (r=0.625) — it optimises a uniform-prior macro metric the deployment distribution does not have. "
         "MT 13-mer scales (50M->250M: r 0.990->1.000); NT-v2 6-mer flat.",ha="center",fontsize=8.4,color=GRAY,wrap=True)
fig.legend(handles=[Patch(color=PURPLE,label="MetaTransformer 13-mer"),Patch(color=TEAL,label="NT-v2+LoRA"),
                    Patch(color=GREEN,label="NT-v2 species-bal"),Patch(color=ORANGE,label="NT-v2 genus-bal")],
           loc="lower left",fontsize=8,ncol=2,framealpha=0.9)
plt.tight_layout(rect=[0,0.05,1,0.96])
plt.savefig("/work/ymj1123ntu/benchmark_results/sample_pool_eval50k/cross_setting_comparison.png",bbox_inches="tight",dpi=200)
print("saved cross_setting_comparison.png")
