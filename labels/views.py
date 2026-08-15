from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from common.http import is_partial_request
from tasks.models import Task
from tasks.selectors import get_tasks_by_label

from .forms import LabelForm, LABEL_COLORS
from .models import Label
from .selectors import LabelSelector
from .services import LabelService


@require_http_methods(["GET"])
def label_list_view(request):
    selector = LabelSelector(user=request.user)
    labels = selector.get_labels()
    context = {
        "labels": labels,
        "page_title": "Manage Labels",
    }
    if is_partial_request(request):
        return render(request, "labels/partials/_label_list.html", context)
    return render(request, "labels/label_list.html", context)


@require_http_methods(["GET", "POST"])
def label_detail_view(request, pk):
    """
    Renders a single label in read-only "view" mode by default.

    Passing ``?mode=edit`` (or submitting the edit form via POST) switches the
    same layout into editable form mode. Successful updates drop back to view
    mode, mirroring the task detail page.
    """
    selector = LabelSelector(user=request.user)
    try:
        label = selector.get_label(pk=pk)
    except Label.DoesNotExist:
        messages.error(request, "No label associated with this id.")
        if request.htmx:
            response = HttpResponse()
            response["HX-Location"] = (
                '{"path": "' + reverse("label_list") + '", "target": "#main-content"}'
            )
            return response
        raise Http404

    editing = request.method == "POST" or request.GET.get("mode") == "edit"

    if request.method == "POST":
        form = LabelForm(request.POST, instance=label)
        if form.is_valid():
            service = LabelService(user=request.user)
            label = service.update_label(
                pk=pk,
                name=form.cleaned_data["name"],
                color=form.cleaned_data["color"],
            )
            messages.success(request, "Label updated successfully")
            editing = False
            form = LabelForm(instance=label)
    else:
        form = LabelForm(instance=label)

    context = {
        "label": label,
        "form": form,
        "editing": editing,
        "label_colors": LABEL_COLORS,
        "label_tasks": get_tasks_by_label(user=request.user, label_id=pk)[:5],
        "Status": Task.Status,
        "Priority": Task.Priority,
    }
    if is_partial_request(request):
        return render(request, "labels/partials/_label_detail.html", context)
    return render(request, "labels/label_detail.html", context)


@require_http_methods(["GET", "POST"])
def label_create_view(request):
    if request.method == "POST":
        form = LabelForm(request.POST)
        if form.is_valid():
            service = LabelService(user=request.user)
            service.create_label(
                name=form.cleaned_data["name"],
                color=form.cleaned_data["color"],
            )
            messages.success(request, "Label created successfully")
            if request.htmx:
                response = HttpResponse()
                response["HX-Location"] = (
                    '{"path": "'
                    + reverse("label_list")
                    + '", "target": "#main-content"}'
                )
                return response
            return HttpResponseRedirect(reverse("label_list"))
    else:
        form = LabelForm()

    context = {
        "form": form,
        "page_title": "Create Label",
        "label_colors": LABEL_COLORS,
    }
    if is_partial_request(request):
        return render(request, "labels/label_form_partial.html", context)
    return render(request, "labels/label_form.html", context)


@require_http_methods(["GET", "POST"])
def label_update_view(request, pk):
    selector = LabelSelector(user=request.user)
    label = selector.get_label(pk=pk)

    if request.method == "POST":
        form = LabelForm(request.POST, instance=label)
        if form.is_valid():
            service = LabelService(user=request.user)
            service.update_label(
                pk=pk,
                name=form.cleaned_data["name"],
                color=form.cleaned_data["color"],
            )
            messages.success(request, "Label updated successfully")
            if request.htmx:
                response = HttpResponse()
                response["HX-Location"] = (
                    '{"path": "'
                    + reverse("label_list")
                    + '", "target": "#main-content"}'
                )
                return response
            return HttpResponseRedirect(reverse("label_list"))
    else:
        form = LabelForm(instance=label)

    context = {
        "form": form,
        "label": label,
        "page_title": "Update Label",
        "label_colors": LABEL_COLORS,
    }
    if is_partial_request(request):
        return render(request, "labels/label_form_partial.html", context)
    return render(request, "labels/label_form.html", context)


@require_http_methods(["POST"])
def label_delete_view(request, pk):
    service = LabelService(user=request.user)
    service.delete_label(pk=pk)
    messages.success(request, "Label deleted successfully")
    if request.htmx:
        response = HttpResponse()
        response["HX-Location"] = (
            '{"path": "' + reverse("label_list") + '", "target": "#main-content"}'
        )
        return response
    return HttpResponseRedirect(reverse("label_list"))


@require_http_methods(["GET"])
def inline_label_form_view(request):
    context = {"label_colors": LABEL_COLORS}
    return render(request, "labels/partials/_inline_label_form.html", context)


@require_http_methods(["POST"])
def inline_label_create_view(request):
    name = request.POST.get("name", "").strip()
    color = request.POST.get("color", LABEL_COLORS[0])

    if name and color in LABEL_COLORS:
        service = LabelService(user=request.user)
        service.create_label(name=name, color=color)

    response = HttpResponse()
    response["HX-Trigger"] = "labelCreated"
    return response
