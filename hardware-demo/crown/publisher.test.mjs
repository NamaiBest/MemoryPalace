import test from "node:test";
import assert from "node:assert/strict";
import { createPublisher } from "./transport.mjs";

const epoch = () => ({ info: { startTime: Date.now() }, data: [[1]] });
const flush = () => new Promise(r => setTimeout(r, 10));

test("ordered delivery includes source, stream ID and authorization", async () => {
  const calls = [];
  const p = createPublisher({ url: "http://localhost:1", token: "secret", streamId: "test",
    fetchImpl: async (url, opts) => { calls.push([url, opts]); return { ok: true }; } });
  p.push(epoch()); p.push(epoch()); await flush();
  assert.equal(calls.length, 2);
  assert.equal(calls[0][1].headers.Authorization, "Bearer secret");
  assert.equal(JSON.parse(calls[0][1].body).stream_id, "test");
});

test("stale EEG is discarded", async () => {
  let sent = 0;
  const p = createPublisher({ url: "http://localhost", streamId: "test", onError() {},
    fetchImpl: async () => { sent++; return { ok: true }; } });
  p.push({ info: { startTime: Date.now() - 10000 } }); await flush();
  assert.equal(sent, 0);
});

test("failure discards queued epochs; next live epoch can recover", async () => {
  let reject, sent = 0;
  const p = createPublisher({ url: "http://localhost", streamId: "test", onError() {},
    fetchImpl: () => { sent++; return sent === 1 ? new Promise((_, r) => { reject = r; }) : Promise.resolve({ ok: true }); } });
  p.push(epoch()); p.push(epoch()); reject(new Error("offline")); await flush();
  assert.equal(p.pending(), 0);
  p.push(epoch()); await flush(); assert.equal(sent, 2);
});
