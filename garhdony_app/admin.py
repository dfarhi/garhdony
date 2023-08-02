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
    def get_game_from_instance(self, instance):
        return instance.game
    
    def full_clean(self, *args, **kwargs):
        for name, field in self.fields.items():
            if hasattr(field, 'set_game'):
                # LARPTextField, needs its game set.
                if self.instance.id is not None:
                    game = self.get_game_from_instance(self.instance)
                    field.set_game(game)
                else:
                    field.set_no_game()

        super(AdminModelFormLARPStringAware, self).full_clean(*args, **kwargs)

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

@admin.register(CharacterStat, site=admin_site)
class CharacterStatAdmin(admin.ModelAdmin):
    list_display = ('stat_type', 'character', 'value')
    list_filter = ('character__game',)
    readonly_fields = ('character',)


@admin.register(CharacterStatType, site=admin_site)
class CharacterStatTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)

@admin.register(GenderizedKeyword, site=admin_site)
class GenderizedKeywordAdmin(admin.ModelAdmin):
    list_filter = ('category',)



@admin.register(GenderizedName, site=admin_site)
class GenderizedNameAdmin(admin.ModelAdmin):
    list_display = (str, 'character')
    list_filter = ('character__game__name',)
    exclude = ["category"]



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

@admin.register(Contact, site=admin_site)
class ContactAdmin(admin.ModelAdmin):
    list_filter = ('owner__game__name', 'owner')
    form = ContactAdminForm



class ContactInline(admin.TabularInline):
    model = Contact
    fk_name = "owner"

class PlayerCharacterAdminForm(AdminModelFormLARPStringAware):
    class Meta:
        model = PlayerCharacter
        exclude = []
@admin.register(PlayerCharacter, site=admin_site)
class PlayerCharacterAdmin(admin.ModelAdmin):
    list_display = (str, 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)
    form = PlayerCharacterAdminForm

class NonPlayerCharacterAdminForm(AdminModelFormLARPStringAware):
    class Meta:
        model = NonPlayerCharacter
        exclude = []
@admin.register(NonPlayerCharacter, site=admin_site)
class NonPlayerCharacterAdmin(admin.ModelAdmin):
    list_display = (str, 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)
    form = NonPlayerCharacterAdminForm

@admin.register(Character, site=admin_site)
class SimpleCharacterAdmin(admin.ModelAdmin):
    list_display = (str, 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)

class SheetRevisionAdminForm(AdminModelFormLARPStringAware):
    class Meta:
        model = SheetRevision
        exclude = []

    def get_game_from_instance(self, instance):
        return instance.sheet.game
@admin.register(SheetRevision, site=admin_site)
class SheetRevisionAdmin(admin.ModelAdmin):
    list_display = ('sheet', 'created', 'author')
    list_filter = ('sheet__game__name', 'sheet__name')
    readonly_fields = ('sheet',)
    form = SheetRevisionAdminForm

@admin.register(PlayerProfile, site=admin_site)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'character', 'confirmed')
    filter_horizontal = ('done_tasks',)
    save_on_top = True
    list_filter = ('character__game__name',)

@admin.register(LogisticalTask, site=admin_site)
class LogisticalTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'deadline', 'display_text', 'form_type']
    ordering = ['sort_order']

@admin.register(GameInfoLink, site=admin_site)
class GameInfoLinkAdmin(admin.ModelAdmin):
    list_display = (str, 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)

@admin.register(TravelProfile, site=admin_site)
class TravelProfileAdmin(admin.ModelAdmin):
    pass

@admin.register(SheetColor, site=admin_site)
class SheetColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'color', 'sort_order']
    ordering = ['sort_order']

@admin.register(SheetType, site=admin_site)
class SheetTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'sort_order']
    ordering = ['sort_order']


@admin.register(SheetStatus, site=admin_site)
class SheetStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'sort_order', 'game']
    ordering = ['sort_order']


@admin.register(GameInstance, site=admin_site)
class GameInstanceAdmin(admin.ModelAdmin):
    def get_actions(self, request):
        return {}


@admin.register(GameTemplate, site=admin_site)
class GameTemplateAdmin(admin.ModelAdmin):
    pass

@admin.register(WebsiteAboutPage, site=admin_site)
class WebsiteAboutPageAdmin(admin.ModelAdmin):
    pass


class SheetAdminForm(AdminModelFormLARPStringAware):
    class Meta:
        model = Sheet
        exclude = []
@admin.register(Sheet, site=admin_site) 
class AllSheetsAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)
    form = SheetAdminForm


@admin.register(EmbeddedImage, site=admin_site)
class EmbeddedImageAdmin(admin.ModelAdmin):
    list_display = ('filename', 'sheets', 'game',)
    list_filter = ('game__name',)
    readonly_fields = ('game',)

@admin.register(QuizSubmission, site=admin_site)
class QuizSubmissionAdmin(admin.ModelAdmin):
    pass


class TimelineEventForm(AdminModelFormLARPStringAware):
    class Meta:
        model = TimelineEvent
        exclude = []
@admin.register(TimelineEvent, site=admin_site)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ('date', 'default_description', 'game',)
    list_filter = ('game__name',)
    ordering = ('game', '-date',)
    form = TimelineEventForm

class TimelineEventSheetDescriptionForm(AdminModelFormLARPStringAware):
    class Meta:
        model = TimelineEventSheetDescription
        exclude = []
    def get_game(self, instance):
        return instance.event.game
@admin.register(TimelineEventSheetDescription, site=admin_site)
class TimelineEventSheetDescriptionAdmin(admin.ModelAdmin):
    form = TimelineEventSheetDescriptionForm
    list_filter = ('event__game__name',)
