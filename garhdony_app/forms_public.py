
from django import forms

class Choice:
    def __init__(self, text, values): # Values is a dict of {Kelemen: 3 ...}
        self.text = text
        self.values = values

class Question:
    def __init__(self, text, choices):
        self.text = text
        self.choices = choices
    def formField(self):
        return forms.ChoiceField(widget=forms.RadioSelect,
                                    label = self.text,
                                    choices= ((str(i), self.choices[i].text,) for i in range(len(self.choices))))

Questions = [
    Question(
		"All right, you've got your BA in English. What's next?",
		[Choice("Straight to PhD",{"Zofiya":2}),
		Choice("Entry-level corporate job",{"Kelemen":2,"Zofiya":1,"Lorink":2}),
		Choice("Travel the world for a year",{"Marika": 1,"Sandor":1,"Almos":2}),
		Choice("Write the next great American novel",{"Sandor":2}),
		Choice("Unpaid internship on the Hill",{"Kelemen":2}),
		Choice('''Unpaid "internship" on your parent's couch''',{"Marika": 1,"Sandor":1}),
		]),
	Question(
		"You're working as an assistant to a businessman and discover that he's been cheating poor customers. What do you do?",
		[Choice("Confront him privately and convince him to stop",{"Marika": 2,"Kelemen":1,"Sandor":2}),
		Choice("Confront him privately and demand a cut",{"Zofiya":1,"Lorink":2}),
		Choice("Gather damning evidence over a few weeks and hand it over to the authorities",{"Kelemen":2,"Zofiya":2}),
		Choice("Confront him publicly and expose him",{"Kelemen":1,"Almos":2}),
		Choice("Anonymously expose him to those he's been exploiting",{"Sandor":2}),
		Choice("Quit and look for new work, without confronting him",{"Marika": 1,"Sandor":1}),
		Choice("Turn a blind eye and continue working",{"Lorink":2}),
		]),
	Question(
		"You have a history paper due on Monday. What are you doing on Sunday afternoon?",
		[Choice("Revising your A paper into an A+ paper",{"Zofiya":2}),
		Choice("Trading papers with your study buddy for last-minute revisions",{"Marika": 2,"Sandor":2,"Zofiya":1}),
		Choice("Nursing a hangover and preparing for an all-nighter",{"Kelemen":1,"Almos":2}),
		Choice("Nursing a hangover, but your paper is already finished",{"Kelemen":2,"Zofiya":1}),
		Choice("Returning from a weekend adventure and preparing for an all-nighter",{"Almos":2}),
		Choice("Bottomless mimosas and plagiarism!",{"Lorink":2}),
		]),
	Question(
		"Which of the following would make you the most relaxed?",
		[Choice("Curling up at home with a good book",{"Zofiya":2}),
		Choice("Drinking beer at the bar with your friends",{"Kelemen":1,"Sandor":2,"Almos":1,"Lorink":1}),
		Choice("Watch the game",{"Marika": 1,"Kelemen":1,"Almos":2}),
		Choice("Browsing your news feeds",{"Marika": 1,"Kelemen":2}),
		Choice("Sitting on a rock in a field and playing your lute",{"Sandor":2,"Almos":1}),
		Choice("Just sitting there in a beautiful place",{"Marika": 2,"Almos":1}),
		Choice("Start a comment war on your friend's facebook wall and watch it burn",{"Lorink":2}),
		]),
	Question(
		"You're 40 and unmarried. What's wrong with you?",
		[Choice("You've dated, but you're still searching for your one true love",{"Marika": 2,"Sandor":2}),
		Choice("You have more important things to worry about",{"Marika": 2,"Kelemen":2,"Zofiya":2}),
		Choice("You're afraid of commitment",{"Almos":2,"Lorink":1}),
		Choice("Adultery and/or murder",{"Lorink":2}),
		]),
	Question(
		"When are you most in the zone?",
		[Choice("Solving an engrossing puzzle",{"Zofiya":2}),
		Choice("High-stakes racquetball showdown",{"Almos":2,"Lorink":1}),
		Choice("Jam session",{"Sandor":2}),
		Choice("Managing a crisis",{"Marika": 1,"Kelemen":2,"Zofiya":1}),
		Choice("Yoga",{"Marika": 2}),
		Choice("Making the rounds at the party",{"Marika": 1,"Kelemen":2,"Almos":1,"Lorink":1}),
		Choice("Making love",{"Sandor":2,"Lorink":1}),
		Choice("Extracting confessions",{"Lorink":2}),
		]),
	Question(
		"Out of these, what's your favorite TV show?",
		[Choice("Game of Thrones",{"Kelemen":2,"Lorink":2}),
		Choice("Friday Night Lights",{"Marika": 2,"Kelemen":1}),
		Choice("Friends",{"Marika": 1,"Sandor":2}),
		Choice("Lost",{"Zofiya":2,"Almos":1,"Lorink":1}),
		Choice("Buffy the Vampire Slayer",{"Sandor":1,"Almos":2}),
		Choice("Breaking Bad",{"Zofiya":1,"Lorink":2}),
		]),
	Question(
		"What's your favorite space show?",
		[Choice("Star Trek (Original Series)",{"Zofiya":1,"Almos":2}),
		Choice("Star Trek: Next Generation",{"Sandor":1,"Zofiya":2,"Almos":1}),
		Choice("Star Trek: Deep Space 9",{"Marika": 2,"Kelemen":2}),
		Choice("Firefly",{"Sandor":2,"Almos":1}),
		Choice("Battlestar Galactica",{"Marika": 1,"Kelemen":1,"Almos":2}),
		Choice("Babylon 5",{"Marika": 2,"Zofiya":2,"Lorink":2}),
		Choice("Cosmos",{"Zofiya":2}),
		]),
	Question(
		"What's stopping you from being the perfect boss?",
		[Choice("You micromanage a bit much",{"Kelemen":2}),
		Choice("You have great concepts but you have trouble communicating them",{"Zofiya":2}),
        Choice("You refuse to deviate from your vision, other opinions be damned",{"Sandor":2}),
        Choice("You chase after big picture ideas and miss the little things",{"Almos":2}),
		Choice("You won't fire bad employees because you feel bad about it",{"Marika": 2}),
		Choice("Your core business (making short, funny videos of animals being maimed) doesn't quite have the widespread appeal you'd hoped",{"Lorink":2}),
		]),
	Question(
		"New England has been annihilated by an asteroid. You survived! Choose an American city to move to.",
		[Choice("Washington, DC",{"Kelemen":2}),
		Choice("San Francisco",{"Zofiya":2}),
		Choice("Denver",{"Almos":2}),
		Choice("Austin",{"Sandor":2}),
		Choice("Chicago",{"Marika": 2}),
		Choice("The barren hellscape formerly known as Cambridge, Massachusetts",{"Lorink":2}),
		]),
	Question(
		"""Choose a facebook post to "like":""",
		[Choice("Thinkpiece about privacy vs security",{"Kelemen":2}),
		Choice("Engagement photoshoot!",{"Sandor":2}),
		Choice("Heartfelt remembrance post about a high school classmate who died",{"Marika": 2}),
		Choice("Mountaintop selfie!",{"Almos":2}),
		Choice("Statistical analysis of subway ridership",{"Zofiya":2}),
		Choice("Thinkpiece literally advocating for the devil",{"Lorink":3}),
		])
]

class AscendedQuizForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(AscendedQuizForm, self).__init__(*args, **kwargs)
        for i, question in enumerate(Questions):
            self.fields['question_%s' % i] = question.formField()