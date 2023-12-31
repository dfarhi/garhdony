from django.urls import re_path as url
from django.contrib import admin
from django.urls import reverse_lazy
from garhdony_app.forms_users import DogmasAuthenticationForm
from garhdony_app.admin import admin_site
from main import settings
from garhdony_app.views_users import NewWriterView
import garhdony_app.views_public
import garhdony_app.views_players
import garhdony_app.views_characters
import garhdony_app.views_game_design
import garhdony_app.views_writing
import garhdony_app.views_media
import garhdony_app.views_users
import django.views.i18n
import django.contrib.auth.views


admin.autodiscover()

urlpatterns = (
    # urls used to include '' but we removed it because of E004

    #### Public ####
    url(r'^$', garhdony_app.views_public.main_page, name='main'),
    url(r'^about/$', garhdony_app.views_public.about_page, name='about'),
    url(r'^ascended_quiz/$', garhdony_app.views_public.AscendedFormView.as_view(), name='quiz'),
    url(r'^ascended_quiz_statistics/$', garhdony_app.views_public.ascended_quiz_statistics, name='quiz_stats'),
    url(r'^genders/$', garhdony_app.views_public.GendersView.as_view(), name='genders'),
    url(r'^([^/]+)/home/$', garhdony_app.views_public.game_blurb_page, name='game_blurb'),
    url(r'^([^/]+)/about/$', garhdony_app.views_public.game_about_page, name='game_about'),
    url(r'^([^/]+)/how_to_apply/$', garhdony_app.views_public.game_how_to_app_page, name='game_how_to_app'),
    url(r'^([^/]+)/apply/$', garhdony_app.views_public.game_app_page, name='game_app'),

    #### Players and Logistics####
    url(r'^([^/]+)/character/([^/]+)/welcome/$', garhdony_app.views_players.character_welcome, name='character_welcome'),
    url(r'^([^/]+)/character/([^/]+)/abdicate/$', garhdony_app.views_players.character_abdicate, name='character_abdicate'),
    url(r'^abdicated/$', garhdony_app.views_players.actually_abdicated, name='actually_abdicated'),
    url(r'^([^/]+)/character/([^/]+)/logistics/([^/]+)/$', garhdony_app.views_players.character_logistics_task,
        name='character_logistics_task'),
    url(r'^([^/]+)/character/([^/]+)/logistics/$', garhdony_app.views_players.character_logistics,
        name='character_logistics'),
    url(r'^writing/([^/]+)/logistics/table/$', garhdony_app.views_players.logistics_table,
        name='game_writer_logistics_table'),

    #### Admin interface ####
    url(r'^admin/jsi18n/$', django.views.i18n.JavaScriptCatalog.as_view(packages=['django.contrib.admin'])),
    url(r'^admin/', admin_site.urls),

    #### Users logging in and out ####
    url(r'^login/', django.contrib.auth.views.LoginView.as_view(template_name='garhdony_app/login.html', authentication_form=DogmasAuthenticationForm),
        name='login_view'),
    url(r'^logout_then_login(.*)$', garhdony_app.views_users.logout_then_login, name='logout_then_login'), # No trailing slash to make the redirect start with a slash.
    url(r'^logout/$', django.contrib.auth.views.LogoutView.as_view(next_page=reverse_lazy('about')),
        name='logout_view'),
    url(r'^user_redirect/$', garhdony_app.views_users.user_redirect, name="user_redirect"),
    url(r'^writing/new_writer', NewWriterView.as_view(), name="new_writer"),

    #### Media ####
    url(r'^media/([^/]+)/player_photos/([^/]+)', garhdony_app.views_media.media_player_photo),
    url(r'^([^/]+)/image/([^/]+)', garhdony_app.views_media.media_sheet_embedded_image, name='embedded_image'),
    url(r'^writing/([^/]+)/sheet/([^/]+)/new_image/([^/]+)', garhdony_app.views_media.media_sheet_upload_image),

    #### Things characters see ####
    url(r'^([^/]+)/character/([^/]+)/$', garhdony_app.views_characters.character_home, name="character_home"),
    url(r'^([^/]+)/character/([^/]+)/contacts/$', garhdony_app.views_characters.character_contacts, name='character_contacts'),
    url(r'^([^/]+)/character/([^/]+)/sheets/([^/]+)/$', garhdony_app.views_characters.character_sheet, name="character_sheet"),

    url(r'^([^/]+)/character/([^/]+)/all_sheets/$', garhdony_app.views_characters.past_player_all_sheets,
        name="past_player_all_sheets"),
    url(r'^([^/]+)/character/([^/]+)/all_sheets/([^/]+)/$', garhdony_app.views_characters.past_player_sheet,
        name="past_player_sheet"),

    #### Game Design ####
    url(r'^writing/$', garhdony_app.views_game_design.writing_home, name='writer_home'),
    url(r'^writing/new$', garhdony_app.views_game_design.writing_new_game, name='writing_new_game'),
    url(r'^writing/([^/]+)/$', garhdony_app.views_game_design.writing_game_home, name='game_writer_home'),
    url(r'^writing/([^/]+)/sheetsgrid/$', garhdony_app.views_game_design.writing_game_sheets_grid,
        name='game_writer_sheets_grid'),
    url(r'^writing/([^/]+)/timeline/$', garhdony_app.views_game_design.writing_game_timeline,
        name='game_writer_timeline'),
    url(r'^writing/([^/]+)/timeline/event/delete/([^/]+)$', garhdony_app.views_game_design.timeline_delete_event,
        name='timeline_delete_event'),
    url(r'^writing/([^/]+)/sheetsgrid/modify/$', garhdony_app.views_game_design.sheets_grid_modify,
        name='sheets_grid_modify'),
    url(r'^writing/([^/]+)/characters/table/$', garhdony_app.views_game_design.writing_characters_table,
        name='game_writer_characters_table'),
    url(r'^writing/([^/]+)/sheet/new/$', garhdony_app.views_game_design.writer_new_sheet, name='new_sheet'),
    url(r'^writing/([^/]+)/sheet/delete/$', garhdony_app.views_game_design.delete_sheet, name='delete_sheet'),
    url(r'^writing/([^/]+)/character/new/$', garhdony_app.views_game_design.new_character, name='new_character'),
    url(r'^writing/([^/]+)/character/delete/$', garhdony_app.views_game_design.delete_character, name='delete_character'),
    url(r'^writing/([^/]+)/NPC/([^/]+)/$', garhdony_app.views_game_design.writing_npc, name='writing_npc'),
    url(r'^writing/([^/]+)/sheet/([^/]+)/$', garhdony_app.views_game_design.writer_sheet, name='writer_sheet'),
    url(r'^writing/([^/]+)/sheet/([^/]+)/add_timeline_viewer$', garhdony_app.views_game_design.add_timeline_viewer, name='add_timeline_viewer'),
    url(r'^([^/]+)/character/([^/]+)/contacts/delete$', garhdony_app.views_game_design.character_contacts_delete,
        name='character_contacts_delete'),
    url(r'^add/title_obj/$', garhdony_app.views_game_design.add_title, name='add_title'),
    url(r'^writing/([^/]+)/search/$', garhdony_app.views_game_design.search, name='search'),
    url(r'^writing/([^/]+)/recent_changes/$', garhdony_app.views_game_design.recent_changes, name='recent_changes'),

    #### Writing ####
    url(r'^writing/([^/]+)/sheet/([^/]+)/edit$', garhdony_app.views_writing.writer_sheet_edit, name='writer_sheet_edit'),
    url(r'^writing/([^/]+)/sheet/([^/]+)/presave/$', garhdony_app.views_writing.writer_sheet_presave_handshake, name='writer_sheet_presave_handshake'),
    url(r'^writing/([^/]+)/sheet/([^/]+)/history$', garhdony_app.views_writing.writer_sheet_history, name='sheet_history'),
    url(r'^writing/([^/]+)/sheet/([^/]+)/revert/([0-9]+)$', garhdony_app.views_writing.writer_sheet_revert, name='sheet_revert'),
    url(r'^writing/([^/]+)/sheet/([^/]+)/diff$', garhdony_app.views_writing.writer_sheet_diff, name='sheet_diff'),
    url(r'^writing/([^/]+)/sheet/([^/]+)/history/([0-9]+)$', garhdony_app.views_game_design.writer_sheet, name='writer_sheet_old'),
    url(r'^writing/([^/]+)/sheet/([^/]+)/release$', garhdony_app.views_writing.writer_sheet_release, name='sheet_release'),
    url(r'^([^/]+)/character/[^/]+/sheets/([^/]+)/release$', garhdony_app.views_writing.writer_sheet_release, name='sheet_release_from_character'),
    url(r'^writing/([^/]+)/sheet/([^/]+)/export$', garhdony_app.views_writing.writer_sheet_export),
    url(r'^([^/]+)/character/[^/]+/sheets/([^/]+)/export$', garhdony_app.views_writing.writer_sheet_export, name='sheet_export_from_character'),
    #### For maybe putting back later ####
    # url(r'wiki/', include('djiki.urls')),
)


