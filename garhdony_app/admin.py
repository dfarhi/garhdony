"""
This sets up the admin site, which is basically a way to talk to the database directly.

You can get to it by going to /admin when logged in as admin or storyteller.
"""

from django.contrib import admin
from garhdony_app.LARPStrings import LARPTextField, LARPTextWidget
from garhdony_app.models import Character, PlayerProfile, GameInstance, Sheet, SheetColor, SheetType, SheetStatus, LogisticalTask, \
    TravelProfile, Contact, GenderizedKeyword, GenderizedName, PlayerCharacter, NonPlayerCharacter, SheetRevision, CharacterStat, \
    CharacterStatType, GameInfoLink, EmbeddedImage, GameTemplate, WebsiteAboutPage, QuizSubmission, TimelineEvent,TimelineEventSheetDescription
from django.contrib.auth.models import User, Group
from django import forms
from django.urls import re_path as url
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.shortcuts import render

class AdminModelFormLARPStringAware(forms.ModelForm):
    """
    Subclass this to avoid errors with "must call set_game() before using LARPTextField".
    See e.g. ContactAdmin below.
    """
    def get_game(self):
        return self.instance.game
    
    def clean(self, *args, **kwargs):
        for name, field in self.fields.items():
            if hasattr(field, 'set_game'):
                field.set_game(self.get_game())
        super(AdminModelFormLARPStringAware, self).clean(*args, **kwargs)

class DogmasAdminSite(admin.sites.AdminSite):
    def get_urls(self):
        urls = super(DogmasAdminSite, self).get_urls()

        # my_urls used to include '' but we removed it because of E004
        my_urls = [url(r'^logistics_table/$', self.logistics_table_view, name='logistics_table'),
                   url(r'^travel_surveys/$', self.travel_surveys_view, name='travel_surveys'),]
        return my_urls + urls

    def logistics_table_view(self, request):
        tasks = LogisticalTask.objects.all().order_by('sort_order')
        players = PlayerProfile.objects.all()
        # Be able to filter by game in the future?
        return render(request, 'admin/logistics_table.html', {'tasks': tasks, 'players': players})

    def travel_surveys_view(self, request):
        surveys = TravelProfile.objects.all()
        # Be able to filter by game in the future?
        return render(request, 'admin/travel_surveys.html', {'surveys': surveys})

    index_template = "admin/index.html"
    # logout_template = "garhdony_app/index.html"


admin_site = DogmasAdminSite()

admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)

class CharacterForm(forms.ModelForm):
    class Meta:
        model = Character
        exclude = []

    first_male = forms.CharField(max_length=50, label="First Name (Male)")
    first_female = forms.CharField(max_length=50, label="First Name (Female)")

    def __init__(self, *args, **kwargs):
        super(CharacterForm, self).__init__(*args, **kwargs)
        current_sheets = Sheet.objects.filter(game=self.instance.game).order_by('color__sort_order', 'filename')
        # I'm not sure this is the right way to prepopulate the fields...
        if self.instance.first_name_obj is not None:
            self.fields['first_male'].initial = self.instance.first_name_obj.male
            self.fields['first_female'].initial = self.instance.first_name_obj.female
        self.fields['sheets'].queryset = current_sheets
        self.fields['title_obj'].queryset = GenderizedKeyword.objects.filter(category='title')

    def save(self, commit=True):
        character = super(CharacterForm, self).save(commit=False)
        if self.instance.first_name_obj is None:
            first = GenderizedName()
            first.character = self.instance
            first.male = "DEFAULT"
            first.female = "DEFAULT"
            character.first_name_obj = first
        else:
            first = character.first_name_obj
        first.male = self.cleaned_data['first_male']
        first.female = self.cleaned_data['first_female']
        if commit:
            character.save()
        return character


class CharacterStatAdmin(admin.ModelAdmin):
    list_display = ('stat_type', 'character', 'value')
    list_filter = ('character__game',)
    readonly_fields = ('character',)


admin_site.register(CharacterStat, CharacterStatAdmin)


class CharacterStatTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)


admin_site.register(CharacterStatType, CharacterStatTypeAdmin)


class GenderizedKeywordAdmin(admin.ModelAdmin):
    list_filter = ('category',)


admin_site.register(GenderizedKeyword, GenderizedKeywordAdmin)


class GenderizedNameAdmin(admin.ModelAdmin):
    list_display = (str, 'character')
    list_filter = ('character__game__name',)
    exclude = ["category"]


admin_site.register(GenderizedName, GenderizedNameAdmin)


class NameInline(admin.TabularInline):
    exclude = ["category"]
    model = GenderizedName

    def queryset(self, request):
        # TODO: Use this to exclude the character's first name.
        qs = super(NameInline, self).queryset(request)
        return qs.none()


class ContactAdminForm(AdminModelFormLARPStringAware):
    class Meta:
        model = Contact
        exclude = []

class ContactAdmin(admin.ModelAdmin):
    list_filter = ('owner__game__name', 'owner')
    form = ContactAdminForm


admin_site.register(Contact, ContactAdmin)


class ContactInline(admin.TabularInline):
    model = Contact
    fk_name = "owner"

class PlayerCharacterAdminForm(AdminModelFormLARPStringAware):
    class Meta:
        model = PlayerCharacter
        exclude = []
class PlayerCharacterAdmin(admin.ModelAdmin):
    list_display = (str, 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)
    form = PlayerCharacterAdminForm
admin_site.register(PlayerCharacter, PlayerCharacterAdmin)

class NonPlayerCharacterAdminForm(AdminModelFormLARPStringAware):
    class Meta:
        model = NonPlayerCharacter
        exclude = []
class NonPlayerCharacterAdmin(admin.ModelAdmin):
    list_display = (str, 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)
    form = NonPlayerCharacterAdminForm
admin_site.register(NonPlayerCharacter, NonPlayerCharacterAdmin)


class SimpleCharacterAdmin(admin.ModelAdmin):
    list_display = (str, 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)


admin_site.register(Character, SimpleCharacterAdmin)

class SheetRevisionAdminForm(AdminModelFormLARPStringAware):
    class Meta:
        model = SheetRevision
        exclude = []

    def get_game(self):
        return self.instance.sheet.game
class SheetRevisionAdmin(admin.ModelAdmin):
    list_display = ('sheet', 'created', 'author')
    list_filter = ('sheet__game__name', 'sheet__name')
    readonly_fields = ('sheet',)
    form = SheetRevisionAdminForm


admin_site.register(SheetRevision, SheetRevisionAdmin)


class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'character', 'confirmed')
    filter_horizontal = ('done_tasks',)
    save_on_top = True
    list_filter = ('character__game__name',)


admin_site.register(PlayerProfile, PlayerProfileAdmin)


class LogisticalTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'deadline', 'display_text', 'form_type']
    ordering = ['sort_order']


admin_site.register(LogisticalTask, LogisticalTaskAdmin)


class GameInfoLinkAdmin(admin.ModelAdmin):
    list_display = (str, 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)
admin_site.register(GameInfoLink, GameInfoLinkAdmin)

class TravelProfileAdmin(admin.ModelAdmin):
    pass
admin_site.register(TravelProfile, TravelProfileAdmin)


class SheetColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'color', 'sort_order']
    ordering = ['sort_order']
admin_site.register(SheetColor, SheetColorAdmin)


class SheetTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'sort_order']
    ordering = ['sort_order']


admin_site.register(SheetType, SheetTypeAdmin)


class SheetStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'sort_order', 'game']
    ordering = ['sort_order']


admin_site.register(SheetStatus, SheetStatusAdmin)

class GameInstanceAdmin(admin.ModelAdmin):
    def get_actions(self, request):
        return {}
admin_site.register(GameInstance, GameInstanceAdmin)



class GameTemplateAdmin(admin.ModelAdmin):
    pass


admin_site.register(GameTemplate, GameTemplateAdmin)


class WebsiteAboutPageAdmin(admin.ModelAdmin):
    pass

admin_site.register(WebsiteAboutPage, WebsiteAboutPageAdmin)

class SheetAdminForm(AdminModelFormLARPStringAware):
    class Meta:
        model = Sheet
        exclude = []
class AllSheetsAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)
    form = SheetAdminForm


admin_site.register(Sheet, AllSheetsAdmin)


class EmbeddedImageAdmin(admin.ModelAdmin):
    list_display = ('filename', 'sheets', 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)

admin_site.register(EmbeddedImage, EmbeddedImageAdmin)

class QuizSubmissionAdmin(admin.ModelAdmin):
    pass
admin_site.register(QuizSubmission, QuizSubmissionAdmin)

class TimelineEventForm(AdminModelFormLARPStringAware):
    class Meta:
        model = TimelineEvent
        exclude = []
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ('date', 'default_description', 'game',)
    list_filter = ('game__name',)
    ordering = ('game', '-date',)
    form = TimelineEventForm
admin_site.register(TimelineEvent, TimelineEventAdmin)

class TimelineEventSheetDescriptionForm(AdminModelFormLARPStringAware):
    class Meta:
        model = TimelineEventSheetDescription
        exclude = []
    def get_game(self):
        return self.instance.event.game
class TimelineEventSheetDescriptionAdmin(admin.ModelAdmin):
    form = TimelineEventSheetDescriptionForm
    list_filter = ('event__game__name',)

admin_site.register(TimelineEventSheetDescription, TimelineEventSheetDescriptionAdmin)