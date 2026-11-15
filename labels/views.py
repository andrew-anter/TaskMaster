from django.contrib import messages
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from common.http import hx_location_response, is_partial_request

from .context import build_label_detail_context
from .exceptions import DuplicateLabelError
from .forms import LABEL_COLORS, LabelForm
from .models import Label
from .selectors import LabelSelector
from .services import LabelService


@require_http_methods(["GET"])
def label_list_view(request):
    selector = LabelSelector(user=request.user)
    # Annotated per request so the partial does not issue a COUNT per row.
    labels = selector.get_labels().annotate(task_count=Count("tasks"))
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
    mode and replace the ``?mode=edit`` URL, mirroring the task detail page.
    """
    try:
        label = LabelSelector(user=request.user).get_label(pk=pk)
    except Label.DoesNotExist:
        messages.error(request, "No label associated with this id.")
        if request.htmx:
            return hx_location_response(reverse("label_list"))
        raise Http404 from None

    editing = request.method == "POST" or request.GET.get("mode") == "edit"
    update_succeeded = False

    if request.method == "POST":
        form = LabelForm(request.POST, instance=label, user=request.user)
        if form.is_valid():
            service = LabelService(user=request.user)
            try:
                label = service.update_label(
                    pk=pk,
                    name=form.cleaned_data["name"],
                    color=form.cleaned_data["color"],
                )
            except DuplicateLabelError as e:
                form.add_error("name", f"{e}")
            else:
                messages.success(request, "Label updated successfully")
                editing = False
                update_succeeded = True
                form = LabelForm(instance=label, user=request.user)
    else:
        form = LabelForm(instance=label, user=request.user)

    if editing:
        context = {
            "label": label,
            "form": form,
            "editing": True,
            "label_colors": LABEL_COLORS,
            "page_title": label.name,
        }
    else:
        context = build_label_detail_context(user=request.user, label=label)

    if is_partial_request(request):
        response = render(request, "labels/partials/_label_detail.html", context)
        if update_succeeded:
            # Leave edit mode in the address bar too, so a reload shows the
            # read-only view instead of the form again.
            response["HX-Replace-Url"] = reverse("label_detail", args=[label.pk])
        return response
    return render(request, "labels/label_detail.html", context)


@require_http_methods(["GET", "POST"])
def label_create_view(request):
    if request.method == "POST":
        form = LabelForm(request.POST, user=request.user)
        if form.is_valid():
            service = LabelService(user=request.user)
            try:
                service.create_label(
                    name=form.cleaned_data["name"],
                    color=form.cleaned_data["color"],
                )
            except DuplicateLabelError as e:
                form.add_error("name", f"{e}")
            else:
                messages.success(request, "Label created successfully")
                if request.htmx:
                    return hx_location_response(reverse("label_list"))
                return HttpResponseRedirect(reverse("label_list"))
    else:
        form = LabelForm(user=request.user)

    context = {
        "form": form,
        "page_title": "Create Label",
        "label_colors": LABEL_COLORS,
    }
    if is_partial_request(request):
        return render(request, "labels/label_form_partial.html", context)
    return render(request, "labels/label_form.html", context)


@require_http_methods(["POST"])
def label_delete_view(request, pk):
    service = LabelService(user=request.user)
    try:
        service.delete_label(pk=pk)
    except Label.DoesNotExist:
        messages.error(request, "No label associated with this id.")
        if request.htmx:
            return hx_location_response(reverse("label_list"))
        raise Http404 from None
    messages.success(request, "Label deleted successfully")
    if request.htmx:
        return hx_location_response(reverse("label_list"))
    return HttpResponseRedirect(reverse("label_list"))


@require_http_methods(["GET"])
def inline_label_form_view(request):
    context = {"label_colors": LABEL_COLORS}
    return render(request, "labels/partials/_inline_label_form.html", context)


@require_http_methods(["POST"])
def inline_label_create_view(request):
    """Creates a label from the task form and returns the refreshed picker."""
    name = request.POST.get("name", "").strip()
    color = request.POST.get("color", LABEL_COLORS[0])
    checked_ids = [
        int(value) for value in request.POST.getlist("labels") if value.isdigit()
    ]

    error = ""
    if not name:
        error = "Enter a label name."
    elif color not in LABEL_COLORS:
        error = "Please select a valid color."
    else:
        service = LabelService(user=request.user)
        try:
            label = service.create_label(name=name, color=color)
        except DuplicateLabelError as e:
            error = f"{e}"
        except DjangoValidationError as e:
            # e.g. a tampered name longer than the model's max_length.
            error = " ".join(e.messages)
        else:
            checked_ids.append(label.pk)

    if error:
        context = {
            "label_colors": LABEL_COLORS,
            "error": error,
            "form_name": name,
            "selected_color": color,
        }
        return render(request, "labels/partials/_inline_label_form.html", context)

    context = {
        "user_labels": Label.objects.filter(owner=request.user).order_by("name"),
        "selected_ids": checked_ids,
        "oob": True,
    }
    response = render(request, "todo/partials/_labels_selector.html", context)
    # Let the task form collapse its now-empty inline label card again.
    response["HX-Trigger"] = "tm-inline-label-created"
    return response
