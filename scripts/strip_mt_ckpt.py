import torch, os, sys
src=sys.argv[1]; out=sys.argv[2]
print("loading (cpu) — 25.8GB from NFS, be patient...", flush=True)
ck=torch.load(src, map_location="cpu", weights_only=False)
keys=list(ck.keys()) if isinstance(ck,dict) else []
print("top-level keys:", keys, flush=True)
drop=[k for k in keys if any(s in k.lower() for s in ('optim','sched','scaler','grad_'))]
slim={k:v for k,v in ck.items() if k not in drop}
print("kept:", list(slim.keys()), "| dropped:", drop, flush=True)
torch.save(slim, out)
print(f"SAVED {out}: {os.path.getsize(out)/1e9:.2f} GB  (was {os.path.getsize(src)/1e9:.2f} GB)", flush=True)
