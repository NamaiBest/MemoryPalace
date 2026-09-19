import { randomUUID } from "node:crypto";
import { Neurosity } from "@neurosity/sdk";
import { createPublisher } from "./transport.mjs";

const { NEUROSITY_DEVICE_ID: deviceId, NEUROSITY_EMAIL: email,
  NEUROSITY_PASSWORD: password, BACKEND_URL: url = "http://127.0.0.1:8771",
  DEMO_TOKEN: token = "" } = process.env;
if (!deviceId || !email || !password) {
  console.error("Fill NEUROSITY_DEVICE_ID, NEUROSITY_EMAIL and NEUROSITY_PASSWORD in .env.");
  process.exit(1);
}

const neurosity = new Neurosity({ deviceId, streamingMode: "wifi-only" });
const subscriptions = [];
const publisher = createPublisher({ url, token, streamId: randomUUID(),
  onProgress: n => console.log(`Delivered ${n} Crown epochs; see backend status for calibration.`) });
let lastEpochAt = Date.now(), closing = false;
const watchdog = setInterval(() => {
  if (Date.now() - lastEpochAt > 5000)
    console.error("No EEG for five seconds. Check Crown power, Wi-Fi, account access and contact.");
}, 5000);

async function close(code = 0) {
  if (closing) return;
  closing = true;
  clearInterval(watchdog);
  subscriptions.forEach(s => s.unsubscribe());
  publisher.stop();
  await Promise.race([neurosity.logout().catch(() => {}), new Promise(r => setTimeout(r, 2000))]);
  process.exit(code);
}
process.on("SIGINT", () => void close());
process.on("SIGTERM", () => void close());

try {
  const health = await fetch(`${url}/status`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal: AbortSignal.timeout(3000)
  });
  if (!health.ok) throw new Error(`Backend HTTP ${health.status}`);
  const state = await health.json();
  if (state.eeg.source !== "crown") throw new Error("Start backend with --source crown");
  await neurosity.login({ email, password });
  console.log("Crown login succeeded. Transport: Wi-Fi via Neurosity cloud. Read something easy for calibration.");
  subscriptions.push(neurosity.brainwaves("rawUnfiltered").subscribe({
    next(epoch) { lastEpochAt = Date.now(); publisher.push(epoch); },
    error() { console.error("Crown EEG subscription failed. Check device access."); void close(1); }
  }));
  subscriptions.push(neurosity.signalQuality().subscribe({
    next(quality) {
      console.log("Frontal contact:", JSON.stringify({ F5: quality.F5, F6: quality.F6 }));
    },
    error() { console.error("Signal-quality subscription unavailable; inspect Crown console."); }
  }));
} catch (error) {
  console.error(`Publisher could not start: ${error.code || error.name}. Check credentials, device claim and backend.`);
  await close(1);
}
