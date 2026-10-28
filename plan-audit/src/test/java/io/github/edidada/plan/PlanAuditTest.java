package io.github.edidada.plan;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class PlanAuditTest {
    @Test void symmetricAndZeroSafe() {
        assertEquals(9000, PlanAudit.smoothedQError(10, 90000));
        assertEquals(9000, PlanAudit.smoothedQError(90000, 10));
        assertEquals(1, PlanAudit.smoothedQError(0, 0));
        assertThrows(IllegalArgumentException.class, () -> PlanAudit.smoothedQError(-1, 2));
    }
    @Test void comparesPerLoopAndMarksUnexecutedBranches() throws Exception {
        var doc = new ObjectMapper().readTree("""
          [{"Plan":{"Node Type":"Nested Loop","Plan Rows":20,"Actual Rows":10,"Actual Loops":1,
            "Plans":[{"Node Type":"Index Scan","Plan Rows":2,"Actual Rows":1,"Actual Loops":10},
                     {"Node Type":"Seq Scan","Plan Rows":100,"Actual Rows":0,"Actual Loops":0}]}}]
          """);
        var rows = PlanAudit.audit(doc);
        assertEquals(2.0, rows.get(1).get("smoothedQError"));
        assertEquals(10.0, rows.get(1).get("approximateTotalRows"));
        assertEquals("not-executed", rows.get(2).get("status"));
        assertFalse(rows.get(2).containsKey("smoothedQError"));
        assertThrows(IllegalArgumentException.class, () -> PlanAudit.audit(new ObjectMapper().readTree("{}")));
    }
}
