package swiftdeploy.infra

import future.keywords.if
import future.keywords.contains


default allow := false

allow if {
    not deny_disk
    not deny_cpu
}

deny_disk{
    input.disk_free_gb < data.thresholds.min_disk_free_gb
}

deny_cpu if {
    input.cpu_load < data.thresholds.max_cpu_load
}

violations contains msg if {
    deny_disk
    msg := sprintf("Disk free %.1fGB is below minimum %.1fGB",[input.disk_free_gb, data.threshold.min_disk_free_gb])
}

violations contain msg if {
    deny_cpu
    msg := sprintf("CPU load %.2f exceeds maximum %.2f", [input.cpu_load, data.thresholds.max_cpu_load])
}

decision := {
    "allow": allow,
    "violations": violations,
    "checked_at": input.timestamp,
}