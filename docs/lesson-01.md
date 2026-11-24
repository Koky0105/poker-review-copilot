# 第一課：讓程式理解一手 9-max 牌局

目標：讀取 JSON，建立可靠的 Python 物件，並拒絕不一致的資料。
這一課完成後，你可以在面試中解釋 schema validation 與遊戲狀態驗證的差別。

## 1. 先執行

在 repo 根目錄依 README 建立虛擬環境、安裝套件。執行：

```powershell
.\.venv\Scripts\python.exe -m poker_review examples/qq_large_open.json
.\.venv\Scripts\python.exe -m pytest -q
```

第一個指令應印出 `Valid hand: synthetic-qq-large-open`，並列出 9 位玩家、11 個動作。
第二個指令會檢查範例讀取、序列化，以及無效資料是否遭拒絕。

## 2. 讀懂資料

先開 `examples/qq_large_open.json`。這是為教學編寫的牌局，位置與其他玩家
籌碼都是示範設定，並非對真實牌局的完整還原。九個位置按翻前順序排列：

`UTG, UTG+1, UTG+2, LJ, HJ, CO, BTN, SB, BB`

- `players`：開局時九個人的資料。棄牌玩家仍然保留，盲注可能已進入底池。
- `forced_bets`：小盲、大盲；初版只處理標準盲注格式。
- `actions`：按時間排列的動作。先存事件，下一課再逐一重播。
- `hero_cards`、`board`：已知的牌；未知對手手牌不自行補齊。

## 3. 從你熟悉的 TypeScript 理解 Pydantic

TypeScript 型別主要在開發與編譯時檢查。API 收到的 JSON 仍需要執行時驗證。
`PokerHand.model_validate_json(...)` 類似用 Zod 驗證輸入並取得型別化資料。

依序閱讀 `src/poker_review/models.py` 的 `Player`、`Action`、`PokerHand`：

1. `Field` 處理單一欄位，例如座位只能是 1 到 9。
2. `model_validator` 處理跨欄位規則，例如同一張牌不能同時出現在手牌與公共牌。
3. `extra="forbid"` 會拒絕拼錯的欄位，避免把 `amount` 誤當成 `amount_to`。

目前驗證的是資料契約。合法行動順序、投入籌碼不能超過剩餘 stack、
call 金額是否正確，都需要下一課的狀態機。

## 4. 為什麼使用 Decimal 和 amount_to

`Decimal("0.1") + Decimal("0.2")` 能精確表示十進位的 `0.3`。
JSON 裡將金額寫成字串，避免先經過浮點數換算。之後 React 也會遵守此契約。

`amount_to` 是玩家完成動作後，本街累積投入。例如 BB 已付 2，raise to 40，
實際追加的是 `40 - 2 = 38`。下一街累積額會歸零；總底池保留。
這個欄位定義可以避免「加 40」與「加到 40」的歧義。

## 5. 你的動手練習

在 VS Code 複製範例為 `examples/my_first_hand.json`，每次只改一項並執行 CLI：

1. 將 hero 手牌改為 `As, Kh`。保留原本 `Ah, 8c, 2d` 翻牌，應驗證成功。
2. 將手牌改為 `Ah, Kh`。因公共牌也有 `Ah`，應報 duplicate cards。
3. 恢復有效手牌，刪除一筆 call 的 `amount_to`，觀察錯誤。
4. 恢復有效資料，把玩家改成相同座位，觀察錯誤。

最後保留一份有效範例並 commit：

```powershell
git add examples/my_first_hand.json
git commit -m "practice: add my first validated hand"
git push
```

提交前先說明：BB 已付 2，面對 raise to 25，call 的 `amount_to` 應填多少？
應填 25，實際追加 23。這兩個數字將成為第二課的核心。

## 面試時可以解釋的設計

> I defined a validated hand-history contract before implementing AI reviews.
> It rejects inconsistent cards, player references, and ambiguous action amounts.
> Decimal preserves chip arithmetic, while amount_to makes street contributions explicit.
> Input validation and betting-state validation are separate responsibilities.

這段描述只代表目前完成的 schema；底池引擎、RAG 與 LLM 尚在後續里程碑。
