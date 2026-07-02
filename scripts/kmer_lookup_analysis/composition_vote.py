#!/usr/bin/env python3
"""Composition lookup baseline (no neural net): each 13-mer -> its DOMINANT genus
(streaming approx majority over reference reads), then classify a test read by
majority vote over ALL its 13-mers' dominant genus. Uses shared 13-mers too
(via their frequency-dominant genus), unlike the unique-key version.

If this dumb composition classifier ~matches MT (98.7%), the task is near-lookup
by COMPOSITION. If it lags MT a lot, MT's neural learning adds real value.
"""
import sys, time, numpy as np

K = 13; W = 150 - K + 1; NCODE = 4 ** K
REF_FA  = "/work/ymj1123ntu/data/reads_50M.fa"
TEST_FA = "/work/ymj1123ntu/taiwania2_testset/reads_clean_common.fa"
REF_MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000_000
BATCH   = 200_000

LUT = np.full(256, 255, np.uint8)
for i, b in enumerate(b"ACGT"):
    LUT[b] = i

def encode_batch(seqs):
    B = len(seqs)
    arr = LUT[np.frombuffer(b"".join(seqs), np.uint8).reshape(B, 150)]
    code = np.zeros((B, W), dtype=np.int64)
    valid = np.ones((B, W), dtype=bool)
    for j in range(K):
        code = code * 4 + arr[:, j:j + W].astype(np.int64)
        valid &= (arr[:, j:j + W] != 255)
    return code, valid

def iread(path):
    with open(path, "rb") as f:
        while True:
            h = f.readline(); s = f.readline()
            if not s: break
            if h[:1] != b">": continue
            s = s.rstrip(b"\n")
            if len(s) != 150: continue
            yield int(h.split(b"|", 4)[3]), s

# dominant genus per code via approx Boyer-Moore streaming majority
lead_g = np.full(NCODE, -1, dtype=np.int16)
lead_c = np.zeros(NCODE, dtype=np.int32)
t0 = time.time(); nref = 0; gb, sb = [], []

def flush_ref():
    global gb, sb
    if not sb: return
    code, valid = encode_batch(sb)
    g = np.broadcast_to(np.array(gb, np.int16)[:, None], code.shape)
    c = code[valid]; gv = g[valid]
    cur = lead_g[c]
    # unassigned -> assign (last write wins on dup codes)
    un = cur == -1
    lead_g[c[un]] = gv[un]; lead_c[c[un]] = 1
    # same genus -> +1 ; different -> -1  (np.add.at handles dup codes)
    cur = lead_g[c]
    same = cur == gv
    np.add.at(lead_c, c[same], 1)
    diff = (~same) & (cur != -1)
    np.add.at(lead_c, c[diff], -1)
    # where count fell <=0, reassign to a challenging genus
    cd = c[diff]; gd = gv[diff]
    neg = lead_c[cd] <= 0
    lead_g[cd[neg]] = gd[neg]; lead_c[cd[neg]] = 1
    gb, sb = [], []

for genus, seq in iread(REF_FA):
    gb.append(genus); sb.append(seq); nref += 1
    if len(sb) >= BATCH:
        flush_ref()
        if nref % 10_000_000 == 0:
            print(f"  ref {nref/1e6:.0f}M | {time.time()-t0:.0f}s", flush=True)
    if nref >= REF_MAX: break
flush_ref()
assigned = int((lead_g >= 0).sum())
print(f"REF built {nref:,} reads | 13-mers with a dominant genus = {assigned:,} "
      f"({100*assigned/NCODE:.1f}% of space) | {time.time()-t0:.0f}s", flush=True)

# classify test reads by majority vote over dominant-genus of all valid 13-mers
n=correct=covered=cov_correct=0; gb, sb = [], []
def flush_test():
    global gb, sb, n, correct, covered, cov_correct
    if not sb: return
    code, valid = encode_batch(sb)
    for i in range(len(sb)):
        vc = code[i][valid[i]]
        dg = lead_g[vc]; kn = dg >= 0
        votes = dg[kn]; truth = gb[i]; n += 1
        if votes.size:
            covered += 1
            pred = np.bincount(votes).argmax()
            ok = int(pred == truth); correct += ok; cov_correct += ok
    gb, sb = [], []

for genus, seq in iread(TEST_FA):
    gb.append(genus); sb.append(seq)
    if len(sb) >= BATCH: flush_test()
flush_test()

print("\n============  COMPOSITION LOOKUP (dominant-genus vote, no neural net)  ============")
print(f"test reads                      : {n:,}")
print(f"coverage (>=1 known 13-mer)     : {100*covered/n:.2f}%")
print(f"composition lookup acc (ALL)    : {100*correct/n:.2f}%")
print(f"composition lookup acc (COVERED): {100*cov_correct/max(covered,1):.2f}%")
print("compare: MT 13-mer @250M = 98.7% ; @50M = 87.5% ; NT-v2 6-mer = 67% ; unique-key lookup = (see other run)")
