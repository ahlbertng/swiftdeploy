package swiftdeploy.canary

import future.keywords.if

test_canary_allows_values_within_limits if {
    allow with input as {
        "error_rate_pct": data.thresholds.max_error_rate_pct - 0.1,
        "p99_latency_ms": data.thresholds.max_p99_latency_ms - 1,
    }
}

test_canary_allows_exact_thresholds if {
    allow with input as {
        "error_rate_pct": data.thresholds.max_error_rate_pct,
        "p99_latency_ms": data.thresholds.max_p99_latency_ms,
    }
}

test_canary_denies_error_rate_above_maximum if {
    not allow with input as {
        "error_rate_pct": data.thresholds.max_error_rate_pct + 0.1,
        "p99_latency_ms": data.thresholds.max_p99_latency_ms - 1,
    }
}

test_canary_denies_latency_above_maximum if {
    not allow with input as {
        "error_rate_pct": data.thresholds.max_error_rate_pct - 0.1,
        "p99_latency_ms": data.thresholds.max_p99_latency_ms + 1,
    }
}

test_canary_reports_both_violations if {
    result := violations with input as {
        "error_rate_pct": data.thresholds.max_error_rate_pct + 0.1,
        "p99_latency_ms": data.thresholds.max_p99_latency_ms + 1,
    }
    count(result) == 2
}
