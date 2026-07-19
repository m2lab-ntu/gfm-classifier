#!/usr/bin/env python3
"""Cross-setting sample-level abundance — FRIENDLY natural pool clean_common
(99,742 reads, strict train-disjoint, 9x10K random-partition). MT-250M pending."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
NAVY,TEAL,GREEN,PURPLE,ORANGE,GRAY="#0A2540","#1E6091","#2E7D32","#6A1B9A","#E65100","#5A6068"
rows=[
 ("MT 13-mer 50M (~5M params)",0.875,0.9991,0.0318,PURPLE),
 ("MT 13-mer 250M (~5M params)",0.987,1.0000,0.0045,"#4A148C"),
 ("NT-v2 50M",0.671,0.9930,0.0979,TEAL),
 ("NT-v2 250M warm",0.673,0.9929,0.0980,TEAL),
 ("NT-v2 250M scratch",0.648,0.9930,0.1133,TEAL),
 ("NT-v2 17.6M species-bal",0.604,0.9927,0.1392,GREEN),
 ("NT-v2 17.6M genus-bal",0.372,0.8615,0.4196,ORANGE),
]
rows=sorted(rows,key=lambda r:r[2])
labels=[r[0] for r in rows]; acc=[r[1] for r in rows]; rr=[r[2] for r in rows]; bc=[r[3] for r in rows]; cols=[r[4] for r in rows]
y=np.arange(len(rows))
fig,ax=plt.subplots(1,2,figsize=(13,5.2))
fig.suptitle("Sample-Level Abundance Estimation — friendly natural pool clean_common (99,742 reads, train-disjoint, 9x10K)",
             fontsize=12,fontweight="bold",color=NAVY,y=0.99)
a=ax[0]; a.barh(y,rr,color=cols,edgecolor="white")
for yi,(r,ac) in zip(y,zip(rr,acc)): a.text(r+0.002,yi,f"{r:.3f}  (read-acc {ac*100:.0f}%)",va="center",fontsize=9,color=NAVY)
a.set_yticks(y); a.set_yticklabels(labels,fontsize=9); a.set_xlim(0.83,1.02)
a.set_xlabel("Pearson r (true vs predicted relative abundance) - higher better")
a.set_title("Abundance accuracy (Pearson r)",fontsize=11.5,fontweight="bold",color=NAVY)
a.axvline(1.0,color=GRAY,ls=":",lw=1,alpha=0.6)
b=ax[1]; b.barh(y,bc,color=cols,edgecolor="white")
for yi,v in zip(y,bc): b.text(v+0.006,yi,f"{v:.3f}",va="center",fontsize=9,color=NAVY)
b.set_yticks(y); b.set_yticklabels([]); b.set_xlim(0,0.48)
b.set_xlabel("Bray-Curtis dissimilarity - lower better")
b.set_title("Community-composition error (Bray-Curtis)",fontsize=11.5,fontweight="bold",color=NAVY)
fig.text(0.5,0.015,"On a natural train-disjoint pool, abundance estimation stays excellent (r=0.993) for all species/natural-trained models down to ~60% read-acc - per-read errors cancel at the sample level. MT-50M is near-perfect (0.999). Genus-balancing breaks it (0.862): it skews predictions toward rare genera, distorting the natural composition. v9 r=0.993 reproduces the thesis value. MT-250M r=1.000 (read-acc 99%): the 13-mer model KEEPS scaling (50M->250M: 88%->99%) while NT-v2 6-mer saturates at 67% - tokenization governs scalability.",
         ha="center",fontsize=8.2,color=GRAY,wrap=True)
fig.legend(handles=[Patch(color=PURPLE,label="MetaTransformer 13-mer"),Patch(color=TEAL,label="NT-v2+LoRA"),
                    Patch(color=GREEN,label="NT-v2 species-bal"),Patch(color=ORANGE,label="NT-v2 genus-bal")],
           loc="lower left",fontsize=8,ncol=2,framealpha=0.9)
plt.tight_layout(rect=[0,0.05,1,0.96])
plt.savefig("/work/ymj1123ntu/benchmark_results/sample_common_eval/cross_setting_comparison.png",bbox_inches="tight",dpi=200)
print("saved")
