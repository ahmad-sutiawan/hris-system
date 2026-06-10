from django import forms

from apps.employees.models import Employee
from apps.leave.models import LeaveRequest, LeaveType
from apps.payroll.models import PayrollRun
from apps.shifts.models import Shift, ShiftAssignment


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "employee_id",
            "full_name",
            "nik",
            "email",
            "phone",
            "plant",
            "department",
            "job_position",
            "join_date",
            "status",
            "base_salary",
            "allowance_transport",
            "tax_status",
        ]

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            from apps.organization.models import Department, JobPosition

            self.fields["department"].queryset = Department.objects.filter(tenant=tenant)
            self.fields["job_position"].queryset = JobPosition.objects.filter(tenant=tenant)


class ShiftAssignmentForm(forms.ModelForm):
    class Meta:
        model = ShiftAssignment
        fields = ["employee", "shift", "work_date"]

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            from apps.shifts.models import Shift

            self.fields["employee"].queryset = Employee.objects.filter(tenant=tenant)
            self.fields["shift"].queryset = Shift.objects.filter(tenant=tenant)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.scheduled_check_in = instance.shift.scheduled_check_in
        instance.scheduled_check_out = instance.shift.scheduled_check_out
        if commit:
            instance.save()
        return instance


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "is_half_day", "reason"]

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields["leave_type"].queryset = LeaveType.objects.filter(
                tenant=tenant, is_active=True
            )


class PayrollRunForm(forms.ModelForm):
    class Meta:
        model = PayrollRun
        fields = ["plant", "period_start", "period_end", "notes"]
