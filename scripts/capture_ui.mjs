import { chromium } from 'playwright';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  console.log('Navigating to canvas...');
  await page.goto('http://localhost:4173/#/canvas', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // 1. 截图：YAML 源码 Tab
  console.log('Clicking YAML tab...');
  const yamlTabBtn = page.locator('.tab-group label:has-text("YAML 源码")');
  await yamlTabBtn.click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'canvas_yaml_screenshot.png' });
  console.log('Captured canvas_yaml_screenshot.png');

  // 2. 截图：触发器 Tab (Cron 预测与 Webhook)
  console.log('Clicking Triggers tab...');
  const triggersTabBtn = page.locator('.tab-group label:has-text("触发器")');
  await triggersTabBtn.click();
  await page.waitForTimeout(300);

  // 点击预测按钮展示未来触发时间
  const predictBtn = page.locator('button:has-text("预测")');
  if (await predictBtn.isVisible()) {
    await predictBtn.click();
  }
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'canvas_triggers_screenshot.png' });
  console.log('Captured canvas_triggers_screenshot.png');

  // 3. 切回步骤配置，展示甘特图
  console.log('Switching back to node tab...');
  const nodeTabBtn = page.locator('.tab-group label:has-text("步骤配置")');
  await nodeTabBtn.click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'canvas_full_screenshot.png' });

  await browser.close();
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
