import { expect, Page, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await mockEmptyDirectory(page);
});

test("presents the authenticated MyHR workspace on desktop", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await expect(navigation.getByText("Overview")).toBeVisible();
  await expect(navigation.getByText("People")).toBeVisible();
  await expect(navigation.getByText("Growth")).toBeVisible();
  await expect(navigation.getByText("Compliance")).toBeVisible();
  await expect(navigation.getByText("Data", { exact: true })).toBeVisible();
  await expect(navigation.getByText("System")).toBeVisible();
  await expect(navigation.getByText("Employees", { exact: true })).toBeVisible();
  await expect(page.locator(".environment-badge")).toHaveText("Local development");
  await expect(page.getByRole("heading", { name: "Employee directory" })).toBeVisible();
  await expect(page.getByLabel("Open navigation")).toBeHidden();
  await expectNoHorizontalOverflow(page);
});

test("switches and persists the selected theme", async ({ page }) => {
  await page.goto("/");

  await page
    .getByRole("button", { name: "Use dark theme" })
    .evaluate((button: HTMLButtonElement) => button.click());
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  await page
    .getByRole("button", { name: "Use light theme" })
    .evaluate((button: HTMLButtonElement) => button.click());
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("uses a contained navigation drawer on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  const openNavigation = page.getByRole("button", { name: "Open navigation" });
  await expect(openNavigation).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeHidden();

  await openNavigation.click();
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Close navigation" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

async function mockEmptyDirectory(page: Page) {
  await page.route("**/api/employees?*", (route) =>
    route.fulfill({
      json: { items: [], total: 0, page: 1, page_size: 10, pages: 1 },
    }),
  );
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
}
