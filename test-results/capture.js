const { chromium, devices } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const device = devices['iPhone 14'];

  const pages = [
    { name: 'home', url: 'https://nraizes.com.br/' },
    { name: 'loja', url: 'https://nraizes.com.br/loja/' },
  ];

  // First capture home and loja
  for (const p of pages) {
    const ctx = await browser.newContext({ ...device });
    const page = await ctx.newPage();
    try {
      await page.goto(p.url, { waitUntil: 'networkidle', timeout: 60000 });
      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'test-results/mobile-' + p.name + '-fold.png' });
      await page.screenshot({ path: 'test-results/mobile-' + p.name + '-full.png', fullPage: true });
      console.log('[OK] ' + p.name + ' - ' + page.url());
    } catch(e) {
      console.log('[FAIL] ' + p.name + ': ' + e.message.slice(0, 150));
    }
    await ctx.close();
  }

  // Now capture a product page by navigating from the shop
  const ctx = await browser.newContext({ ...device });
  const page = await ctx.newPage();
  try {
    await page.goto('https://nraizes.com.br/loja/', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(1000);
    
    // Find first product link
    const productLink = await page.locator('ul.products li.product a').first();
    const href = await productLink.getAttribute('href');
    if (href) {
      await page.goto(href, { waitUntil: 'networkidle', timeout: 60000 });
      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'test-results/mobile-produto-fold.png' });
      await page.screenshot({ path: 'test-results/mobile-produto-full.png', fullPage: true });
      console.log('[OK] produto - ' + page.url());
    }
  } catch(e) {
    console.log('[FAIL] produto: ' + e.message.slice(0, 150));
  }
  await ctx.close();

  // Capture cart page
  const ctx2 = await browser.newContext({ ...device });
  const page2 = await ctx2.newPage();
  try {
    await page2.goto('https://nraizes.com.br/carrinho/', { waitUntil: 'networkidle', timeout: 60000 });
    await page2.waitForTimeout(2000);
    await page2.screenshot({ path: 'test-results/mobile-carrinho-fold.png' });
    await page2.screenshot({ path: 'test-results/mobile-carrinho-full.png', fullPage: true });
    console.log('[OK] carrinho - ' + page2.url());
  } catch(e) {
    console.log('[FAIL] carrinho: ' + e.message.slice(0, 150));
  }
  await ctx2.close();

  await browser.close();
  console.log('Done! Screenshots saved in test-results/');
})();
