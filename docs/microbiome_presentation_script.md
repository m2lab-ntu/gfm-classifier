# Microbiome 架構圖 — 講稿（明儒 AI 方法部分）

> 搭配架構圖中「AI Deep Learning Method」區塊使用。
> 輔助圖片：`pipeline_gfm_detailed.png`、`comparison_traditional_vs_ai.png`

---

## 一、開場銜接（從架構圖整體切入你的部分）

大家可以看到這張圖的中間有兩條路徑：上面是昭佑負責的 **Traditional Alignment** 方法，利用 BLASTn 去比對 NCBI 資料庫；下面是我負責的 **AI Deep Learning** 方法。

兩種方法的輸入是一樣的——都是從環境樣本中萃取出來的混合 DNA，也就是 metagenomic short reads，大約 150 個鹼基對長。我們的目標也是一樣的：把每一條 read 分類到正確的物種。

差別在於「怎麼做分類」。

---

## 二、為什麼需要 AI 方法？

昭佑的 BLASTn 方法非常直觀：拿一條 query read，去比對一個巨大的參考資料庫，找到最相似的序列，就知道它是哪個物種。這在精確度上很可靠，但有兩個限制：

1. **速度**：每一條 read 都要和資料庫裡幾百萬條序列做比對，計算量是 O(n × m)，在大規模 metagenomics（幾千萬條 reads）的場景下會非常慢
2. **參考依賴**：如果資料庫裡沒有收錄某個物種的參考基因組，就無法辨識

AI 方法的思路不同：我們不做比對，而是讓模型「學會」DNA 序列的特徵，直接做分類。推論速度大約是每秒 1,800 條 reads，而且可以透過 pre-training 學到 DNA 的通用特徵。

> **（可搭配展示 `comparison_traditional_vs_ai.png`）**

---

## 三、我的方法：Genomic Foundation Model + LoRA

> **（展示 `pipeline_gfm_detailed.png`）**

我的方法可以拆成四個階段：

### 階段 1：6-mer Tokenization

首先，把 DNA 序列轉換成模型能理解的格式。我們使用 **6-mer tokenizer**，也就是用一個滑動窗口，每 6 個鹼基為一組切割成 token。一條 150bp 的 read 大約會產生 25 個 tokens，詞彙表大小是 4,101 個。

這跟 NLP 裡的 tokenization 概念完全一樣——把文字切成詞，這裡是把 DNA 切成短片段。

### 階段 2：Nucleotide Transformer v2（Pre-trained Backbone）

核心是 **Nucleotide Transformer v2**，由 InstaDeep 開發的基因組基礎模型。它是：
- 一個 **29 層的 Transformer** 架構（跟 GPT 一樣的技術）
- 在 **32 億條基因組序列**上做 pre-training（遮蔽語言模型，masked language modeling）
- 總共 **4.98 億個參數**
- 輸出每個 token 的 **1024 維向量表示**

簡單來說，這個模型已經「讀過」大量的 DNA 序列，學會了 DNA 的語法和結構特徵。我們拿來做 fine-tuning，讓它專門做分類任務。

### 階段 3：LoRA 微調（Parameter-Efficient Fine-Tuning）

但 4.98 億個參數全部重新訓練太貴了。所以我們用 **LoRA（Low-Rank Adaptation）** 技術：

- 只在 Transformer 的 **query、key、value** 矩陣上插入小型的低秩矩陣
- 實際訓練的參數只有 **550 萬個**，佔總參數的 **1.1%**
- 效果接近全量微調，但計算成本低非常多

### 階段 4：Attention Pooling → 分類

最後，Transformer 輸出的是一組 token embeddings（每個 token 一個向量）。我們用一個 **Attention Pooling** 機制，讓模型自己學習「哪些 token 比較重要」，加權聚合後進行分類。

分類目標有兩個層級：
- **Genus（屬）**：120 個類別
- **Species（種）**：1,535 個類別

---

## 四、目前的進度與成果

- 資料量：使用 **5,000 萬條平衡 reads** 進行訓練（來自 HGR-UMGS 人類腸道參考基因組）
- Genus 分類準確率：目前約 **64%**（仍在訓練中，尚未收斂）
- 核心發現：**資料量是最關鍵的因素**——從 50 萬條擴展到 500 萬條，準確率就提升了近 8 個百分點
- 硬體：在 **NVIDIA H100 80GB GPU** 上訓練，VRAM 使用率不到 5%，資源非常充裕

---

## 五、與昭佑方法的互補性

我們的目標不是用 AI 取代 BLASTn，而是讓兩者互補：

| | Traditional (BLASTn) | AI (GFM + LoRA) |
|---|---|---|
| 速度 | 慢（逐條比對） | 快（~1,800 reads/sec） |
| 精確度 | 高（有參考時） | 依賴訓練資料 |
| 新物種 | 無法辨識 | 可學習特徵模式 |
| 適用場景 | 精確鑑定、小量樣本 | 大規模篩選、快速分類 |

未來的整合方向是：**先用 AI 做快速初篩，再用 BLASTn 做精確驗證**，兼顧速度與準確度。

---

## 六、接下來的研究計畫

1. **Backbone Ablation**：把 29 層的 pre-trained backbone 換成單層 Transformer（從頭訓練），驗證 pre-training 的價值
2. **Species-level Classification**：用 50M 資料訓練 species 模型，結合 hierarchical classification（先預測 genus，再在 genus 內預測 species）
3. **資料持續 scaling**：最終目標是使用完整的 2.58 億條 reads

---

> **Q&A 備用回答：**
>
> **Q: 為什麼不直接用 ChatGPT / LLM？**
> A: 一般的 LLM 是在自然語言上訓練的，不懂 DNA 語法。Nucleotide Transformer 是專門在基因組序列上 pre-train 的，理解的是鹼基之間的生物學關係。
>
> **Q: 準確率為什麼還沒到很高？**
> A: 主要是資料量還在 scaling 中。MetaTransformer（同類型的 AI 方法）用大規模平衡資料集（從 2,505 個基因組模擬，估計約 6 億條 reads）達到 98.3% genus recall，我們目前用 5,000 萬條還在訓練。資料量是最大的瓶頸。
>
> **Q: LoRA 是什麼？**
> A: 打個比方，就像你有一個已經學會英文的翻譯員，你不需要從零開始教他中文，只需要教他一些中文的「轉換規則」就好。LoRA 就是這些小型的轉換規則，讓大模型用極少的訓練量就能適應新任務。
