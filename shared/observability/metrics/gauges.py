"""Standard UpDownCounter (gauge-like) metric constructors."""

from __future__ import annotations

from opentelemetry.metrics import Meter, UpDownCounter


def make_active_connections_counter(meter: Meter) -> UpDownCounter:
    return meter.create_up_down_counter(
        "active_connections",
        description="Current number of active connections",
        unit="1",
    )


def make_queue_depth_counter(meter: Meter) -> UpDownCounter:
    return meter.create_up_down_counter(
        "queue_depth",
        description="Current message queue depth",
        unit="1",
    )


def make_active_tenants_counter(meter: Meter) -> UpDownCounter:
    return meter.create_up_down_counter(
        "active_tenants",
        description="Current number of active tenants",
        unit="1",
    )
