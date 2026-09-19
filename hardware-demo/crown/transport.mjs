// One request in flight. Bounded queue prevents a disconnected backend from
// turning minutes-old EEG into a delayed live trigger after reconnection.
export function createPublisher({ url, token = "", source = "crown", streamId,
  fetchImpl = fetch, onError = console.error, onProgress = () => {} }) {
  let queue = [], sending = false, stopped = false, count = 0;
  async function drain() {
    if (sending || stopped) return;
    sending = true;
    try {
      while (queue.length && !stopped) {
        const epoch = queue.shift();
        const age = Date.now() - epoch.info.startTime;
        if (source === "crown" && (age > 3000 || age < -5000)) {
          onError("Dropping stale EEG; check laptop/Crown clock and network.");
          continue;
        }
        try {
          const response = await fetchImpl(`${url.replace(/\/$/, "")}/eeg`, {
            method: "POST", headers: { "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}) },
            body: JSON.stringify({ source, stream_id: streamId, epoch }),
            signal: AbortSignal.timeout(2000)
          });
          if (!response.ok) throw new Error(`Backend HTTP ${response.status}`);
          count++;
          if (count % 160 === 0) onProgress(count);
        } catch (error) {
          queue = [];
          onError(`EEG delivery failed (${error.message}); discarded backlog.`);
          // No blind retries. A later timestamp exposes the missing data to the
          // backend, which clears its partial window and persistence counter.
        }
      }
    } finally { sending = false; }
  }
  return {
    push(epoch) {
      if (stopped) return;
      if (queue.length >= 32) {
        queue = [];
        onError("EEG queue overflow; discarded backlog.");
      }
      queue.push(epoch);
      void drain();
    },
    stop() { stopped = true; queue = []; },
    pending() { return queue.length + Number(sending); }
  };
}
