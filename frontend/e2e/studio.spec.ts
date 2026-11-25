import { test, expect } from "@playwright/test";

test("replay, save, retrieve, review, edit and delete a hand", async ({
  page,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "牌桌重播" })).toBeVisible();
  await expect(page.getByRole("slider", { name: "重播步驟" })).toHaveValue("9");
  await expect(page.getByText("35.17%", { exact: true })).toBeVisible();
  await page.screenshot({
    path: "test-results/studio-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "下一步", exact: true }).click();
  await expect(page.getByRole("slider")).toHaveValue("10");
  await page.getByRole("button", { name: "上一步", exact: true }).click();
  await page.getByRole("button", { name: "記錄牌局", exact: true }).click();
  const editor = page.getByRole("textbox", { name: "JSON 牌譜", exact: true });
  const hand = JSON.parse(await editor.inputValue());
  const id = "e2e-" + Date.now();
  hand.hand_id = id;
  hand.players[0].starting_stack = String(
    800 + Math.floor(Math.random() * 100000),
  );
  await editor.fill(JSON.stringify(hand, null, 2));
  await page.getByRole("button", { name: "驗證並重播", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "儲存牌局", exact: true }).click();
  await expect(page.getByText("牌局已儲存", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "規則摘要", exact: true }).click();
  await expect(page.getByText("仍缺少的資訊", { exact: true })).toBeVisible();
  await page.locator(".citation").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "關閉來源", exact: true }).click();
  await page.getByRole("button", { name: "決策趨勢", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "找到值得再看一眼的決策。" }),
  ).toBeVisible();
  await expect(page.getByText("資料尚不足", { exact: true })).toHaveCount(3);
  await page.getByRole("button", { name: "策略知識庫", exact: true }).click();
  await page
    .getByRole("textbox", { name: "搜尋策略筆記" })
    .fill("pot odds equity");
  await page.getByRole("button", { name: "搜尋", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "跟注價格與 equity 的區別" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "牌局工作室", exact: true }).click();
  await page.getByRole("textbox", { name: "搜尋已儲存牌局" }).fill(id);
  await expect(page.locator(".saved-row")).toHaveCount(1);
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "刪除", exact: true }).click();
  await expect(page.getByText("已刪除牌局", { exact: true })).toBeVisible();
  expect(failures).toEqual([]);
});

test("invalid input remains editable and is not saved", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("slider")).toHaveValue("9");
  await page.getByRole("button", { name: "記錄牌局", exact: true }).click();
  await page
    .getByRole("textbox", { name: "JSON 牌譜", exact: true })
    .fill("{bad json");
  await page.getByRole("button", { name: "驗證並重播", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText(
    "JSON 格式有誤",
  );
});

test("mobile layout, navigation and replayer fit screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("slider")).toHaveValue("9");
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow).toBe(false);
  await page.screenshot({
    path: "test-results/studio-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "決策趨勢", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "找到值得再看一眼的決策。" }),
  ).toBeVisible();
});
