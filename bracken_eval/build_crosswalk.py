#!/usr/bin/env python3
"""
Build a DB `species_N` -> model genus_class (and species_class) crosswalk.

The custom Kraken2 DB assigns each of the 1,535 genomes a synthetic taxid;
`species_N` has N = taxid - taxid_offset (offset=2). We join the DB's
accession->taxid (seqid2taxid.map, inside the Kraken2 DB dir) with the labels'
accession(species_name)->genus_class/species_class.

Output TSV columns: species_N  species_class  genus_class  genus_name

If accessions don't match cleanly, reuse the exact map that produced
predictions_kraken2_twcc.npz instead (see README "crosswalk note").
"""
import argparse, re, sys
import pandas as pd


def norm_acc(s):
    """Normalise an accession/name for matching: drop version suffix & whitespace."""
    s = str(s).strip()
    # strip a trailing .N version (GCF_000155515.1 -> GCF_000155515)
    s = re.sub(r"\.\d+$", "", s)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seqid2taxid", required=True, help="Kraken2 DB seqid2taxid.map (seqid <tab> taxid)")
    ap.add_argument("--labels", required=True, help="labels_100K.tsv (species_name, species_class, genus_class, genus_name)")
    ap.add_argument("--taxid_offset", type=int, default=2)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    lab = pd.read_csv(args.labels, sep="\t")
    for c in ["species_name", "species_class", "genus_class", "genus_name"]:
        if c not in lab.columns:
            sys.exit(f"labels file missing column: {c}")
    lab["acc"] = lab["species_name"].map(norm_acc)
    acc2row = {a: r for a, r in zip(lab["acc"], lab.to_dict("records"))}

    # seqid2taxid.map: "<seqid>\t<taxid>" (seqid often contains the accession)
    seq = pd.read_csv(args.seqid2taxid, sep=r"\s+", header=None,
                      names=["seqid", "taxid"], usecols=[0, 1], engine="python")
    seq["taxid"] = seq["taxid"].astype(int)

    rows, unmatched = {}, 0
    for seqid, taxid in zip(seq["seqid"], seq["taxid"]):
        N = taxid - args.taxid_offset
        if N in rows:
            continue
        # try to find the labels accession inside the seqid
        cand = norm_acc(seqid)
        hit = acc2row.get(cand)
        if hit is None:  # substring search fallback
            for a, r in acc2row.items():
                if a and a in cand:
                    hit = r; break
        if hit is None:
            unmatched += 1
            continue
        rows[N] = (N, int(hit["species_class"]), int(hit["genus_class"]), hit["genus_name"])

    out = pd.DataFrame(sorted(rows.values()),
                       columns=["species_N", "species_class", "genus_class", "genus_name"])
    out.to_csv(args.out, sep="\t", index=False)
    print(f"wrote {args.out}: {len(out)} species_N mapped; {unmatched} seqid taxids unmatched")
    if unmatched:
        print("  (unmatched are usually version/format mismatches; if many, use the "
              "authoritative map from the kraken2->npz conversion instead — see README.)")


if __name__ == "__main__":
    main()
