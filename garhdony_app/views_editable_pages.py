"""
Sets up the render_editable_pages function
Which other views (mostly in views_writing) use to make pages that display stuff with edit buttons.

Using the render_editable_page function is relatively easy; you just ue it like render in the view
and then in the template you can use the writable_field tag (defined and documented in garhdony_tags.py)
"""

import garhdony_app.auth as auth
from django.http import HttpResponseRedirect

def render_editable_page(request, template, template_args, on_save_url_func, writer, edit_form_getter, *args):
    """
    Renders the template with arguments template_args (just like the render function).
    But also allows that template to use the {% writable_field %} tag.
    Which causes the thing to be displayed with an edit button that opens a form for editing that thing.

    This function is responsible for saving and generating the edit forms, and passing the following extra
    arguments to the template in addition to the ones you specify:
        'editable_page': (generally just True)
        'editing': The name of the writable_field that the user is currently editing (since there might be several on one page)
        'edit_form': The form for use in editing the current field.
        'fixing': 'True' if we ware fixing up a previously saved form (with genders, for instance).

    :param request: Usual request object
    :param template: The template to render (string defining its path, like usual)
    :param template_args: Any args you want to pass to the template. These will be augmented with a few more related to the editable field.
    :param on_save_url_func: A function of no arguments that returns the url for redirecting after saved edits (probably the same page's url).
                            It has to be a function so that it is evaluated after the edits take place; for instance
                            we want to "sheet.filename" in the url to be the new one, after the form is saved.
    :param writer: Is the user a writer? If not, don't do anything fancy.
    :param edit_form_getter: A function which takes a few arguments, but primarily a string called "edit_field",
                             which returns an appropriate form for editing that field.
                             So every time you use {% writable_field 'NAME' %} in your template,
                             'NAME' has to be a valid argument that can be passed to this function to
                             get the form for editing field NAME.
    :param args: Any extra args to pass to edit_form_getter.
    """

    new_args = editable_page_update_args(request, writer, edit_form_getter, *args)
    if new_args=="SAVED":
        return HttpResponseRedirect(on_save_url_func())
    else:
        template_args.update(new_args)
        return auth.callback_package(template, template_args)

def editable_page_update_args(request, writer, edit_form_getter, *args):
    """
    This does most of the logic.

    If a form was POSTed, it saves the form and returns the constant "SAVED"

    Otherwise, it checks if an edit button was pressed, and if so generates appropriate arguments for passing to the template.
    """
    if not writer:
        # Don't do anything special since non-writers can't be editing
        return {}
    if request.method == 'POST':
        # Figure out what field was edited;
        # in case there are multiple {% writable_field %}s on one page,
        # the Save argument of the POST dict is set to the name of the one that was saved.
        if "Save" in request.POST:
            edit_field = request.POST.get("Save")
        else:
            raise ValueError(f"Not saving editable field; need 'Save' argument in POST dict.")

        # Make a form and check if it's valid.
        form = edit_form_getter(request, edit_field, request.POST, request.FILES, *args)
        if form.is_valid():
            # LARPTextForms have an extra "complete" attribute,
            # Which indicates whether they need to be fixed up because of gender stuff.

            needs_fix = hasattr(form, 'complete') and not form.complete()

            # We generally want to save it anyway if it's an incomplete form, in case the user gets bored and doesn't fix it up.
            # However, if you're making a new instance of something (like a contact), it will be tricky to redirect you to the same
            # form again. So in that case we don't save it until you fix it up.
            # TODO: That could be improved?
            needs_saving = (not hasattr(form, 'instance')) or (form.instance.pk is not None)
            if needs_saving or not needs_fix:
                form.save()

            # If needs_fix, we want to redirect you back to the same form, so you can fix up the gender words.
            # We set the 'fixing' argument, in case templates want that.
            if needs_fix:
                return {'editing':edit_field, 'edit_form':form, 'fixing':'True', 'editable_page':True}
            else:
                return "SAVED"
        # If form is not valid, you fall through to the edit-mode display at the end.
    else:
        # If you get here it's a GET request.
        # SO either a normal view of the page, or an edit view, depending on whether ?Edit=NAME is in the GET dictionary.
        if 'Edit' in request.GET:
            # The user has clicked the 'edit' button on one of the writable_field tags.
            edit_field = request.GET.get("Edit")
            form = edit_form_getter(request, edit_field, None, None, *args)
        else:
            # Regular view.
            return {'editable_page':True}
    return {'editing':edit_field, 'edit_form':form, 'editable_page':True}



