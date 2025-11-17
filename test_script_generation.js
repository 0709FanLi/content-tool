const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // 监听控制台消息
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[') && (
      text.includes('Sidebar') ||
      text.includes('loadProjectData') ||
      text.includes('watch projectId') ||
      text.includes('handleGenerateKeyframes')
    )) {
      console.log('CONSOLE:', text);
    }
  });

  // 打开页面
  console.log('导航到首页...');
  await page.goto('http://localhost:3000');
  
  // 等待页面加载
  await page.waitForTimeout(2000);
  
  // 检查是否需要登录
  const currentUrl = page.url();
  console.log('当前URL:', currentUrl);
  
  if (currentUrl.includes('login')) {
    console.log('需要登录，请在浏览器中手动登录，然后按任意键继续...');
    // 等待用户登录
    await page.waitForTimeout(30000);
  }
  
  // 等待项目列表出现
  console.log('\n等待项目列表加载...');
  await page.waitForSelector('.project-list .project-item', { timeout: 10000 });
  
  // 获取第一个项目
  const firstProject = await page.locator('.project-list .project-item').first();
  const projectName = await firstProject.locator('.project-name').textContent();
  console.log('\n找到项目:', projectName);
  
  // 点击项目
  console.log('\n点击项目...');
  await firstProject.click();
  
  // 等待页面跳转和加载
  await page.waitForTimeout(3000);
  
  const newUrl = page.url();
  console.log('跳转后URL:', newUrl);
  
  // 等待脚本内容加载
  await page.waitForTimeout(2000);
  
  // 检查是否有"生成关键帧"按钮
  const generateButton = page.locator('button:has-text("生成关键帧")');
  const buttonExists = await generateButton.count() > 0;
  
  if (buttonExists) {
    // 检查按钮是否可用
    const isDisabled = await generateButton.getAttribute('disabled');
    console.log('\n"生成关键帧"按钮状态:', isDisabled ? '禁用' : '可用');
    
    if (!isDisabled) {
      console.log('\n点击"生成关键帧"...');
      await generateButton.click();
      
      // 等待一会儿看响应
      await page.waitForTimeout(2000);
    } else {
      console.log('按钮被禁用，无法点击');
    }
  } else {
    console.log('未找到"生成关键帧"按钮');
  }
  
  // 保持浏览器打开一段时间以观察
  console.log('\n等待30秒以观察...');
  await page.waitForTimeout(30000);
  
  await browser.close();
})();
