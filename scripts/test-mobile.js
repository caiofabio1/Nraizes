/**
 * Mobile Testing Suite - Novas Raizes
 * 
 * Runs Lighthouse audits + Playwright screenshots for mobile UX testing.
 * 
 * Usage:
 *   node scripts/test-mobile.js                    # Test all pages
 *   node scripts/test-mobile.js --url /base-dados  # Test specific page
 *   node scripts/test-mobile.js --screenshots-only  # Skip Lighthouse
 *   node scripts/test-mobile.js --lighthouse-only   # Skip screenshots
 */

const { chromium, devices } = require('playwright');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// ============================================
// CONFIG
// ============================================
const BASE_URL = 'https://nraizes.com.br';
const OUTPUT_DIR = path.join(__dirname, '..', 'test-results');

const PAGES_TO_TEST = [
  { name: 'home', path: '/' },
  { name: 'loja', path: '/loja/' },
  { name: 'base-dados', path: '/base-de-dados/' },
];

const MOBILE_DEVICES = [
  { name: 'iPhone-14', device: 'iPhone 14' },
  { name: 'Pixel-7', device: 'Pixel 7' },
  { name: 'Galaxy-S21', width: 360, height: 800, deviceScaleFactor: 3, isMobile: true, hasTouch: true, userAgent: 'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36' },
];

// ============================================
// ARGS
// ============================================
const args = process.argv.slice(2);
let specificUrl = args.find(a => a.startsWith('--url='))?.split('=')[1];
const screenshotsOnly = args.includes('--screenshots-only');
const lighthouseOnly = args.includes('--lighthouse-only');

if (specificUrl) {
  // Fix Git Bash path mangling on Windows (e.g. /base-de-dados/ becomes C:/Program Files/Git/base-de-dados/)
  specificUrl = specificUrl.replace(/.*Git\//i, '/').replace(/^([^/])/, '/$1');
  if (!specificUrl.endsWith('/')) specificUrl += '/';
  const safeName = specificUrl.replace(/^\/|\/$/g, '').replace(/\//g, '-') || 'custom';
  PAGES_TO_TEST.length = 0;
  PAGES_TO_TEST.push({ name: safeName, path: specificUrl });
}

// ============================================
// HELPERS
// ============================================
function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function timestamp() {
  return new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
}

function printHeader(text) {
  const line = '='.repeat(60);
  console.log(`\n${line}`);
  console.log(`  ${text}`);
  console.log(line);
}

function printScore(label, score) {
  const pct = Math.round(score * 100);
  let indicator = '  ';
  if (pct >= 90) indicator = '  [GOOD]';
  else if (pct >= 50) indicator = '  [NEEDS WORK]';
  else indicator = '  [POOR]';
  console.log(`  ${label.padEnd(20)} ${pct}/100${indicator}`);
}

// ============================================
// LIGHTHOUSE AUDIT
// ============================================
async function runLighthouse(pagePath, pageName) {
  const url = BASE_URL + pagePath;
  const outDir = path.join(OUTPUT_DIR, 'lighthouse');
  ensureDir(outDir);
  
  const jsonPath = path.join(outDir, `${pageName}-mobile.json`);
  const htmlPath = path.join(outDir, `${pageName}-mobile.html`);

  console.log(`\n  Auditing: ${url}`);
  console.log(`  Mode: Mobile emulation`);
  
  try {
    // Run Lighthouse via npx (uses the installed version)
    execSync(
      `npx lighthouse "${url}" --output=json,html --output-path="${path.join(outDir, pageName + '-mobile')}" --form-factor=mobile --screenEmulation.mobile --screenEmulation.width=375 --screenEmulation.height=812 --throttling-method=simulate --chrome-flags="--headless --no-sandbox --disable-gpu" --quiet`,
      { 
        stdio: 'pipe',
        timeout: 120000,
        env: { ...process.env, NODE_OPTIONS: '' }
      }
    );

    // Parse results
    const jsonFile = path.join(outDir, `${pageName}-mobile.report.json`);
    if (fs.existsSync(jsonFile)) {
      const report = JSON.parse(fs.readFileSync(jsonFile, 'utf8'));
      const cats = report.categories;
      
      console.log(`\n  SCORES:`);
      printScore('Performance', cats.performance?.score || 0);
      printScore('Accessibility', cats.accessibility?.score || 0);
      printScore('Best Practices', cats['best-practices']?.score || 0);
      printScore('SEO', cats.seo?.score || 0);
      
      // Core Web Vitals
      const audits = report.audits;
      console.log(`\n  CORE WEB VITALS:`);
      console.log(`  LCP:  ${audits['largest-contentful-paint']?.displayValue || 'N/A'}`);
      console.log(`  FID:  ${audits['max-potential-fid']?.displayValue || 'N/A'}`);
      console.log(`  CLS:  ${audits['cumulative-layout-shift']?.displayValue || 'N/A'}`);
      console.log(`  TBT:  ${audits['total-blocking-time']?.displayValue || 'N/A'}`);
      console.log(`  FCP:  ${audits['first-contentful-paint']?.displayValue || 'N/A'}`);
      console.log(`  SI:   ${audits['speed-index']?.displayValue || 'N/A'}`);

      // Mobile-specific issues
      const tapTargets = audits['tap-targets'];
      if (tapTargets && tapTargets.score < 1) {
        console.log(`\n  [!] TAP TARGETS: ${tapTargets.displayValue}`);
        (tapTargets.details?.items || []).slice(0, 5).forEach(item => {
          console.log(`      - ${item.tapTarget?.snippet || 'Unknown'} (${item.size})`);
        });
      }

      const fontSize = audits['font-size'];
      if (fontSize && fontSize.score < 1) {
        console.log(`  [!] FONT SIZE: ${fontSize.displayValue}`);
      }

      const viewport = audits['viewport'];
      if (viewport && viewport.score < 1) {
        console.log(`  [!] VIEWPORT: Not configured properly`);
      }

      console.log(`\n  HTML Report: ${path.join(outDir, pageName + '-mobile.report.html')}`);

      return {
        page: pageName,
        performance: Math.round((cats.performance?.score || 0) * 100),
        accessibility: Math.round((cats.accessibility?.score || 0) * 100),
        bestPractices: Math.round((cats['best-practices']?.score || 0) * 100),
        seo: Math.round((cats.seo?.score || 0) * 100),
        lcp: audits['largest-contentful-paint']?.numericValue,
        cls: audits['cumulative-layout-shift']?.numericValue,
        tbt: audits['total-blocking-time']?.numericValue,
      };
    }
  } catch (err) {
    console.log(`  [ERROR] Lighthouse failed: ${err.message?.slice(0, 200)}`);
    return null;
  }
}

// ============================================
// PLAYWRIGHT SCREENSHOTS
// ============================================
async function takeScreenshots(pagePath, pageName) {
  const url = BASE_URL + pagePath;
  const outDir = path.join(OUTPUT_DIR, 'screenshots', pageName);
  ensureDir(outDir);

  const browser = await chromium.launch({ headless: true });

  for (const deviceConfig of MOBILE_DEVICES) {
    const deviceName = deviceConfig.name;
    console.log(`\n  Device: ${deviceName} -> ${url}`);

    let contextOpts;
    if (deviceConfig.device) {
      contextOpts = { ...devices[deviceConfig.device] };
    } else {
      contextOpts = {
        viewport: { width: deviceConfig.width, height: deviceConfig.height },
        deviceScaleFactor: deviceConfig.deviceScaleFactor,
        isMobile: deviceConfig.isMobile,
        hasTouch: deviceConfig.hasTouch,
        userAgent: deviceConfig.userAgent,
      };
    }

    const context = await browser.newContext(contextOpts);
    const page = await context.newPage();

    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(1000);

      // 1. Full page screenshot
      const fullPath = path.join(outDir, `${deviceName}-full.png`);
      await page.screenshot({ path: fullPath, fullPage: true });
      console.log(`    [ok] Full page: ${deviceName}-full.png`);

      // 2. Above the fold (viewport only)
      const foldPath = path.join(outDir, `${deviceName}-fold.png`);
      await page.screenshot({ path: foldPath });
      console.log(`    [ok] Above fold: ${deviceName}-fold.png`);

      // 3. Test interactive elements
      // Search bar
      const searchInput = await page.$('#nrc-search');
      if (searchInput) {
        await searchInput.click();
        await page.waitForTimeout(300);
        await searchInput.fill('vitamina');
        await page.waitForTimeout(500);
        const searchPath = path.join(outDir, `${deviceName}-search.png`);
        await page.screenshot({ path: searchPath });
        console.log(`    [ok] Search active: ${deviceName}-search.png`);
        
        // Clear and reset
        await searchInput.fill('');
        await page.waitForTimeout(300);
      }

      // 4. Open a product card
      const firstCard = await page.$('.nrc-card summary');
      if (firstCard) {
        await firstCard.click();
        await page.waitForTimeout(500);
        const cardPath = path.join(outDir, `${deviceName}-card-open.png`);
        await page.screenshot({ path: cardPath, fullPage: false });
        console.log(`    [ok] Card open: ${deviceName}-card-open.png`);
      }

      // 5. Scroll to CTA store banner
      const storeCta = await page.$('.nrc-store-cta');
      if (storeCta) {
        await storeCta.scrollIntoViewIfNeeded();
        await page.waitForTimeout(300);
        const ctaPath = path.join(outDir, `${deviceName}-store-cta.png`);
        await page.screenshot({ path: ctaPath });
        console.log(`    [ok] Store CTA: ${deviceName}-store-cta.png`);
      }

      // 6. Check WhatsApp button visibility
      const waBtn = await page.$('a.qlwapp__button, [class*="whatsapp"], a[href*="wa.me"]');
      if (waBtn) {
        console.log(`    [ok] WhatsApp button found`);
      } else {
        console.log(`    [--] WhatsApp button NOT visible`);
      }

      // 7. Touch target audit
      const smallTargets = await page.evaluate(() => {
        const issues = [];
        const clickables = document.querySelectorAll('a, button, input, [role="button"]');
        clickables.forEach(el => {
          const rect = el.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0 && (rect.width < 44 || rect.height < 44)) {
            const text = el.textContent?.trim().slice(0, 30) || el.className?.slice(0, 30) || 'unknown';
            issues.push({ text, width: Math.round(rect.width), height: Math.round(rect.height) });
          }
        });
        return issues.slice(0, 10);
      });

      if (smallTargets.length) {
        console.log(`    [!] Small touch targets found (< 44px):`);
        smallTargets.forEach(t => {
          console.log(`        - "${t.text}" (${t.width}x${t.height}px)`);
        });
      } else {
        console.log(`    [ok] All touch targets >= 44px`);
      }

    } catch (err) {
      console.log(`    [ERROR] ${err.message?.slice(0, 100)}`);
    }

    await context.close();
  }

  await browser.close();
  console.log(`\n  Screenshots saved in: ${outDir}`);
}

// ============================================
// MAIN
// ============================================
async function main() {
  const ts = timestamp();
  ensureDir(OUTPUT_DIR);

  printHeader(`MOBILE TEST SUITE - Novas Raizes (${ts})`);
  console.log(`  Base URL: ${BASE_URL}`);
  console.log(`  Pages: ${PAGES_TO_TEST.map(p => p.path).join(', ')}`);
  console.log(`  Devices: ${MOBILE_DEVICES.map(d => d.name).join(', ')}`);

  const allResults = [];

  for (const page of PAGES_TO_TEST) {
    printHeader(`Testing: ${page.name} (${page.path})`);

    // Lighthouse
    if (!screenshotsOnly) {
      printHeader(`Lighthouse Audit: ${page.name}`);
      const result = await runLighthouse(page.path, page.name);
      if (result) allResults.push(result);
    }

    // Screenshots
    if (!lighthouseOnly) {
      printHeader(`Screenshots: ${page.name}`);
      await takeScreenshots(page.path, page.name);
    }
  }

  // Summary
  if (allResults.length) {
    printHeader('SUMMARY - Lighthouse Mobile Scores');
    console.log('');
    console.log('  Page'.padEnd(20) + 'Perf'.padEnd(8) + 'A11y'.padEnd(8) + 'BP'.padEnd(8) + 'SEO'.padEnd(8));
    console.log('  ' + '-'.repeat(44));
    allResults.forEach(r => {
      console.log(
        `  ${r.page.padEnd(18)}${String(r.performance).padEnd(8)}${String(r.accessibility).padEnd(8)}${String(r.bestPractices).padEnd(8)}${String(r.seo).padEnd(8)}`
      );
    });
    console.log('');
  }

  // Save summary JSON
  const summaryPath = path.join(OUTPUT_DIR, `summary-${ts}.json`);
  fs.writeFileSync(summaryPath, JSON.stringify({
    timestamp: ts,
    baseUrl: BASE_URL,
    lighthouse: allResults,
    pages: PAGES_TO_TEST.map(p => p.path),
    devices: MOBILE_DEVICES.map(d => d.name),
  }, null, 2));

  printHeader('DONE');
  console.log(`  Results in: ${OUTPUT_DIR}`);
  console.log(`  Summary: ${summaryPath}`);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
