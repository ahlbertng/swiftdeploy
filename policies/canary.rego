package swiftdeploy.canary

import future.keywords if
import future.keywords.contain

default allow :=false

allow if{
    not deny_error_rate
    not deny_latency
}

deny_error_rate if {
    input.error_rate_ptc > data.thresholds.max_error_rate_pct
}

deny_latency if {
    input.p99_latency_ms > data.thresholds.max_p99_latency_ms
}

violations contains msg if {
    deny_error_rate
    msg :=sprintf("error rate %.2f%% exceeds maximum %f%%", [input.error_rate_ptc, data.thresholds.max_error_rate_pct])
}

violations contains msg if {
    deny_latency
    msg := sprintf("p99 latency %.0fms exceeds maximum %.0fms", [input.p99_latency_ms, data.thresholds.max_p99_latency_ms])
}

decision :={
    "allow": allow,
    "violations": violations,
    "checked_at: input.timestamp
}