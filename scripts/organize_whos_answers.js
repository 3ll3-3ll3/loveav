#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const DEFAULT_DIRECTORY = String.raw`C:\Users\WJL\Desktop\windows\杂记\secret\beauty\whostv`;
const DEFAULT_STATE = path.resolve(__dirname, "..", "references", "whostv-state.json");
const TIME_ZONE = "Asia/Shanghai";

function usage(message = "") {
  if (message) console.error(message);
  console.error("用法：node organize_whos_answers.js <JSON路径> [--output <目录或.md>] [--state <状态JSON>] [--mode auto|pages|incremental] [--cutoff /helps/10250] [--no-update-state]");
  process.exit(2);
}

function parseArgs(argv) {
  const options = { input: "", output: "", state: DEFAULT_STATE, mode: "auto", cutoff: "", updateState: true };
  const values = [...argv];
  while (values.length) {
    const token = values.shift();
    if (!token.startsWith("-") && !options.input) options.input = token;
    else if (token === "--output") options.output = values.shift() || usage("--output 缺少路径");
    else if (token === "--state") options.state = values.shift() || usage("--state 缺少路径");
    else if (token === "--mode") options.mode = values.shift() || usage("--mode 缺少值");
    else if (token === "--cutoff") options.cutoff = values.shift() || usage("--cutoff 缺少路径");
    else if (token === "--no-update-state") options.updateState = false;
    else usage(`未知参数：${token}`);
  }
  if (!options.input) usage("缺少输入 JSON 路径");
  if (!new Set(["auto", "pages", "incremental"]).has(options.mode)) usage("--mode 只支持 auto、pages、incremental");
  return options;
}

function shanghaiDate(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(now);
  const get = (type) => parts.find((item) => item.type === type)?.value || "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
}

function readState(file) {
  try {
    const value = readJson(file);
    return value && typeof value === "object" ? value : {};
  } catch (error) {
    if (error && error.code === "ENOENT") return {};
    throw new Error(`无法读取状态文件：${error.message}`);
  }
}

function normalizeInput(payload) {
  if (Array.isArray(payload)) return { entries: payload, metadata: {}, sourceKind: "array" };
  if (!payload || typeof payload !== "object" || !Array.isArray(payload.entries)) {
    throw new Error("JSON 必须是普通数组，或包含 entries 数组的对象。");
  }
  if (!Number.isInteger(payload.count)) throw new Error("对象 JSON 缺少整数元数据 count。");
  if (payload.count !== payload.entries.length) {
    throw new Error(`元数据 count=${payload.count}，但 entries.length=${payload.entries.length}。`);
  }
  return { entries: payload.entries, metadata: payload, sourceKind: "object" };
}

function httpUrls(answer) {
  const matches = String(answer).match(/https?:\/\/[^\s<>"'`]+/gi) || [];
  return matches.map((value) => value.replace(/[),.;!?，。；！？、\]}]+$/u, ""));
}

function extractCodes(answer) {
  const text = String(answer).replace(/https?:\/\/[^\s<>"'`]+/gi, (value) => " ".repeat(value.length));
  const found = [];
  const seen = new Set();
  const add = (value) => {
    const code = value.toUpperCase().replace(/[＿_\t ]+/g, "-").replace(/-{2,}/g, "-");
    const key = code.toLowerCase();
    if (!seen.has(key)) { seen.add(key); found.push(code); }
  };
  const pattern = /\bFC2[\t _-]*PPV[\t _-]*\d{5,9}\b|\b\d{6}-\d{3}\b|\b\d{3,6}-[A-Z]{2,8}\d{2,9}\b|\b[A-Z]{2,12}[\t _-]+\d{2,7}(?:[\t _-]+[A-Z0-9]{1,12})?\b/gi;
  for (const match of text.matchAll(pattern)) {
    const fc2 = match[0].match(/^FC2[\t _-]*PPV[\t _-]*(\d{5,9})$/i);
    add(fc2 ? `FC2-PPV-${fc2[1]}` : match[0]);
  }
  return found;
}

function pathnameOf(value, label) {
  let parsed;
  try { parsed = new URL(String(value)); } catch { throw new Error(`${label} 不是有效 URL：${value}`); }
  if (!new Set(["http:", "https:"]).has(parsed.protocol)) throw new Error(`${label} 必须是 http/https URL。`);
  return parsed.pathname.replace(/\/$/, "") || "/";
}

function helpId(pathname) {
  const match = String(pathname).match(/^\/helps\/(\d+)$/);
  return match ? Number(match[1]) : null;
}

function validateEntries(input, options, state, inputName) {
  const { entries, metadata, sourceKind } = input;
  const errors = [];
  const duplicateUrls = [];
  const emptyAnswers = [];
  const seenUrls = new Set();
  const pages = new Set();
  let previousPage = 0;
  const previousPositions = new Map();
  const normalized = [];

  if (!entries.length) errors.push("entries 为空，不能生成最终 Markdown。");
  entries.forEach((raw, index) => {
    const rowNumber = index + 1;
    if (!raw || typeof raw !== "object") { errors.push(`第 ${rowNumber} 条不是对象。`); return; }
    const missing = ["page", "position", "title", "answer", "url", "pageUrl"].filter((key) => raw[key] === undefined || raw[key] === null || String(raw[key]).trim() === "");
    if (missing.length) errors.push(`第 ${rowNumber} 条缺少：${missing.join(", ")}。`);
    const page = Number(raw.page);
    const position = Number(raw.position);
    if (!Number.isInteger(page) || page < 1) errors.push(`第 ${rowNumber} 条 page 必须是正整数。`);
    if (!Number.isInteger(position) || position < 1) errors.push(`第 ${rowNumber} 条 position 必须是正整数。`);
    const answer = String(raw.answer ?? "").trim();
    if (!answer) emptyAnswers.push(rowNumber);
    let pathname = "";
    try { pathname = pathnameOf(raw.url, `第 ${rowNumber} 条 url`); } catch (error) { errors.push(error.message); }
    try { pathnameOf(raw.pageUrl, `第 ${rowNumber} 条 pageUrl`); } catch (error) { errors.push(error.message); }
    const urlKey = String(raw.url || "").trim();
    if (urlKey) {
      if (seenUrls.has(urlKey)) duplicateUrls.push(urlKey);
      seenUrls.add(urlKey);
    }
    if (Number.isInteger(page) && page >= 1) {
      pages.add(page);
      if (page < previousPage) errors.push(`第 ${rowNumber} 条页码倒退，结果没有保持页面顺序。`);
      const priorPosition = previousPositions.get(page) || 0;
      if (position <= priorPosition) errors.push(`第 ${rowNumber} 条 position 未按页面内顺序递增。`);
      previousPositions.set(page, position);
      previousPage = Math.max(previousPage, page);
    }
    normalized.push({
      page, position, title: String(raw.title ?? "").trim(), answer,
      url: urlKey, pageUrl: String(raw.pageUrl || "").trim(), pathname,
    });
  });

  if (emptyAnswers.length) errors.push(`存在 ${emptyAnswers.length} 条空答案：${emptyAnswers.join(", ")}。`);
  if (duplicateUrls.length) errors.push(`存在 ${duplicateUrls.length} 个重复帖子 URL。`);
  const maxPage = pages.size ? Math.max(...pages) : 0;
  for (let page = 1; page <= maxPage; page += 1) if (!pages.has(page)) errors.push(`页码没有连续覆盖 1-${maxPage}，缺少第 ${page} 页。`);

  let mode = options.mode;
  if (mode === "auto") {
    const metadataMode = String(metadata.mode || "").toLowerCase();
    mode = metadataMode === "incremental" || /whos_tv_solved_answers_since_/i.test(inputName) ? "incremental" : "pages";
  }
  const cutoff = options.cutoff || String(metadata.cutoffPath || metadata.cutoff || state.cutoffPath || "");
  if (mode === "incremental") {
    if (!cutoff) errors.push("增量 JSON 没有可用截止帖路径。");
    if (normalized.some((row) => row.pathname === cutoff)) errors.push(`增量结果错误地包含截止帖 ${cutoff}。`);
    if (sourceKind === "object" && metadata.stopFound === false) errors.push(`增量抓取未找到截止帖 ${cutoff}。`);
  }
  if (errors.length) throw new Error(errors.join("\n"));
  return {
    entries: normalized, mode, cutoff, maxPage,
    summary: {
      total: normalized.length, pageRange: maxPage ? `1-${maxPage}` : "无",
      first: normalized[0]?.url || "", last: normalized.at(-1)?.url || "",
      emptyAnswers: emptyAnswers.length, duplicates: duplicateUrls.length,
    },
  };
}

function classify(entries) {
  const groups = { onlyLinks: [], other: [], both: [], onlyCodes: [] };
  for (const entry of entries) {
    const links = httpUrls(entry.answer);
    const codes = extractCodes(entry.answer);
    const row = { ...entry, links, codes };
    if (codes.length && links.length) groups.both.push(row);
    else if (codes.length) groups.onlyCodes.push(row);
    else if (links.length) groups.onlyLinks.push(row);
    else groups.other.push(row);
  }
  return groups;
}

function quoteAnswer(value) {
  return String(value).split(/\r?\n/).map((line) => `> ${line}`).join("\n");
}

function cleanHeading(value) {
  return String(value).replace(/[\r\n]+/g, " ").replace(/\s+/g, " ").trim() || "无标题";
}

function detailBlock(rows) {
  if (!rows.length) return "无。";
  return rows.map((row) => [
    `## ${cleanHeading(row.title)}`,
    "",
    `- 来源：${row.url}`,
    `- 页码：${row.page}`,
    "",
    quoteAnswer(row.answer),
  ].join("\n")).join("\n\n");
}

function buildMarkdown(groups) {
  const codes = [];
  const seen = new Set();
  for (const row of groups.onlyCodes) {
    for (const code of row.codes) {
      const key = code.toLowerCase();
      if (!seen.has(key)) { seen.add(key); codes.push(code); }
    }
  }
  const text = [
    `# 番号列表（${codes.length} 条）`, "", "```txt", ...codes, "```", "",
    `# 答案只有访问链接的（${groups.onlyLinks.length} 条）`, "", detailBlock(groups.onlyLinks), "",
    `# 其他内容（${groups.other.length} 条）`, "", detailBlock(groups.other), "",
    `# 答案同时有番号和访问链接的（${groups.both.length} 条）`, "", detailBlock(groups.both), "",
    `# 答案只有番号的（${groups.onlyCodes.length} 条）`, "", "已统一收录于文档开头的番号列表。", "",
  ].join("\n");
  return { text, codes };
}

function resolveOutput(value, date) {
  const target = path.resolve(value || DEFAULT_DIRECTORY);
  return target.toLowerCase().endsWith(".md") ? target : path.join(target, `${date}.md`);
}

function atomicWrite(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = path.join(path.dirname(file), `.${path.basename(file)}.${process.pid}.tmp`);
  fs.writeFileSync(temporary, content, "utf8");
  fs.renameSync(temporary, file);
}

function backupExisting(file) {
  if (!fs.existsSync(file)) return "";
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const backup = path.join(path.dirname(file), "backups", `${path.basename(file, ".md")}-${stamp}.md`);
  fs.mkdirSync(path.dirname(backup), { recursive: true });
  fs.copyFileSync(file, backup);
  return backup;
}

function updateState(file, state, firstEntry, date, inputName) {
  const nextPath = firstEntry.pathname;
  if (!nextPath) return { updated: false, reason: "第一条记录没有有效 pathname" };
  const current = String(state.cutoffPath || "");
  const currentId = helpId(current);
  const nextId = helpId(nextPath);
  if (currentId !== null && nextId !== null && nextId < currentId) {
    return { updated: false, reason: `拒绝把截止点从 ${current} 倒退到 ${nextPath}` };
  }
  const updated = {
    ...state, version: 1, timeZone: TIME_ZONE,
    lastProcessedDate: date,
    previousCutoffPath: current || state.previousCutoffPath || "",
    cutoffPath: nextPath,
    nextJsonName: `whos_tv_solved_answers_since_${date}.json`,
    updatedAt: new Date().toISOString(),
    updatedFrom: inputName,
  };
  atomicWrite(file, `${JSON.stringify(updated, null, 2)}\n`);
  return { updated: true, cutoffPath: nextPath };
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const inputFile = path.resolve(options.input);
  const inputName = path.basename(inputFile);
  const stateFile = path.resolve(options.state);
  const state = readState(stateFile);
  const normalized = normalizeInput(readJson(inputFile));
  const validated = validateEntries(normalized, options, state, inputName);
  const groups = classify(validated.entries);
  const totalClassified = Object.values(groups).reduce((sum, rows) => sum + rows.length, 0);
  if (totalClassified !== validated.entries.length) throw new Error("四类数量之和不等于 JSON 总数。");
  const markdown = buildMarkdown(groups);
  if (markdown.codes.some((code) => !/^(?:FC2-PPV-\d{5,9}|\d{6}-\d{3}|\d{3,6}-[A-Z]{2,8}\d{2,9}|[A-Z]{2,12}-\d{2,7}(?:-[A-Z0-9]{1,12})?)$/.test(code))) {
    throw new Error("番号列表中出现了非纯番号行。");
  }
  if (new Set(markdown.codes.map((code) => code.toLowerCase())).size !== markdown.codes.length) throw new Error("番号列表存在重复。");

  const date = shanghaiDate();
  const output = resolveOutput(options.output, date);
  const backup = backupExisting(output);
  atomicWrite(output, markdown.text);
  let stateResult = { updated: false, reason: "已按参数禁止更新" };
  if (options.updateState && validated.entries.length) stateResult = updateState(stateFile, state, validated.entries[0], date, inputName);

  const counts = {
    onlyLinks: groups.onlyLinks.length,
    other: groups.other.length,
    both: groups.both.length,
    onlyCodes: groups.onlyCodes.length,
  };
  console.log(JSON.stringify({
    ok: true, output, backup: backup || null, validation: validated.summary,
    counts, pureCodeCount: markdown.codes.length, state: stateResult,
  }, null, 2));
}

try { main(); } catch (error) {
  console.error(`校验或整理失败：\n${error.message}`);
  process.exitCode = 1;
}
