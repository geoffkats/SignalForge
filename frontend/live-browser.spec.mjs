import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const shotDir = path.join(__dirname, "test-results", "live");

test.describe("SignalForge live UI", () => {
  test("home → assay prediction → atlas ranking", async ({ page }) => {
    // API readiness first
    const health = await page.request.get("http://127.0.0.1:8000/healthz");
    expect(health.ok()).toBeTruthy();
    const healthJson = await health.json();
    expect(healthJson.inference_mode).toBe("model");
    expect(healthJson.atlas_size).toBe(300);

    // Home / start
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /workspace|start|assay|tools/i }).first()).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: path.join(shotDir, "01-home.png"), fullPage: true });

    // Assay
    await page.goto("/assay");
    await expect(page.getByRole("heading", { name: "Assay" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Compound → genes|Compound/i })).toBeVisible();

    const smiles = page.locator("textarea").first();
    await expect(smiles).toBeVisible();
    await smiles.fill("CC1(C(=O)Nc2cccc(c2)C#N)CS(=O)(=O)c2cc(C(F)(F)F)ccc2N1");

    const geneInput = page.locator('input').filter({ hasNot: page.locator("[type=hidden]") }).first();
    await geneInput.fill("AR, KLK3, TMPRSS2, PTEN");

    await page.getByRole("button", { name: /Run prediction/i }).click();
    await expect(page.getByText(/Scoring gene panel|Predicted regulation|Mean confidence/i).first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/Mean confidence/i)).toBeVisible({ timeout: 60_000 });
    // Wait until loading finishes
    await expect(page.getByRole("button", { name: /^Re-run$/i })).toBeEnabled({ timeout: 60_000 });
    await page.screenshot({ path: path.join(shotDir, "02-assay.png"), fullPage: true });

    // Atlas
    await page.goto("/atlas");
    await expect(page.getByRole("heading", { name: "Atlas" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Reverse search/i })).toBeVisible();

    await page.getByRole("button", { name: /Rank compounds/i }).click();
    await expect(page.locator(".rank-row").first()).toBeVisible({ timeout: 120_000 });
    const rows = page.locator(".rank-row");
    await expect(rows).toHaveCount(20, { timeout: 30_000 });

    await rows.nth(1).click();
    await expect(page.locator(".atlas-detail")).toContainText(/Score|BRD-|score/i);
    await page.screenshot({ path: path.join(shotDir, "03-atlas.png"), fullPage: true });

    // No error banner
    await expect(page.locator(".error-banner")).toHaveCount(0);
  });
});
