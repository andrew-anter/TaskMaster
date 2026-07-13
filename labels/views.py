from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import LabelForm, LABEL_COLORS
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
    if request.htmx:
        return render(request, "labels/partials/_label_list.html", context)
    return render(request, "labels/label_list.html", context)


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
                response["HX-Location"] = '{"path": "' + reverse("label_list") + '", "target": "#main-content"}'
                return response
            return HttpResponseRedirect(reverse("label_list"))
    else:
        form = LabelForm()

    context = {
        "form": form,
        "page_title": "Create Label",
        "label_colors": LABEL_COLORS,
    }
    if request.htmx:
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
                response["HX-Location"] = '{"path": "' + reverse("label_list") + '", "target": "#main-content"}'
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
    if request.htmx:
        return render(request, "labels/label_form_partial.html", context)
    return render(request, "labels/label_form.html", context)


@require_http_methods(["POST"])
def label_delete_view(request, pk):
    service = LabelService(user=request.user)
    service.delete_label(pk=pk)
    messages.success(request, "Label deleted successfully")
    if request.htmx:
        response = HttpResponse()
        response["HX-Location"] = '{"path": "' + reverse("label_list") + '", "target": "#main-content"}'
        return response
    return HttpResponseRedirect(reverse("label_list"))
