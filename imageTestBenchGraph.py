
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os

parser = argparse.ArgumentParser(description="Generate graphs from stream_log.csv in specified directory")
parser.add_argument("--map", type=str, required=True, help="Map of stream_log.csv")

args = parser.parse_args()
csv_folder = args.map
csv_filename = os.path.join(csv_folder, "stream_log.csv")


def generate_combined_graphs(csv_path):
    df = pd.read_csv(csv_path)

    if "resolution" not in df.columns or "jpeg_quality" not in df.columns:
        print("⚠️ CSV does not contain required columns.")
        return

    setup_description = df["setup description"].iloc[0] if "setup description" in df.columns else "Unknown Setup"

    metrics = ["size_kb", "compression_time_ms", "encryption_time_ms", "fps"]
    metric_titles = {
        "size_kb": "Average Size (KB)",
        "compression_time_ms": "Average Compression Time (ms)",
        "encryption_time_ms": "Average Encryption Time (ms)",
        "fps": "Frames Per Second (FPS)"
    }

    jpeg_qualities = sorted(df["jpeg_quality"].unique())
    resolutions = sorted(df["resolution"].unique())

    # 3. Summary by filename
    summary = df.groupby("filename").agg({
        "fps": ["mean", "min", "max"],
        "size_kb": "mean",
        "compression_time_ms": "mean",
        "encryption_time_ms": "mean"
    })
    summary.columns = ["_".join(col).strip() for col in summary.columns.values]
    summary_file = csv_path.replace(".csv", "_summary_by_filename.csv")
    summary.to_csv(summary_file)
    print(f"📋 Saved summary CSV by filename: {summary_file}")

    # 4. Graph per filename (example: fps vs jpeg_quality)
    for metric in metrics:
        plt.figure(figsize=(12, 6))
        for filename in df["filename"].unique():
            df_file = df[df["filename"] == filename]
            grouped = df_file.groupby("jpeg_quality")[metric].mean()
            grouped = grouped.reindex(jpeg_qualities)
            plt.plot(jpeg_qualities, grouped, marker='o', label=filename)

        plt.title(f"{metric_titles[metric]} by JPEG Quality per Filename\n{setup_description}")
        plt.xlabel("JPEG Quality (%)")
        plt.ylabel(metric_titles[metric])
        plt.grid(True)
        plt.legend(title="Filename", fontsize=8)
        plt.xticks(jpeg_qualities)
        plt.tight_layout()

        output_file = csv_path.replace(".csv", f"_{metric}_by_filename.png")
        plt.savefig(output_file)
        plt.close()
        print(f"📁 Saved filename breakdown chart: {output_file}")

    # FPS vs. Size
    df_filtered = df[df["size_kb"] >= 35].copy()
    df_filtered["size_kb_rounded"] = df_filtered["size_kb"].round(0)
    grouped = df_filtered.groupby("size_kb_rounded")["fps"].agg(["mean", "std"]).reset_index()
    plt.figure(figsize=(10, 6))
    plt.plot(grouped["size_kb_rounded"], grouped["mean"], label="Mean FPS", marker='o', linestyle='-')
    plt.fill_between(grouped["size_kb_rounded"],
                     grouped["mean"] - grouped["std"],
                     grouped["mean"] + grouped["std"],
                     color='blue', alpha=0.2, label="±1 Std Dev")
    plt.title(f"Mean FPS over Compressed Size (Rounded KB, ≥ 35 KB)\n{setup_description}")
    plt.xlabel("Compressed Size (KB, rounded)")
    plt.ylabel("FPS")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    output_file = csv_path.replace(".csv", "_fps_mean_std_over_size_filtered.png")
    plt.savefig(output_file)
    plt.close()
    print(f"📈 Saved filtered FPS vs. Size chart: {output_file}")


    # Latency vs. Size
    df_filtered = df[df["size_kb"] >= 35].copy()
    df_filtered["size_kb_rounded"] = df_filtered["size_kb"].round(0)

    grouped = df_filtered.groupby("size_kb_rounded")["latency_ms"].agg(["mean", "std"]).reset_index()

    x = grouped["size_kb_rounded"].to_numpy(dtype=float)
    y_mean = grouped["mean"].to_numpy(dtype=float)
    y_std = grouped["std"].to_numpy(dtype=float)

    plt.figure(figsize=(10, 6))
    plt.plot(x, y_mean, label="Mean Latency (ms)", marker='o', linestyle='-')
    plt.fill_between(x, y_mean - y_std, y_mean + y_std,
                     color='red', alpha=0.2, label="±1 Std Dev")

    plt.title(f"Mean Latency over Compressed Size (Rounded KB ≥ 35)\n{setup_description}")
    plt.xlabel("Compressed Size (KB, rounded)")
    plt.ylabel("Latency (ms)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    output_file = csv_path.replace(".csv", "_latency_mean_std_over_size_filtered.png")
    plt.savefig(output_file)
    plt.close()
    print(f"📈 Saved filtered Latency vs. Size chart: {output_file}")




    # Mbits vs FPS
    df_filtered = df[df["fps"] >= 10].copy()
    df_filtered["fps_rounded"] = df_filtered["fps"].round(0)
    grouped = df_filtered.groupby("fps_rounded")["Mbits"].agg(["mean", "std"]).reset_index()
    x = grouped["fps_rounded"].to_numpy(dtype=float)
    y_mean = grouped["mean"].to_numpy(dtype=float)
    y_std = grouped["std"].to_numpy(dtype=float)
    plt.figure(figsize=(10, 6))
    plt.plot(x, y_mean, label="Mean Bitrate (Mbit/s)", marker='o', linestyle='-')
    plt.fill_between(x, y_mean - y_std, y_mean + y_std,
                     color='orange', alpha=0.2, label="±1 Std Dev")
    plt.title(f"Bitrate vs FPS (Rounded FPS ≥ 10)\n{setup_description}")
    plt.xlabel("Frames Per Second (FPS)")
    plt.ylabel("Bitrate (Mbit/s)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    output_file = csv_path.replace(".csv", "_mbits_mean_std_over_fps_filtered.png")
    plt.savefig(output_file)
    plt.close()
    print(f"📈 Saved Bitrate vs FPS chart: {output_file}")

    # Mbits vs Size
    df_filtered = df[df["size_kb"] >= 10].copy()
    df_filtered["size_kb_rounded"] = df_filtered["size_kb"].round(0)
    grouped = df_filtered.groupby("size_kb_rounded")["Mbits"].agg(["mean", "std"]).reset_index()
    x = grouped["size_kb_rounded"].to_numpy(dtype=float)
    y_mean = grouped["mean"].to_numpy(dtype=float)
    y_std = grouped["std"].to_numpy(dtype=float)
    plt.figure(figsize=(10, 6))
    plt.plot(x, y_mean, label="Mean Bitrate (Mbit/s)", marker='o', linestyle='-')
    plt.fill_between(x, y_mean - y_std, y_mean + y_std,
                     color='purple', alpha=0.2, label="±1 Std Dev")
    plt.title(f"Bitrate vs Compressed Frame Size (Rounded KB ≥ 10)\n{setup_description}")
    plt.xlabel("Compressed Size (KB)")
    plt.ylabel("Bitrate (Mbit/s)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    output_file = csv_path.replace(".csv", "_mbits_mean_std_over_size_filtered.png")
    plt.savefig(output_file)
    plt.close()
    print(f"📈 Saved Bitrate vs Size chart: {output_file}")

generate_combined_graphs(csv_filename)
