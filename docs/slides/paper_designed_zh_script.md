# 逐字稿 — 論文完整內容與架構簡報

適用簡報：`paper_designed_zh.pptx` / `paper_designed_en.pptx`（兩份語言版本內容與頁序相同，此逐字稿以中文口說為準，共 19 頁）

---

## 第 1 頁｜封面

大家好，今天要跟大家完整介紹我正在投稿的這篇論文——題目是「How should genomic foundation models be evaluated for metagenomic taxonomic classification」，中文大概是「基因體基礎模型該如何被評估用於總體基因體的分類任務」。這篇是投給 *Briefings in Bioinformatics*，文章類型是 Problem-solving Protocol。

先講結論，整份論文只想講一句話：150bp 短讀的分類效能上限，是由 tokenization 決定的，不是由 backbone 的 pre-training 決定的。接下來的內容都是在鋪陳、驗證、也誠實地質疑這句話。

---

## 第 2 頁｜分隔頁：論文摘要

先花三頁把摘要拆開講，跟大家過一次 Background、Methods、Results、Conclusion 四段式摘要的內容。

---

## 第 3 頁｜摘要：Background

先講背景。Genomic foundation model，也就是 GFM，在很多基因體任務上已經證明表現不錯。但是對 150bp 這種短讀、訊號又稀疏的 metagenomic taxonomic classification，它到底好不好用，其實文獻上沒講清楚。更根本的問題是：我們不知道最後表現好壞，到底是 pre-training 的功勞、還是 tokenization 的選擇、還是單純資料量堆出來的。這個「不知道是哪個因子在起作用」，就是整篇論文要系統性拆解的核心問題。

---

## 第 4 頁｜摘要：Methods

方法上，我們用一個統一的人類腸道基因體目錄去模擬 reads，涵蓋 120 個屬、1,535 個種。然後刻意用「一次只改一個因子」的方式做四組 ablation：資料規模從 500K 一路到 250M reads；pre-training 比較 498M 參數的 pretrained backbone 跟 random-init；tokenization 比較 6-mer、12-mer、13-mer，還有 overlapping 跟 non-overlapping 的差別；最後評估的層級也是一個變因，我們同時看 read-level、sample-level、還有 detection 三種。同時全程都拿 alignment-free 的 Kraken2 當對照，而且不只用 Kraken2 的原始輸出，也用 Bracken 修正過的版本。

---

## 第 5 頁｜摘要：Results

結果的部分，最重要的一句話是：overlapping 13-mer 這個 tokenization，是決定效能上限的關鍵，而不是 pre-training。從零開始訓練的 13-mer 模型可以到 87.4%，反而贏過用了 498M 參數 pretrained backbone 的 6-mer 模型的 67.1%。而且 6-mer 模型在 50M reads 之後幾乎完全飽和，只增加 0.22 個百分點；13-mer 在同樣的資料規模區間卻可以一路衝到 98.7%。固定 tokenization 不變的話，pre-training 還是有貢獻，大概是 13.2 個百分點。在 sample level，一個準確度只有 67% 的 read 分類器，做豐度估計可以到 Pearson r=0.99；Kraken2 原始輸出是 0.82，但用 Bracken 修正後可以拉到 0.997。最後，我們也誠實地放上真實 mock community 的結果：所有方法在真實資料上都崩到 r 大概 0.4 到 0.6，沒有一個方法是明顯贏家。

---

## 第 6 頁｜五個關鍵發現

摘要之外，論文另外整理了五個 Key Points，這是投稿規定要放的部分，最多五點。

第一，資料規模的效益取決於 tokenizer：50M 到 250M 對 6-mer 幾乎沒有幫助，但對 13-mer 卻有 11 個百分點的提升。第二，決定上限的是 tokenization，不是 pre-training：13-mer 從零訓練就能打敗參數量大很多、而且還有 pretrain 的 6-mer 模型。第三，但 pre-training 不是沒用，在固定 tokenization 的前提下，它還是獨立貢獻了 13.2 個百分點——這兩個因子是可以分開看、而且都重要的。第四，read-level 的準確度跟 sample-level 的實際效用會分歧，而且更關鍵的是，這個排名在模擬數據上成立，並不代表能轉移到真實的 mock community。第五，我們給出了實務上的具體建議，也主張未來的 microbial foundation model 應該用 overlapping 的長 k-mer 去做預訓練。

---

## 第 7 頁｜分隔頁：全文導覽

接下來我會照著論文實際的九個章節順序，帶大家逐章看一次完整的論證脈絡。

---

## 第 8 頁｜全文架構地圖

這是整篇論文的骨架。從 §1 的破題、§2 說明為什麼這個任務對 GFM 特別不友善，到 §3 的 benchmark 設計，§4 資料規模、§5 pre-training 跟 tokenization 的因果拆解，§6 讀到樣本層級的效用、加上真實資料的驗證，§7 給出實務建議，最後 §8 誠實地把限制講清楚。貫穿全文的核心論點只有一個：tokenization，特別是 overlapping 13-mer，而不是 backbone 的 pre-training，決定了 150bp 短讀分類的效能上限。

---

## 第 9 頁｜為什麼 GFM 對短讀分類是逆風局

這一段對應論文的第一、第二節。先講動機：像 Kraken2、Centrifuge 這種 alignment-free 工具，在資料庫涵蓋得到的物種上又快又準，但一遇到新物種、資料庫沒有的東西就直接失效。GFM 在其他基因體任務上表現不錯，那能不能拿來解決這個問題？

但這個任務對 GFM 其實有三個結構性的不利之處。第一，reads 只有 150bp，GFM 最強的長距離建模能力在這裡完全用不上。第二，也是全文最核心的矛盾：tokenization 決定訊號有沒有被保留下來——NT-v2 用的是 non-overlapping 6-mer，一條 read 切一切大概只剩 25 個 token，很多有意義的 motif 會被硬生生切斷；相對地 Kraken2 用的是 overlapping 的長 k-mer，等於每一個子字串都有被看到。第三，這是一個 120 到 1,535 類、長尾分布的分類問題，你選哪一種 metric 來評估，很可能會直接改變「誰是贏家」這個結論。

---

## 第 10 頁｜Benchmark 設計與評估協定

這是第三節，講整個研究設計。資料來源是腸道基因體目錄，120 屬、1,535 種，用 ART 模擬出 150bp 的 reads。為了避免資料洩漏，我們同時用 read 跟 genome 兩個層級去做切分。這裡有個細節值得特別提一下：258.67M reads 的來源池，扣掉重複之後其實只有 42.64M 條唯一序列，也就是說有 6.07 倍的冗餘——這個發現後面對解釋資料規模飽和很關鍵。我們準備了三個測試池：自然分布池是主要拿來報告的，比較難的 leftover 池是保守下界，還有一個跟 Kraken2 資料庫覆蓋率對齊的池，專門拿來做公平比較。三個軸——資料規模、pre-training、tokenization——一次只改一個，而且全程都對照 Kraken2 加 Bracken。

---

## 第 11 頁｜資料規模與飽和效應

第四節的重點。固定住 NT-v2 的 6-mer tokenization，只改資料量，從 500K 一路加到 250M：準確度是 55.29%、63.05%、67.07%、67.29%，過了 50M 之後幾乎完全不動，只多了 0.22 個百分點。但同一個資料規模區間，13-mer 模型卻是一路從 87.42% 衝到 98.7%，多了 11.3 個百分點。更有說服力的證據是：6-mer 模型連自己的訓練集都 fit 不到 66% 以上，train 跟 val 幾乎打平——這代表這是一個表徵能力的瓶頸，不是優化沒做好的問題。換句話說，再多的資料量，都無法突破 tokenizer 本身設下的天花板。

---

## 第 12 頁｜Pre-training vs Tokenization 分解

第五節，也是整篇論文因果推論最重要的一段。固定在 50M reads：random-init 的 6-mer 模型是 53.88%，換成 pretrained 的 NT-v2 6-mer 是 67.07%，這中間 pre-training 貢獻了 13.19 個百分點。接著固定一樣是 50M reads、一樣是從零訓練，只改 tokenization：13-mer 是 87.42%，6-mer 是 47 到 49%，這中間 tokenization 貢獻了 20.35 個百分點——比 pre-training 的效果還大。

這邊我們也很誠實地面對一個尖銳的質疑：13-mer 的 98.7%，會不會其實只是在查表？我們做了一整條檢驗鏈：如果是靠 exact-match 查表，準確度只有 0.72%，因為 13-mer 在這個空間裡其實不是屬層級的唯一鍵；如果只是多數決，是 35.3%；用完整的 multinomial naive Bayes，可以到 74.9%；而神經網路在 naive Bayes 之上還能再加 13 個百分點，到 87.4%。所以結論是：神經網路學到的是組成的表徵，不是死記硬背的查表。

---

## 第 13 頁｜Read-level vs Sample-level：與 Kraken2 的權衡

第六節的前半段。在 in-database 的資料上，一個準確度只有 67% 的 read 分類器，做屬層級的豐度估計居然可以到 Pearson r=0.99。而 Kraken2 原始輸出的豐度會被壓低，r 只有 0.823，原因是它大概有三成的 reads 選擇不分類，這個棄權行為會系統性地讓豐度被低估。但這裡要誠實講：如果用 Bracken 重新估計，Kraken2 的豐度可以恢復到 r=0.997，跟表現最好的神經模型（r=0.999）幾乎打平。可是在 detection 這件事情上，Kraken2 加 Bracken 依然是壓倒性的優勢，ROC AUC 0.966、95% 特異度下的敏感度是 93.5%，遠高於神經模型。所以神經模型真正的價值，其實是 read-level 的準確度、還有在資料庫沒涵蓋的物種上的穩健表現，而不是豐度估計上的優勢。

---

## 第 14 頁｜真實試煉：ZymoBIOMICS Mock Community

這是第六節的後半段，我覺得是整篇論文最誠實、也最關鍵的一段。前面講的都是模擬數據，這裡我們拿兩個重複的真實 Illumina reads 去驗證——用的是 ZymoBIOMICS 的 D6331 標準品，兩筆 SRA 資料各 3M reads、135bp。21 個 mock 物種裡，有 11 個屬在我們的訓練集裡，涵蓋社群裡 81.5% 的 reads；剩下的，包括佔 14% 的 Escherichia，都不在訓練集內。

結果是：所有方法的豐度相關性，從模擬數據上的 r 大概 0.99 到 0.997，全部崩落到真實資料上的 r 大概 0.41 到 0.58。而且更有意思的是，Kraken2 在真實資料上的分類率只剩下大約 44%，模擬時是七成左右；就算用 Bracken 修正，偵測敏感度也只有 55.6%，反而比神經模型還低——NT-v2 是 83.3%，MT 13-mer 是 77.8%。結論很清楚：closed-set 模擬數據上的排名，沒有辦法直接搬到真實世界，這是全文最重要、也最需要後續解決的開放問題。

---

## 第 15 頁｜分隔頁：收尾

最後三個部分，我們來看實務建議、限制，還有整體總結。

---

## 第 16 頁｜實務建議

第七節。我們整理了一個 8 步驟、可以重複使用的評估協定：先固定 read 長度，再用 read 跟 genome 雙重切分，算唯一序列數而不只是算 reads 數，一次只改一個軸，三個層級分開評估，同時用原始跟修正後的 baseline 做比較，統一 RC-TTA 的協定，最後一定要在真實資料上驗證過，並且把所有東西都公開。另外也給了一個決策指南：低豐度的偵測任務用 Kraken2；closed-set 的 read 分類選長 k-mer 模型；如果手上只有 6-mer 的 GFM，不要指望靠堆資料量解決問題。給做模型的人的建議是：tokenization 是槓桿最大的設計選擇，未來的 microbial foundation model 應該用 overlapping 的 12 到 13-mer 去預訓練；但這裡也點名一個真實的工程挑戰——長 k-mer 的詞彙表意味著數十億參數等級的 embedding table，需要 factorization 或 hashing 這類技術去解決。

---

## 第 17 頁｜限制與未來方向

第八節，我們選擇主動把限制講清楚，而不是等 reviewer 抓到。最重要的一項是 P0：out-of-genome generalization 實驗。雖然我們已經證明 13-mer 的 98.7% 學到的是組成表徵而不是查表，但 closed-set 的驗證終究還是 closed-set，這件事還需要更多驗證才能真正下定論。第二，模擬 reads 本身有侷限，ART 模擬可能天生對 alignment 或 k-mer 方法比較有利，雖然我們已經加了真實 mock community 的驗證，但目前也只有一個標準品、11 個屬而已。第三，我們目前只跟 Kraken2 比較，之後應該加入像 Centrifuge 這樣的其他分類器。第四，目前只測了單一 read 長度——模擬用 150bp、mock 用 135bp，其他長度都還沒測試過。

---

## 第 18 頁｜Supplementary 與投稿前待補清單

補充材料的部分有八個小節，從資料切分、訓練設定、其他 backbone 的比較、完整結果、train-fit 上限分析、查表分析、計算成本，一直到真實 mock community 的細節都有涵蓋。行政資訊的部分，已經填好的有：利益衝突聲明、code availability（GitHub repo 已經公開）、還有 AI 使用揭露。但還有幾項待補：funding 的金額跟 grant number、data 的 DOI、第二作者跟 ORCID 跟 CRediT 的縮寫、致謝名單，另外 supplementary 裡 optimizer 跟 scheduler 的名稱也需要再確認一次。簡單講，科學內容的部分已經完整一致了，行政資訊是目前唯一還沒完成的部分。

---

## 第 19 頁｜總結

最後用一張投影片總結整篇論文。核心貢獻是：把資料規模、pre-training、tokenization 這三個平常很容易被混在一起講的因子，用嚴謹的一次只改一個變量的實驗設計拆開來看，最後找到 tokenization 才是真正決定性的變數。我覺得整篇論文最誠實的地方，是我們主動加入了 Bracken 這個更強的 baseline，把先前過度宣稱的豐度優勢撤回；也主動加入了真實 mock community 的驗證，把模擬數據跟真實世界之間的落差攤開來講，而不是藏起來。目前最大的待辦事項，是 out-of-genome generalization 這個 P0 實驗，再來就是作者、funding、DOI 這些行政資訊要補齊。下一步的規劃，就是先把 P0 實驗做完，再把行政資訊補齊，準備正式投稿。

謝謝大家。
