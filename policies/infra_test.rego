package swiftdeploy.infra

import future.keywords.if

test_infra_allows_values_within_limits if {
    allow with input as {
        "disk_free_gb": data.thresholds.min_disk_free_gb + 1,
        "cpu_load": data.thresholds.max_cpu_load - 1,
    }
}

test_infra_allows_exact_thresholds if {
    allow with input as {
        "disk_free_gb": data.thresholds.min_disk_free_gb,
        "cpu_load": data.thresholds.max_cpu_load,
    }
}

test_infra_denies_disk_below_minimum if {
    not allow with input as {
        "disk_free_gb": data.thresholds.min_disk_free_gb - 1,
        "cpu_load": data.thresholds.max_cpu_load - 1,
    }
}

test_infra_denies_cpu_above_maximum if {
    not allow with input as {
        "disk_free_gb": data.thresholds.min_disk_free_gb + 1,
        "cpu_load": data.thresholds.max_cpu_load + 1,
    }
}

test_infra_reports_both_violations if {
    result := violations with input as {
        "disk_free_gb": data.thresholds.min_disk_free_gb - 1,
        "cpu_load": data.thresholds.max_cpu_load + 1,
    }
    count(result) == 2
}
