from apps.attendance.models import AttendanceRecord


def get_punch_ui_state(record: AttendanceRecord | None) -> dict:
    """Dashboard badge state — buttons stay enabled for flexible re-punch."""
    if not record or not record.check_in:
        status = "pending"
    elif record.check_in and not record.check_out:
        status = "in"
    else:
        status = "out"

    return {
        "status": status,
        "can_clock_in": True,
        "can_clock_out": True,
    }
