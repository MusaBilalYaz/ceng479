package com.ceng479.imaging;

import java.nio.file.Files;
import java.nio.file.Path;

import com.ceng479.imaging.core.Filter;
import com.ceng479.imaging.filters.GaussianBlurFilter;
import com.ceng479.imaging.filters.GrayscaleFilter;
import com.ceng479.imaging.filters.SobelFilter;
import com.ceng479.imaging.parallel.ExecutorParallelProcessor;
import com.ceng479.imaging.parallel.ForkJoinParallelProcessor;
import com.ceng479.imaging.sequential.SequentialProcessor;
import com.ceng479.imaging.util.CorrectnessVerifier;
import com.ceng479.imaging.util.ImageIOUtils;
import com.ceng479.imaging.util.ImageIOUtils.ImageData;
/**
 * Command-line entry point.
 *
 * <p>Modes:
 * <pre>
 *   (no args)                  Run a correctness check + quick timing demo on a
 *                              synthetic 2048x2048 image for all three filters.
 *
 *   demo &lt;inputImage&gt;          Apply all three filters to a real image and save
 *                              the outputs under outputs/demo/.
 *
 *   time &lt;w&gt; &lt;h&gt; &lt;threads&gt;     Quick sequential-vs-parallel timing on a synthetic
 *                              image of the given size. NOTE: for rigorous
 *                              numbers use the JMH harness (BenchmarkRunner),
 *                              not this rough System.nanoTime() mode.
 * </pre>
 *
 * <p>For grade-quality speedup figures, always use the JMH benchmark
 * (see {@code com.ceng479.imaging.benchmark.FilterBenchmark}). This class's
 * {@code time} mode is only a convenience sanity check and is subject to JIT
 * warm-up distortion.
 */
public final class App {

    private static final Filter[] FILTERS = {
        new GrayscaleFilter(),
        new GaussianBlurFilter(),
        new SobelFilter()
    };

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            runDefaultDemo();
        } else if (args[0].equals("demo") && args.length == 2) {
            runImageDemo(args[1]);
        } else if (args[0].equals("time") && args.length == 4) {
            runTiming(Integer.parseInt(args[1]),
                      Integer.parseInt(args[2]),
                      Integer.parseInt(args[3]));
        } else {
            printUsage();
        }
    }

    private static void runDefaultDemo() {
        int w = 2048, h = 2048;
        System.out.println("=== Correctness + quick timing demo (" + w + "x" + h + " synthetic) ===");
        ImageData img = ImageIOUtils.generateSynthetic(w, h, 42L);
        int threads = Runtime.getRuntime().availableProcessors();

        SequentialProcessor seq = new SequentialProcessor();

        for (Filter filter : FILTERS) {
            int[] seqOut = seq.process(img.pixels, w, h, filter);

            try (ExecutorParallelProcessor exec = new ExecutorParallelProcessor(threads)) {
                int[] execOut = exec.process(img.pixels, w, h, filter);
                int diff = CorrectnessVerifier.firstDifference(seqOut, execOut);
                System.out.printf("  [%-16s] Executor(%d threads) correctness: %s%n",
                        filter.name(), threads,
                        diff == -1 ? "PASS" : "FAIL @ index " + diff);
            }

            try (ForkJoinParallelProcessor fj = new ForkJoinParallelProcessor(threads)) {
                int[] fjOut = fj.process(img.pixels, w, h, filter);
                int diff = CorrectnessVerifier.firstDifference(seqOut, fjOut);
                System.out.printf("  [%-16s] ForkJoin(%d threads) correctness: %s%n",
                        filter.name(), threads,
                        diff == -1 ? "PASS" : "FAIL @ index " + diff);
            }
        }

        System.out.println();
        System.out.println("Correctness verified. For rigorous speedup numbers, run the JMH benchmark:");
        System.out.println("  java -cp target/image-processing.jar com.ceng479.imaging.benchmark.BenchmarkRunner");
        System.out.println("  or: mvn exec:java -Dexec.mainClass=com.ceng479.imaging.benchmark.BenchmarkRunner");
    }

    private static void runImageDemo(String inputPath) throws Exception {
    System.out.println("Loading " + inputPath + " ...");
    ImageData img = ImageIOUtils.load(inputPath);
    System.out.printf("Loaded %dx%d image.%n", img.width, img.height);

    int threads = Runtime.getRuntime().availableProcessors();

    Path outputDir = Path.of("outputs", "demo");
    Files.createDirectories(outputDir);

    Path inputFile = Path.of(inputPath);
    String fileName = inputFile.getFileName().toString();
    String baseName = removeExtension(fileName);

    try (ExecutorParallelProcessor exec = new ExecutorParallelProcessor(threads)) {
        for (Filter filter : FILTERS) {
            int[] out = exec.process(img.pixels, img.width, img.height, filter);

            Path outputPath = outputDir.resolve(baseName + "_" + filter.name() + ".png");
            ImageIOUtils.savePng(out, img.width, img.height, outputPath.toString());

            System.out.println("  Saved " + outputPath);
        }
    }

    System.out.println();
    System.out.println("Demo outputs written under: " + outputDir);
    }   
    
    
    private static String removeExtension(String fileName) {
        int dotIndex = fileName.lastIndexOf('.');

        if (dotIndex <= 0) {
            return fileName;
        }

        return fileName.substring(0, dotIndex);
    }

    private static void runTiming(int w, int h, int threads) {
        System.out.printf("=== Rough timing (%dx%d, %d threads) ===%n", w, h, threads);
        System.out.println("WARNING: System.nanoTime() timing is subject to JIT warm-up noise.");
        System.out.println("Use the JMH benchmark for grade-quality numbers.\n");

        ImageData img = ImageIOUtils.generateSynthetic(w, h, 42L);
        SequentialProcessor seq = new SequentialProcessor();

        for (Filter filter : FILTERS) {
            // warm-up
            seq.process(img.pixels, w, h, filter);

            long t0 = System.nanoTime();
            int[] seqOut = seq.process(img.pixels, w, h, filter);
            long seqMs = (System.nanoTime() - t0) / 1_000_000;

            long parMs;
            try (ExecutorParallelProcessor exec = new ExecutorParallelProcessor(threads)) {
                exec.process(img.pixels, w, h, filter); // warm-up
                long t1 = System.nanoTime();
                int[] parOut = exec.process(img.pixels, w, h, filter);
                parMs = (System.nanoTime() - t1) / 1_000_000;
                boolean ok = CorrectnessVerifier.identical(seqOut, parOut);

                if (!ok) {
                    System.out.println("  WARNING: parallel output differs!");
                }
            }

            double speedup = parMs == 0 ? 0 : (double) seqMs / parMs;
            System.out.printf("  [%-16s] seq=%5d ms  par=%5d ms  speedup=%.2fx%n",
                    filter.name(), seqMs, parMs, speedup);
        }
    }

    private static void printUsage() {
        System.out.println("Usage:");
        System.out.println("  java -jar image-processing.jar                         # correctness + demo");
        System.out.println("  java -jar image-processing.jar demo <image>            # filter a real image");
        System.out.println("  java -jar image-processing.jar time <w> <h> <threads>  # rough timing");
    }
}