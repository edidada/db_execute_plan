package io.github.edidada.plan;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** PostgreSQL 17 JSON plans: actual rows are per-loop averages, not totals. */
public final class PlanAudit {
    private static final ObjectMapper JSON = new ObjectMapper();

    public static double smoothedQError(double estimate, double actual) {
        if (!Double.isFinite(estimate) || !Double.isFinite(actual) || estimate < 0 || actual < 0) {
            throw new IllegalArgumentException("Cardinalities must be finite and non-negative");
        }
        double e = Math.max(1, estimate), a = Math.max(1, actual);
        return Math.max(e / a, a / e);
    }

    public static List<Map<String, Object>> audit(JsonNode document) {
        JsonNode root = document.isArray() ? document.path(0) : document;
        if (!root.path("Plan").isObject()) throw new IllegalArgumentException("Missing PostgreSQL Plan object");
        List<Map<String, Object>> rows = new ArrayList<>();
        visit(root.path("Plan"), "0", rows);
        return rows;
    }

    private static void visit(JsonNode node, String path, List<Map<String, Object>> rows) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("path", path);
        row.put("operator", node.path("Node Type").asText());
        if (node.has("Actual Rows") && node.has("Actual Loops") && node.has("Plan Rows")) {
            double estimate = node.path("Plan Rows").asDouble();
            double actual = node.path("Actual Rows").asDouble();
            double loops = node.path("Actual Loops").asDouble();
            row.put("estimatedRowsPerLoop", estimate);
            row.put("actualRowsPerLoop", actual);
            row.put("loops", loops);
            row.put("approximateTotalRows", actual * loops);
            if (loops > 0) row.put("smoothedQError", smoothedQError(estimate, actual));
            else row.put("status", "not-executed");
        } else row.put("status", "estimate-only-or-incomplete");
        rows.add(row);
        int i = 0;
        for (JsonNode child : node.path("Plans")) visit(child, path + "." + i++, rows);
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 0) throw new IllegalArgumentException("Usage: java -jar plan-audit-1.0.0.jar pg-plan.json [...]");
        Map<String, Object> report = new LinkedHashMap<>();
        for (String arg : args) report.put(arg, audit(JSON.readTree(Path.of(arg).toFile())));
        System.out.println(JSON.writerWithDefaultPrettyPrinter().writeValueAsString(report));
    }
}
