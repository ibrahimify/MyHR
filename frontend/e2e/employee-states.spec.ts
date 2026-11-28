import { expect, Page, test } from "@playwright/test";

const ada = employee(1, "DEMO-EMP-0001", "Ada", "Lovelace", "Software Engineer");
const grace = employee(2, "DEMO-EMP-0002", "Grace", "Hopper", "Systems Analyst");

test("shows loading, empty, and API error states", async ({ page }) => {
  let releaseLoading!: () => void;
  const loadingGate = new Promise<void>((resolve) => {
    releaseLoading = resolve;
  });
  await page.route("**/api/employees?*", async (route) => {
    await loadingGate;
    await route.fulfill({ json: employeePage([]) });
  });

  await page.goto("/");
  await expect(page.getByLabel("Loading employees")).toBeVisible();
  releaseLoading();
  await expect(page.getByRole("heading", { name: "No employees yet" })).toBeVisible();

  await page.unroute("**/api/employees?*");
  await page.route("**/api/employees?*", (route) =>
    route.fulfill({ status: 503, json: { detail: "Service temporarily unavailable." } }),
  );
  await page.getByLabel("Refresh employees").click();
  await expect(page.getByRole("heading", { name: "Directory unavailable" })).toBeVisible();
  await expect(page.getByText("Service temporarily unavailable.")).toBeVisible();
});

test("keeps the latest list and detail when older requests finish later", async ({
  page,
}) => {
  await page.route("**/api/employees?*", async (route) => {
    const search = new URL(route.request().url()).searchParams.get("search");
    if (search === "slow") {
      await delay(500);
      await route.fulfill({ json: employeePage([ada]) });
      return;
    }
    if (search === "fast") {
      await route.fulfill({ json: employeePage([grace]) });
      return;
    }
    await route.fulfill({ json: employeePage([ada, grace]) });
  });
  await page.route("**/api/employees/1", async (route) => {
    await delay(500);
    await route.fulfill({ json: ada });
  });
  await page.route("**/api/employees/2", (route) => route.fulfill({ json: grace }));

  await page.goto("/");
  await page.getByRole("button", { name: /Grace Hopper/ }).click();
  await expect(page.getByRole("heading", { name: "Grace Hopper" })).toBeVisible();
  await delay(600);
  await expect(page.getByRole("heading", { name: "Grace Hopper" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ada Lovelace" })).toHaveCount(0);

  await submitSearch(page, "slow");
  await submitSearch(page, "fast");
  await expect(page.getByRole("button", { name: /Grace Hopper/ })).toBeVisible();
  await delay(600);
  await expect(page.getByRole("button", { name: /Grace Hopper/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Ada Lovelace/ })).toHaveCount(0);
});

test("keeps the employee workflow usable on a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockEmployees(page, [ada, grace]);
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Employees", level: 1 })).toBeVisible();
  await expect(page.getByRole("button", { name: "Add employee" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Ada Lovelace/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ada Lovelace" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);

  const listBox = await page
    .getByRole("region", { name: "Employees" })
    .boundingBox();
  const detailBox = await page.locator(".detail-region").boundingBox();
  expect(listBox).not.toBeNull();
  expect(detailBox).not.toBeNull();
  expect(detailBox!.y).toBeGreaterThan(listBox!.y);
});

async function mockEmployees(page: Page, employees: ReturnType<typeof employee>[]) {
  await page.route("**/api/employees?*", (route) =>
    route.fulfill({ json: employeePage(employees) }),
  );
  for (const item of employees) {
    await page.route(`**/api/employees/${item.id}`, (route) =>
      route.fulfill({ json: item }),
    );
  }
}

async function submitSearch(page: Page, value: string) {
  await page.getByLabel("Search employees").fill(value);
  await page.getByRole("button", { name: "Search", exact: true }).click();
}

function employee(
  id: number,
  employeeId: string,
  firstName: string,
  lastName: string,
  position: string,
) {
  return {
    id,
    employee_id: employeeId,
    first_name: firstName,
    last_name: lastName,
    degree: "BSc",
    position,
    status: "active",
    title_id: 1,
    title_name: "Local Demo Specialist",
    title_currency: "USD",
    org_unit_id: 1,
    org_unit_name: "Local Demo Engineering",
    reports_to_id: null,
    work_email: `${firstName.toLowerCase()}@example.test`,
    work_phone: null,
    join_date: "2024-01-15",
    base_salary: 3200,
  };
}

function employeePage(items: ReturnType<typeof employee>[]) {
  return { items, total: items.length, page: 1, page_size: 10 };
}

function delay(milliseconds: number) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}
