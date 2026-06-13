# Parallel Image Processing Engine Using Java Threads

**CENG479 — Parallel Computer Architectures and Programming — Submission 2**  
Gazi University, Department of Computer Engineering — Spring 2026

**Team Members**
- 21118080027 — Muhammed Çakırgöz
- 21118080060 — Musa Bilal Yaz

---

## 1. Project Overview

This project implements a **Parallel Image Processing Engine** in Java. The main goal is to
apply image filters to large images and compare a single-threaded sequential baseline against
two Java thread-based parallel implementations.

| Implementation | Strategy |
|---|---|
| `SequentialProcessor` | Single-threaded row-by-row baseline |
| `ExecutorParallelProcessor` | Fixed thread pool with horizontal strip decomposition |
| `ForkJoinParallelProcessor` | `ForkJoinPool` divide-and-conquer with work stealing |

The engine supports three filters:

| Filter | Type | Parallelism Character |
|---|---|---|
| `Grayscale` | Point-wise luminance conversion | Memory-bandwidth-bound |
| `GaussianBlur5x5` | 5×5 convolution | Compute-bound |
| `Sobel3x3` | 3×3 edge detection | Compute-bound |

The core parallelization idea is **pixel independence**. Each output pixel depends only on
a fixed neighborhood of the input image. Therefore, the image can be divided across multiple
worker threads. During the main computation phase, the source image is read-only and every
worker writes only to its own output rows, so no lock is required.

---

## 2. Proposal Compliance

The final implementation follows the original project proposal:

- Java Threads are used as the selected technology.
- `ExecutorService` is implemented as the fixed thread pool approach.
- `ForkJoinPool` is implemented as the divide-and-conquer / work-stealing approach.
- The three proposed filters are implemented:
  - Grayscale
  - Gaussian Blur 5×5
  - Sobel Edge Detection 3×3
- Performance measurement is done with JMH.
- The benchmark includes the proposed thread counts:
  - 1, 2, 4, 8, 16
- The benchmark includes small, medium, large, and 4K image cases:
  - 512×512
  - 1024×1024
  - 2048×2048
  - 3840×2160

The largest benchmark case is the proposal's 4K UHD image size:

```text
3840 × 2160 = 8,294,400 pixels
```

---

## 3. Correctness Verification

Correctness is verified by comparing the output of each parallel implementation against the
sequential baseline using `CorrectnessVerifier.firstDifference()`.

Expected correctness demo output:

```text
=== Correctness + quick timing demo (2048x2048 synthetic) ===
  [Grayscale       ] Executor(...) correctness: PASS
  [Grayscale       ] ForkJoin(...) correctness: PASS
  [GaussianBlur5x5 ] Executor(...) correctness: PASS
  [GaussianBlur5x5 ] ForkJoin(...) correctness: PASS
  [Sobel3x3        ] Executor(...) correctness: PASS
  [Sobel3x3        ] ForkJoin(...) correctness: PASS
```

The parallel and sequential outputs are bit-identical because:

1. Row partitions are disjoint, so there are no overlapping writes.
2. The source image is read-only during processing, so there are no data races.
3. Edge handling uses the same clamped-coordinate logic in all implementations.

### Halo Handling

The proposal described a halo region for convolution filters. In the final implementation,
halo handling is achieved implicitly. Each worker can read neighboring rows directly from
the shared read-only source array, while writing only to its own output rows. Border pixels
are handled with clamped coordinates. This preserves correctness without copying separate
halo buffers.

---

## 4. Requirements

- JDK 17 or newer
- Maven 3.6+
- Python 3
- `matplotlib` for chart generation

Install matplotlib if needed:

```bash
pip install matplotlib
```

or:

```bash
python -m pip install matplotlib
```

---

## 5. Build

```bash
mvn clean package
```

This produces:

```text
target/image-processing.jar
```

---

## 6. Run the Correctness Demo

```bash
java -jar target/image-processing.jar
```

This mode checks whether the two parallel processors produce the same output as the
sequential baseline for all three filters.

---

## 7. Filter a Real Image

```bash
java -jar target/image-processing.jar demo path/to/photo.jpg
```

Example output files:

```text
photo_Grayscale.png
photo_GaussianBlur5x5.png
photo_Sobel3x3.png
```

This mode is mainly for visual demonstration. It shows that the filters are actually applied
to a real image.

---

## 8. Quick Timing Mode

```bash
java -jar target/image-processing.jar time 2048 2048 4
```

This mode uses `System.nanoTime()`. It is useful for a quick local check, but it is affected
by JVM warm-up and should not be used as the final benchmark result.

For report-quality performance numbers, use the JMH benchmark.

---

## 9. JMH Benchmark

Run the full JMH benchmark with:

```bash
mvn clean package
java -cp target/image-processing.jar com.ceng479.imaging.benchmark.BenchmarkRunner
```

The benchmark writes raw results to:

```text
jmh-results.csv
```

The proposal-aligned benchmark sweep is:

| Parameter | Values |
|---|---|
| Image case | 512×512, 1024×1024, 2048×2048, 3840×2160 |
| Threads | 1, 2, 4, 8, 16 |
| Filters | Grayscale, GaussianBlur5x5, Sobel3x3 |
| Implementations | Sequential, ExecutorService, ForkJoinPool |

The full benchmark may take a long time because it covers all image sizes, filters, thread
counts, and implementations.

---

## 10. Process Benchmark Results

After generating `jmh-results.csv`, run:

```bash
python scripts/process_results.py outputs/benchmark/jmh-results.csv
```

The script generates:

```text
outputs/benchmark/jmh-results.csv
outputs/benchmark/speedup_table.csv
outputs/speedup/speedup_Grayscale.png
outputs/speedup/speedup_GaussianBlur5x5.png
outputs/speedup/speedup_Sobel3x3.png
outputs/speedup/speedup_combined_4k_executor.png
outputs/efficiency/efficiency_Grayscale.png
outputs/efficiency/efficiency_GaussianBlur5x5.png
outputs/efficiency/efficiency_Sobel3x3.png
outputs/efficiency/efficiency_combined_4k_executor.png
```

---

## 11. Metrics

The result-processing script calculates the following metrics:

| Metric | Formula | Meaning |
|---|---|---|
| Execution time | JMH `AverageTime` | Average time per filter operation |
| Speedup | `T_sequential / T_parallel` | How much faster the parallel version is |
| Efficiency | `Speedup / Thread Count` | How effectively threads are used |
| Throughput | `Megapixels / Second` | Amount of image data processed per second |

For the 4K case:

```text
Megapixels = 3840 × 2160 / 1,000,000 = 8.2944 MP
```

Throughput is calculated as:

```text
Throughput = Megapixels / (Execution Time in Seconds)
```

---

## 12. Expected Interpretation

The expected trend is:

```text
Gaussian Blur 5×5  -> strong speedup because it is compute-bound
Sobel 3×3          -> strong speedup because it performs gradient convolution
Grayscale          -> limited speedup because it is memory-bandwidth-bound
```

Therefore, compute-heavy filters should benefit more from thread-level parallelism, while
Grayscale may plateau earlier due to memory bandwidth limits.

Small images such as 512×512 may show more fluctuation because thread scheduling and JMH
overhead can become relatively more visible. For final analysis, the 2048×2048 and 3840×2160
cases are more representative.

---

## 13. Project Layout

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
│   └── SequentialProcessor.java    # sequential baseline
├── parallel/
│   ├── ExecutorParallelProcessor.java
│   └── ForkJoinParallelProcessor.java
├── util/
│   ├── ImageIOUtils.java           # load/save + synthetic image generator
│   └── CorrectnessVerifier.java
└── benchmark/
    ├── FilterBenchmark.java        # JMH benchmark
    └── BenchmarkRunner.java        # programmatic launcher → CSV
```

---

## 14. Notes for Repository Cleanliness

The active Maven project is located at the repository root. Build outputs should not be committed.

Recommended `.gitignore` entries:

```gitignore
target/
dependency-reduced-pom.xml
*.class
```

`dependency-reduced-pom.xml` is a Maven Shade Plugin generated file and is not required for
the project source repository.

---

## 15. Summary

This project demonstrates data-parallel image processing on multi-core CPUs using Java
threads. It implements and compares two parallelization strategies, verifies correctness against
a sequential baseline, and uses JMH to measure speedup, efficiency, and throughput across
multiple image sizes and thread counts, including the proposal's 4K benchmark case.
