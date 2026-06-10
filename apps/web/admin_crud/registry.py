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


REGISTRY: dict[str, AdminResource] = {}
_BOOTSTRAPPED = False

APP_SECTION_ORDER = [
    "Core",
    "Organization",
    "Employees",
    "Shifts",
    "Attendance",
    "Leave",
    "Payroll",
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


def resources_by_app() -> list[tuple[str, list[AdminResource]]]:
    grouped = resources_by_section()
    ordered = []
    for section in APP_SECTION_ORDER:
        if section in grouped:
            ordered.append((section, grouped[section]))
    for section, items in grouped.items():
        if section not in APP_SECTION_ORDER:
            ordered.append((section, items))
    return ordered


def ensure_bootstrapped():
    global _BOOTSTRAPPED
    if not _BOOTSTRAPPED:
        from apps.web.admin_crud.bootstrap import bootstrap_registry

        bootstrap_registry()
        _BOOTSTRAPPED = True
