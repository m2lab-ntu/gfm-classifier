#!/usr/bin/env python3
"""
Convert MT-style raw-header soil shards (a dir of *.fa with headers
  >lbl|<genus_idx>|<genus_name>|<species_idx>|<accession>-<pos>/<mate>)
into the NT-v2 name-keyed format that data_loader.load_data expects:
  <out>.fa           (sequences; header used as seq_id)
  <out>_labels.tsv   (seq_id, genus_name, species_name)

Uses the canonical idx2name.json so genus_name is consistent (incl. Candidatus
idx 40-44 -> Candidatus_NN). This lets NT-v2 train/eval on the EXACT same reads
as the MT-5M run (same shards under mt5m_soil/data/).
"""
import os, sys, json, glob, argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards_dir", required=True, help="dir of raw-header *.fa shards")
    ap.add_argument("--out_fa", required=True)
    ap.add_argument("--out_tsv", required=True)
    ap.add_argument("--idx2name", required=True)
    args = ap.parse_args()

    canon = json.load(open(args.idx2name))
    canon = {int(k): (v if v else f"class_{k}") for k, v in canon.items()}

    n = 0
    with open(args.out_fa, "w") as fa, open(args.out_tsv, "w") as tsv:
        tsv.write("seq_id\tgenus_name\tspecies_name\n")
        for shard in sorted(glob.glob(os.path.join(args.shards_dir, "*.fa"))):
            hdr, seq = None, []
            with open(shard) as f:
                for line in f:
                    line = line.rstrip("\n")
                    if line.startswith(">"):
                        if hdr is not None:
                            n += emit(fa, tsv, hdr, "".join(seq), canon)
                        hdr, seq = line[1:], []
                    else:
                        seq.append(line)
                if hdr is not None:
                    n += emit(fa, tsv, hdr, "".join(seq), canon)
    print(f"wrote {n:,} reads -> {args.out_fa}")

def emit(fa, tsv, hdr, seq, canon):
    if not seq:
        return 0
    fld = hdr.split("|")
    if len(fld) < 2:
        return 0
    try:
        gidx = int(fld[1])
    except ValueError:
        return 0
    gname = canon.get(gidx, f"class_{gidx}")
    sp = (fld[4].split("-")[0] if len(fld) == 5 else f"sp_g{gidx}") or f"sp_g{gidx}"
    fa.write(f">{hdr}\n{seq}\n")
    tsv.write(f"{hdr}\t{gname}\t{sp}\n")
    return 1

if __name__ == "__main__":
    main()
