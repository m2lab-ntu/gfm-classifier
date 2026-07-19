# Handoff — 本地 (RTX 4090):MT 6-mer 在真實 mock (D6331) 的推論

## 目的
論文改版:§6 的 MetaTransformer baseline 一律以 **6-mer** 呈現(和 NT-v2 6-mer 公平對照)。
`tab:mock`(真實 mock community)目前只有 MT 13-mer + NT-v2,缺 **MT 6-mer**,需要補跑。
**只做推論,單張 4090,不用訓練、不用 HPC。**

跟先前 MT 13-mer 的 mock 跑法完全一樣,只換「模型 + vocab + class head」:
- 模型:MT 6-mer(genus, stride-1 overlap)取代 MT 13-mer
- vocab:vocab_6mer.txt 取代 vocab_13mer.txt
- 其餘(reads、composition、genus_map、eval 腳本)都不變

## 需要的檔(來源路徑;若 4090 上路徑不同請對應調整)
| 用途 | 路徑 |
|---|---|
| MT 6-mer 模型 (genus, k=6, stride=1, 50M) | `/work/ymj1123ntu/mt_models/mt_6mer_stride1_50M_887333/`(含 `config.yaml` + `checkpoints/classification_transformer_ckpt_best.pt`)|
| 6-mer vocab | `/work/ymj1123ntu/gfm-classifier/small_predictions/vocab_6mer.txt` |
| 推論腳本 | `/work/ymj1123ntu/gfm-classifier/scripts/extract_mt_predictions.py` |
| 評估腳本 | `/work/ymj1123ntu/gfm-classifier/mock_community_eval/eval_mock_abundance.py` |
| genus 對照表 | `/work/ymj1123ntu/data/labels_100K.tsv`(欄位 `genus_class,genus_name`)|
| 期望組成 | `/work/ymj1123ntu/gfm-classifier/mock_community_eval/composition.csv` |
| MetaTransformer src(PYTHONPATH) | `/work/ymj1123ntu/MetaTransformer/src` |
| **mock reads(關鍵)** | 先前跑 MT 13-mer / NT-v2 mock 用的**同一份** D6331 單行 FASTA(SRR33710519、SRR33710518 各一份 R1)。**請直接沿用同一份檔**,確保輸入完全一致。若 4090 上已不在,見文末「重抓 reads」。|

> ⚠️ 一定要沿用先前 mt13/ntv2 那份 mock FASTA(header 已含 `|` 分隔欄位、genus 欄在 index 3)。
> 用不同的檔或不同 header 格式,`extract_mt_predictions.py` 會讀不到 label 欄而報錯,或造成輸入不一致、數字不可比。

## 步驟

環境:照 `local_realworld_eval/README.md` §1–3 的 env(和先前 mt13 mock 相同的 conda 環境)。

### 1) 每個 replicate 各跑一次推論(genus,class_indices=3)
把「只含該 replicate mock.fa」的資料夾當 `--val_dir`(和 mt13 一樣,一個資料夾一份 .fa)。

```bash
MT_SRC=/work/ymj1123ntu/MetaTransformer/src
EXP=/work/ymj1123ntu/mt_models/mt_6mer_stride1_50M_887333
VOCAB=/work/ymj1123ntu/gfm-classifier/small_predictions/vocab_6mer.txt
cd /work/ymj1123ntu/gfm-classifier

# replicate 1 (SRR33710519)
PYTHONPATH=$MT_SRC python scripts/extract_mt_predictions.py \
  --exp_dir $EXP \
  --val_dir <dir_with_only_SRR33710519_mock.fa> \
  --vocab $VOCAB \
  --out mock_community_eval/out/mock_mt6/rep1_preds.npz \
  --class_indices 3 --batch_size 1024

# replicate 2 (SRR33710518)
PYTHONPATH=$MT_SRC python scripts/extract_mt_predictions.py \
  --exp_dir $EXP \
  --val_dir <dir_with_only_SRR33710518_mock.fa> \
  --vocab $VOCAB \
  --out mock_community_eval/out/mock_mt6/rep2_preds.npz \
  --class_indices 3 --batch_size 1024
```
(`preds.npz` 裡的 `labels` 是 placeholder,eval 會忽略。)

### 2) 各自算 mock 豐度指標
```bash
cd /work/ymj1123ntu/gfm-classifier/mock_community_eval
for R in rep1 rep2; do
  python eval_mock_abundance.py \
    --preds_npz out/mock_mt6/${R}_preds.npz \
    --genus_map /work/ymj1123ntu/data/labels_100K.tsv \
    --composition composition.csv \
    --exp_name "MT 6-mer ${R}" \
    --detect_threshold 0.01 \
    --out out/mock_mt6/${R}_metrics.json
done
```

### 3) 取兩 replicate 平均(論文 tab:mock 報均值)
把兩個 `*_metrics.json` 的 `pearson_r_in_set`、`bray_curtis_in_set`、
`detection_sensitivity_in_set`、以及 assigned-read fraction 各自平均即可。

## 要回傳給我的東西
1. `out/mock_mt6/rep1_metrics.json`、`rep2_metrics.json`(兩份完整 json)
2. 兩 replicate 的 **per-genus 預測分數表**(給 Supplementary;和 mt13 一樣的格式)
3. 用的模型 scale 確認(見下)、reads 的 accession 與 read length(median bp)

我會用這些把 `tab:mock` 的「MT 13-mer」列換成「MT 6-mer」、更新 §6 內文與 Supplementary per-replicate 表。

## 兩個要注意 / 要回報的點
- **模型 scale**:我在 `/work` 只確認到 6-mer genus 的 **50M** checkpoint(`mt_6mer_stride1_50M_887333`,就是產出論文 §5 「MT 6-mer 48.87%」那個)。先前 MT 13-mer mock 用的是 **250M**。
  - 若 4090 上有 **6-mer stride-1 genus 250M** 的 checkpoint,優先用它(和 mt13 mock 的 scale 對齊);
  - 沒有就用 50M(`887333`)即可——真實 mock 上 6-mer 50M vs 250M 差異極小(§5:48.9% vs 50.6%),且和論文別處「MT 6-mer (scratch)」標示一致。**請回報實際用了哪個 scale。**
- **一定要用 stride-1 overlap 的 6-mer**(不是 non-overlap stride-6),才和 §5/§6 其他 MT 6-mer 數字同一設定。
- **read length**:回報 mock reads 的 median bp(D6331 之前是 ~135 bp);這只影響敘述,不影響本推論。
- **genus only**:`--class_indices 3`(species 索引跨資料集不對齊,不要用)。

## 若 4090 上已無 reads —— 重抓 D6331
```bash
for ACC in SRR33710519 SRR33710518; do
  prefetch $ACC && fasterq-dump --split-files $ACC   # -> ${ACC}_1.fastq (R1)
done
```
再依先前 mt13/ntv2 mock 的做法,把每個 replicate 的 R1 轉成單行 FASTA
(header 需保留 `|` 分隔欄位、genus placeholder 在 index 3),放進各自的 `val_dir`。
**若可能,沿用先前那份 FASTA 而不要重建,以確保與 mt13/ntv2 完全同輸入。**
