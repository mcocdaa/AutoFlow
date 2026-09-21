import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { spawn } from 'child_process';

async function main() {
  // 1. Start backend server on port 3001
  console.log('Starting backend server on port 3001...');
  const backend = spawn(process.cwd() + '/.venv/bin/uvicorn', ['app.main:app', '--host', '127.0.0.1', '--port', '3001'], {
    cwd: process.cwd() + '/backend',
    stdio: 'pipe',
  });

  // 2. Start frontend preview server on port 4180
  console.log('Starting frontend preview server on port 4180...');
  const preview = spawn('npm', ['run', 'preview', '--', '--port', '4180', '--host', '127.0.0.1'], {
    cwd: process.cwd() + '/frontend',
    stdio: 'pipe',
    env: { ...process.env, VITE_API_PROXY_URL: 'http://127.0.0.1:3001' },
  });

  await new Promise((resolve) => setTimeout(resolve, 3500));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 920 } });
  const page = await context.newPage();

  try {
    // 1. Flow Hub Page with real flows
    console.log('Navigating to Flow Hub (#/hub)...');
    await page.goto('http://127.0.0.1:4180/#/hub', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: 'flow_hub_screenshot.png' });
    console.log('Saved flow_hub_screenshot.png');

    // 2. YAML Preview Modal
    console.log('Opening YAML Preview Modal...');
    const yamlBtn = page.locator('.action-btn:has-text("查看 YAML")').first();
    if (await yamlBtn.isVisible()) {
      await yamlBtn.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: 'flow_hub_yaml_modal_screenshot.png' });
      console.log('Saved flow_hub_yaml_modal_screenshot.png');
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    }

    // 3. Secrets Vault Page
    console.log('Navigating to Secrets Vault (#/secrets)...');
    await page.goto('http://127.0.0.1:4180/#/secrets', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // 4. Open Add Secret Modal and save a secret
    console.log('Opening Add Secret Modal...');
    const addSecretBtn = page.locator('button:has-text("添加凭据")');
    if (await addSecretBtn.isVisible()) {
      await addSecretBtn.click();
      await page.waitForTimeout(500);

      await page.fill('input[placeholder*="OPENAI_API_KEY"]', 'OPENAI_API_KEY');
      await page.fill('input[type="password"]', 'sk-proj-super-secret-key-1234567890abcdef');
      await page.waitForTimeout(300);

      const saveBtn = page.locator('.modal-footer button:has-text("加密保存")');
      await saveBtn.click();
      await page.waitForTimeout(1200);

      await page.screenshot({ path: 'secrets_vault_screenshot.png' });
      console.log('Saved secrets_vault_screenshot.png');
    }

  } finally {
    await browser.close();
    preview.kill();
    backend.kill();
  }
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
