# Parallel Image Processing Engine (Java Threads)

**CENG479 — Parallel Computing — Submission 2**  
Gazi University, Department of Computer Engineering — Spring 2026

**Team:**
- Muhammed Çakırgöz
- Musa Bilal Yaz

---

## Overview

This project applies three image filters to large images and compares a
**sequential baseline** against two **parallel implementations** built with
Java's concurrency framework.

| Implementation | Strategy |
|---|---|
| `SequentialProcessor` | Single-threaded, row-by-row baseline |
| `ExecutorParallelProcessor` | Fixed thread pool + horizontal strip decomposition |
| `ForkJoinParallelProcessor` | `ForkJoinPool` work-stealing + divide-and-conquer |

**Filters:**
- **Grayscale** — point-wise luminance conversion, memory-bandwidth-bound
- **Gaussian Blur 5×5** — convolution-based smoothing, 25 weighted taps per pixel
- **Sobel 3×3** — edge detection using horizontal and vertical gradient kernels

The core idea is **pixel independence**: each output pixel depends only on a
fixed neighborhood of the input image. Therefore, the image can be split across
threads with no locking during the main compute phase.

---

## Proposal Alignment and Final Scope

The final implementation follows the main design described in the project
proposal: Java Threads, `ExecutorService`, `ForkJoinPool`, horizontal
strip-based decomposition, and the three planned filters: Grayscale,
Gaussian Blur 5×5, and Sobel 3×3.

There are two small scope adjustments compared to the original proposal:

1. The final JMH benchmark sweep uses image sizes **512×512, 1024×1024, and
   2048×2048**, and thread counts **1, 2, 4, and 8**. The proposal also listed
   4K images and 16-thread experiments, but these were excluded from the final
   benchmark sweep to keep the JMH runtime manageable and reproducible on the
   available 6-core / 12-thread machine.
2. Halo handling for convolution filters is implemented **implicitly**. Instead
   of copying separate halo rows for each strip, each task reads from the full
   shared read-only source array and uses clamped coordinates at image borders.
   Since each task writes only to its own output rows, this still prevents write
   conflicts and keeps the implementation simple.

As a result, the final project preserves the core algorithmic and technological
goals of the proposal while using a practical benchmark scope for the available
hardware.

---

## Benchmark Results (Highlights)

Measured with JMH on a 6-core / 12-thread machine using a 2048×2048 image and
8 worker threads:

| Filter | Executor Speedup | ForkJoin Speedup |
|---|---:|---:|
| Grayscale (memory-bound) | 1.55× | 1.54× |
| Gaussian Blur 5×5 (compute-bound) | 4.30× | 4.81× |
| Sobel 3×3 (compute-bound) | 4.49× | 5.10× |

The compute-bound filters scale significantly better than the memory-bound
grayscale filter. This shows that parallel speedup depends not only on the
number of threads, but also on the arithmetic intensity of the workload.

### Efficiency Summary

Efficiency is calculated as:

```text
Efficiency = Speedup / Number of Threads
```

For the largest benchmarked image size, 2048×2048 with 8 threads, the
approximate efficiencies are:

| Filter | Executor Speedup | Executor Efficiency | ForkJoin Speedup | ForkJoin Efficiency |
|---|---:|---:|---:|---:|
| Grayscale | 1.55× | 0.19 | 1.54× | 0.19 |
| Gaussian Blur 5×5 | 4.30× | 0.54 | 4.81× | 0.60 |
| Sobel 3×3 | 4.49× | 0.56 | 5.10× | 0.64 |

These values confirm that compute-intensive filters use the available threads
more efficiently than the memory-bandwidth-bound grayscale conversion.

### Throughput Note

Throughput can be derived from the JMH average execution time as:

```text
Throughput = image_pixels / execution_time
```

In this final project, execution time and speedup are used as the main
comparison metrics, while throughput is discussed indirectly through the
speedup and scalability analysis.

---

## Requirements

- JDK 17 or newer
- Maven 3.6+

---

## Build

```bash
mvn clean package
```

This produces `target/image-processing.jar`, an executable fat JAR.

---

## Run the Correctness Demo

The demo verifies that both parallel implementations produce **pixel-identical**
output compared with the sequential baseline for all three filters:

```bash
java -jar target/image-processing.jar
```

---

## Filter a Real Image

```bash
java -jar target/image-processing.jar demo path/to/photo.png
```

This writes:

```text
photo_Grayscale.png
photo_GaussianBlur5x5.png
photo_Sobel3x3.png
```

---

## Quick Rough Timing

```bash
java -jar target/image-processing.jar time 2048 2048 4
```

This mode uses `System.nanoTime()` and is affected by JVM warm-up effects.
For report-quality performance numbers, use the JMH benchmark below.

---

## Benchmarking with JMH

The JMH harness runs warm-up iterations, prevents dead-code elimination, and
forks a clean JVM per configuration, producing more reproducible benchmark
results than simple `System.nanoTime()` measurements.

```bash
mvn clean package
java -cp target/image-processing.jar com.ceng479.imaging.benchmark.BenchmarkRunner
```

Results are written to:

```text
jmh-results.csv
```

The benchmark sweeps:

- **size** ∈ {512, 1024, 2048}
- **threads** ∈ {1, 2, 4, 8}
- **filter** ∈ {Grayscale, GaussianBlur5x5, Sobel3x3}

**Note on final benchmark scope:** The initial proposal also listed 3840×2160
(4K) images and 16-thread experiments. In the final implementation, the JMH
benchmark scope was limited to 512, 1024, and 2048 square images with 1, 2, 4,
and 8 threads to keep the benchmark runtime manageable and reproducible on the
available 6-core / 12-thread machine.

### Computing Speedup

```text
speedup = sequential_time(size, filter) / parallel_time(size, threads, filter)
```

Turn the raw CSV into a tidy speedup table and charts:

```bash
python3 scripts/process_results.py jmh-results.csv
```

If the updated result-processing script is used, the generated table can also
include efficiency columns:

```text
executor_efficiency = executor_speedup / threads
forkjoin_efficiency = forkjoin_speedup / threads
```

---

## Project Layout

```text
src/main/java/com/ceng479/imaging/
├── App.java                        # CLI entry point: demo / time modes
├── core/
│   ├── Filter.java                 # filter contract: applyPixel(...)
│   └── PixelUtils.java             # channel + clamp helpers
├── filters/
│   ├── GrayscaleFilter.java
│   ├── GaussianBlurFilter.java
│   └── SobelFilter.java
├── sequential/
│   └── SequentialProcessor.java    # baseline
├── parallel/
│   ├── ExecutorParallelProcessor.java
│   └── ForkJoinParallelProcessor.java
├── util/
│   ├── ImageIOUtils.java           # load/save + synthetic generator
│   └── CorrectnessVerifier.java
└── benchmark/
    ├── FilterBenchmark.java        # JMH benchmark
    └── BenchmarkRunner.java        # programmatic launcher → CSV
```

---

## Notes on Correctness

All parallel implementations are verified against the sequential baseline using
`CorrectnessVerifier.firstDifference()`, a pixel-for-pixel comparison.

The parallel and sequential outputs are **bit-identical** because:

1. Strip/row partitions are disjoint, so there are no overlapping writes.
2. The source array is read-only during processing, so there are no data races.
3. Edge handling uses the same clamped-coordinate logic in every implementation.

### Halo Handling

For convolution filters, neighboring rows across strip boundaries are read
directly from the shared read-only source array. Therefore, the implementation
does not need to copy separate halo buffers. Border pixels are handled with
clamped coordinates, so the sequential, `ExecutorService`, and `ForkJoinPool`
versions produce identical output.

---

## Repository Note

The active Maven project should be located at the repository root. If a
duplicate extracted folder such as `parallel-image-processing-main/` exists in
the repository, it is not required for building or running the final project and
can be removed to avoid confusion.

---

## Summary

This project demonstrates that image filtering is well suited to data-parallel
execution on multi-core CPUs. The final implementation shows measurable speedup
for compute-intensive filters, verifies correctness against a sequential
baseline, and compares two Java thread-based strategies: fixed thread pools and
ForkJoin work-stealing.
