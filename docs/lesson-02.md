# 第二課：從下注事件重建底池與籌碼

目標：逐一重播動作、保存決策當下的狀態，並計算跟注價格。
本課分支 `lesson/02-pot-replay` 建立在第一課之上，PR 的 base 是第一課分支。

## 1. 更新與執行

先 commit 或 stash 你尚未保存的修改，再從 repo 根目錄執行：

```powershell
git fetch origin
git switch lesson/02-pot-replay
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m poker_review examples/qq_large_open.json --replay
.\.venv\Scripts\python.exe -m pytest -q
```

若尚未建立環境，先 `python -m venv .venv`。程式碼在 `src/poker_review/engine.py`。
先閱讀下面三個小概念，再讀完整引擎。

## 2. 概念一：只把新增籌碼加入底池

```python
added = action.amount_to - state.committed[player_id]
remaining[player_id] -= added
pot += added
```

`committed` 是這位玩家「本街已投入」的金額。BB 已付 2，現在 call to 25，
只會再付 23。換街時 committed 歸零，總底池與剩餘籌碼保留。
這和前端 reducer 類似：一個事件對應一次狀態更新。

## 3. 概念二：一個動作會改變哪些狀態

`PokerState` 儲存 pot、remaining、committed、folded、pending 等資料。
`pending` 是這一輪還需要行動的玩家佇列；每個動作必須來自第一個人。

- fold：移除玩家的行動資格，已投入的錢留在底池。
- check / call：完成一次回應，從 pending 移除。
- bet / raise：所有其他未棄牌玩家重新進入 pending。
- pending 清空：可進下一街；BB 在 limp pot 中仍保留 check/raise 的機會。

`apply_action()` 回傳一個 Transition，包含動作前、動作後的狀態。
它會複製更新到的字典，避免後續事件改寫之前的決策資料。
`frozen=True` 防止重新指派 dataclass 欄位，但不會深度凍結字典；呼叫端也應避免修改它們。

檢查一條重要不變量（invariant）：

```text
所有玩家剩餘籌碼總和 + 尚未派發的底池 = 所有玩家起始籌碼總和
```

每一步都必須成立，棄牌不會讓籌碼消失。這是面試中可解釋的測試設計。

## 4. 概念三：在玩家行動之前計算指標

範例假設九人開局每人 650、小盲 1、大盲 2，UTG raise to 125，BTN 跟注，其他人棄牌。
位置、籌碼與花色為教學設定。

| 時點 | 底池 | Hero 剩餘 | 對手剩餘 |
|---|---:|---:|---:|
| 大小盲完成 | 3 | 650 | 650 |
| UTG raise to 125 | 128 | 650 | 525 |
| BTN call to 125 | 253 | 525 | 525 |
| 翻牌對手 bet 300 | 553 | 525 | 225 |
| Hero fold，退回未被跟注的 300 | 253 | 525 | 525 |

在 Hero fold **之前**：需要付 300，付完後底池會是 `553 + 300 = 853`。

```text
call_price = 300 / 853 ≈ 35.17%
flop_start_spr = min(525, 525) / 253 ≈ 2.08
```

35.17% 是在無後續投入、完全實現 equity 的假設下，跟注所需的損益兩平比例。
它不是 QQ 實際的 equity；翻牌後還有未來下注與 equity realization 的問題。
程式保留 street 開始時的 SPR，因此不會誤用對手 bet 完之後的 225 / 553。
多人底池暫不提供單一 SPR，因為需要指定對手與有效籌碼。

## 5. 你自己做的練習

1. 複製範例成 `examples/qq_bet_150.json`。
2. 只把 flop 對手的 `amount_to` 從 `300` 改成 `150`。
3. 先手算：底池 403、跟注 150、跟注後底池 553，價格約 27.12%。
4. 執行新範例的 `--replay`，比對你的計算。翻牌開始時的 SPR 仍應是 2.08。
5. 把 Hero 最後動作改成 `call` 並加入 `"amount_to": "150"`，再執行。
   這時翻牌輪結束，但 turn 尚未記錄，所以整手牌應顯示 `Betting complete: False`。

保留修改並 commit，這就是你親手完成的第二課練習。

## 6. 範圍與下一步

本課支援標準盲注、非 all-in 的 fold/check/call/bet/full raise。
All-in（含短盲注）會回報明確錯誤；邊池與不足額加注重新開啟行動需要另做。
未被跟注的下注會退回；勝者派彩、showdown、rake、ante 與 straddle 尚未處理。
輸入可以停在決策點；程式會保留 pending 並標記尚未結束。
未知 turn/river 不會由程式補出；缺少公共牌卻出現對應街動作會遭拒絕。

下一課將把 Hero 的每個決策保存成可查詢資料，為相似牌局搜尋與個人漏洞分析準備。

面試描述：

> I built a deterministic replay engine that derives pot and stack snapshots from
> hand-history events. It validates betting transitions, preserves chip conservation,
> and captures metrics before each decision. This gives downstream AI reviews
> reproducible arithmetic and prevents future events from changing earlier contexts.
