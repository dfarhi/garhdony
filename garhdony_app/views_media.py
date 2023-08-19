from sendfile import sendfile
import garhdony_app.auth as auth
from django.http import Http404, HttpResponse
from garhdony_app.models import EmbeddedImage, Sheet
from garhdony_app.forms_game_design import NewEmbeddedImageForm
from django.utils.html import escape

def can_see_player_photo(request, character_first_name):
    # This only gets called if the user is not a writer.
    # So we just need to check if the user's character has
    # contact_first_name as a contact.
    try:
        contacts = request.user.character.contacts
        return character_first_name in contacts.filter(first_name=character_first_name)
    except:
        return False


def media_player_photo(request, run_name, contact_name):
    def render_photo(game, writer):
        if writer or can_see_player_photo(request, contact_name):
            return sendfile(request, game.abs_photo_directory+"/"+contact_name)
        else:
            raise Http404
    return auth.authenticate_resolve_and_callback(request, render_photo, run_name)

def can_see_image(request, image_name):
    # See if the player described by request can see the embedded_image in image_name.
    # TODO: Test this!
    try:
        the_image = EmbeddedImage.objects.get(filename=image_name)
        character = request.user.character
    except:
        # There is no such image; they can't see it.
        return False
    if character.game.complete:
        return True
    for sheet in character.sheets.all():
        if sheet in the_image.sheets:
            return True
    return False


def media_sheet_embedded_image(request, run_name, image_name):
    def render_embedded_image(writer, game):
        if writer or can_see_image(request, image_name):
            image = EmbeddedImage.objects.get(game=game, filename=image_name)
            return sendfile(request, image.absolute_path)
        else:
            raise Http404
    return auth.authenticate_resolve_and_callback(request, render_embedded_image, run_name)



def media_sheet_upload_image(request, run_name, sheet, replace_or_new):
    def render_image(writer, game, sheet):
        if request.method == 'POST':
            if 'Upload' in request.POST:
                upload_form = NewEmbeddedImageForm(game, sheet, request.POST, request.FILES)
                if upload_form.is_valid():
                    upload_form.save()
                    return HttpResponse('<script type="text/javascript">opener.modifyImageClosePopup(window, "%s", "%s");</script>' %(
                        escape(upload_form.instance.url),
                        str(upload_form.instance.id)))
            elif 'Select' in request.POST:
                id = request.POST.get('image')
                image = EmbeddedImage.objects.get(id=int(id))
                #image.sheets.add(sheet)
                if 'scope' in request.POST:
                    scope = request.POST.get('scope')
                else:
                    scope = 'new'
                if scope == "sheet":
                    # Change all instances in this sheet.
                    change_all = "true"
                elif scope == "all":
                    # Change all instances in all sheets.
                    # TODO: requires global find-replace.
                    change_all="true"
                    # TODO: Mark this image as obsolete.
                else:
                    change_all="false"
                return HttpResponse('<script type="text/javascript">opener.modifyImageClosePopup(window, "%s", "%s", "%s");</script>' %(
                    escape(image.url),
                    str(image.id),
                    change_all,))
            else:
                raise ValueError("Invalid submit button")
        else:
            upload_form = NewEmbeddedImageForm(game, sheet)
        available_images = EmbeddedImage.objects.filter(game=game)
        image_sheet_dic = EmbeddedImage.current_images_sheets_dict(game)
        return auth.callback_package('garhdony_app/upload_embedded_image.html', {'upload_form': upload_form, 'image_sheet_dic':image_sheet_dic, 'available_images':available_images, 'replace_or_new':replace_or_new, "possibly_unsaved_images":True})
    return auth.authenticate_resolve_and_callback(request, render_image, run_name, sheet=sheet, sheet_by_display_name=False)