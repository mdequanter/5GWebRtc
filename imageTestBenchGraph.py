import pandas as pd
import matplotlib.pyplot as plt

csv_filename = "stream_log.csv"

def generate_combined_graphs(csv_path):
    df = pd.read_csv(csv_path)

    if "resolution" not in df.columns or "jpeg_quality" not in df.columns:
        print("⚠️ CSV does not contain required columns.")
        return

    metrics = ["size_kb", "compression_time_ms", "encryption_time_ms", "fps"]
    metric_titles = {
        "size_kb": "Average Size (KB)",
        "compression_time_ms": "Average Compression Time (ms)",
        "encryption_time_ms": "Average Encryption Time (ms)",
        "fps": "Frames Per Second (FPS)"
    }

    jpeg_qualities = sorted(df["jpeg_quality"].unique())
    resolutions = sorted(df["resolution"].unique())

    # 1. Combined graphs by resolution
    for metric in metrics:
        plt.figure(figsize=(10, 6))
        for res in resolutions:
            df_res = df[df["resolution"] == res]
            grouped = df_res.groupby("jpeg_quality")[metric].mean()
            grouped = grouped.reindex(jpeg_qualities)
            plt.plot(jpeg_qualities, grouped, marker='o', label=res)

        plt.title(f"{metric_titles[metric]} by JPEG Quality")
        plt.xlabel("JPEG Quality (%)")
        plt.ylabel(metric_titles[metric])
        plt.grid(True)
        plt.legend(title="Resolution")
        plt.xticks(jpeg_qualities)
        plt.tight_layout()

        output_file = csv_path.replace(".csv", f"_{metric}_combined.png")
        plt.savefig(output_file)
        plt.close()
        print(f"📈 Saved combined chart: {output_file}")

    # 2. FPS vs Resolution grouped by JPEG Quality
    plt.figure(figsize=(10, 6))
    for quality in jpeg_qualities:
        df_qual = df[df["jpeg_quality"] == quality]
        grouped = df_qual.groupby("resolution")["fps"].mean()
        plt.plot(grouped.index, grouped.values, marker='o', label=f"{quality}%")

    plt.title("FPS by Resolution (Grouped by JPEG Quality)")
    plt.xlabel("Resolution")
    plt.ylabel("FPS")
    plt.grid(True)
    plt.legend(title="JPEG Quality")
    plt.tight_layout()
    output_file = csv_path.replace(".csv", "_fps_by_resolution.png")
    plt.savefig(output_file)
    plt.close()
    print(f"📈 Saved FPS vs. Resolution chart: {output_file}")

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

        plt.title(f"{metric_titles[metric]} by JPEG Quality per Filename")
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

    # 5. FPS vs. Size (mean + std, grouped by rounded size_kb, starting from 35 KB)
    df_filtered = df[df["size_kb"] >= 35].copy()
    df_filtered["size_kb_rounded"] = df_filtered["size_kb"].round(0)  # Round to nearest KB

    grouped = df_filtered.groupby("size_kb_rounded")["fps"].agg(["mean", "std"]).reset_index()

    plt.figure(figsize=(10, 6))
    plt.plot(grouped["size_kb_rounded"], grouped["mean"], label="Mean FPS", marker='o', linestyle='-')
    plt.fill_between(grouped["size_kb_rounded"],
                     grouped["mean"] - grouped["std"],
                     grouped["mean"] + grouped["std"],
                     color='blue', alpha=0.2, label="±1 Std Dev")

    plt.title("Mean FPS over Compressed Size (Rounded KB, ≥ 35 KB)")
    plt.xlabel("Compressed Size (KB, rounded)")
    plt.ylabel("FPS")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    output_file = csv_path.replace(".csv", "_fps_mean_std_over_size_filtered.png")
    plt.savefig(output_file)
    plt.close()
    print(f"📈 Saved filtered FPS vs. Size chart: {output_file}")



generate_combined_graphs(csv_filename)
