from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.attendance.models import DailyTimesheet
from apps.attendance.models import AttendanceRecord
from apps.attendance.models import OvertimeRequest
from apps.attendance.services.export import export_timesheets_csv
from apps.attendance.services.overtime_workflow import (
    OvertimeError,
    approve_overtime_request,
    cancel_overtime_request,
    get_raw_overtime_minutes,
    reject_overtime_request,
    submit_overtime_request,
)
from apps.attendance.services.punch import PunchError, clock_in, clock_out
from apps.attendance.services.photo import PhotoError, decode_selfie
from apps.attendance.services.punch_ui import get_punch_ui_state
from apps.core.decorators import require_roles
from apps.core.models import AuditLog, Notification, User
from apps.core.services.notifications import mark_notifications_read
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest
from apps.leave.services.leave_workflow import (
    LeaveError,
    approve_leave_request,
    cancel_leave_request,
    reject_leave_request,
    submit_leave_request,
)
from apps.employees.services.onboarding import employee_leave_balances_summary
from apps.payroll.models import PayrollRun, Payslip
from apps.employees.services.user_link import ensure_employee_profile
from apps.employees.services.import_csv import import_employees_csv, template_csv
from apps.employees.services.onboarding import provision_new_employee
from apps.payroll.services.bank_export import export_bank_csv
from apps.payroll.services.payslip_pdf import generate_payslip_pdf
from apps.payroll.services.payroll_run import PayrollError, calculate_payroll_run, finalize_payroll_run
from apps.shifts.models import ShiftAssignment
from apps.web.forms import (
    EmployeeForm,
    LeaveRequestForm,
    OvertimeRequestForm,
    PayrollRunForm,
    ShiftAssignmentForm,
)


def _employee_profile(user):
    return getattr(user, "employee_profile", None)


def _form_context(form, title, *, cancel_url=None, subtitle="", submit_label="Simpan"):
    return {
        "form": form,
        "title": title,
        "cancel_url": cancel_url,
        "subtitle": subtitle,
        "submit_label": submit_label,
    }


@login_required
def dashboard(request):
    user = request.user
    tenant = user.tenant
    stats = {
        "employee_count": 0,
        "pending_leave": 0,
        "pending_overtime": 0,
        "today_timesheets": 0,
        "draft_payroll": 0,
    }
    today = timezone.localdate()
    punch_ui = {
        "status": "pending",
        "can_clock_in": False,
        "can_clock_out": False,
        "needs_ci_photo": False,
        "needs_co_photo": False,
    }
    today_record = None
    profile = _employee_profile(user)

    if tenant:
        emp_qs = Employee.objects.filter(tenant=tenant)
        if user.plant_id and not user.is_admin:
            emp_qs = emp_qs.filter(plant=user.plant)
        stats["employee_count"] = emp_qs.exclude(
            status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
        ).count()
        stats["pending_leave"] = LeaveRequest.objects.filter(
            tenant=tenant,
            status=LeaveRequest.Status.PENDING,
        ).count()
        stats["pending_overtime"] = OvertimeRequest.objects.filter(
            tenant=tenant,
            status=OvertimeRequest.Status.PENDING,
        ).count()
        stats["today_timesheets"] = DailyTimesheet.objects.filter(
            tenant=tenant, work_date=today
        ).count()
        stats["draft_payroll"] = PayrollRun.objects.filter(
            tenant=tenant,
            status=PayrollRun.Status.DRAFT,
        ).count()

    if profile:
        today_record = AttendanceRecord.objects.filter(
            employee=profile, work_date=today
        ).first()
        punch_ui = get_punch_ui_state(today_record)

    return render(
        request,
        "web/dashboard.html",
        {
            "stats": stats,
            "punch_ui": punch_ui,
            "profile": profile,
            "today_record": today_record,
            "today": today,
        },
    )


@login_required
@require_POST
def punch_action(request):
    profile = _employee_profile(request.user)
    if not profile:
        messages.error(request, "Akun tidak terhubung ke data karyawan.")
        return redirect("web:dashboard")

    action = request.POST.get("action")
    photo_data = request.POST.get("photo", "").strip()
    if not photo_data:
        messages.error(request, "Foto selfie wajib. Buka kamera dan ambil foto sebelum absen.")
        return redirect("web:dashboard")

    try:
        photo = decode_selfie(photo_data)
    except PhotoError as exc:
        messages.error(request, str(exc))
        return redirect("web:dashboard")

    try:
        if action == "in":
            record = clock_in(profile, source=AttendanceRecord.Source.WEB, photo=photo)
            when = timezone.localtime(record.check_in)
            messages.success(
                request,
                f"Clock in berhasil — {when.strftime('%d %b %Y %H:%M')}.",
            )
        elif action == "out":
            record = clock_out(profile, photo=photo)
            when = timezone.localtime(record.check_out)
            messages.success(
                request,
                f"Clock out berhasil — {when.strftime('%d %b %Y %H:%M')}.",
            )
        else:
            messages.error(request, "Aksi absensi tidak valid.")
    except PunchError as exc:
        messages.error(request, str(exc))
    return redirect("web:dashboard")


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def employee_list(request):
    qs = Employee.objects.filter(tenant=request.user.tenant).select_related(
        "plant",
        "legal_entity",
        "department",
        "job_position",
        "manager",
        "user",
    )
    if request.user.plant_id and not request.user.is_admin:
        qs = qs.filter(plant=request.user.plant)

    query = request.GET.get("q", "").strip()
    if query:
        text = query
        filters = Q(
            employee_id__icontains=text,
        ) | Q(full_name__icontains=text) | Q(nik__icontains=text) | Q(email__icontains=text)
        filters |= Q(phone__icontains=text) | Q(npwp__icontains=text) | Q(tax_status__icontains=text)
        filters |= Q(bank_name__icontains=text) | Q(bank_account_number__icontains=text)
        filters |= Q(bank_account_name__icontains=text) | Q(status__icontains=text)
        filters |= Q(salary_scheme__icontains=text) | Q(bpjs_kesehatan_number__icontains=text)
        filters |= Q(bpjs_ketenagakerjaan_number__icontains=text)
        filters |= Q(plant__code__icontains=text) | Q(plant__name__icontains=text)
        filters |= Q(legal_entity__name__icontains=text) | Q(department__name__icontains=text)
        filters |= Q(department__code__icontains=text) | Q(job_position__title__icontains=text)
        filters |= Q(job_position__code__icontains=text) | Q(manager__full_name__icontains=text)
        filters |= Q(manager__employee_id__icontains=text) | Q(user__username__icontains=text)
        qs = qs.filter(filters)

    employees = list(qs.order_by("full_name")[:500])
    return render(
        request,
        "web/employees/list.html",
        {
            "employees": employees,
            "search_query": query,
            "result_count": len(employees),
        },
    )


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def employee_import_template(request):
    content = template_csv()
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="employee_import_template.csv"'
    return response


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def employee_import(request):
    if request.method == "POST":
        upload = request.FILES.get("file")
        if not upload:
            messages.error(request, "Pilih file CSV terlebih dahulu.")
            return redirect("web:employee_import")
        content = upload.read().decode("utf-8-sig")
        try:
            result = import_employees_csv(request.user.tenant, content)
            messages.success(
                request,
                f"Import selesai: {result['created']} baru, {result['updated']} diupdate.",
            )
            if result["errors"]:
                messages.warning(request, f"{len(result['errors'])} baris gagal.")
                for err in result["errors"][:5]:
                    messages.error(request, err)
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("web:employee_list")
    return render(request, "web/employees/import.html")


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def employee_create(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST, tenant=request.user.tenant, user=request.user)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.tenant = request.user.tenant
            employee.save()
            provision_new_employee(employee, assign_shift=True)
            messages.success(
                request,
                "Karyawan berhasil ditambahkan. Jatah cuti dan shift default telah diinisialisasi.",
            )
            return redirect("web:employee_list")
    else:
        form = EmployeeForm(
            initial={"plant": request.user.plant},
            tenant=request.user.tenant,
            user=request.user,
        )
    ctx = _form_context(form, "Tambah Karyawan", cancel_url="/employees/")
    return render(request, "web/employees/form.html", ctx)


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk, tenant=request.user.tenant)
    if request.user.plant_id and not request.user.is_admin and employee.plant_id != request.user.plant_id:
        messages.error(request, "Akses ditolak.")
        return redirect("web:employee_list")

    if request.method == "POST":
        form = EmployeeForm(
            request.POST,
            instance=employee,
            tenant=request.user.tenant,
            user=request.user,
        )
        if form.is_valid():
            updated = form.save(commit=False)
            updated.tenant = request.user.tenant
            updated.save()
            provision_new_employee(updated)
            messages.success(request, "Data karyawan berhasil diperbarui.")
            return redirect("web:employee_list")
    else:
        form = EmployeeForm(instance=employee, tenant=request.user.tenant, user=request.user)

    ctx = _form_context(
        form,
        f"Edit — {employee.full_name}",
        cancel_url="/employees/",
        subtitle=employee.employee_id,
    )
    return render(request, "web/employees/form.html", ctx)


@login_required
@require_POST
@require_roles(User.Role.ADMIN, User.Role.HR)
def employee_deactivate(request, pk):
    employee = get_object_or_404(Employee, pk=pk, tenant=request.user.tenant)
    if request.user.plant_id and not request.user.is_admin and employee.plant_id != request.user.plant_id:
        messages.error(request, "Akses ditolak.")
        return redirect("web:employee_list")

    employee.status = Employee.Status.INACTIVE
    employee.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Karyawan {employee.full_name} dinonaktifkan.")
    return redirect("web:employee_list")


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def shift_assignment_list(request):
    qs = ShiftAssignment.objects.filter(tenant=request.user.tenant).select_related(
        "employee", "shift"
    ).order_by("-work_date")
    if request.user.plant_id and not request.user.is_admin:
        qs = qs.filter(employee__plant=request.user.plant)

    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(employee__full_name__icontains=query)
            | Q(employee__employee_id__icontains=query)
            | Q(shift__code__icontains=query)
            | Q(shift__name__icontains=query)
        )

    assignments = list(qs[:500])
    return render(
        request,
        "web/shifts/list.html",
        {
            "assignments": assignments,
            "search_query": query,
            "result_count": len(assignments),
        },
    )


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def shift_assign(request):
    if request.method == "POST":
        instance = None
        employee_id = request.POST.get("employee")
        work_date = request.POST.get("work_date")
        if employee_id and work_date:
            instance = ShiftAssignment.objects.filter(
                employee_id=employee_id,
                work_date=work_date,
                tenant=request.user.tenant,
            ).first()

        form = ShiftAssignmentForm(
            request.POST,
            instance=instance,
            tenant=request.user.tenant,
            user=request.user,
        )
        if form.is_valid():
            from apps.attendance.services.timesheet import recalculate_daily_timesheet

            employee = form.cleaned_data["employee"]
            shift = form.cleaned_data["shift"]
            work_date = form.cleaned_data["work_date"]
            assignment, created = ShiftAssignment.objects.update_or_create(
                employee=employee,
                work_date=work_date,
                defaults={
                    "tenant": request.user.tenant,
                    "shift": shift,
                    "scheduled_check_in": shift.scheduled_check_in,
                    "scheduled_check_out": shift.scheduled_check_out,
                },
            )
            recalculate_daily_timesheet(employee, work_date)
            verb = "di-assign" if created else "diperbarui"
            messages.success(request, f"Shift berhasil {verb}.")
            return redirect("web:shift_assignment_list")
    else:
        form = ShiftAssignmentForm(tenant=request.user.tenant, user=request.user)

    ctx = _form_context(
        form,
        "Assign Shift",
        cancel_url="/shifts/",
        submit_label="Assign Shift",
    )
    return render(request, "web/shifts/assign.html", ctx)


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def shift_edit(request, pk):
    assignment = get_object_or_404(
        ShiftAssignment.objects.select_related("employee", "shift"),
        pk=pk,
        tenant=request.user.tenant,
    )
    if request.user.plant_id and not request.user.is_admin and assignment.employee.plant_id != request.user.plant_id:
        messages.error(request, "Akses ditolak.")
        return redirect("web:shift_assignment_list")

    if request.method == "POST":
        form = ShiftAssignmentForm(
            request.POST,
            instance=assignment,
            tenant=request.user.tenant,
            user=request.user,
        )
        if form.is_valid():
            from apps.attendance.services.timesheet import recalculate_daily_timesheet

            updated = form.save(commit=False)
            updated.tenant = request.user.tenant
            updated.save()
            recalculate_daily_timesheet(updated.employee, updated.work_date)
            messages.success(request, "Assignment shift diperbarui.")
            return redirect("web:shift_assignment_list")
    else:
        form = ShiftAssignmentForm(
            instance=assignment,
            tenant=request.user.tenant,
            user=request.user,
        )

    ctx = _form_context(
        form,
        "Edit Assignment Shift",
        cancel_url="/shifts/",
        subtitle=f"{assignment.employee.full_name} · {assignment.work_date}",
    )
    return render(request, "web/shifts/form.html", ctx)


@login_required
@require_POST
@require_roles(User.Role.ADMIN, User.Role.HR)
def shift_delete(request, pk):
    assignment = get_object_or_404(ShiftAssignment, pk=pk, tenant=request.user.tenant)
    employee = assignment.employee
    work_date = assignment.work_date
    assignment.delete()
    from apps.attendance.services.timesheet import recalculate_daily_timesheet

    recalculate_daily_timesheet(employee, work_date)
    messages.success(request, "Assignment shift dihapus.")
    return redirect("web:shift_assignment_list")


@login_required
def attendance_list(request):
    qs = DailyTimesheet.objects.filter(tenant=request.user.tenant).select_related(
        "employee", "plant", "attendance_code"
    )

    profile = _employee_profile(request.user)
    if profile and not request.user.is_hr:
        qs = qs.filter(employee=profile)

    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(employee__employee_id__icontains=query)
            | Q(employee__full_name__icontains=query)
            | Q(shift_code__icontains=query)
            | Q(attendance_code__code__icontains=query)
        )

    timesheets = list(qs.order_by("-work_date")[:500])
    record_map = {}
    if timesheets:
        records = AttendanceRecord.objects.filter(
            tenant=request.user.tenant,
            employee_id__in={row.employee_id for row in timesheets},
            work_date__in={row.work_date for row in timesheets},
        )
        record_map = {(r.employee_id, r.work_date): r for r in records}

    for row in timesheets:
        row.punch_record = record_map.get((row.employee_id, row.work_date))

    return render(
        request,
        "web/attendance/list.html",
        {
            "timesheets": timesheets,
            "record_map": record_map,
            "profile": profile,
            "search_query": query,
            "result_count": len(timesheets),
        },
    )


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def attendance_export(request):
    qs = DailyTimesheet.objects.filter(tenant=request.user.tenant).select_related(
        "employee",
        "employee__department",
        "employee__job_position",
        "plant",
        "shift",
        "attendance_code",
    ).order_by("-work_date", "employee__employee_id")
    content = export_timesheets_csv(qs)
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="timesheet_export.csv"'
    return response


@login_required
def leave_list(request):
    qs = LeaveRequest.objects.filter(tenant=request.user.tenant).select_related(
        "employee", "leave_type"
    ).order_by("-created_at")
    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(employee__full_name__icontains=query)
            | Q(employee__employee_id__icontains=query)
            | Q(leave_type__code__icontains=query)
            | Q(leave_type__name__icontains=query)
            | Q(status__icontains=query)
            | Q(reason__icontains=query)
        )
    leave_requests = list(qs[:500])
    can_approve = request.user.role in {
        User.Role.ADMIN,
        User.Role.HR,
        User.Role.MANAGER,
    }
    profile = _employee_profile(request.user)
    return render(
        request,
        "web/leave/list.html",
        {
            "leave_requests": leave_requests,
            "can_approve": can_approve,
            "profile": profile,
            "search_query": query,
            "result_count": len(leave_requests),
        },
    )


@login_required
def leave_create(request):
    profile = _employee_profile(request.user)
    if not profile and request.user.role in {User.Role.EMPLOYEE, User.Role.MANAGER}:
        profile = ensure_employee_profile(request.user)

    show_employee_picker = request.user.is_hr
    can_submit = bool(profile or request.user.is_hr)

    form_kwargs = {
        "tenant": request.user.tenant,
        "user": request.user,
        "show_employee_picker": show_employee_picker,
        "profile": profile,
    }

    if request.method == "POST":
        if not can_submit:
            messages.error(
                request,
                "Akun belum terhubung ke data karyawan. Hubungi HR untuk menghubungkan akun Anda.",
            )
            return redirect("web:leave_list")

        form = LeaveRequestForm(request.POST, **form_kwargs)
        if form.is_valid():
            employee = form.cleaned_data["employee"]
            try:
                submit_leave_request(
                    employee=employee,
                    leave_type=form.cleaned_data["leave_type"],
                    start_date=form.cleaned_data["start_date"],
                    end_date=form.cleaned_data["end_date"],
                    reason=form.cleaned_data.get("reason", ""),
                    is_half_day=form.cleaned_data.get("is_half_day", False),
                )
                messages.success(request, "Pengajuan cuti berhasil dikirim.")
                return redirect("web:leave_list")
            except LeaveError as exc:
                messages.error(request, str(exc))
    else:
        form = LeaveRequestForm(**form_kwargs)

    ctx = _form_context(
        form,
        "Ajukan Cuti",
        cancel_url="/leave/",
        submit_label="Kirim Pengajuan",
    )
    leave_balances = employee_leave_balances_summary(profile) if profile else []
    ctx.update(
        {
            "profile": profile,
            "show_employee_picker": show_employee_picker,
            "can_submit": can_submit,
            "leave_balances": leave_balances,
        }
    )
    return render(request, "web/leave/form.html", ctx)


@login_required
@require_POST
def leave_cancel(request, pk):
    leave_req = get_object_or_404(LeaveRequest, pk=pk, tenant=request.user.tenant)
    profile = _employee_profile(request.user)
    if not (
        request.user.is_hr
        or (profile and profile.pk == leave_req.employee_id)
    ):
        messages.error(request, "Akses ditolak.")
        return redirect("web:leave_list")

    try:
        cancel_leave_request(leave_req, request.user)
        messages.success(request, "Pengajuan cuti dibatalkan.")
    except LeaveError as exc:
        messages.error(request, str(exc))
    return redirect("web:leave_list")


@login_required
@require_POST
@require_roles(User.Role.ADMIN, User.Role.HR, User.Role.MANAGER)
def leave_approve(request, pk):
    leave_req = get_object_or_404(LeaveRequest, pk=pk, tenant=request.user.tenant)
    try:
        approve_leave_request(leave_req, request.user)
        messages.success(request, "Cuti disetujui.")
    except LeaveError as exc:
        messages.error(request, str(exc))
    return redirect("web:leave_list")


@login_required
@require_POST
@require_roles(User.Role.ADMIN, User.Role.HR, User.Role.MANAGER)
def leave_reject(request, pk):
    leave_req = get_object_or_404(LeaveRequest, pk=pk, tenant=request.user.tenant)
    reason = request.POST.get("reason", "")
    try:
        reject_leave_request(leave_req, request.user, reason=reason)
        messages.success(request, "Cuti ditolak.")
    except LeaveError as exc:
        messages.error(request, str(exc))
    return redirect("web:leave_list")


@login_required
def overtime_list(request):
    qs = OvertimeRequest.objects.filter(tenant=request.user.tenant).select_related(
        "employee", "approver"
    ).order_by("-created_at")
    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(employee__full_name__icontains=query)
            | Q(employee__employee_id__icontains=query)
            | Q(status__icontains=query)
            | Q(reason__icontains=query)
        )
    overtime_requests = list(qs[:500])
    can_approve = request.user.role in {
        User.Role.ADMIN,
        User.Role.HR,
        User.Role.MANAGER,
    }
    profile = _employee_profile(request.user)
    return render(
        request,
        "web/overtime/list.html",
        {
            "overtime_requests": overtime_requests,
            "can_approve": can_approve,
            "profile": profile,
            "search_query": query,
            "result_count": len(overtime_requests),
        },
    )


@login_required
def overtime_create(request):
    profile = _employee_profile(request.user)
    if not profile and request.user.role in {User.Role.EMPLOYEE, User.Role.MANAGER}:
        profile = ensure_employee_profile(request.user)

    show_employee_picker = request.user.is_hr
    can_submit = bool(profile or request.user.is_hr)
    suggested_ot = None
    if profile:
        suggested_ot = get_raw_overtime_minutes(profile, timezone.localdate())

    form_kwargs = {
        "tenant": request.user.tenant,
        "user": request.user,
        "show_employee_picker": show_employee_picker,
        "profile": profile,
        "suggested_ot": suggested_ot,
    }

    if request.method == "POST":
        if not can_submit:
            messages.error(
                request,
                "Akun belum terhubung ke data karyawan. Hubungi HR untuk menghubungkan akun Anda.",
            )
            return redirect("web:overtime_list")

        form = OvertimeRequestForm(request.POST, **form_kwargs)
        if form.is_valid():
            employee = form.cleaned_data["employee"]
            try:
                submit_overtime_request(
                    employee=employee,
                    work_date=form.cleaned_data["work_date"],
                    ot_before_minutes=form.cleaned_data.get("ot_before_minutes") or 0,
                    ot_after_minutes=form.cleaned_data.get("ot_after_minutes") or 0,
                    reason=form.cleaned_data.get("reason", ""),
                )
                messages.success(request, "Pengajuan lembur berhasil dikirim.")
                return redirect("web:overtime_list")
            except OvertimeError as exc:
                messages.error(request, str(exc))
    else:
        form = OvertimeRequestForm(**form_kwargs)

    ctx = _form_context(
        form,
        "Ajukan Lembur",
        cancel_url="/overtime/",
        submit_label="Kirim Pengajuan",
    )
    ctx.update(
        {
            "profile": profile,
            "show_employee_picker": show_employee_picker,
            "can_submit": can_submit,
            "suggested_ot": suggested_ot,
        }
    )
    return render(request, "web/overtime/form.html", ctx)


@login_required
@require_POST
def overtime_cancel(request, pk):
    overtime_req = get_object_or_404(OvertimeRequest, pk=pk, tenant=request.user.tenant)
    profile = _employee_profile(request.user)
    if not (
        request.user.is_hr
        or (profile and profile.pk == overtime_req.employee_id)
    ):
        messages.error(request, "Akses ditolak.")
        return redirect("web:overtime_list")

    try:
        cancel_overtime_request(overtime_req, request.user)
        messages.success(request, "Pengajuan lembur dibatalkan.")
    except OvertimeError as exc:
        messages.error(request, str(exc))
    return redirect("web:overtime_list")


@login_required
@require_POST
@require_roles(User.Role.ADMIN, User.Role.HR, User.Role.MANAGER)
def overtime_approve(request, pk):
    overtime_req = get_object_or_404(OvertimeRequest, pk=pk, tenant=request.user.tenant)
    try:
        approve_overtime_request(overtime_req, request.user)
        messages.success(request, "Lembur disetujui.")
    except OvertimeError as exc:
        messages.error(request, str(exc))
    return redirect("web:overtime_list")


@login_required
@require_POST
@require_roles(User.Role.ADMIN, User.Role.HR, User.Role.MANAGER)
def overtime_reject(request, pk):
    overtime_req = get_object_or_404(OvertimeRequest, pk=pk, tenant=request.user.tenant)
    reason = request.POST.get("reason", "")
    try:
        reject_overtime_request(overtime_req, request.user, reason=reason)
        messages.success(request, "Lembur ditolak.")
    except OvertimeError as exc:
        messages.error(request, str(exc))
    return redirect("web:overtime_list")


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def payroll_list(request):
    qs = PayrollRun.objects.filter(tenant=request.user.tenant).select_related("plant").order_by(
        "-period_end"
    )
    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(plant__code__icontains=query)
            | Q(plant__name__icontains=query)
            | Q(status__icontains=query)
            | Q(notes__icontains=query)
        )
    payroll_runs = list(qs[:500])
    return render(
        request,
        "web/payroll/list.html",
        {
            "payroll_runs": payroll_runs,
            "search_query": query,
            "result_count": len(payroll_runs),
        },
    )


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def payroll_create(request):
    if request.method == "POST":
        form = PayrollRunForm(request.POST, tenant=request.user.tenant, user=request.user)
        if form.is_valid():
            try:
                run = form.save(commit=False)
                run.tenant = request.user.tenant
                run.save()
                messages.success(request, "Payroll run dibuat.")
                return redirect("web:payroll_detail", pk=run.pk)
            except Exception as exc:
                messages.error(request, f"Gagal membuat payroll: {exc}")
    else:
        today = timezone.localdate()
        form = PayrollRunForm(
            initial={
                "plant": request.user.plant,
                "period_start": today.replace(day=1),
                "period_end": today,
            },
            tenant=request.user.tenant,
            user=request.user,
        )
    ctx = _form_context(form, "Buat Payroll Run", cancel_url="/payroll/")
    return render(request, "web/payroll/form.html", ctx)


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def payroll_edit(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk, tenant=request.user.tenant)
    if run.status != PayrollRun.Status.DRAFT:
        messages.error(request, "Hanya payroll draft yang bisa diedit.")
        return redirect("web:payroll_detail", pk=pk)

    if request.method == "POST":
        form = PayrollRunForm(
            request.POST,
            instance=run,
            tenant=request.user.tenant,
            user=request.user,
        )
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Payroll run diperbarui.")
                return redirect("web:payroll_detail", pk=pk)
            except Exception as exc:
                messages.error(request, f"Gagal memperbarui payroll: {exc}")
    else:
        form = PayrollRunForm(instance=run, tenant=request.user.tenant, user=request.user)

    ctx = _form_context(
        form,
        "Edit Payroll Run",
        cancel_url=f"/payroll/{pk}/",
        subtitle=f"{run.plant.code} · {run.period_start} — {run.period_end}",
    )
    return render(request, "web/payroll/form.html", ctx)


@login_required
@require_POST
@require_roles(User.Role.ADMIN, User.Role.HR)
def payroll_cancel(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk, tenant=request.user.tenant)
    if run.status == PayrollRun.Status.FINALIZED:
        messages.error(request, "Payroll finalized tidak bisa dibatalkan.")
        return redirect("web:payroll_detail", pk=pk)

    run.status = PayrollRun.Status.CANCELLED
    run.save(update_fields=["status", "updated_at"])
    messages.success(request, "Payroll run dibatalkan.")
    return redirect("web:payroll_list")


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def payroll_detail(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk, tenant=request.user.tenant)
    qs = Payslip.objects.filter(payroll_run=run).select_related("employee")
    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(employee__full_name__icontains=query)
            | Q(employee__employee_id__icontains=query)
        )
    payslips = list(qs)
    return render(
        request,
        "web/payroll/detail.html",
        {
            "payroll_run": run,
            "payslips": payslips,
            "search_query": query,
            "result_count": len(payslips),
        },
    )


@login_required
@require_POST
@require_roles(User.Role.ADMIN, User.Role.HR)
def payroll_calculate(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk, tenant=request.user.tenant)
    try:
        calculate_payroll_run(run)
        messages.success(request, "Payroll berhasil dihitung.")
    except PayrollError as exc:
        messages.error(request, str(exc))
    return redirect("web:payroll_detail", pk=pk)


@login_required
@require_POST
@require_roles(User.Role.ADMIN, User.Role.HR)
def payroll_finalize(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk, tenant=request.user.tenant)
    try:
        finalize_payroll_run(run)
        messages.success(request, "Payroll difinalize.")
    except PayrollError as exc:
        messages.error(request, str(exc))
    return redirect("web:payroll_detail", pk=pk)


@login_required
def payslip_list(request):
    profile = _employee_profile(request.user)
    if request.user.is_hr or request.user.is_admin:
        qs = Payslip.objects.filter(tenant=request.user.tenant).select_related(
            "employee", "payroll_run"
        ).order_by("-payroll_run__period_end")
    elif profile:
        qs = Payslip.objects.filter(employee=profile).select_related("payroll_run").order_by(
            "-payroll_run__period_end"
        )
    else:
        qs = Payslip.objects.none()

    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(employee__full_name__icontains=query)
            | Q(employee__employee_id__icontains=query)
            | Q(verification_hash__icontains=query)
            | Q(payroll_run__plant__code__icontains=query)
        )

    payslips = list(qs[:500])
    return render(
        request,
        "web/payroll/payslips.html",
        {
            "payslips": payslips,
            "search_query": query,
            "result_count": len(payslips),
        },
    )


@login_required
def payslip_download(request, pk):
    payslip = get_object_or_404(Payslip, pk=pk, tenant=request.user.tenant)
    profile = _employee_profile(request.user)
    if not (request.user.is_hr or request.user.is_admin) and (
        not profile or profile.id != payslip.employee_id
    ):
        messages.error(request, "Akses ditolak.")
        return redirect("web:payslip_list")

    if payslip.pdf_file:
        response = HttpResponse(payslip.pdf_file.read(), content_type="application/pdf")
    else:
        pdf_bytes = generate_payslip_pdf(payslip)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")

    filename = f"slip_{payslip.employee.employee_id}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def payroll_bank_export(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk, tenant=request.user.tenant)
    if run.status != PayrollRun.Status.FINALIZED:
        messages.error(request, "Payroll harus finalized sebelum export bank.")
        return redirect("web:payroll_detail", pk=pk)
    content = export_bank_csv(run)
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="bank_export_{run.plant.code}_{run.period_end}.csv"'
    return response


@login_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user).order_by("-created_at")
    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(message__icontains=query)
            | Q(category__icontains=query)
        )
    notifications = list(qs[:500])
    return render(
        request,
        "web/notifications/list.html",
        {
            "notifications": notifications,
            "search_query": query,
            "result_count": len(notifications),
        },
    )


@login_required
@require_POST
def notification_mark_read(request, pk):
    mark_notifications_read(request.user, [pk])
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    return redirect(next_url)


@login_required
@require_POST
def notification_mark_all_read(request):
    mark_notifications_read(request.user)
    return redirect("web:notification_list")


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def audit_log_list(request):
    qs = AuditLog.objects.filter(tenant=request.user.tenant).select_related("user").order_by(
        "-created_at"
    )
    model_name = request.GET.get("model", "").strip()
    if model_name:
        qs = qs.filter(model_name__icontains=model_name)

    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(model_name__icontains=query)
            | Q(object_repr__icontains=query)
            | Q(changes__icontains=query)
            | Q(action__icontains=query)
            | Q(user__username__icontains=query)
        )

    audit_logs = list(qs[:500])
    return render(
        request,
        "web/audit/list.html",
        {
            "audit_logs": audit_logs,
            "model_filter": model_name,
            "search_query": query,
            "result_count": len(audit_logs),
        },
    )
