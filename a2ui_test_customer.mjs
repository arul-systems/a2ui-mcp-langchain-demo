import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage();
page.on("console", (msg) => {
  if (msg.type() === "error") console.log("[console error]", msg.text());
});
page.on("pageerror", (err) => console.log("[page error]", String(err)));

await page.goto("http://localhost:5173/");
await page.reload();
await page.waitForSelector(".composer input");

// 1. Create a customer via the form.
await page.fill(".composer input", "I want to create a new customer");
await page.click(".composer button");
await page.waitForSelector(".surface a2ui-basic-textfield", { timeout: 20000 });

const inputs = await page.$$(".surface:not(.surface-disabled) input, .surface:not(.surface-disabled) textarea");
console.log("customer form field count:", inputs.length);
await inputs[0].fill("Alex Rivera");
await inputs[1].fill("alex.rivera@example.com");
await inputs[2].fill("+1-555-0199");
await inputs[3].fill("Denver");
await inputs[4].fill("United States");

const bubbleCountBefore = (await page.$$(".bubble")).length;
await page.click(".surface:not(.surface-disabled) button");

await page.waitForFunction(
  (before) => document.querySelectorAll(".bubble").length >= before + 2,
  bubbleCountBefore,
  { timeout: 20000 },
);
await page.waitForSelector(".surface.surface-disabled", { timeout: 5000 });
console.log("customer form disabled after submit");

const chatAfterCreate = await page.textContent(".chat-log");
console.log("--- chat after create ---");
console.log(chatAfterCreate.slice(-400));

// 2. Ask to list customers -- should render customer_table.
await page.fill(".composer input", "Show me all customers in a table");
await page.click(".composer button");
await page.waitForSelector(".surface a2ui-basic-row", { timeout: 20000 });
await page.waitForTimeout(300);

const tableText = await page.evaluate(() => {
  const surfaces = document.querySelectorAll(".surface");
  return surfaces[surfaces.length - 1].textContent;
});
console.log("--- latest table surface text ---");
console.log(tableText);

await browser.close();
