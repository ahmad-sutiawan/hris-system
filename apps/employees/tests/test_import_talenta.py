from io import BytesIO

import openpyxl
from django.test import TestCase

from apps.core.models import Plant, Tenant
from apps.employees.models import Employee
from apps.employees.services.import_talenta import import_employees_talenta_xlsx
from apps.organization.models import Department, JobLevel, JobPosition

TALENTA_HEADERS = [
    "Employee ID",
    "Full Name",
    "Barcode",
    "Organization",
    "Job Position",
    "Job Level",
    "Join Date",
    "Resign Date",
    "Status Employee",
    "End Date",
    "Sign Date",
    "Email",
    "Birth Date",
    "Age",
    "Birth Place",
    "Citizen ID Address",
    "Residential Address",
    "NPWP",
    "PTKP Status",
    "Employee Tax Status",
    "Tax Config",
    "Bank Name",
    "Bank Account",
    "Bank Account Holder",
    "BPJS Ketenagakerjaan",
    "BPJS Kesehatan",
    "NIK (NPWP 16 Digit)",
    "Mobile Phone",
    "Phone",
    "Branch Name",
    "Parent Branch Name",
    "Religion",
    "Gender",
    "Marital Status",
    "Blood Type",
    "Nationality Code",
    "Currency",
    "Length Of Service",
    "Payment Schedule",
    "Approval Line",
    "Manager",
]


def _row(**overrides):
    base = {
        "Employee ID": "25",
        "Full Name": "Amaludin",
        "Organization": "Production - Rolling Mills",
        "Job Position": "Maintenance D",
        "Job Level": "Technician",
        "Join Date": "2020-07-22",
        "Status Employee": "Harian",
        "Email": "amalu@example.com",
        "Birth Date": "1996-04-14",
        "Birth Place": "Pandeglang",
        "Residential Address": "Kp. Kubangkampil",
        "NPWP": "96.473.808.2-419.000",
        "PTKP Status": "TK/0",
        "Bank Name": "BCA",
        "Bank Account": "4930380054",
        "Bank Account Holder": "Amaludin",
        "BPJS Ketenagakerjaan": "22122086436",
        "NIK (NPWP 16 Digit)": "3601291710950003",
        "Mobile Phone": "83147187578",
        "Branch Name": "PT. Baja Perkasa Sentosa (Harian)",
        "Parent Branch Name": "PT Baja Perkasa Sentosa",
        "Gender": "Male",
        "Marital Status": "Single",
        "Manager": "",
    }
    base.update(overrides)
    return base


def _build_xlsx(rows):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(TALENTA_HEADERS)
    for row in rows:
        sheet.append([row.get(h, None) for h in TALENTA_HEADERS])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class TalentaImportTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="BPS", slug="bps")

    def test_import_creates_employee_and_org(self):
        content = _build_xlsx([_row()])
        result = import_employees_talenta_xlsx(self.tenant, content)

        self.assertEqual(result["created"], 1)
        self.assertEqual(result["errors"], [])

        employee = Employee.objects.get(tenant=self.tenant, employee_id="25")
        self.assertEqual(employee.full_name, "Amaludin")
        self.assertEqual(employee.gender, Employee.Gender.MALE)
        self.assertEqual(employee.marital_status, Employee.MaritalStatus.SINGLE)
        self.assertEqual(employee.status, Employee.Status.PERMANENT)
        self.assertEqual(employee.salary_scheme, Employee.SalaryScheme.DAILY)
        self.assertEqual(employee.tax_status, "TK/0")
        self.assertEqual(employee.bank_name, "BCA")
        self.assertEqual(employee.nik, "3601291710950003")
        self.assertEqual(employee.phone, "83147187578")

        self.assertTrue(Plant.objects.filter(tenant=self.tenant).exists())
        self.assertTrue(employee.plant.branch_type == Plant.BranchType.BPS_HARIAN)
        self.assertTrue(Department.objects.filter(tenant=self.tenant).exists())
        self.assertTrue(JobPosition.objects.filter(tenant=self.tenant).exists())
        self.assertEqual(employee.status_employee, "Harian")

    def test_contract_and_resign_status(self):
        rows = [
            _row(**{"Employee ID": "100", "Full Name": "Budi", "Status Employee": "Contract", "End Date": "2027-01-01"}),
            _row(**{"Employee ID": "101", "Full Name": "Citra", "Resign Date": "2025-12-31"}),
        ]
        import_employees_talenta_xlsx(self.tenant, _build_xlsx(rows))

        budi = Employee.objects.get(tenant=self.tenant, employee_id="100")
        self.assertEqual(budi.status, Employee.Status.CONTRACT)
        self.assertEqual(budi.status_employee, "Contract")
        self.assertEqual(str(budi.contract_end_date), "2027-01-01")

        citra = Employee.objects.get(tenant=self.tenant, employee_id="101")
        self.assertEqual(citra.status, Employee.Status.RESIGNED)
        self.assertEqual(str(citra.resign_date), "2025-12-31")

    def test_manager_relation_linked(self):
        rows = [
            _row(**{"Employee ID": "200", "Full Name": "Rusmanto", "Job Position": "Supervisor"}),
            _row(**{"Employee ID": "201", "Full Name": "Andi", "Manager": "Rusmanto"}),
        ]
        result = import_employees_talenta_xlsx(self.tenant, _build_xlsx(rows))

        self.assertEqual(result["managers_linked"], 1)
        andi = Employee.objects.get(tenant=self.tenant, employee_id="201")
        self.assertEqual(andi.manager.full_name, "Rusmanto")

    def test_reuses_same_org_for_duplicate_names(self):
        rows = [
            _row(**{"Employee ID": "300", "Full Name": "A"}),
            _row(**{"Employee ID": "301", "Full Name": "B"}),
        ]
        import_employees_talenta_xlsx(self.tenant, _build_xlsx(rows))

        self.assertEqual(Department.objects.filter(tenant=self.tenant).count(), 1)
        self.assertEqual(JobPosition.objects.filter(tenant=self.tenant).count(), 1)

    def test_update_existing_employee(self):
        import_employees_talenta_xlsx(self.tenant, _build_xlsx([_row()]))
        result = import_employees_talenta_xlsx(
            self.tenant, _build_xlsx([_row(**{"Email": "new@example.com"})])
        )
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["created"], 0)
        employee = Employee.objects.get(tenant=self.tenant, employee_id="25")
        self.assertEqual(employee.email, "new@example.com")

    def test_reimport_does_not_duplicate_master_data(self):
        rows = [
            _row(**{"Employee ID": "400", "Full Name": "A"}),
            _row(**{"Employee ID": "401", "Full Name": "B", "Job Position": "QC Inspector", "Organization": "Quality Control - Melting"}),
            _row(**{"Employee ID": "402", "Full Name": "C", "Job Position": "QC Inspector", "Organization": "Quality Control - Rolling Mills"}),
        ]
        content = _build_xlsx(rows)
        import_employees_talenta_xlsx(self.tenant, content)
        plants_1 = Plant.objects.filter(tenant=self.tenant).count()
        depts_1 = Department.objects.filter(tenant=self.tenant).count()
        jobs_1 = JobPosition.objects.filter(tenant=self.tenant).count()
        levels_1 = JobLevel.objects.filter(tenant=self.tenant).count()

        result = import_employees_talenta_xlsx(self.tenant, content)

        self.assertEqual(result["created"], 0)
        self.assertEqual(Plant.objects.filter(tenant=self.tenant).count(), plants_1)
        self.assertEqual(Department.objects.filter(tenant=self.tenant).count(), depts_1)
        self.assertEqual(JobPosition.objects.filter(tenant=self.tenant).count(), jobs_1)
        self.assertEqual(JobLevel.objects.filter(tenant=self.tenant).count(), levels_1)

    def test_same_title_different_department_creates_distinct_positions(self):
        rows = [
            _row(**{"Employee ID": "500", "Full Name": "Mel", "Job Position": "QC Inspector", "Organization": "Quality Control - Melting"}),
            _row(**{"Employee ID": "501", "Full Name": "Roll", "Job Position": "QC Inspector", "Organization": "Quality Control - Rolling Mills"}),
        ]
        import_employees_talenta_xlsx(self.tenant, _build_xlsx(rows))

        positions = JobPosition.objects.filter(tenant=self.tenant, title="QC Inspector")
        self.assertEqual(positions.count(), 2)
        depts = {p.department.name for p in positions}
        self.assertEqual(depts, {"Quality Control - Melting", "Quality Control - Rolling Mills"})

        mel = Employee.objects.get(tenant=self.tenant, employee_id="500")
        roll = Employee.objects.get(tenant=self.tenant, employee_id="501")
        self.assertEqual(mel.job_position.department.name, "Quality Control - Melting")
        self.assertEqual(roll.job_position.department.name, "Quality Control - Rolling Mills")

    def test_import_creates_three_distinct_branches(self):
        rows = [
            _row(**{"Employee ID": "601", "Full Name": "Harian A", "Branch Name": "PT. Baja Perkasa Sentosa (Harian)"}),
            _row(**{"Employee ID": "602", "Full Name": "Staff B", "Branch Name": "PT Baja Perkasa Sentosa"}),
            _row(**{"Employee ID": "603", "Full Name": "Spv C", "Branch Name": "PT. Baja Perkasa Sentosa (SPV Up)"}),
        ]
        import_employees_talenta_xlsx(self.tenant, _build_xlsx(rows))

        plants = Plant.objects.filter(
            tenant=self.tenant,
            entity_type=Plant.EntityType.BRANCH,
        ).order_by("code")
        codes = set(plants.values_list("code", flat=True))
        self.assertEqual(codes, {"BPS_HARIAN", "BPS_STAFF", "SPV_UP"})
        self.assertTrue(
            Plant.objects.filter(tenant=self.tenant, entity_type=Plant.EntityType.PT).exists()
        )

        harian = Employee.objects.get(tenant=self.tenant, employee_id="601")
        staff = Employee.objects.get(tenant=self.tenant, employee_id="602")
        spv = Employee.objects.get(tenant=self.tenant, employee_id="603")
        self.assertEqual(harian.plant.code, "BPS_HARIAN")
        self.assertEqual(staff.plant.code, "BPS_STAFF")
        self.assertEqual(staff.plant.branch_type, Plant.BranchType.BPS_STAFF)
        self.assertEqual(spv.plant.code, "SPV_UP")
        self.assertEqual(spv.plant.branch_type, Plant.BranchType.SPV_UP)
