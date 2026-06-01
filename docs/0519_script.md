# 0519 Weekly Progress — 逐字稿

---

## Slide 1 — Title

（直接進下一張）

---

## Slide 2 — This Week's Highlights

本週的主題是 sample-level evaluation，也就是把 per-read 的預測結果聚合成樣本層級，看它在實際應用場景下的表現。

重點有四個。

第一，在 genus level，我們把三個模型都跑了：MT 13-mer、NT-Genus、MT 6-mer。主要發現是：在**相同 6-mer tokenization 條件下**，NT-Genus 在所有 sample-level 指標上都勝過 MT 6-mer，包括 Pearson r、Bray-Curtis、和 detection AUC。而 NT-Genus 的豐度估計表現其實非常接近 MT 13-mer，r 是 0.993 對 0.999，差距很小。

第二，在 species level，MT 13-mer 跨過了一個實用門檻：Pearson r 0.466、ROC AUC 0.966，已經可以實際用來估算物種豐度。NT-Species 在 17.8% read accuracy 的情況下 Pearson r 只有 0.135，雖然不是完全的 0，但跟 MT 13-mer 的 0.466 差了 3.4 倍，顯示 6-mer tokenization 在 species level 無法突破這個門檻。

第三，hierarchical masking 在 MT 13-mer species 上有小但一致的提升，四個指標全部改善。

第四，整個故事的核心結論是：tokenization 的選擇不只影響 read accuracy，它直接決定了方法在 sample level 有沒有實用性。

---

## Slide 3 — Section: Genus-Level

---

## Slide 4 — Genus 3-model results table

這是三個 genus model 的 sample-level 完整數字。

我想強調兩個比較。

第一個比較是 **NT-Genus vs MT 6-mer**。兩者都用 6-mer tokenization，但 NT-Genus 有 pre-trained backbone，MT 6-mer 沒有。NT-Genus 的 Bray-Curtis 是 0.094，MT 6-mer 是 0.167，前者少了將近一半的豐度誤差。Detection AUC 是 0.705 對 0.569。這個差距完全來自 pre-trained backbone 的貢獻，tokenization 都一樣。

第二個比較是 **NT-Genus vs MT 13-mer**。MT 13-mer 用的是 overlapping 13-mer，有 87.4% read accuracy，明顯比 NT-Genus 的 67.1% 更高。但在**豐度估計**上，差距很小：Pearson r 是 0.993 對 0.999，幾乎一樣高。真正拉開差距的是 detection：AUC 0.705 對 0.900，這是因為 detection task 對 per-read accuracy 更敏感，等一下 Slide 15 會解釋原因。

genus level 有 120 個 class，每個 class 的平均豐度大概是 0.83%，誤分類的 reads 會分散到各個 genus，大部分的誤差在聚合的時候互相抵消。這就是為什麼 genus level 的 Pearson r 全部都很高，連最差的 MT 6-mer 都有 0.984。

---

## Slide 5 — Genus 3-model bar figure

這張圖把三個指標的比較視覺化。

左邊 Pearson r：三個模型都在 0.984 以上，幾乎一樣高，bar 高度很相近，差異不明顯。

中間 Bray-Curtis：這裡分開了。MT 13-mer 0.028，NT-Genus 0.094，MT 6-mer 0.167——三個 bar 有明顯的梯度，代表 Bray-Curtis 是在 genus level 能區分模型的敏感指標。

右邊 ROC AUC：也有梯度，0.900、0.705、0.569，同樣能區分三個模型。

結論：genus level 的 Pearson r 已經飽和，Bray-Curtis 和 detection AUC 才是有鑑別力的指標。

---

## Slide 5b — Genus: Read Accuracy vs Abundance Quality

這張 scatter 把三個模型的 read accuracy 和 sample-level 品質的關係畫出來。

左圖是 Pearson r：48%、67%、87%，三個點的 r 值分別是 0.984、0.993、0.999，幾乎貼著上界，曲線趨近飽和。這說明在 genus level，read accuracy 只要過了 ~50%，豐度估計就已經是高品質的了。

右圖是 Bray-Curtis：隨著 read accuracy 提升，BC 從 0.167 降到 0.094 再降到 0.028，是單調下降的，而且還沒飽和。NT-Genus 的 0.094 在 MT 6-mer 和 MT 13-mer 之間，完全跟 read accuracy 的排序一致。

---

## Slide 6 — Section: Species-Level

---

## Slide 7 — Species results summary table

這裡的情況跟 genus level 非常不同。

先看上半部。NT-Species flat 有 17.8% read accuracy，Pearson r 是 0.135——noise floor 限制下的低相關性。NT-Species hier（用 NT-Genus 66% router 做 topk=1 logit masking）反而更差，read acc 掉到 15.8%、Pearson r 降到 0.106、Bray-Curtis 從 0.589 升到 0.608——router 不夠準時 hier masking 是 net negative。MT 6-mer models 更差，read accuracy 只有 6–9%，Pearson r 在 0.034–0.065 之間。所有模型都在 100K 獨立 test set 上評估，條件統一。

下半部的 MT 13-mer flat 有 49.7% read accuracy，Pearson r 0.466，ROC AUC 0.966。加上 hierarchical masking 之後（router 87.5%），Pearson r 提升到 0.478，ROC AUC 0.967，四個指標全部改善。

這裡有兩個值得記的觀察：第一，read accuracy 在 20% 以下的模型，Pearson r 全部接近 0；到了 50% 才開始有意義。原因是 species level 的 class 數量是 1535，每個 species 的平均豐度只有 0.065%，誤分類的 reads 平均分散到另外 1534 個 class，噪聲完全蓋過信號。等一下 Slide 15 會定量解釋這個機制。第二，hierarchical masking 的方向完全由 router accuracy 決定：87.5% router 提升所有指標，66% router 在多數指標上反而退步，48.9% router 退步最多——這是個 monotonic 的 pattern，Slide 13 會再強調。

---

## Slide 8 — Species summary 4-panel figure

這張是四個指標的同步比較。

四個 panel 從左到右是：read accuracy、Pearson r、1 − Bray-Curtis（越高越好）、ROC AUC。

可以看到 MT 13-mer flat 和 hierarchical 在所有四個指標上都明顯高於其他四個模型，而且 hierarchical 在每個指標上都比 flat 稍高——這個一致性就是 hierarchical masking 在 router 夠準（87.5%）時有效的證據。

NT-Species flat 的 Pearson r 0.135 雖然比 MT 13-mer 低很多，但明顯高於 MT 6-mer 的 0.034–0.065，跟 read accuracy 的排序一致。ROC AUC 也是：NT-Species 0.794 > MT 6-mer 0.667–0.690，差距很清楚。NT-Species hier 的 bar 在多數 panel 上都比 NT-Species flat 矮一點——同樣 hier masking、但 router 從 87.5% 換成 66%，方向就反過來了，這是 router 門檻的直接視覺證據。

---

## Slide 9 — Abundance estimation bar

這張把豐度估計的兩個指標——Pearson r 和 Bray-Curtis——拉出來比較。

最直觀的觀察是：只有 MT 13-mer 的 Pearson r 是有意義的（0.466–0.478）。NT-Species flat 的 0.135 雖然比 MT 6-mer 的 0.034–0.065 高，但仍遠低於實用門檻；NT-Species hier 還掉到 0.106，比 flat 更差。Bray-Curtis 那邊，NT-Species flat 的 0.589 比 MT 6-mer 的 0.65–0.69 稍低，hier 是 0.608，介於 flat 和 6-mer 之間；MT 13-mer 的 0.369–0.378 才算是有一定品質的豐度估計。

這張圖的六個 species model 現在都用同一個 100K 獨立 test set，所以數字完全可比。要注意的是 genus 和 species 的評估條件不同（genus 5M pool / 50K reads/sample，species 100K pool / 1K reads/sample），所以這兩個任務的絕對數字不能直接跨任務比較。

---

## Slide 10 — ROC AUC comparison

這張是 species detection 的 ROC AUC 比較。

MT 13-mer flat 和 hierarchical 的 AUC 是 0.966–0.967，非常高，代表模型對 species 的有無有很強的辨別力。

NT-Species flat 是 0.794，hier 是 0.796——這是 NT-Species hier 唯一沒退步的指標，但提升只有 0.002，沒實質意義。兩者都比 MT 6-mer 模型（0.667–0.690）高，跟 read accuracy 的排序完全一致（15.8%/17.8% vs 6–9%）。現在所有模型都用同一個 100K 獨立 test set，數字完全可比。

MT 6-mer models 是 0.667–0.690，不比 NT-Species 差太多，但都是 6-mer 的限制。

---

## Slide 11 — Operating points figure

這張看的是在固定 specificity 下的 sensitivity。

MT 13-mer hierarchical 在 90% specificity 下，sensitivity 是 92.5%。也就是說，在允許 10% 的誤報率時，它可以找到 92.5% 的真實 species。

NT-Species 在同樣的 90% specificity 下是 55.8%，只找到一半多一點。

MT 6-mer flat 是 41.2%，更差。

這個差距在 99% specificity 時會更大——MT 13-mer hier. 的 sensitivity 還有 83%，NT-Species 掉到接近 0。

---

## Slide 12 — Detection threshold curves

這張是用 predicted read count 作為 threshold 的 sensitivity / specificity 曲線，對六個 species model 一起畫。

Sensitivity panel（左）：MT 13-mer 在 threshold=5 reads 時，sensitivity 是 78.4%；MT 6-mer 只有 20.3%；NT-Species 介於中間。

Specificity panel（右）：所有模型在 threshold 越高的時候 specificity 都上升，但 MT 13-mer 在低 threshold 就有高 specificity，代表它的 false positive 本來就少。

實際使用的時候，可以設 threshold = 5–10 reads 來平衡 sensitivity 和 specificity，MT 13-mer 在這個點上效果最好。

---

## Slide 13 — MT 13-mer: flat vs hierarchical detection

這張特別把 MT 13-mer flat 和 hierarchical 的 detection 放大比較，用不同的 abundance threshold 來切。

左圖 sensitivity：hierarchical 在每一個 abundance threshold 上都比 flat 高，差異在高 abundance 端（≥1%）最明顯，從 56.7% 提升到 58.4%。

右圖 specificity：兩個模型幾乎一樣，hierarchical 沒有因為提高 sensitivity 而犧牲 specificity。

這就是 genus-guided logit masking 的效果：把每個 read 的 species 預測限制在對應的 genus 範圍內，排除了跨 genus 的混淆，在 router 夠準（87.5%）的情況下，consistently 提升所有指標。

我們用同樣的 topk=1 masking 在另外兩個 router 上做對照實驗，得到一個 monotonic 的 pattern：87.5% MT 13-mer router → 五個指標全部提升；66% NT-Genus router → 五個指標有四個退步、ROC AUC 微升 0.002；48.9% MT 6-mer router → 退步最多。這個三段式比較直接驗證 router accuracy 是 hier masking 有沒有用的決定性條件——大概要 80% 以上才會是 net positive。

---

## Slide 14 — Section: Why Read Accuracy → Abundance Quality

---

## Slide 15 — Connecting Read Accuracy to Sample-Level Utility

這張解釋為什麼 read accuracy 和 sample-level 表現之間有這麼強的非線性關係。

規律是：read accuracy 低於 ~20%，Pearson r 受 noise floor 壓制（NT-Species: 17.8% → 0.135）；到了 ~50% 就有 0.47；到了 ~67% genus level 就有 0.993，但那是因為只有 120 個 class。

原因是什麼？核心是 noise floor 的概念。

以 1535 個 species 為例，每個 species 的真實豐度大概是 0.065%，對應每個 sample 1000 reads 裡面大約 0.65 個 read。

如果一個模型只有 17.8% accuracy，也就是 82.2% 的 reads 都分配錯了，而且這些錯誤的 reads 平均分散到另外 1534 個 species。每個 species 大概會收到 (1000 × 0.822) / 1534 ≈ 0.54 個 spurious reads，信號才 0.65 reads——SNR 接近 1。在這種條件下 Pearson r 被壓到 0.135，遠低於實用範圍。

到了 50% accuracy，正確的 reads 有 500 個，噪聲有 (500) / 1534 ≈ 0.33 reads/species，信號開始能蓋過噪聲，Pearson r 才能回到 0.47。

這個分析告訴我們，在 1535 個 species 的任務下，要讓豐度估計有意義，需要 ~40–50% 的 read accuracy 作為門檻。NT-Species 的上限是 15.9%，永遠過不了這個門檻；MT 13-mer 的 49.7% 剛好跨過去了。

tokenization 選擇不是只在 read accuracy 上的差距，它決定了方法有沒有實用性。

---

## Slide 16 — Section: Next Steps

---

## Slide 17 — Remaining Experiments & Timeline

TWCC 這邊本週的 evaluation 都跑完了。NT-Genus、NT-Species、四個 MT species models 的 sample-level 評估全部完成，論文的 §4.13 sample-level section 也已經更新完畢，現在是 131 頁。

目前還在進行的是 Taiwana2 上的 MT per-genus species classifiers。這是下一個主要的比較實驗：如果 MT 13-mer per-genus classifiers 的表現能接近 oracle genus 的 50.86%，那就代表 per-genus decomposition 在有夠強 tokenizer 的條件下是真的有效的。這也是我們自己的 NT-Genus per-genus pipeline 的 upper bound 參考。

步驟是：Split 45M reads by genus → 訓練 81 個 MT 6-mer per-genus classifiers → 抽出 predictions → scp 到 TWCC 做 sample-level eval。

---

## Slide 18 — Complete Results reference

這張是所有數字的完整整理，老師如果要查對照可以用這張。

最重要的幾個數字：
- NT-Genus genus 67.07%（RC TTA），sample-level Pearson r 0.993，BC 0.094
- MT 13-mer genus 87.42%，r 0.999，BC 0.028
- MT 13-mer hierarchical species 50.86%，sample-level Pearson r 0.478，ROC AUC 0.967
- NT-Species 17.8% flat，sample-level Pearson r 0.135（100K independent test set, 1K reads/sample）
- NT-Species hierarchical（NT-Genus 66.1% router）：15.8% read acc，Pearson r 0.106，ROC AUC 0.796（大多數指標比 flat 差，驗證 masking 需要 >80% router 才有效）

---

## Slide 19 — Section: Backup

以下是備用投影片，如果老師有問題可以翻到這裡。

---

## Slide 20 — Sample eval methodology

（如果老師問 sample-level evaluation 是怎麼做的）

我們用 `evaluate_sample.py` 從已經算好的 predictions 檔案直接做聚合，不需要重新跑 GPU inference。

有兩種 sample 類型。第一種是 random partition samples，把 test pool 切成不重疊的子集，每個 sample 都有所有 genus/species，用來評估豐度估計。第二種是 sparse community samples，每個 sample 只選一部分的 genus（60/120 或 50/120），剩下的當 true negative，用來做 binary detection。

metrics 是 per-sample 算完再取 mean ± std。

Genus 用 5M pool、reads_per_sample=50K；Species 因為 pool 只有 100K reads（1535 個 species 平均每個才 65 reads），所以 reads_per_sample 只能設 1000。這兩個條件不一樣，genus 和 species 的指標不能直接比絕對值。

---

## Slide 21 — Data scaling figure

（如果老師問 scaling 的部分）

這是 genus RC TTA accuracy 對訓練資料量的關係圖。三個數據點：500K 到 5M 加了 7.76 pp，5M 到 50M 加了 4.02 pp，每增加 10 倍資料，增益在遞減。MetaTransformer 的星號是他們 paper 報告的數字，x 軸位置是依照他們訓練的 token 數換算的，不完全可比。

---

## Slides 22–24 — Individual ROC / scatter figures

（backup 個別實驗的圖，需要的時候翻）
