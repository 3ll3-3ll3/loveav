"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const organizer = path.join(root, "scripts", "organize_whos_answers.js");
const generator = path.join(root, "scripts", "generate_whostv_scraper.js");

function run(script, args) {
  return spawnSync(process.execPath, [script, ...args], { encoding: "utf8" });
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function fixtureEntries() {
  return [
    { page: 1, position: 1, title: "只有番号", answer: "ABC-123\nFC2 PPV 123456", url: "https://whos.tv/helps/10260", pageUrl: "https://whos.tv/helps?status=solved&page=1" },
    { page: 1, position: 2, title: "只有链接", answer: "请看 https://example.com/a", url: "https://whos.tv/helps/10259", pageUrl: "https://whos.tv/helps?status=solved&page=1" },
    { page: 2, position: 1, title: "番号和链接", answer: "DEF-456\nhttps://example.com/b", url: "https://whos.tv/helps/10258", pageUrl: "https://whos.tv/helps?status=solved&page=2" },
    { page: 2, position: 2, title: "其他", answer: "暂时不知道，多行\n继续查找", url: "https://whos.tv/helps/10257", pageUrl: "https://whos.tv/helps?status=solved&page=2" },
  ];
}

test("organizer validates, classifies, writes Markdown, and advances cutoff", (t) => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "whostv-organizer-"));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  const input = path.join(temp, "whos_tv_solved_answers_since_2026-08-27.json");
  const state = path.join(temp, "state.json");
  const output = path.join(temp, "output");
  const entries = fixtureEntries();
  writeJson(input, { mode: "incremental", count: entries.length, cutoffPath: "/helps/10250", stopFound: true, entries });
  writeJson(state, { version: 1, timeZone: "Asia/Shanghai", lastProcessedDate: "2026-08-27", cutoffPath: "/helps/10250", nextJsonName: "whos_tv_solved_answers_since_2026-08-27.json" });

  const result = run(organizer, [input, "--output", output, "--state", state]);
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  assert.deepEqual(report.counts, { onlyLinks: 1, other: 1, both: 1, onlyCodes: 1 });
  assert.equal(report.pureCodeCount, 2);
  const markdown = fs.readFileSync(report.output, "utf8");
  assert.match(markdown, /# 番号列表（2 条）/);
  assert.match(markdown, /ABC-123\nFC2-PPV-123456/);
  assert.match(markdown, /# 答案只有访问链接的（1 条）[\s\S]*# 其他内容（1 条）[\s\S]*# 答案同时有番号和访问链接的（1 条）[\s\S]*# 答案只有番号的（1 条）/);
  assert.equal((markdown.match(/^ABC-123$/gm) || []).length, 1);
  assert.equal(readJson(state).cutoffPath, "/helps/10260");
});

test("organizer rejects duplicate URLs without output or state change", (t) => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "whostv-invalid-"));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  const input = path.join(temp, "whos_tv_solved_answers_since_2026-08-27.json");
  const state = path.join(temp, "state.json");
  const output = path.join(temp, "result.md");
  const entries = fixtureEntries().slice(0, 2);
  entries[1].url = entries[0].url;
  writeJson(input, { mode: "incremental", count: entries.length, cutoffPath: "/helps/10250", stopFound: true, entries });
  writeJson(state, { cutoffPath: "/helps/10250" });
  const result = run(organizer, [input, "--output", output, "--state", state]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /重复帖子 URL/);
  assert.equal(fs.existsSync(output), false);
  assert.equal(readJson(state).cutoffPath, "/helps/10250");
});

test("generator archives newest script first and copies organizer", (t) => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "whostv-generator-"));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  const state = path.join(temp, "state.json");
  writeJson(state, { lastProcessedDate: "2026-08-27", cutoffPath: "/helps/10250", nextJsonName: "whos_tv_solved_answers_since_2026-08-27.json" });

  const first = run(generator, ["--pages", "3", "--directory", temp, "--state", state, "--reason", "首次测试"]);
  assert.equal(first.status, 0, first.stderr);
  const second = run(generator, ["--incremental", "--directory", temp, "--state", state, "--reason", "增量修订"]);
  assert.equal(second.status, 0, second.stderr);
  const report = JSON.parse(second.stdout);
  const script = fs.readFileSync(report.scriptFile, "utf8");
  assert.match(script, /credentials: 'include'/);
  assert.match(script, /cache: 'no-store'/);
  assert.match(script, /article\[data-help-id\]/);
  assert.match(script, /\/helps\/10250/);
  const archive = fs.readFileSync(report.archiveFile, "utf8");
  assert.ok(archive.indexOf("Whos.tv 增量抓取") < archive.indexOf("Whos.tv 第 1-3 页抓取"));
  assert.equal(fs.existsSync(report.organizerFile), true);
});

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
