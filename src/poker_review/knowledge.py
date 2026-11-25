"""Original educational notes; not solver output or a strategy authority."""

NOTES = [
    {"id": "note-price", "title": "跟注價格與 equity 的區別", "tags": ["pot odds", "equity", "跟注價格"],
     "body": "Pot odds 跟注價格 = 本次需要追加的籌碼 / 跟注後可競爭的底池。對手下注已在目前底池裡，不可重複加一次。這是完全實現 equity、無後續投入假設下的門檻，不是手牌的實際 equity。翻牌與轉牌仍需考慮未來下注、位置、範圍與 equity realization。多人 all-in 只能計入自己有資格贏得的主池和邊池。"},
    {"id": "note-spr", "title": "SPR 與低底池深度的提前計畫", "tags": ["SPR", "low spr", "低SPR"],
     "body": "Stack-to-pot ratio (SPR) 為該街開始時有效剩餘籌碼 / 底池。Heads-up 可取兩人的較小剩餘籌碼。Low SPR 低 SPR 表示後續下注容易投入大量有效籌碼，但不代表一定要跟到底。應在翻前比較不同決策會產生的底池與翻牌計畫。多人底池沒有一個能代表所有對手的單一有效籌碼。"},
    {"id": "note-premium", "title": "QQ／強口袋對面對超大 open", "tags": ["QQ", "premium", "large open", "強牌"],
     "body": "AA KK QQ premium pair 面對超大 open raise 時，先確認是否有 straddle、limpers、位置、有效深度及對手範圍。Live 1/2 的 125 open 很大，但尺度不直接證明範圍。比較 fold、call、3-bet 的可行後續，不因為輸掉單手就認定 call 錯誤。缺少範圍或 solver 基準時只能記錄待檢查假設。"},
    {"id": "note-overbet", "title": "面對 overbet 的範圍思考", "tags": ["overbet", "bluff catch", "超池"],
     "body": "Overbet 超池下注可能來自極化價值／詐唬範圍，也可能是 live 玩家非標準尺度。先計算價格，再檢查對手可合理採取的價值與詐唬組合、阻擋牌和牌面。不能只用 minimum defense frequency 要求單一手牌跟注，也不能把所有超池下注視為詐唬。"},
    {"id": "note-position", "title": "位置與多人底池", "tags": ["position", "multiway", "OOP", "位置"],
     "body": "Position 位置會影響資訊與 equity realization。OOP 不利位置、多位玩家仍未行動時，跟注價格不是最終價格，可能遭到 squeeze。比較牌局需對齊位置、有效深度、玩家數、底池類型與動作序列；只因同樣拿 QQ 就認定策略相同，會造成錯誤檢索。"},
    {"id": "note-evidence", "title": "從重複模式到可驗證漏洞", "tags": ["leak", "sample", "漏洞", "selection bias"],
     "body": "Leak 決策漏洞需要可比較的機會、正確分母與可靠策略基準。記錄三次相同行動只代表重複模式，不代表統計信心或錯誤。選擇性只記輸掉的大底池會有 selection bias。示範牌局不能當作個人資料。無 solver 或教練確認時，保留未知與替代解釋，避免用結果評斷決策。"},
]


def seed_notes(store):
    existing = {note["id"] for note in store.notes()}
    for note in NOTES:
        if note["id"] not in existing:
            store.save_note({**note, "source": "專案原創教學筆記（非 solver 結果）"})
