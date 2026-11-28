import { expect, test } from "@playwright/test";

test("uses the real API for directory, search, filter, create, and edit", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Employees", level: 1 })).toBeVisible();
  await expect(page.getByText("3 employees")).toBeVisible();
  await page.getByRole("button", { name: /Ada Lovelace/ }).click();
  await expect(page.getByRole("heading", { name: "Ada Lovelace" })).toBeVisible();

  const listBox = await page
    .getByRole("region", { name: "Employees" })
    .boundingBox();
  const detailBox = await page.locator(".detail-region").boundingBox();
  expect(listBox).not.toBeNull();
  expect(detailBox).not.toBeNull();
  expect(listBox!.x).toBeLessThan(detailBox!.x);

  await page.getByLabel("Search employees").fill("Grace");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByText("1 employee")).toBeVisible();
  await expect(page.getByRole("button", { name: /Grace Hopper/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Grace Hopper" })).toBeVisible();

  await page.getByLabel("Search employees").fill("");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await page.getByLabel("Status").selectOption("inactive");
  await expect(page.getByRole("heading", { name: "No matching employees" })).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page.getByText("3 employees")).toBeVisible();

  await page.getByRole("button", { name: "Add employee" }).click();
  const createDialog = page.getByRole("dialog", { name: "Add employee" });
  await expect(createDialog).toBeVisible();
  await createDialog.getByLabel("First name").fill("Katherine");
  await createDialog.getByLabel("Last name").fill("Johnson");
  await createDialog.getByLabel("Position").fill("Research Analyst");
  await createDialog.getByLabel("Join date").fill("2025-02-03");
  await createDialog.getByLabel("Base salary").fill("2800");
  await createDialog
    .getByLabel("Title")
    .selectOption({ label: "DEMO-L1 - Local Demo Associate" });
  await createDialog
    .getByLabel("Organization unit")
    .selectOption({ label: "Local Demo Engineering (department)" });
  await createDialog
    .getByLabel("Manager")
    .selectOption({ label: "Ada Lovelace (DEMO-EMP-0001)" });
  await createDialog.getByLabel("Work email").fill("katherine.johnson@example.test");
  await createDialog.getByRole("button", { name: "Add employee" }).click();
  await expect(page.getByRole("status")).toContainText("Katherine Johnson was added");

  await page.getByLabel("Search employees").fill("Katherine");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Katherine Johnson" })).toBeVisible();
  await page.getByRole("button", { name: "Edit" }).click();
  const editDialog = page.getByRole("dialog", { name: "Edit employee" });
  await editDialog.getByLabel("Position").fill("Senior Research Analyst");
  await editDialog.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("status")).toContainText("Katherine Johnson was updated");
  await expect(page.getByText("Senior Research Analyst", { exact: true })).toBeVisible();
});
