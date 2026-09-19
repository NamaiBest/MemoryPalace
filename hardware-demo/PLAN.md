# HackMIT preparation plan

Target: a wearer-calibrated, sustained EEG-load trigger stops a recording that our
application started. This is a feasibility demo, not validated confusion detection.

1. Reuse the existing Python feature extractor and persistence detector. Feed them
   exact, non-overlapping sample windows independent of network packet sizes.
2. Expose Crown-shaped EEG ingestion, calibration/status, recording start/stop,
   and an acknowledged phone-command queue over HTTP.
3. Run synthetic baseline/load EEG through that same HTTP path and stop an actual
   FFmpeg test-pattern recording. Save raw input, decisions, actions, and an MP4.
4. Prepare an official Neurosity SDK publisher using Node and Wi-Fi/cloud transport.
5. Prepare the Meta phone integration against a pinned official CameraAccess sample.
6. Test packet boundaries, invalid/missing data, calibration, stop delivery, retries,
   and the complete demo. Record the remaining physical-device checks in README.md.

No automatic recording restart after a trigger. A person must start the next clip.
The original capture-on-trigger experiments remain available in their own folders.

Execution: steps 1–4 and the software portion of step 6 are complete and verified.
Step 5's Android integration is prepared; compilation is blocked by the local
Java/Android setup and still requires Meta package access. See VERIFICATION.md for
the exact tested scope and README.md for the hardware-day sequence.
