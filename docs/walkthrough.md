# 完整版完成後的學習路線

先依 README 啟動，從你能看見的行為反推程式碼。每一階段先解釋設計，再自己做一個小修改。

## 1. 先操作產品

載入 QQ 示範、拖動時間軸、儲存為示範、建立規則摘要、點開引用來源。
試著輸入不合法 JSON，再嘗試重複儲存不同 ID 的相同牌局，觀察錯誤。
使用「策略知識庫」搜尋 pot odds，新增自己的筆記。新增筆記後，下一次搜尋就能取得。

## 2. 資料如何流動

從 `frontend/src/main.tsx` 的 `preview()` 跟到 `POST /api/analyze`。
接著讀 `models.py`、`analysis.py`、`engine.py`，最後回前端的 `report` 與 `timeline`。
理解 TypeScript 型別與 Pydantic 執行時驗證為何都需要。

練習：新增一個顯示「動作前底池」的 UI 欄位，直接使用後端 `pot_before`。

## 3. 底池引擎

先讀 `initial_state()`、`apply_action()`，再讀 `tests/test_engine.py`。
對照 React reducer，追蹤 committed、remaining、pending 和 min_raise。
接著讀 `tests/test_allin.py`，說明短 all-in 何時重新開啟加注權，以及誰有資格贏邊池。

練習：在測試中增加一個三人 all-in 籌碼例子，先手算各層底池。

## 4. Persistence 與 API

讀 `storage.py` 的 parameterized SQL、content hash 與 upsert。
理解為什麼更新牌局要清除舊復盤，以及為什麼 exact duplicate 不能用來增加樣本。
在 `/docs` 呼叫 API，觀察金額字串與錯誤狀態碼。

練習：新增一個手動輸入的牌局標籤，從 JSON 契約、儲存到 UI 都接通。

## 5. RAG

從 `knowledge.py` 的六篇原創教學筆記開始。讀 `chunks()`、`bm25()` 和 `search_notes()`。
搜尋命中後，追蹤 source ID 如何進入 `generate_review()`，再回到前端可點開的引用。
這是 retrieval → context → generation 的完整路徑。沒有 Key 時，生成部分是明確標示的規則摘要。

設定自己的 Key 後，才執行一次 AI 復盤。想比較語意搜尋時，設定 `POKER_RETRIEVAL=openai` 並重啟。
比較相同查詢的 BM25 / embedding 結果，理解 cache key 為什麼包含模型名稱。

練習：新增一篇筆記與一個 query/source 評估案例，說明它會改善哪種查詢。

## 6. 個人決策模式

讀 `analysis.py` 的 contexts 與 `aggregate_patterns()`。找出 numerator、denominator 與 evidence。
示範牌局不進個人統計。三次行為是顯示門檻，沒有統計信心意義。
每手牌的選擇和其實際輸贏不能直接當作對錯標籤。

練習：設計一個新模式，先定義「什麼算一次機會」，再定義要觀察的行動。

## 7. 評估與面試

執行 pytest、前端 build、Playwright 和 retrieval evaluation。分別說明它們能驗證什麼、不能驗證什麼。
再讀 `docs/architecture.md`，練習用英文描述三個 tradeoff：

- 為什麼算術用 deterministic code？
- 為什麼先用 SQLite / BM25，如何升級？
- 為什麼有來源、有重複模式，仍不能直接宣稱找到漏洞？

完成這些之後，你能從產品流程、程式碼、測試和取捨四個角度解釋這個專案。
