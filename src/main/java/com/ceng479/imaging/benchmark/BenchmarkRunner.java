package com.ceng479.imaging.benchmark;

import java.nio.file.Files;
import java.nio.file.Path;

import org.openjdk.jmh.results.format.ResultFormatType;
import org.openjdk.jmh.runner.Runner;
import org.openjdk.jmh.runner.RunnerException;
import org.openjdk.jmh.runner.options.Options;
import org.openjdk.jmh.runner.options.OptionsBuilder;
/**
 * Programmatic JMH launcher.
 *
 * Runs FilterBenchmark and writes raw results to jmh-results.csv.
 */
public final class BenchmarkRunner {

    private BenchmarkRunner() {
        // Utility class
    }

    public static void main(String[] args) throws RunnerException {
    try {
        Files.createDirectories(Path.of("outputs", "benchmark"));
    } catch (Exception e) {
        throw new RuntimeException("Could not create benchmark output directory", e);
    }

    Options opt = new OptionsBuilder()
            .include(".*FilterBenchmark.*")
            .resultFormat(ResultFormatType.CSV)
            .result("outputs/benchmark/jmh-results.csv")
            .shouldFailOnError(true)
            .build();

    System.out.println("Running JMH benchmarks. This will take several minutes...");
    System.out.println("Results will be written to outputs/benchmark/jmh-results.csv\n");

    new Runner(opt).run();

    System.out.println("\nDone. See outputs/benchmark/jmh-results.csv for the raw data.");
    System.out.println("Compute speedup as: speedup = sequential_time / parallel_time");
    System.out.println("Compare rows with the same imageCase + filterName.");
    }
}