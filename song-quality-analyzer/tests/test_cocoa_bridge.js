"use strict";
// Exercise the native protocol while forbidding dynamic code generation.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("music_library_lab/cocoa_bridge.py", "utf8");
const script = source.split('SAFE_API = r"""')[1].split('"""')[0];
const messages = [];
const callbacks = new Map();
const context = vm.createContext({
  window: { pywebview: {
    api: {}, _returnValuesCallbacks: {},
    _checkValue(name, resolve, reject, id) { callbacks.set(id, { resolve, reject }); },
    _jsApiCallback(name, args, id) { messages.push({ name, args, id }); }
  } },
}, { codeGeneration: { strings: false, wasm: false } });
vm.runInContext(script, context);
context.window.pywebview._createApi([
  ...["choose_folder", "choose_file", "save_report", "drop_status", "take_drop"].map(func => ({ func })),
  {func: "__proto__.polluted"}, {func: "arbitrary_command"}
]);
assert.equal(typeof context.window.pywebview.api.choose_file, "function");
assert.equal(context.window.pywebview.api.arbitrary_command, undefined);
assert.equal({}.polluted, undefined);
(async () => {
  const result = context.window.pywebview.api.save_report("café % తెలుగు");
  assert.equal(messages[0].name, "save_report");
  assert.equal(messages[0].args[0], "café % తెలుగు");
  callbacks.get(messages[0].id).resolve({ saved: true });
  assert.deepEqual(await result, { saved: true });
  const cancelled = context.window.pywebview.api.choose_folder();
  callbacks.get(messages[1].id).resolve(null);
  assert.equal(await cancelled, null);
  const rejected = context.window.pywebview.api.choose_file();
  callbacks.get(messages[2].id).reject(new Error("denied"));
  await assert.rejects(rejected, /denied/);
  console.log("Cocoa bridge protocol passed with dynamic code generation disabled: whitelist, arguments, resolution, cancellation and rejection.");
})().catch(error => { console.error(error); process.exitCode = 1; });
