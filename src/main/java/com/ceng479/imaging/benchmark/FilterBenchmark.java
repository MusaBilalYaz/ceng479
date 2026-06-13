package com.ceng479.imaging.benchmark;

import java.util.concurrent.TimeUnit;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Fork;
import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Measurement;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.Setup;
import org.openjdk.jmh.annotations.State;
import org.openjdk.jmh.annotations.TearDown;
import org.openjdk.jmh.annotations.Warmup;
import org.openjdk.jmh.infra.Blackhole;

import com.ceng479.imaging.core.Filter;
import com.ceng479.imaging.filters.GaussianBlurFilter;
import com.ceng479.imaging.filters.GrayscaleFilter;
import com.ceng479.imaging.filters.SobelFilter;
import com.ceng479.imaging.parallel.ExecutorParallelProcessor;
import com.ceng479.imaging.parallel.ForkJoinParallelProcessor;
import com.ceng479.imaging.sequential.SequentialProcessor;
import com.ceng479.imaging.util.ImageIOUtils;
import com.ceng479.imaging.util.ImageIOUtils.ImageData;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * JMH microbenchmark comparing the sequential baseline against two parallel
 * implementations: ExecutorService and ForkJoinPool.
 */
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@State(Scope.Benchmark)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 10, time = 1)
@Fork(value = 1)
public class FilterBenchmark {

    /** Image case; includes the proposal's 4K UHD size. */
    @Param({"512x512", "1024x1024", "2048x2048", "3840x2160"})
    public String imageCase;

    /** Worker thread count for the parallel implementations. */
    @Param({"1", "2", "4", "8", "16"})
    public int threads;

    /** Which filter to apply. */
    @Param({"Grayscale", "GaussianBlur5x5", "Sobel3x3"})
    public String filterName;

    private int[] src;
    private int width;
    private int height;

    private Filter filter;
    private SequentialProcessor sequential;
    private ExecutorParallelProcessor executor;
    private ForkJoinParallelProcessor forkJoin;

    @Setup(Level.Trial)
    public void setup() {
        String[] parts = imageCase.toLowerCase().split("x");
        width = Integer.parseInt(parts[0]);
        height = Integer.parseInt(parts[1]);

        ImageData img = ImageIOUtils.generateSynthetic(width, height, 42L);
        src = img.pixels;

        filter = resolveFilter(filterName);

        sequential = new SequentialProcessor();
        executor = new ExecutorParallelProcessor(threads);
        forkJoin = new ForkJoinParallelProcessor(threads);
    }

    @TearDown(Level.Trial)
    public void tearDown() {
        if (executor != null) {
            executor.close();
        }

        if (forkJoin != null) {
            forkJoin.close();
        }
    }

    private static Filter resolveFilter(String name) {
        switch (name) {
            case "Grayscale":
                return new GrayscaleFilter();
            case "GaussianBlur5x5":
                return new GaussianBlurFilter();
            case "Sobel3x3":
                return new SobelFilter();
            default:
                throw new IllegalArgumentException("Unknown filter: " + name);
        }
    }

    @Benchmark
    public void sequential(Blackhole bh) {
        bh.consume(sequential.process(src, width, height, filter));
    }

    @Benchmark
    public void executorParallel(Blackhole bh) {
        bh.consume(executor.process(src, width, height, filter));
    }

    @Benchmark
    public void forkJoinParallel(Blackhole bh) {
        bh.consume(forkJoin.process(src, width, height, filter));
    }
}