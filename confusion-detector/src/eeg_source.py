"""EEG input, with one interface for real hardware and for development without it.

Boards supported out of the box:
  synthetic - BrainFlow's built-in generator. No hardware. Use this to develop.
  muse2 / muses - the team's Muse headbands (TP9, AF7, AF8, TP10 @ 256 Hz)
  cyton     - OpenBCI Cyton 8-channel (HackMIT stocks these)
  ganglion  - OpenBCI Ganglion 4-channel (HackMIT stocks these)
  playback  - replay a previously recorded session from disk

The point is that everything downstream is identical regardless of source, so the demo
can be built and rehearsed today and the headband dropped in unchanged.
"""
import time
import numpy as np
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

BOARDS = {
    "synthetic": BoardIds.SYNTHETIC_BOARD,
    "muse2": BoardIds.MUSE_2_BOARD,
    "muses": BoardIds.MUSE_S_BOARD,
    "cyton": BoardIds.CYTON_BOARD,
    "ganglion": BoardIds.GANGLION_BOARD,
}


class EEGSource:
    """Streams EEG as (n_channels, n_samples) float arrays in microvolts."""

    def __init__(self, board="synthetic", serial_port="", mac_address="", verbose=False):
        if board not in BOARDS:
            raise ValueError(f"unknown board {board!r}; options: {list(BOARDS)}")
        self.board_name = board
        self.board_id = BOARDS[board]
        params = BrainFlowInputParams()
        if serial_port:
            params.serial_port = serial_port
        if mac_address:
            params.mac_address = mac_address
        if not verbose:
            BoardShim.disable_board_logger()
        self._shim = BoardShim(self.board_id, params)
        self._started = False

        self.fs = BoardShim.get_sampling_rate(self.board_id)
        self.eeg_rows = BoardShim.get_eeg_channels(self.board_id)
        try:
            self.ch_names = BoardShim.get_eeg_names(self.board_id)
        except Exception:
            self.ch_names = [f"ch{i}" for i in range(len(self.eeg_rows))]

    def start(self):
        self._shim.prepare_session()
        self._shim.start_stream()
        self._started = True
        return self

    def stop(self):
        if self._started:
            try:
                self._shim.stop_stream()
                self._shim.release_session()
            except Exception:
                pass
            self._started = False

    def read(self):
        """Drain everything buffered since the last read. May return 0 samples."""
        data = self._shim.get_board_data()
        if data.size == 0:
            return np.zeros((len(self.eeg_rows), 0))
        return data[self.eeg_rows, :]

    def frontal_indices(self, preferred):
        """Indices of the channels we want for cognitive load.

        Falls back to all channels if none of the preferred names are present (which is
        the case for the synthetic board, whose channels are unnamed).
        """
        idx = [i for i, n in enumerate(self.ch_names) if n in preferred]
        return idx if idx else list(range(len(self.ch_names)))

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


class PlaybackSource:
    """Replay a recorded .npz so a demo can be rehearsed deterministically.

    Useful for two things: testing the detector against a known-good recording, and
    having a guaranteed-working fallback if the hardware misbehaves on demo day.
    """

    def __init__(self, path, realtime=True):
        d = np.load(path, allow_pickle=True)
        self.data = d["eeg"]
        self.fs = int(d["fs"])
        self.ch_names = [str(c) for c in d["ch_names"]]
        self.board_name = f"playback:{path}"
        self.realtime = realtime
        self._pos = 0
        self._last = None

    def start(self):
        self._last = time.time()
        return self

    def stop(self):
        pass

    def read(self):
        now = time.time()
        if self.realtime:
            n = int((now - self._last) * self.fs)
        else:
            n = self.fs  # one second per call, as fast as possible
        self._last = now
        if n <= 0 or self._pos >= self.data.shape[1]:
            return np.zeros((self.data.shape[0], 0))
        chunk = self.data[:, self._pos:self._pos + n]
        self._pos += n
        return chunk

    def exhausted(self):
        return self._pos >= self.data.shape[1]

    def data_time(self):
        """Seconds of signal consumed so far.

        In fast mode wall-clock time is meaningless (we replay far faster than
        realtime), so the session must measure elapsed time by how much data it has
        actually seen. Without this, calibration burns through the whole recording.
        """
        return self._pos / self.fs

    def frontal_indices(self, preferred):
        idx = [i for i, n in enumerate(self.ch_names) if n in preferred]
        return idx if idx else list(range(len(self.ch_names)))

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()


def make_source(board, **kw):
    if board.startswith("playback:"):
        return PlaybackSource(board.split(":", 1)[1], realtime=kw.get("realtime", True))
    return EEGSource(board, **{k: v for k, v in kw.items() if k != "realtime"})
