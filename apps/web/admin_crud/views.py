from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.decorators import require_admin, require_master_data
from apps.web.admin_crud.queryset import get_cell_value, get_queryset, save_instance
from apps.web.admin_crud.registry import (
    ensure_bootstrapped,
    get_resource,
    resources_by_app,
    resources_master_data,
)
from apps.core.listing import parse_list_filters
from apps.web.services.list_exports import export_admin_resource_csv
from apps.web.services.listing import resolve_list
from apps.web.views import _form_context

ensure_bootstrapped()


def _get_resource_or_404(slug, *, scope="manage"):
    resource = get_resource(slug)
    if not resource:
        from django.http import Http404

        raise Http404("Modul tidak ditemukan.")
    if scope == "master" and not resource.master_data:
        from django.http import Http404

        raise Http404("Modul master data tidak ditemukan.")
    if scope == "manage" and resource.master_data:
        from django.http import Http404

        raise Http404("Modul ini tersedia di Master Data.")
    return resource


def _crud_url_names(scope):
    if scope == "master":
        return {
            "hub": "web:master_hub",
            "list": "web:master_list",
            "create": "web:master_create",
            "edit": "web:master_edit",
            "delete": "web:master_delete",
        }
    return {
        "hub": "web:manage_hub",
        "list": "web:manage_list",
        "create": "web:manage_create",
        "edit": "web:manage_edit",
        "delete": "web:manage_delete",
    }


def _crud_context(scope, slug):
    url_names = _crud_url_names(scope)
    prefix = "/master/" if scope == "master" else "/manage/"
    return {
        "crud_scope": scope,
        "crud_url_names": url_names,
        "crud_hub_url": reverse(url_names["hub"]),
        "crud_list_url": reverse(url_names["list"], kwargs={"slug": slug}),
        "crud_prefix": prefix,
    }


def _resource_list(request, slug, *, scope="manage"):
    resource = _get_resource_or_404(slug, scope=scope)
    filters = parse_list_filters(request)
    qs = get_queryset(request, resource, filters)
    export_name = f"{resource.slug}_export.xlsx"
    response, list_ctx = resolve_list(
        request,
        qs,
        export_filename=export_name,
        export_fn=lambda queryset: export_admin_resource_csv(resource, queryset),
    )
    if response:
        return response

    rows = []
    for obj in list_ctx["page_obj"].object_list:
        rows.append(
            {
                "obj": obj,
                "cells": [get_cell_value(obj, col.attr) for col in resource.columns],
            }
        )
    ctx = _crud_context(scope, slug)
    ctx.update(list_ctx)
    ctx.update(
        {
            "resource": resource,
            "rows": rows,
        }
    )
    template = "web/master/list.html" if scope == "master" else "web/manage/list.html"
    return render(request, template, ctx)


def _resource_create(request, slug, *, scope="manage"):
    resource = _get_resource_or_404(slug, scope=scope)
    url_names = _crud_url_names(scope)
    if not resource.allow_create:
        messages.error(request, "Create tidak diizinkan untuk modul ini.")
        return redirect(url_names["list"], slug=slug)

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
            return redirect(url_names["list"], slug=slug)
    else:
        form = resource.form_class(tenant=request.user.tenant, user=request.user)

    ctx = _form_context(
        form,
        f"Tambah {resource.title}",
        cancel_url=reverse(url_names["list"], kwargs={"slug": slug}),
        submit_label="Simpan",
    )
    return render(request, "web/employees/form.html", ctx)


def _resource_edit(request, slug, pk, *, scope="manage"):
    resource = _get_resource_or_404(slug, scope=scope)
    url_names = _crud_url_names(scope)
    if not resource.allow_edit:
        messages.error(request, "Edit tidak diizinkan untuk modul ini.")
        return redirect(url_names["list"], slug=slug)

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
            return redirect(url_names["list"], slug=slug)
    else:
        form = resource.form_class(
            instance=obj,
            tenant=request.user.tenant,
            user=request.user,
        )

    ctx = _form_context(
        form,
        f"Edit {resource.title}",
        cancel_url=reverse(url_names["list"], kwargs={"slug": slug}),
        subtitle=str(obj),
        submit_label="Simpan Perubahan",
    )
    return render(request, "web/employees/form.html", ctx)


def _resource_delete(request, slug, pk, *, scope="manage"):
    resource = _get_resource_or_404(slug, scope=scope)
    url_names = _crud_url_names(scope)
    if not resource.allow_delete:
        messages.error(request, "Delete tidak diizinkan untuk modul ini.")
        return redirect(url_names["list"], slug=slug)

    qs = get_queryset(request, resource)
    obj = get_object_or_404(qs, pk=pk)
    label = str(obj)
    try:
        obj.delete()
    except ProtectedError:
        messages.error(
            request,
            f"Tidak dapat menghapus «{label}»: masih ada data terkait yang belum bisa "
            "diputus. Hubungi administrator jika masalah berlanjut.",
        )
        return redirect(url_names["list"], slug=slug)
    messages.success(request, f"{resource.title} «{label}» berhasil dihapus.")
    return redirect(url_names["list"], slug=slug)


@login_required
@require_admin
def manage_hub(request):
    return render(
        request,
        "web/manage/index.html",
        {"sections": dict(resources_by_app(exclude_master=True))},
    )


@login_required
@require_admin
def resource_list(request, slug):
    return _resource_list(request, slug, scope="manage")


@login_required
@require_admin
def resource_create(request, slug):
    return _resource_create(request, slug, scope="manage")


@login_required
@require_admin
def resource_edit(request, slug, pk):
    return _resource_edit(request, slug, pk, scope="manage")


@login_required
@require_admin
@require_POST
def resource_delete(request, slug, pk):
    return _resource_delete(request, slug, pk, scope="manage")


@login_required
@require_master_data
def master_hub(request):
    return render(
        request,
        "web/master/index.html",
        {"sections": dict(resources_master_data())},
    )


@login_required
@require_master_data
def master_resource_list(request, slug):
    return _resource_list(request, slug, scope="master")


@login_required
@require_master_data
def master_resource_create(request, slug):
    return _resource_create(request, slug, scope="master")


@login_required
@require_master_data
def master_resource_edit(request, slug, pk):
    return _resource_edit(request, slug, pk, scope="master")


@login_required
@require_master_data
@require_POST
def master_resource_delete(request, slug, pk):
    return _resource_delete(request, slug, pk, scope="master")
