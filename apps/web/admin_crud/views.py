from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.decorators import require_admin
from apps.web.admin_crud.queryset import get_cell_value, get_queryset, save_instance
from apps.web.admin_crud.registry import (
    ensure_bootstrapped,
    get_resource,
    resources_by_app,
    resources_by_section,
)
from apps.web.views import _form_context

ensure_bootstrapped()


def _get_resource_or_404(slug):
    resource = get_resource(slug)
    if not resource:
        from django.http import Http404

        raise Http404("Modul admin tidak ditemukan.")
    return resource


@login_required
@require_admin
def manage_hub(request):
    return render(
        request,
        "web/manage/index.html",
        {"sections": dict(resources_by_app())},
    )


@login_required
@require_admin
def resource_list(request, slug):
    resource = _get_resource_or_404(slug)
    qs = get_queryset(request, resource)
    objects = list(qs[: resource.list_limit])
    rows = []
    for obj in objects:
        rows.append(
            {
                "obj": obj,
                "cells": [get_cell_value(obj, col.attr) for col in resource.columns],
            }
        )
    return render(
        request,
        "web/manage/list.html",
        {
            "resource": resource,
            "rows": rows,
            "search_query": request.GET.get("q", ""),
        },
    )


@login_required
@require_admin
def resource_create(request, slug):
    resource = _get_resource_or_404(slug)
    if not resource.allow_create:
        messages.error(request, "Create tidak diizinkan untuk modul ini.")
        return redirect("web:manage_list", slug=slug)

    if request.method == "POST":
        form = resource.form_class(
            request.POST,
            request.FILES,
            tenant=request.user.tenant,
            user=request.user,
        )
        if form.is_valid():
            save_instance(form, request, resource)
            messages.success(request, f"{resource.title} berhasil ditambahkan.")
            return redirect("web:manage_list", slug=slug)
    else:
        form = resource.form_class(tenant=request.user.tenant, user=request.user)

    ctx = _form_context(
        form,
        f"Tambah {resource.title}",
        cancel_url=f"/manage/{slug}/",
        submit_label="Simpan",
    )
    return render(request, "web/employees/form.html", ctx)


@login_required
@require_admin
def resource_edit(request, slug, pk):
    resource = _get_resource_or_404(slug)
    if not resource.allow_edit:
        messages.error(request, "Edit tidak diizinkan untuk modul ini.")
        return redirect("web:manage_list", slug=slug)

    qs = get_queryset(request, resource)
    obj = get_object_or_404(qs, pk=pk)

    if request.method == "POST":
        form = resource.form_class(
            request.POST,
            request.FILES,
            instance=obj,
            tenant=request.user.tenant,
            user=request.user,
        )
        if form.is_valid():
            save_instance(form, request, resource)
            messages.success(request, f"{resource.title} berhasil diperbarui.")
            return redirect("web:manage_list", slug=slug)
    else:
        form = resource.form_class(
            instance=obj,
            tenant=request.user.tenant,
            user=request.user,
        )

    ctx = _form_context(
        form,
        f"Edit {resource.title}",
        cancel_url=f"/manage/{slug}/",
        subtitle=str(obj),
        submit_label="Simpan Perubahan",
    )
    return render(request, "web/employees/form.html", ctx)


@login_required
@require_admin
@require_POST
def resource_delete(request, slug, pk):
    resource = _get_resource_or_404(slug)
    if not resource.allow_delete:
        messages.error(request, "Delete tidak diizinkan untuk modul ini.")
        return redirect("web:manage_list", slug=slug)

    qs = get_queryset(request, resource)
    obj = get_object_or_404(qs, pk=pk)
    label = str(obj)
    obj.delete()
    messages.success(request, f"{resource.title} «{label}» berhasil dihapus.")
    return redirect("web:manage_list", slug=slug)
