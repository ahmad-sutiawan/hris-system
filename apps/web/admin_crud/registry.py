from dataclasses import dataclass, field


@dataclass
class Column:
    header: str
    attr: str


@dataclass
class AdminResource:
    slug: str
    model: type
    form_class: type
    section: str
    title: str
    title_plural: str
    columns: list[Column] = field(default_factory=list)
    search_fields: list[str] = field(default_factory=list)
    select_related: list[str] = field(default_factory=list)
    order_by: list[str] = field(default_factory=lambda: ["-pk"])
    allow_create: bool = True
    allow_edit: bool = True
    allow_delete: bool = True
    tenant_scoped: bool = True
    list_limit: int = 100
    subtitle: str = ""
    master_data: bool = False
    master_group: str = ""
    hide_from_admin_nav: bool = False


REGISTRY: dict[str, AdminResource] = {}
_BOOTSTRAPPED = False

APP_SECTION_ORDER = [
    "Employees",
    "Organization",
    "Attendance",
    "Shifts",
    "Leave",
    "Payroll",
    "Core",
]


def register(resource: AdminResource):
    REGISTRY[resource.slug] = resource
    return resource


def get_resource(slug: str) -> AdminResource | None:
    return REGISTRY.get(slug)


def resources_by_section() -> dict[str, list[AdminResource]]:
    grouped: dict[str, list[AdminResource]] = {}
    for resource in REGISTRY.values():
        grouped.setdefault(resource.section, []).append(resource)
    for items in grouped.values():
        items.sort(key=lambda r: r.title)
    return grouped


MASTER_GROUP_ORDER = [
    "Organization Structure",
    "Attendance",
    "Operations",
    "Finance",
    "Workflow",
]

MASTER_SLUG_ORDER = [
    "plants",
    "departments",
    "job-positions",
    "job-levels",
    "punch-locations",
    "holidays",
    "shifts",
    "attendance-codes",
    "overtime-types",
    "leave-types",
    "salary-components",
    "shift-allowance-rates",
    "pph21-ter-categories",
    "pph21-ter-brackets",
    "pph21-ter-ptkp",
    "approval-lines",
]


def _master_sort_key(resource: AdminResource) -> tuple[int, str]:
    try:
        idx = MASTER_SLUG_ORDER.index(resource.slug)
    except ValueError:
        idx = len(MASTER_SLUG_ORDER)
    return (idx, resource.title)


def resources_master_data() -> list[tuple[str, list[AdminResource]]]:
    grouped: dict[str, list[AdminResource]] = {}
    for resource in REGISTRY.values():
        if not resource.master_data:
            continue
        grouped.setdefault(resource.master_group or "Other", []).append(resource)
    ordered = []
    for group in MASTER_GROUP_ORDER:
        if group in grouped:
            items = grouped.pop(group)
            items.sort(key=_master_sort_key)
            ordered.append((group, items))
    for group, items in sorted(grouped.items()):
        items.sort(key=_master_sort_key)
        ordered.append((group, items))
    return ordered


def master_nav_items() -> list[AdminResource]:
    items: list[AdminResource] = []
    for _, resources in resources_master_data():
        items.extend(resources)
    return items


def resources_by_app(*, exclude_master: bool = False) -> list[tuple[str, list[AdminResource]]]:
    grouped = resources_by_section()
    ordered = []
    for section in APP_SECTION_ORDER:
        if section in grouped:
            items = [
                resource
                for resource in grouped[section]
                if not (exclude_master and resource.master_data)
                and not resource.hide_from_admin_nav
            ]
            if items:
                ordered.append((section, items))
    for section, items in grouped.items():
        if section not in APP_SECTION_ORDER:
            filtered = [
                resource
                for resource in items
                if not (exclude_master and resource.master_data)
                and not resource.hide_from_admin_nav
            ]
            if filtered:
                ordered.append((section, filtered))
    return ordered


def ensure_bootstrapped():
    global _BOOTSTRAPPED
    if not _BOOTSTRAPPED:
        from apps.web.admin_crud.bootstrap import bootstrap_registry

        bootstrap_registry()
        _BOOTSTRAPPED = True
