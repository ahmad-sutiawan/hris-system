"""SVG inner markup for sidebar nav icons (Heroicons-style outline, 24x24)."""

NAV_ICONS: dict[str, str] = {
    "default": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>'
    ),
    "dashboard": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>'
    ),
    "notifications": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>'
    ),
    "employees": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>'
    ),
    "profile": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>'
    ),
    "attendance": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>'
    ),
    "shift-schedule": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>'
    ),
    "leave": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>'
    ),
    "overtime": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M13 10V3L4 14h7v7l9-11h-7z"/>'
    ),
    "payroll": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>'
    ),
    "payslip": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>'
    ),
    "audit": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/>'
    ),
    "admin-hub": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>'
        '<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>'
    ),
    "building": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>'
    ),
    "scale": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"/>'
    ),
    "department": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>'
    ),
    "briefcase": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>'
    ),
    "clock": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>'
    ),
    "rotation": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>'
    ),
    "tag": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/>'
    ),
    "bookmark": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/>'
    ),
    "cash": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/>'
    ),
    "wallet": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>'
    ),
    "globe": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>'
    ),
    "user": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>'
    ),
    "flag": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 7H21l-3 6H3z"/>'
    ),
    "document": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/>'
    ),
    "chart": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>'
    ),
    "gift": (
        '<path stroke-linecap="round" stroke-linejoin="round" '
        'd="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7"/>'
    ),
}

# Map menu url names, resource slugs, and aliases to icon keys.
NAV_ICON_ALIASES: dict[str, str] = {
    "dashboard": "dashboard",
    "notifications": "notifications",
    "notification_list": "notifications",
    "employee_list": "employees",
    "employee_create": "employees",
    "employee_edit": "employees",
    "employee_import": "employees",
    "employee_profile": "profile",
    "employees": "employees",
    "attendance_list": "attendance",
    "attendance_export": "attendance",
    "attendance-records": "clock",
    "attendance-codes": "tag",
    "overtime-types": "overtime",
    "shift_assignment_list": "shift-schedule",
    "shift_assign": "shift-schedule",
    "shift-assignments": "shift-schedule",
    "leave_list": "leave",
    "leave_create": "leave",
    "leave-requests": "leave",
    "leave-types": "bookmark",
    "leave-balances": "wallet",
    "leave-segments": "clock",
    "overtime_list": "overtime",
    "overtime_create": "overtime",
    "payroll_list": "payroll",
    "payroll-runs": "payroll",
    "payslip_list": "payslip",
    "payslips": "payslip",
    "audit_log_list": "audit",
    "audit-logs": "audit",
    "manage_hub": "admin-hub",
    "plants": "building",
    "legal-entities": "scale",
    "departments": "department",
    "job-positions": "briefcase",
    "shifts": "clock",
    "shift-rotations": "rotation",
    "salary-components": "cash",
    "tenants": "globe",
    "users": "user",
    "feature-flags": "flag",
    "employee-documents": "document",
    "daily-timesheets": "chart",
    "thr-runs": "gift",
    "admin-notifications": "notifications",
}


def resolve_nav_icon(key: str) -> str:
    icon_key = NAV_ICON_ALIASES.get(key, key)
    return NAV_ICONS.get(icon_key, NAV_ICONS["default"])
