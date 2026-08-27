#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const DEFAULT_DIRECTORY = String.raw`C:\Users\WJL\Desktop\windows\杂记\secret\beauty\whostv`;
const DEFAULT_STATE = path.resolve(__dirname, "..", "references", "whostv-state.json");

function usage(message = "") {
  if (message) console.error(message);
  console.error("用法：node generate_whostv_scraper.js (--pages n | --from 1 --to n | --incremental) [--directory 路径] [--state 状态JSON] [--reason 原因] [--delay 500]");
  process.exit(2);
}

function parseArgs(argv) {
  const options = { mode: "", from: 1, to: 0, directory: DEFAULT_DIRECTORY, state: DEFAULT_STATE, reason: "按用户要求生成", delay: 500 };
  const values = [...argv];
  while (values.length) {
    const token = values.shift();
    if (token === "--pages") { options.mode = "pages"; options.from = 1; options.to = Number(values.shift()); }
    else if (token === "--from") options.from = Number(values.shift());
    else if (token === "--to") { options.mode = "pages"; options.to = Number(values.shift()); }
    else if (token === "--incremental") options.mode = "incremental";
    else if (token === "--directory") options.directory = values.shift() || usage("--directory 缺少路径");
    else if (token === "--state") options.state = values.shift() || usage("--state 缺少路径");
    else if (token === "--reason") options.reason = values.shift() || usage("--reason 缺少说明");
    else if (token === "--delay") options.delay = Number(values.shift());
    else usage(`未知参数：${token}`);
  }
  if (!options.mode) usage("必须指定 --pages、--to 或 --incremental");
  if (options.mode === "pages" && (!Number.isInteger(options.from) || !Number.isInteger(options.to) || options.from !== 1 || options.to < options.from)) usage("只支持第 1-n 页，起始页必须是 1");
  if (!Number.isInteger(options.delay) || options.delay < 200 || options.delay > 10000) usage("--delay 必须是 200-10000 毫秒");
  return options;
}

function readState(file) {
  try { return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "")); }
  catch (error) { throw new Error(`无法读取动态状态 ${file}：${error.message}`); }
}

function shanghaiParts(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(now);
  const get = (type) => parts.find((part) => part.type === type)?.value || "";
  return { date: `${get("year")}-${get("month")}-${get("day")}`, stamp: `${get("year")}${get("month")}${get("day")}-${get("hour")}${get("minute")}${get("second")}` };
}

function buildConsoleScript(config) {
  const template = String.raw`(async () => {
  'use strict';
  const CONFIG = __CONFIG__;
  const host = location.hostname.toLowerCase();
  if (!(host === 'whos.tv' || host.endsWith('.whos.tv'))) {
    throw new Error('请先打开 whos.tv 的已解决列表页面，再运行此脚本。');
  }

  const isVisible = (element) => {
    if (!element) return false;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
  };
  const controls = [...document.querySelectorAll('a, button, [role="button"], [data-account-menu], [data-user-menu]')].filter(isVisible);
  const hasLogout = controls.some((element) => /(?:登出|退出登录|logout|sign\s*out)/i.test((element.textContent || '').trim()));
  const hasAccountMenu = controls.some((element) =>
    element.matches('[data-account-menu], [data-user-menu], [aria-label*="account" i], [aria-label*="账户" i], [aria-label*="账号" i]') ||
    /(?:账户|账号|个人资料|account|profile)/i.test((element.textContent || '').trim())
  );
  if (!hasAccountMenu || !hasLogout) {
    throw new Error('未通过可见账户菜单和“登出”确认登录。请先登录并展开账户菜单，然后重新运行。');
  }
  if (!document.querySelector('article[data-help-id], article[data-post-href]')) {
    throw new Error('当前页面不像 whos.tv 已解决列表页：没有找到帖子 article。');
  }

  const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
  const absolute = (value, base) => new URL(value, base).href;
  const realHttp = (value, base) => {
    try {
      const url = new URL(value, base);
      return /^https?:$/.test(url.protocol) ? url.href : '';
    } catch { return ''; }
  };
  const textWithLinks = (element, baseUrl) => {
    const clone = element.cloneNode(true);
    for (const anchor of clone.querySelectorAll('a[href]')) {
      const url = realHttp(anchor.getAttribute('href'), baseUrl);
      const label = (anchor.textContent || '').trim();
      anchor.replaceWith(document.createTextNode(url ? (label && label !== url ? label + ' ' + url : url) : label));
    }
    return (clone.textContent || '').replace(/\u00a0/g, ' ').replace(/[ \t]+\n/g, '\n').trim();
  };
  const parsePage = (html, page, pageUrl) => {
    const documentForPage = new DOMParser().parseFromString(html, 'text/html');
    const articles = [...documentForPage.querySelectorAll('article[data-help-id], article[data-post-href]')];
    if (!articles.length) throw new Error('第 ' + page + ' 页解析为 0 条，停止且不下载。');
    return articles.map((article, index) => {
      const heading = article.querySelector('h2');
      const link = article.getAttribute('data-post-href') || heading?.querySelector('a[href*="/helps/"]')?.getAttribute('href') || '';
      if (!link) throw new Error('第 ' + page + ' 页第 ' + (index + 1) + ' 条找不到帖子地址。');
      const url = absolute(link, pageUrl);
      const title = (heading?.textContent || '').replace(/\s+/g, ' ').trim();
      if (!title) throw new Error('第 ' + page + ' 页第 ' + (index + 1) + ' 条标题为空。');
      const answerRegion = article.querySelector('[data-post-answer-preview]');
      let answer = '';
      if (answerRegion) {
        const paragraphs = [...answerRegion.querySelectorAll('p')];
        answer = (paragraphs.length ? paragraphs.map((paragraph) => textWithLinks(paragraph, pageUrl)) : [textWithLinks(answerRegion, pageUrl)]).filter(Boolean).join('\n');
      }
      if (!answer) {
        const fallback = (article.textContent || '').match(/答案[：:]\s*([\s\S]+)$/u);
        answer = fallback ? fallback[1].trim() : '';
      }
      if (!answer) throw new Error('第 ' + page + ' 页第 ' + (index + 1) + ' 条答案为空，停止且不下载。');
      return { page, position: index + 1, title, answer, url, pageUrl };
    });
  };
  const fetchPage = async (page) => {
    const pageUrl = new URL(location.href);
    pageUrl.hash = '';
    pageUrl.searchParams.set('page', String(page));
    const response = await fetch(pageUrl.href, { credentials: 'include', cache: 'no-store' });
    if (!response.ok) throw new Error('第 ' + page + ' 页请求失败：HTTP ' + response.status);
    return { pageUrl: pageUrl.href, html: await response.text() };
  };

  const entries = [];
  const seenUrls = new Set();
  let stopFound = CONFIG.mode !== 'incremental';
  const append = (row) => {
    if (seenUrls.has(row.url)) throw new Error('发现重复帖子 URL：' + row.url);
    seenUrls.add(row.url);
    entries.push(row);
  };

  if (CONFIG.mode === 'pages') {
    for (let page = CONFIG.fromPage; page <= CONFIG.toPage; page += 1) {
      const fetched = await fetchPage(page);
      for (const row of parsePage(fetched.html, page, fetched.pageUrl)) append(row);
      if (page < CONFIG.toPage) await sleep(CONFIG.delayMs);
    }
  } else {
    outer: for (let page = 1; page <= CONFIG.maxPages; page += 1) {
      const fetched = await fetchPage(page);
      const rows = parsePage(fetched.html, page, fetched.pageUrl);
      for (const row of rows) {
        if (new URL(row.url).pathname.replace(/\/$/, '') === CONFIG.cutoffPath) {
          stopFound = true;
          break outer;
        }
        append(row);
      }
      if (page < CONFIG.maxPages) await sleep(CONFIG.delayMs);
    }
    if (!stopFound) throw new Error('抓取到安全页数上限仍未找到截止帖 ' + CONFIG.cutoffPath + '，停止且不下载。');
  }

  if (!entries.length) throw new Error('没有抓到截止帖之前的新答案，不生成空文件。');
  if (entries.some((entry) => !entry.answer.trim())) throw new Error('结果中存在空答案，不下载。');
  const payload = {
    mode: CONFIG.mode,
    count: entries.length,
    generatedAt: new Date().toISOString(),
    cutoffPath: CONFIG.mode === 'incremental' ? CONFIG.cutoffPath : '',
    stopFound,
    pageStart: CONFIG.fromPage,
    pageEnd: Math.max(...entries.map((entry) => entry.page)),
    entries,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' });
  const downloadUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = downloadUrl;
  anchor.download = CONFIG.outputFile;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
  console.log('Whos.tv 抓取完成', { count: entries.length, first: entries[0].url, last: entries.at(-1).url, output: CONFIG.outputFile });
})();`;
  return template.replace("__CONFIG__", JSON.stringify(config, null, 2));
}

function archive(directory, script, metadata) {
  fs.mkdirSync(directory, { recursive: true });
  const scriptFile = path.join(directory, metadata.scriptName);
  fs.writeFileSync(scriptFile, `${script}\n`, "utf8");
  const archiveFile = path.join(directory, "whostv_scripts.md");
  const old = fs.existsSync(archiveFile) ? fs.readFileSync(archiveFile, "utf8").replace(/^\uFEFF/, "") : "";
  const entry = [
    `# ${metadata.title}`, "",
    `- 用途：${metadata.purpose}`,
    `- 范围：${metadata.range}`,
    `- 输出文件：\`${metadata.outputFile}\``,
    `- 修改原因：${metadata.reason}`,
    "", "```javascript", script, "```", "",
  ].join("\n");
  fs.writeFileSync(archiveFile, old ? `${entry}\n${old}` : entry, "utf8");
  const organizerFile = path.join(directory, "organize_whos_answers.js");
  fs.copyFileSync(path.resolve(__dirname, "organize_whos_answers.js"), organizerFile);
  return { scriptFile, archiveFile, organizerFile };
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const state = readState(path.resolve(options.state));
  const time = shanghaiParts();
  let config;
  let metadata;
  if (options.mode === "incremental") {
    const cutoffPath = String(state.cutoffPath || "");
    if (!/^\/helps\/\d+$/.test(cutoffPath)) throw new Error(`动态状态中的截止点无效：${cutoffPath}`);
    const outputFile = String(state.nextJsonName || `whos_tv_solved_answers_since_${state.lastProcessedDate || time.date}.json`);
    config = { mode: "incremental", fromPage: 1, toPage: null, cutoffPath, outputFile, delayMs: options.delay, maxPages: 500 };
    metadata = {
      title: `Whos.tv 增量抓取（截止 ${cutoffPath}）`, purpose: "从第 1 页抓取到当前截止帖之前",
      range: `第 1 页开始；遇到 ${cutoffPath} 停止且不收录截止帖`, outputFile,
      reason: options.reason, scriptName: `whostv_incremental_${time.stamp}.js`,
    };
  } else {
    const outputFile = `whos_tv_solved_answers_pages_${options.from}-${options.to}.json`;
    config = { mode: "pages", fromPage: options.from, toPage: options.to, cutoffPath: "", outputFile, delayMs: options.delay, maxPages: options.to };
    metadata = {
      title: `Whos.tv 第 ${options.from}-${options.to} 页抓取`, purpose: "抓取指定范围的已解决页面",
      range: `第 ${options.from}-${options.to} 页`, outputFile,
      reason: options.reason, scriptName: `whostv_pages_${options.from}_${options.to}_${time.stamp}.js`,
    };
  }
  const script = buildConsoleScript(config);
  const paths = archive(path.resolve(options.directory), script, metadata);
  console.log(JSON.stringify({ ok: true, mode: options.mode, config, ...paths }, null, 2));
}

try { main(); } catch (error) {
  console.error(`生成 Whos.tv 抓取脚本失败：${error.message}`);
  process.exitCode = 1;
}
