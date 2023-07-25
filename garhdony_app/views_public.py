"""
The views that you can see without logging in.
"""
from django.urls import reverse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.generic import View, TemplateView
from django.http import HttpResponseRedirect
from garhdony_app.forms_public import AscendedQuizForm, Questions
from garhdony_app.models import GameTemplate, WebsiteAboutPage, QuizSubmission
from collections import Counter


def main_page(request):
    all_games = GameTemplate.objects.all()
    upcoming_games = [game for game in all_games if game.is_upcoming ]
    other_games = [game for game in all_games if not game.is_upcoming ]
    return render(request, 'garhdony_app/index.html', {"here": "Home", "upcoming_games": upcoming_games, "other_games": other_games})
    # here is the arg that tells the tabs at the top which is selected.


def about_page(request):
    about_page = WebsiteAboutPage.objects.all()[0]
    return render(request, 'garhdony_app/about.html', {"here": "About", "content": about_page.content }) # here is the arg that tells the tabs at the top which is selected.

def game_blurb_page(request, game):
    game_object = GameTemplate.objects.get(name=game)
    return render(request, 'garhdony_app/game_blurb.html', {"here": "Home", "game": game_object})

def game_about_page(request, game):
    game_object = GameTemplate.objects.get(name=game)
    return render(request, 'garhdony_app/game_about.html', {"here": "About", "game": game_object})

def game_how_to_app_page(request, game):
    game_object = GameTemplate.objects.get(name=game)
    return render(request, 'garhdony_app/game_how_to_app.html', {"here": "How To Apply", "game": game_object})

def game_app_page(request, game):
    game_object = GameTemplate.objects.get(name=game)
    return render(request, 'garhdony_app/game_app.html', {"here": "How To Apply", "game": game_object})

Descriptions = {
    "Marika":  "Your patron Ascended is Marika, The Silver Queen! Followers of Marika value faith, forgiveness, redemption, and tradition. Many of Garhdony's priests take Marika as their patron. The cathedral of Marika is located in Sarvahr; she is the most popular patron among all commonfolk, especially in Ambrus where her cathedral sits and Tzonka, widely considerd the most devout kingdom.",
    "Kelemen": "Your patron Ascended is Kelemen, The Eternal King! Followers of Kelemen value justice, order, and loyalty. Many of Garhdony's rulers and law enforcement take Kelemen as their patron. The cathedral of Kelemen is located in Vac and he is a popular patron among commonfolk in most major cities.",
    "Sandor": "Your patron Ascended is Sandor, The Painter of Memory! Followers of Sandor value love, beauty, and art. Many of Garhdony's artists, artisans, and musicians take Sandor as their patron. The cathedral of Sandor is located in Suumeg and he is a popular patron among commonfolk in Tzonka.",
    "Zofiya": "Your patron Ascended is Zofiya, The Warden of Secrets! Followers of Zofiya value knowledge and curiosity. Many of Garhdony's wizards and scholars take Zofiya as their patron. The cathedral of Zofiya is located in Vehsto and she is a popular patron among commonfolk in Kazka.",
    "Almos": "Your patron Ascended is Almos, The Truthseeker! Followers of Almos value adventure, truth, and honor. Many of Garhdony's knights take Almos as their patron. The cathedral of Almos is located in Seratal and he is a popular patron among commonfolk in Rihul.",
    "Lorink": "Your patron Ascended is... Lorink the Antagonist? Lorink is not an Ascended. Lorink is the <i>antagonist</i> to the Ascended, who marshaled the forces of evil during the Years of Terror. You're not allowed to take Lorink as your patron. Try again and pick answers that are less terrible."
}

class GendersView(TemplateView):
    template_name = "garhdony_app/genders.html"

class AscendedFormView(View):
    form_class = AscendedQuizForm
    template_name = 'garhdony_app/ascended_quiz_template.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        if request.method == 'GET' and request.GET.has_key('result'):
            winner = request.GET['result']
            if Descriptions.has_key(winner):
                text = Descriptions[winner]
                imgsrc = request.build_absolute_uri(static('garhdony_app/'+winner+'.png'))
                return render(request, 'garhdony_app/ascended_quiz_results.html',
                          {'winner':winner, "text":text, 'imgsrc':imgsrc.lower()})
            else:
                imgsrc = request.build_absolute_uri(static('garhdony_app/all-ascended.png'))
                return render(request, self.template_name, {'form': form, 'imgsrc': imgsrc})
        else:
            imgsrc = request.build_absolute_uri(static('garhdony_app/all-ascended.png'))
            return render(request, self.template_name, {'form': form, 'imgsrc': imgsrc})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            scores = {"Kelemen": 0, "Almos":0, "Marika":0, "Sandor":0, "Zofiya":0, "Lorink":0}
            for i, question in enumerate(Questions):
                chosen_index = form.cleaned_data['question_%s' % i]
                values = question.choices[int(chosen_index)].values
                for ascended in scores:
                    if ascended in values:
                        scores[ascended]+=values[ascended]
            winner = max(scores, key=scores.get)
            submission = QuizSubmission()
            submission.result = winner
            submission.save()
            return HttpResponseRedirect(reverse('quiz') + '?result=' + winner)

        imgsrc = request.build_absolute_uri(static('garhdony_app/all-ascended.png'))
        return render(request, self.template_name, {'form': form, 'imgsrc': imgsrc})

def ascended_quiz_statistics(request):
    submissions = [sub.result for sub in QuizSubmission.objects.all()]
    counts = Counter(submissions)
    results = [[a, counts[a]] for a in counts.keys()]
    return render(request, 'garhdony_app/ascended_quiz_statistics.html', {'results':results})
