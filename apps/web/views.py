from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.attendance.models import DailyTimesheet
from apps.attendance.models import AttendanceRecord
from apps.attendance.models import OvertimeRequest
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
from apps.core.services.announcements import (
    announcements_for_user,
    dismiss_announcement,
    get_announcement_for_user,
    increment_announcement_views,
)
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
from apps.web.services.leave_form import build_leave_balance_context
from apps.employees.services.profile import build_employee_profile_context
from apps.payroll.models import PayrollRun, Payslip
from apps.employees.services.user_link import ensure_employee_profile
from apps.employees.services.import_csv import import_employees_csv, template_csv
from apps.employees.services.onboarding import provision_new_employee, sync_employee_default_shift
from apps.attendance.services.import_punches import (
    PunchImportError,
    import_attendance_csv,
    template_csv as attendance_import_template_csv,
)
from apps.payroll.services.bank_export import export_bank_csv
from apps.payroll.services.compliance_export import export_bpjs_csv, export_pph21_csv
from apps.payroll.services.payslip_pdf import generate_payslip_pdf
from apps.payroll.services.payroll_run import PayrollError, calculate_payroll_run, finalize_payroll_run
from apps.payroll.services.payroll_validation import PayrollValidationError, validate_payroll_against_csv
from apps.attendance.services.overtime_compensation import build_compensation_preview
from apps.shifts.models import ShiftAssignment
from apps.web.services.dashboard import build_dashboard_context
from apps.web.services.list_exports import (
    export_attendance_csv,
    export_audit_csv,
    export_employees_csv,
    export_leave_csv,
    export_notifications_csv,
    export_overtime_csv,
    export_payroll_runs_csv,
    export_payslips_csv,
    export_shifts_csv,
)
from apps.web.services.list_querysets import (
    attach_attendance_records,
    audit_log_queryset,
    attendance_list_queryset,
    employee_list_queryset,
    leave_list_queryset,
    leave_history_queryset,
    notification_list_queryset,
    overtime_list_queryset,
    overtime_history_queryset,
    payroll_detail_payslip_queryset,
    payroll_list_queryset,
    payslip_list_queryset,
    shift_assignment_queryset,
)
from apps.payroll.services.salary_preview import build_salary_preview
from apps.payroll.services.ter import seed_ter_master
from apps.web.services.listing import resolve_list
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

    dashboard_ctx = build_dashboard_context(
        user=user,
        tenant=tenant,
        today=today,
        profile=profile,
    )

    return render(
        request,
        "web/dashboard.html",
        {
            "stats": stats,
            "punch_ui": punch_ui,
            "profile": profile,
            "today_record": today_record,
            "today": today,
            **dashboard_ctx,
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
def employee_profile(request):
    profile = _employee_profile(request.user)
    if not profile and request.user.role in {User.Role.EMPLOYEE, User.Role.MANAGER}:
        profile = ensure_employee_profile(request.user)

    if not profile:
        return render(
            request,
            "web/employees/profile.html",
            {"missing_profile": True},
        )

    ctx = build_employee_profile_context(profile)
    ctx["missing_profile"] = False
    return render(request, "web/employees/profile.html", ctx)


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def employee_list(request):
    from apps.core.listing import parse_list_filters

    filters = parse_list_filters(request)
    qs = employee_list_queryset(request.user, filters)
    response, ctx = resolve_list(
        request,
        qs,
        export_filename="employees_export.csv",
        export_fn=export_employees_csv,
    )
    if response:
        return response
    return render(
        request,
        "web/employees/list.html",
        {**ctx, "employees": list(ctx["page_obj"].object_list)},
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
            sync_employee_default_shift(employee)
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
            sync_employee_default_shift(updated)
            messages.success(request, "Data karyawan berhasil diperbarui.")
            return redirect("web:employee_list")
    else:
        form = EmployeeForm(instance=employee, tenant=request.user.tenant, user=request.user)

    seed_ter_master(request.user.tenant)
    ctx = _form_context(
        form,
        f"Edit — {employee.full_name}",
        cancel_url="/employees/",
        subtitle=employee.employee_id,
    )
    ctx["salary_preview"] = build_salary_preview(employee, tenant=request.user.tenant)
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
    from apps.core.listing import parse_list_filters

    filters = parse_list_filters(request)
    qs = shift_assignment_queryset(request.user, filters)
    response, ctx = resolve_list(
        request,
        qs,
        export_filename="shift_assignments_export.csv",
        export_fn=export_shifts_csv,
    )
    if response:
        return response
    return render(
        request,
        "web/shifts/list.html",
        {**ctx, "assignments": list(ctx["page_obj"].object_list)},
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

            assignment = form.save(commit=False)
            assignment.tenant = request.user.tenant
            assignment.save()
            recalculate_daily_timesheet(assignment.employee, assignment.work_date)
            created = instance is None
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
    from apps.core.listing import parse_list_filters

    profile = _employee_profile(request.user)
    filters = parse_list_filters(request)
    qs = attendance_list_queryset(request.user, filters)
    export_qs = qs.select_related(
        "employee",
        "employee__department",
        "employee__job_position",
        "plant",
        "shift",
        "attendance_code",
    )
    response, ctx = resolve_list(
        request,
        export_qs,
        export_filename="timesheet_export.csv",
        export_fn=export_attendance_csv,
    )
    if response:
        return response
    timesheets = list(ctx["page_obj"].object_list)
    record_map = attach_attendance_records(timesheets, request.user.tenant)
    return render(
        request,
        "web/attendance/list.html",
        {
            **ctx,
            "timesheets": timesheets,
            "record_map": record_map,
            "profile": profile,
        },
    )


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def attendance_export(request):
    """Backward-compatible export URL — preserves active list filters."""
    from django.urls import reverse
    from apps.core.listing import build_filter_query

    query = build_filter_query(request)
    suffix = f"{query}&export=csv" if query else "export=csv"
    return redirect(f"{reverse('web:attendance_list')}?{suffix}")


@login_required
def leave_list(request):
    from apps.core.listing import parse_list_filters

    filters = parse_list_filters(request)
    qs = leave_list_queryset(request.user, filters)
    response, ctx = resolve_list(
        request,
        qs,
        export_filename="leave_requests_export.csv",
        export_fn=export_leave_csv,
    )
    if response:
        return response
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
            **ctx,
            "leave_requests": list(ctx["page_obj"].object_list),
            "can_approve": can_approve,
            "profile": profile,
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
    ctx.update(
        {
            "profile": profile,
            "show_employee_picker": show_employee_picker,
            "can_submit": can_submit,
            "leave_history": leave_history_queryset(request.user),
            "show_history_employee": request.user.is_hr
            or request.user.role == User.Role.MANAGER,
            **build_leave_balance_context(
                profile=profile,
                show_employee_picker=show_employee_picker,
                form=form,
            ),
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
    from apps.core.listing import parse_list_filters

    filters = parse_list_filters(request)
    qs = overtime_list_queryset(request.user, filters)
    response, ctx = resolve_list(
        request,
        qs,
        export_filename="overtime_requests_export.csv",
        export_fn=export_overtime_csv,
    )
    if response:
        return response
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
            **ctx,
            "overtime_requests": list(ctx["page_obj"].object_list),
            "can_approve": can_approve,
            "profile": profile,
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
                    overtime_type=form.cleaned_data["overtime_type"],
                    ot_before_minutes=form.cleaned_data.get("ot_before_minutes") or 0,
                    ot_after_minutes=form.cleaned_data.get("ot_after_minutes") or 0,
                    compensation_mode=form.cleaned_data.get(
                        "compensation_mode",
                        OvertimeRequest.CompensationMode.CASH,
                    ),
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
    preview_employee = profile
    if form.is_bound:
        preview_employee = form.cleaned_data.get("employee") if form.is_valid() else None
        if not preview_employee:
            raw_employee = form.data.get("employee")
            preview_employee = (
                Employee.objects.select_related("default_shift").filter(pk=raw_employee).first()
                if raw_employee
                else profile
            )
    if show_employee_picker and preview_employee is None and form.fields.get("employee"):
        first_option = form.fields["employee"].queryset.first()
        preview_employee = first_option or profile

    def _preview_int(field_name, default=0):
        if form.is_valid():
            return form.cleaned_data.get(field_name) or default
        raw = form.data.get(field_name)
        try:
            return int(raw) if raw not in (None, "") else default
        except (TypeError, ValueError):
            return default

    preview_type = None
    if form.is_valid():
        preview_type = form.cleaned_data.get("overtime_type")
    elif form.data.get("overtime_type"):
        from apps.attendance.models import OvertimeType

        preview_type = OvertimeType.objects.filter(pk=form.data.get("overtime_type")).first()

    compensation_preview = None
    if preview_employee:
        compensation_preview = build_compensation_preview(
            preview_employee,
            ot_before_minutes=_preview_int("ot_before_minutes", suggested_ot[0] if suggested_ot else 0),
            ot_after_minutes=_preview_int("ot_after_minutes", suggested_ot[1] if suggested_ot else 0),
            overtime_type=preview_type,
        )

    ctx.update(
        {
            "profile": profile,
            "show_employee_picker": show_employee_picker,
            "can_submit": can_submit,
            "suggested_ot": suggested_ot,
            "compensation_preview": compensation_preview,
            "overtime_history": overtime_history_queryset(request.user),
            "show_history_employee": request.user.is_hr
            or request.user.role == User.Role.MANAGER,
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
    from apps.core.listing import parse_list_filters

    filters = parse_list_filters(request)
    qs = payroll_list_queryset(request.user, filters)
    response, ctx = resolve_list(
        request,
        qs,
        export_filename="payroll_runs_export.csv",
        export_fn=export_payroll_runs_csv,
    )
    if response:
        return response
    return render(
        request,
        "web/payroll/list.html",
        {**ctx, "payroll_runs": list(ctx["page_obj"].object_list)},
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
    from apps.core.listing import parse_list_filters

    run = get_object_or_404(PayrollRun, pk=pk, tenant=request.user.tenant)
    filters = parse_list_filters(request)
    qs = payroll_detail_payslip_queryset(run, filters)
    response, ctx = resolve_list(
        request,
        qs,
        export_filename=f"payslips_{run.plant.code}_{run.period_end}.csv",
        export_fn=export_payslips_csv,
    )
    if response:
        return response
    return render(
        request,
        "web/payroll/detail.html",
        {
            **ctx,
            "payroll_run": run,
            "payslips": list(ctx["page_obj"].object_list),
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
    from apps.core.listing import parse_list_filters

    filters = parse_list_filters(request)
    qs = payslip_list_queryset(request.user, filters)
    response, ctx = resolve_list(
        request,
        qs,
        export_filename="payslips_export.csv",
        export_fn=export_payslips_csv,
    )
    if response:
        return response
    return render(
        request,
        "web/payroll/payslips.html",
        {**ctx, "payslips": list(ctx["page_obj"].object_list)},
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
@require_roles(User.Role.ADMIN, User.Role.HR)
def payroll_bpjs_export(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk, tenant=request.user.tenant)
    content = export_bpjs_csv(run)
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="bpjs_{run.plant.code}_{run.period_end}.csv"'
    return response


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def payroll_pph21_export(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk, tenant=request.user.tenant)
    content = export_pph21_csv(run)
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="pph21_{run.plant.code}_{run.period_end}.csv"'
    return response


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def payroll_validate(request, pk):
    run = get_object_or_404(PayrollRun, pk=pk, tenant=request.user.tenant)
    result = None
    if request.method == "POST":
        upload = request.FILES.get("file")
        if not upload:
            messages.error(request, "Pilih file CSV terlebih dahulu.")
        else:
            try:
                result = validate_payroll_against_csv(run, upload.read().decode("utf-8-sig"))
                if result["ok"]:
                    messages.success(request, f"Validasi OK — {result['matched']} karyawan cocok.")
                else:
                    messages.warning(
                        request,
                        f"Ada selisih: {len(result['mismatches'])} mismatch, "
                        f"{len(result['missing_in_system'])} tidak ada di sistem.",
                    )
            except PayrollValidationError as exc:
                messages.error(request, str(exc))
    return render(
        request,
        "web/payroll/validate.html",
        {"payroll_run": run, "result": result},
    )


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def attendance_import_template(request):
    response = HttpResponse(attendance_import_template_csv(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="attendance_import_template.csv"'
    return response


@login_required
@require_roles(User.Role.ADMIN, User.Role.HR)
def attendance_import(request):
    if request.method == "POST":
        upload = request.FILES.get("file")
        if not upload:
            messages.error(request, "Pilih file CSV terlebih dahulu.")
        else:
            try:
                result = import_attendance_csv(
                    request.user.tenant,
                    upload.read().decode("utf-8-sig"),
                    plant=request.user.plant if not request.user.is_admin else None,
                )
                messages.success(
                    request,
                    f"Import absensi: {result['created']} baru, {result['updated']} diupdate.",
                )
                if result["errors"]:
                    for err in result["errors"][:5]:
                        messages.error(request, err)
            except PunchImportError as exc:
                messages.error(request, str(exc))
        return redirect("web:attendance_list")
    return render(request, "web/attendance/import.html")


@login_required
def notification_list(request):
    from apps.core.listing import parse_list_filters

    filters = parse_list_filters(request)
    qs = notification_list_queryset(request.user, filters)
    response, ctx = resolve_list(
        request,
        qs,
        export_filename="notifications_export.csv",
        export_fn=export_notifications_csv,
    )
    if response:
        return response
    return render(
        request,
        "web/notifications/list.html",
        {**ctx, "notifications": list(ctx["page_obj"].object_list)},
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
    from django.conf import settings

    from apps.core.listing import parse_list_filters

    default_days = getattr(settings, "HRIS_AUDIT_LIST_DEFAULT_DAYS", 90)
    filters = parse_list_filters(request)
    qs = audit_log_queryset(request.user, filters, default_days=default_days)

    model_name = request.GET.get("model", "").strip()
    if model_name:
        qs = qs.filter(model_name__icontains=model_name)
    if filters.q:
        qs = qs.filter(
            Q(model_name__icontains=filters.q)
            | Q(object_repr__icontains=filters.q)
            | Q(changes__icontains=filters.q)
            | Q(action__icontains=filters.q)
            | Q(user__username__icontains=filters.q)
        )

    response, ctx = resolve_list(
        request,
        qs,
        export_filename="audit_log_export.csv",
        export_fn=export_audit_csv,
    )
    if response:
        return response
    return render(
        request,
        "web/audit/list.html",
        {
            **ctx,
            "audit_logs": list(ctx["page_obj"].object_list),
            "model_filter": model_name,
            "default_days": default_days,
            "extra_filter_active": bool(model_name),
        },
    )


@login_required
def announcement_list(request):
    announcements = announcements_for_user(request.user)
    return render(
        request,
        "web/announcements/list.html",
        {
            "announcements": announcements,
            "result_count": len(announcements),
        },
    )


@login_required
def announcement_detail(request, pk):
    announcement = get_announcement_for_user(request.user, pk)
    if not announcement:
        messages.error(request, "Pengumuman tidak ditemukan atau tidak tersedia untuk Anda.")
        return redirect("web:announcement_list")

    increment_announcement_views(announcement)
    announcement.refresh_from_db(fields=["view_count"])
    return render(
        request,
        "web/announcements/detail.html",
        {"announcement": announcement},
    )


@login_required
@require_POST
def announcement_dismiss(request, pk):
    announcement = get_announcement_for_user(request.user, pk)
    if not announcement:
        messages.error(request, "Pengumuman tidak ditemukan.")
        return redirect(request.META.get("HTTP_REFERER") or reverse("web:dashboard"))

    dismiss_announcement(request.user, announcement)
    messages.success(request, "Pengumuman ditutup.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("web:dashboard"))
