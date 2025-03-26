# 📊 Testbench Results – 5GWebRtc

This section summarizes the performance evaluation of the 5GWebRtc pipeline. The testbench analyzed the impact of JPEG compression and encryption on frame rate, compression time, and overall transmission performance.

---

## 🎥 Recording

A screen recording of the live stream test in 640×480 resolution:

▶️ [`recording_640x480.avi`](./recording_640x480.avi)

---

## 📈 Performance Summary

### 1. Mean FPS over Compressed Size

![FPS over Size](./stream_log_fps_mean_std_over_size_filtered.png)

- **FPS remains stable** (~22 FPS) for images ≤ 200 KB.
- **Performance drops sharply** beyond 200 KB, hitting ~11 FPS at ~390 KB.
- 🔎 *Recommendation*: Limit image size to ≤ 200 KB for real-time streaming.

---

### 2. Average Compression Time (JPEG Quality)

![Compression Time](./stream_log_compression_time_ms_combined.png)

- **Resolutions tested**: `640x480` and `800x600`.
- **Compression time increases** with higher JPEG quality.
  - 640x480: ~0.9 to 1.3 ms
  - 800x600: ~1.2 to 2.0 ms
- ⚖️ *Recommendation*: Use JPEG quality between 50–70% for real-time performance.

---

### 3. Average Encryption Time (JPEG Quality by File)

![Encryption Time](./stream_log_encryption_time_ms_by_filename.png)

- **Encryption overhead is low**, mostly between 0.1–0.6 ms.
- **White noise images** consistently take more time to encrypt.
- AES-256-CBC encryption scales slightly with file complexity and size.

---

### 4. Summary Log (CSV)

📄 [`stream_log_summary_by_filename.csv`](./stream_log_summary_by_filename.csv)

Includes per-frame metrics:
- JPEG quality
- Compression time (ms)
- Encryption time (ms)
- Compressed size (KB)
- Achieved FPS
- Filename and resolution

---

## 🧠 Key Insights

- 💡 Optimal JPEG Quality: **50–70%**
- 🎯 Target Size: **≤ 200 KB** for smooth ~22 FPS
- 🔐 AES-256 Encryption: Low latency impact
- 🧪 Dataset includes cityscapes and synthetic noise for robustness testing

---

📂 All results were generated using the included graph and logging scripts in this repository.

Feel free to open an issue or discussion for questions about the benchmarking methodology.
