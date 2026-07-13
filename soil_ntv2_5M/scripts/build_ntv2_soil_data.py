#!/usr/bin/env python3
"""
Build NT-v2 soil data in the gut pipeline's name-keyed format:
  <name>.fa            : reads (full sequence, unwrapped)
  <name>_labels.tsv    : seq_id, genus_name, species_name

Label from soil header (class_indices=1): genus_idx = field[1] -> canonical name.
species_name = accession (field[4] before first '-') or sp_<species_idx> if missing
(Candidatus 3-field reads). Samples from multiple byte offsets for representativeness.
"""
import os, json, argparse

CANON = json.load(open("/nas2/gfm-classifier/soil_reeval/idx2name.json"))
CANON = {int(k): (v if v else f"class_{k}") for k, v in CANON.items()}

def emit(src, out_fa, out_tsv, n_reads, offsets, chunk=120_000_000):
    per = n_reads // len(offsets)
    size = os.path.getsize(src)
    tot = 0
    with open(src, "rb") as f, open(out_fa, "w") as fa, open(out_tsv, "w") as tsv:
        tsv.write("seq_id\tgenus_name\tspecies_name\n")
        for off in offsets:
            f.seek(min(off, size - chunk)); raw = f.read(chunk)
            j = raw.find(b"\n>"); blob = raw[j+1:] if j >= 0 else b""
            recs = blob.split(b"\n>"); n = 0
            for k, p in enumerate(recs):
                if n >= per or k == len(recs) - 1:
                    break
                rec = (p if p.startswith(b">") else b">" + p).decode("latin-1")
                lines = rec.split("\n")
                hdr = lines[0][1:]                       # drop '>'
                seq = "".join(lines[1:]).strip()
                if not seq:
                    continue
                fld = hdr.split("|")
                if len(fld) < 2:
                    continue
                try:
                    gidx = int(fld[1])
                except ValueError:
                    continue
                gname = CANON.get(gidx, f"class_{gidx}")
                if len(fld) == 5:
                    acc = fld[4].split("-")[0]
                    spname = acc if acc else f"sp_{fld[3]}"
                else:                                    # malformed Candidatus (3-field)
                    spname = f"sp_g{gidx}"
                fa.write(f">{hdr}\n{seq}\n")
                tsv.write(f"{hdr}\t{gname}\t{spname}\n")
                n += 1
            tot += n
    return tot

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out_fa", required=True)
    ap.add_argument("--out_tsv", required=True)
    ap.add_argument("--n_reads", type=int, required=True)
    ap.add_argument("--n_offsets", type=int, default=16)
    ap.add_argument("--off_lo_frac", type=float, default=0.0)
    ap.add_argument("--off_hi_frac", type=float, default=0.49)
    args = ap.parse_args()
    size = os.path.getsize(args.src); chunk = 120_000_000
    lo = int(size * args.off_lo_frac); hi = int(size * args.off_hi_frac) - chunk
    hi = max(hi, lo)
    offs = [int(lo + (hi - lo) * i / max(args.n_offsets - 1, 1)) for i in range(args.n_offsets)]
    tot = emit(args.src, args.out_fa, args.out_tsv, args.n_reads, offs)
    print(f"wrote {tot:,} reads -> {args.out_fa}")

if __name__ == "__main__":
    main()
