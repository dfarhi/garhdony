from django.core.urlresolvers import reverse
from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.utils.safestring import mark_safe
from django.utils.html import escape
from diff_match_patch import diff_match_patch
import auth
from django.views.decorators.csrf import csrf_exempt
from garhdony_app.forms_writing import SheetContentForm, SheetUploadForm
from garhdony_app.models import Sheet, SheetRevision, EditLock, GameInstance
from LARPStrings import LARPstring
import utils
import span_parser
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

#####################################################
################### Main Edit Tab ###################
#####################################################


@csrf_exempt
# This prevents CSRF checking on this view.
# We do this so that you don't get in trouble for opening an edit tab, logging out and back in from a different tab
# Then saving the first edit tab.
# It might be insecure in some way?
def writer_sheet_edit(request, run_name, filename):
    def render_edit(game, writer, sheet):
        if sheet.content_type == 'html':
            logger.debug(str(datetime.now())+": Editing HTML.")
            return writer_sheet_edit_html(request, game, sheet)
        else:
            logger.debug(str(datetime.now())+": Editing file.")
            return writer_sheet_edit_file(request, game, sheet)

    return auth.authenticate_resolve_and_callback(request, render_edit, run_name, sheet=filename, requires_writer=True)

def writer_sheet_edit_html(request, game, sheet):
    """
    The main edit tab view.

    If the request is a GET request, it hands it off to regular_edit, which opens the sheet for editing.
    If the request is a POST request, it checks the 'action' (which big button was pressed).
    On the main page the actions are:
        'Save'
        'Cancel'
    When an edit conflict occurs, the user gets the addition options:
        'Automerge' (apply my diff to the current head)
        'Override' (Save my changes and drop intervening changes)
    If a normal GET request finds a lock, it provides another action:
        'Break' (break the existing lock and begin editing)
    """

    lock_warning ="You have locked this sheet for editing. To release the lock cleanly, please press the Cancel button rather than just navigating away."
    warnings  = [lock_warning]
    if request.method=="GET":
        # Handle the normal view
        # (when the user just wants to open the page to begin to edit)
        # in this separate function
        logger.debug(str(datetime.now())+": regular_edit")
        return regular_edit(request, sheet, warnings)

    # So now request method is post; user has posted something.
    action = request.POST.get('action')
    # Action tells us which big button they pressed

    logger.debug(str(datetime.now())+": Writer action = "+action)

    if action =="Cancel":
        # We delete the edit lock (remember that each edit lock is tied to a single time they opened the edit tab)
        lock_id = request.POST.get('edit_lock')
        lock = EditLock.objects.get(pk=lock_id)
        if not lock.saved:
            # If they pressed the back button by accident after saving, remember that it was saved.
            lock.break_lock()
        return HttpResponseRedirect(reverse('writer_sheet', args=[game.name, sheet.filename]))

    if action == "Break":
        # This is for if they want to break the existing lock.
        # So we break it, and then edit as normal.
        sheet.break_lock()
        logger.debug(str(datetime.now())+": Lock broken; redirecting to regular_edit")
        return regular_edit(request, sheet, warnings)

    # Other actions will actually require us to bind a form, so here we go:
    form = SheetContentForm(sheet, request.user, data=request.POST.copy()) # Dear past-David: what's with the copy?
    logger.debug(str(datetime.now())+": Bound Form")
    if form.is_valid():
        # So the form is valid and we need to do something.
        # We go through the possible actions, and set the lock_valid option
        # depending on the action the user chose and the current lock status

        # Then if lock_valid is true, we save.

        logger.debug(str(datetime.now())+": Valid Sheet Content Form")

        my_lock = form.cleaned_data['edit_lock']

        # intervening locks is the locks that have been created since we started. We're going to resolve it later.
        # Why not resolve it now? TODO: Probably that would be better.
        intervening_locks = "UNRESOLVED"



        if my_lock.saved:
            # Since each lock is tied to a particular tab,
            # it should never be possible that a given lock gets saved twice.
            raise ValueError("Your edit lock has already been saved.")

        if action == "Override":
            # The user wants to override the existing lock and save the forms content.
            sheet.steal_lock(my_lock)
            lock_valid = True

        elif action =="MergeKeepMine":
            # The user wants to override the existing lock and save their original content.
            sheet.steal_lock(my_lock)
            form.cleaned_data['content'] = LARPstring(form.cleaned_data['edit_conflict_my_content'])
            lock_valid = True

        elif action == "Automerge":
            # The user wants to rebase to the current version.
            sheet.steal_lock(my_lock)

            # This applies our diff to the current version.
            success = form.merge_rebase()
            if success:
                lock_valid = True
            else:
                # It is really weird to get here, since it ran a dry run before presenting the user with this option.
                logger.debug("Automerge failed after successful dry run!")
                lock_valid = False

        elif action=="Save":
            # This is by far the most common use case.

            # The only complication is the recovered_lock argument,
            # Which the form will pass if it did client-side stuff and found an older lock
            # that it wants to pretend to be.
            recovered_lock = form.cleaned_data['recovered_edit_lock']
            if recovered_lock is None:
                # Nice and simple. My lock is valid if its the current lock,
                # Which is equivalent to if it's unbroken.
                lock_valid = (my_lock==sheet.current_lock())
                assert(lock_valid == (not my_lock.broken))
            else:
                # by supplying recovered_lock, the client is saying that really their edits are based on that lock's
                # base_revision instead of based on the base_revision of the lock we assigned.

                logger.debug(str(datetime.now())+": Found recovered_lock")
                # intervening locks are all the ones since recovered_lock,
                # except for the one that they're actually saving (my_lock).
                intervening_locks = sheet.edit_locks.filter(created__gt=recovered_lock.created).exclude(pk=my_lock.pk)
                if len(intervening_locks)==0:
                    # If there aren't any, that means no one has taken out an edit lock since
                    # the original recovered_lock except for my_lock.
                    # (So my_lock should be the curent_lock and should be unbroken;
                    # if it were broken, it can't be a current_lock
                    # and if there were any after it it would be broken.)
                    # So the data in the form is safe; go ahead and edit
                    logger.debug(str(datetime.now())+": recovered_lock is current.")
                    lock_valid = True
                    assert my_lock==sheet.current_lock()
                    assert not my_lock.broken
                else:
                    logger.debug(str(datetime.now())+": recovered_lock not current; conflict pending.")
                    # If there are intervening_locks, we're going to need to merge.
                    lock_valid = False

                    # For the upcoming merge, my_lock should be aware
                    # that it's based on whatever recovered_lock was based on.
                    my_lock.base_revision = recovered_lock.base_revision
                    my_lock.save()

        else:
            raise ValueError("What form did you even submit?")

        if not lock_valid:
            # lock_valid was false, because the user pressed 'Save' but their lock was broken.
            # We should show them the merging view
            # But first we check to make sure that there actually was an intervening lock.
            # And decide exactly what to do depending whether:
            # 1) There were any intervening locks that were actually saved (with which we could merge)
            # 2) There is currently another lock out there that's active.

            logger.debug(str(datetime.now())+": Edit lock invalid.")

            if intervening_locks == "UNRESOLVED":
                intervening_locks = sheet.edit_locks.filter(created__gt=my_lock.created)

            warnings.remove(lock_warning)
            intervening_saved_locks = intervening_locks.filter(saved=True)
            active_lock = sheet.current_lock()

            # Code is repeated a bit in the next if/elif/elif/else, but I think the clarity is worth it.
            if len(intervening_saved_locks)>0 and active_lock is not None:
                # There are intervening saves and a new active lock.
                # We need to merge.
                warnings += ["EDIT CONFLICT: Someone else has saved edits to this sheet since your last action!"]
                warnings += [mark_safe("%(author)s has an Active edit lock!<br>Saving your changes will break <b>%(author)s's</b> lock timestamped <b>%(time)s</b>"%{'author':active_lock.author, 'time':active_lock.created_display})]
                return merge_view(sheet, form, my_lock, intervening_locks, warnings)
            elif len(intervening_saved_locks)>0 and active_lock is None:
                # There are intervening saves but now new active lock.
                # We need to merge.
                warnings += ["EDIT CONFLICT: Someone else has saved edits to this sheet since your last action!"]
                return merge_view(sheet, form, my_lock, intervening_locks, warnings)
            elif len(intervening_saved_locks)==0 and active_lock is not None:
                # Someone is editing right now, but no saved revisions.
                # So there's nothing to merge.
                warnings += [mark_safe("BROKEN LOCK: %(author)s has stolen your edit lock!<br>Saving your changes will break <b>%(author)s's</b> Active lock timestamped <b>%(time)s</b>"%{'author':active_lock.author, 'time':active_lock.created_display})]
                # Redisplay the writing template, but tell it that next time it Saves it should override the lock.
                return auth.callback_package('garhdony_app/sheet_writing.html', {'sheet':sheet, 'form':form, 'here':"Write", 'warnings':warnings, 'save_override':True})
            else: # len(intervening_saved_locks)==0 and active_lock is None:
                # There aren't actually any locks in the way.
                # Restore my lock.
                my_lock.broken = False
                my_lock.save()

                # Redisplay and ask for approval just to be safe.
                warnings += ["Your edit lock has been broken, but there appear to be no other locks or revisions since you checked this sheet out. Click Save to save your changes."]
                return auth.callback_package('garhdony_app/sheet_writing.html', {'sheet':sheet, 'form':form, 'here':"Write", 'warnings':warnings})

        else:
            # All clear, one way or another.
            # Tell the form to save, then tell the editlock that it has been saved.
            logger.debug(str(datetime.now())+": Valid lock: saving")

            form.save()

            # After saving (crucially), we check whether we should redisplay the form due to incompleteness.
            # "form.complete" is an attribute that forms can have to mark whether they need to be redisplayed to the user for fixing.
            # It's defined in forms.WithComplete
            if hasattr(form, 'complete') and form.complete(): # TODO the hasattr is more of an assert; should be error if not, rather than going down some particular control path.
                # If it doesn't need corrections, we can redirect to the Read view;
                # otherwise we should redisplay the form as though it failed validation.
                return HttpResponseRedirect(reverse('writer_sheet', args=[game.name, sheet.filename]))
            else:
                # They need to edit again.
                # Make a new lock (leave the previous lock as saved, to remember that we made those changes).
                new_edit_lock = EditLock(sheet=sheet, base_revision=sheet.current_revision, author=request.user)
                new_edit_lock.save()
                form.data['edit_lock'] = new_edit_lock
                # Control flow falls through from here to if the form was invalid.

    # You got here either because the form was invalid and needs to be redisplayed,
    # or it was valid but incomplete (needs gender fixes) and thus needs to be redisplayed.
    logger.debug(str(datetime.now())+": Redisplaying form.")

    if hasattr(form, 'complete') and not form.complete():
        # Make a warning explaining what's going on.
        warnings += [mark_safe("Found unresolved gendered words (red). Click to resolve them.<br>(If you're a bad person who wants to not deal with it, your changes have been saved and you can just click Cancel).")]
    return auth.callback_package('garhdony_app/sheet_writing.html', {'sheet':sheet, 'form':form, 'here':"Write", 'warnings':warnings})

@csrf_exempt
# This is what the ajax calls to make sure the server is there and everything is ok.
def writer_sheet_presave_handshake(request, run_name, filename):
    if not request.user.is_authenticated():
        return JsonResponse({"status": "NOT LOGGED IN"})
    elif not request.user.has_perm('garhdony_app.writer'):
        return JsonResponse({"status": "NOT LOGGED IN AS WRITER"})
    else:
        try:
            game = GameInstance.objects.get(name=run_name)
        except:
            return JsonResponse({"status": "INVALID GAME ... WTF?"})
        if not (request.user.has_perm('garhdony_app.writer', game) or request.user.is_staff):
            return JsonResponse({"status": "NOT LOGGED IN AS WRITER ON THAT GAME"})
        try:
            sheet = game.sheets.get(filename=filename)
        except:
            return JsonResponse({"status": "INVALID SHEET NAME"})
        return JsonResponse({"status": "OK"})

def regular_edit(request, sheet, warnings):
    # Load the sheet for editing.
    # If there's a current lock, ask what to do.
    if sheet.current_lock():
        # Make sure we're not the one who has the lock!
        # If we are, tell the template that and it will render differently.
        self_conflict = sheet.current_lock().author == request.user
        return auth.callback_package('garhdony_app/sheet_locked.html', {'sheet':sheet, 'prev_lock':sheet.current_lock(), 'here':"Write", 'self_conflict':self_conflict})
    else:
        # We are free to edit.
        # Make a new lock and then display the writing page.
        edit_lock = EditLock(sheet=sheet, base_revision=sheet.current_revision, author=request.user)
        edit_lock.save()
        form = SheetContentForm(sheet, request.user, initial={'edit_lock':edit_lock})

        # Also check if there were any LARPstring syntax errors, and alert the user.
        if len(form.fields['content'].initial.syntax_problems)>0:
            syntax_warning = "This sheet had LARP markup syntax problems that may not have been fixed correctly:"
            for p in form.fields['content'].initial.syntax_problems[:10]:
                syntax_warning+="\n    "+p
            warnings +=[syntax_warning]
        return auth.callback_package('garhdony_app/sheet_writing.html', {'sheet':sheet, 'form':form, 'here':"Write", 'warnings':warnings})


def writer_sheet_edit_file(request, game, sheet):
    warnings = ["This is a file-based sheet. There are no edit locks."]
    if request.method=="GET":
        form = SheetUploadForm(sheet, request.user)
    else:
        form = SheetUploadForm(sheet, request.user, data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('writer_sheet', args=[game.name, sheet.filename]))
    return auth.callback_package('garhdony_app/sheet_upload.html', {'sheet':sheet, 'form':form, 'here':"Write", 'warnings':warnings})

def merge_view(sheet, form, my_lock, intervening_locks, warnings):
    """
    For merging after an edit conflict.
    It assembles all the different versions into a version with markup indicating the diffs,
    So the user can easily see them.
    """
    warnings += [mark_safe("You do <i>not</i> have this sheet locked. Don't stay here long; I don't know what will happen if someone else saves while you're merging.")]

    # This stores my_content in the edit_conflict_my_content field.
    form.prepare_for_merge()

    # See if it is possible to automatically rebase to the current revision.
    # This boolean is passed to the template, which provides automerging as an option to the user if it's True
    can_rebase = form.merge_rebase(commit=False)

    # Define all the different versions:
    # base is the contents of the revision I branched from
    # mine is the contents of my revision
    # saved is the most recent revision
    # We escape all of them, because the diff wants to treat the html as text.
    base = escape(my_lock.base_revision.content.raw())
    mine = escape(form.cleaned_data['content'].raw())
    saved = escape(sheet.current_revision.content.raw())

    # Assemble the diffs.
    # double_diff returns a list of trios, each of which is a [mine_operation, saved_operation, text]
    # where operations are None, d_m_p.DIFF_INSERT, d_m_p.DIFF_DELETE, d_m_p.DIFF_EQUAL
    # And based on the many possibilities for the pair of operations, we markup the text.
    # The markup uses these data-larp-action tags:
    # remove-label: when you save this, django will unwrap this span (so we don't have random class=mine text in the db)
    # remove: when you save this, django will remove this span and its contents.
    dbl_diff = utils.double_diff(base, mine, saved)
    new_content = ""
    for my_op, saved_op, text in dbl_diff:
        if my_op ==  diff_match_patch.DIFF_INSERT:
            # I inserted something; saved has nothing here. By default it should stay, so mark with a remove-label
            new_bit = span_parser.add_tag(text, "<span data-larp-action='remove-label' class='mine'>", "</span>")
        elif saved_op == diff_match_patch.DIFF_INSERT:
            # Saved inserted something; mine has nothing here. By default it should stay, so mark it with a remove-label
            new_bit = span_parser.add_tag(text, "<span data-larp-action='remove-label' class='theirs'>", "</span>")
        elif my_op == diff_match_patch.DIFF_DELETE and saved_op==diff_match_patch.DIFF_DELETE:
            # Both revisions removed this; mark with remove.
            new_bit = span_parser.add_tag(text, "<span data-larp-action='remove' class='removed-both'><strike>", "</strike></span>")
        elif my_op == diff_match_patch.DIFF_DELETE and saved_op==diff_match_patch.DIFF_EQUAL:
            # I removed this; saved kept it. Mark for removal.
            new_bit = span_parser.add_tag(text, "<span data-larp-action='remove' class='mine'><strike>", "</strike></span>")
        elif my_op == diff_match_patch.DIFF_EQUAL and saved_op==diff_match_patch.DIFF_DELETE:
            # Saved removed this; I kept it. Mark for removal.
            new_bit = span_parser.add_tag(text, "<span data-larp-action='remove' class='theirs'><strike>", "</strike></span>")
        elif my_op == diff_match_patch.DIFF_EQUAL and saved_op==diff_match_patch.DIFF_EQUAL:
            # Neither revision touched this; don't mark it at all.
            new_bit = text
        # The other combinations should not be possible.
        new_content += new_bit

    # Now, we want to add a tag around the whole thingy telling django to unescape it after the remove-tags are applied.
    # This is parsed by span_parse into an UnescapeNode, which does the unescaping.
    new_content = "<span data-larp-action='unescape'>"+new_content+"</span>"

    # Render the writing form with the diff as the content.
    # Also mention whether automerging was successful
    form.set_bound_content(new_content)
    return auth.callback_package('garhdony_app/sheet_writing.html', {'sheet':sheet, 'form':form, 'can_rebase':can_rebase, 'intervening_locks':intervening_locks, 'warnings':warnings})


#####################################################
############# Top-right Floater Buttons #############
#####################################################


def writer_sheet_release(request, run_name, filename):
    """
    Breaks my lock on sheet determined by filename.
    Then redirect to that sheet's page, or to next if it's in the GET.
    """
    def render_release(game, writer, sheet):
        lock = sheet.current_lock()
        if lock.author == request.user:
            lock.break_lock()
        if request.method=="POST" and "next" in request.POST:
            redir = request.POST['next']
        else:
            redir = reverse('writer_sheet', args=[run_name, filename])
        return HttpResponseRedirect(redir)
    return auth.authenticate_resolve_and_callback(request, render_release, run_name, sheet=filename, requires_writer=True)


def writer_sheet_export(request, run_name, filename):
    """
    Generates PDFs for the sheet.
    Then redirects to the sheet's page, or next if it's provided.
    """
    def render_export(game, writer, sheet):
        sheet.print_sheet_pdf()
        if request.method=="POST" and "next" in request.POST:
            redir = request.POST['next']
        else:
            redir = reverse('writer_sheet', args=[run_name, filename])
        return HttpResponseRedirect(redir)
    return auth.authenticate_resolve_and_callback(request, render_export, run_name, sheet=filename, requires_writer=True)



#####################################################
############### History and Reverting ###############
#####################################################
# Much of this code is from djiki

def writer_sheet_history(request, run_name, filename):
    def render_history(game, writer, sheet):
        # Get all the revisions and pass them to the template.
        history = sheet.revisions.order_by('-created')
        return auth.callback_package('garhdony_app/sheet_history.html', {'sheet':sheet, 'history':history, 'here':"History"})
    return auth.authenticate_resolve_and_callback(request, render_history, run_name, sheet=filename, requires_writer=True)


def writer_sheet_revert(request, run_name, filename, revision_pk):
    # Revert to revision whose pk is revision_pk
    def render_revert(game, writer, sheet):
        src_revision = sheet.revisions.get(pk=revision_pk)

        # Make the description
        src_author = src_revision.author
        if src_author:
            src_author_name = src_author.username
        else:
            src_author_name = "anon"
        description = "Reverted to revision of %(time)s by %(user)s."%{'time':src_revision.created, 'user':src_author_name}

        # Construct a new revision whose content is the source's content
        new_revision = SheetRevision(sheet=sheet, author=request.user, content = src_revision.content, description=description)
        new_revision.save()
        return HttpResponseRedirect(reverse('writer_sheet', args=[game.name, sheet.filename]))
    return auth.authenticate_resolve_and_callback(request, render_revert, run_name, sheet=filename, requires_writer=True)


def writer_sheet_diff(request, run_name, filename):
    """
    Compare two revisions (the two revisions' pks are in the GET).
    """
    def render_diff(game, writer, sheet):
        # Get the revisions.
        try:
            from_rev = sheet.revisions.get(pk=request.REQUEST['from_revision_pk'])
            to_rev = sheet.revisions.get(pk=request.REQUEST['to_revision_pk'])
        except (KeyError, Sheet.DoesNotExist):
            return HttpResponseNotFound()

        from_time = from_rev.created
        to_time = to_rev.created
        if from_time>to_time:
            # The older one should be the from rev, no matter what they pressed.
            from_rev, to_rev = to_rev, from_rev

        # Make the diff and send it to the template.
        dmp = diff_match_patch()
        diff = dmp.diff_compute(from_rev.content.render(), to_rev.content.render(), True, 2)
        return auth.callback_package('garhdony_app/sheet_diff.html', {'sheet': sheet, 'from_revision': from_rev, 'to_revision': to_rev, 'diff': diff, 'here':"History"})
    return auth.authenticate_resolve_and_callback(request, render_diff, run_name, sheet=filename, requires_writer=True)