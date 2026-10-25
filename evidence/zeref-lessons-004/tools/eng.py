# subject english. G rows: (subject, topic, note, [(q,a,regex)]) ; H rows: (subject,q,ref,regex)
G=[];H=[]
def g(topic,note,rows,subject="english"):G.append((subject,topic,note,rows))
def h(rows,subject="english"):H.extend((subject,q,a,e) for q,a,e in rows)

# ---- opposites
OPP=[("hot","cold"),("up","down"),("big","small"),("fast","slow"),("happy","sad"),("day","night"),("open","closed"),("wet","dry"),("full","empty"),("old","new"),("hard","soft"),("light","dark"),("loud","quiet"),("near","far"),("high","low"),("long","short"),("in","out"),("yes","no"),("start","stop"),("push","pull"),("young","old"),("clean","dirty"),("early","late"),("front","back"),("thick","thin"),("strong","weak"),("tall","short"),("win","lose"),("wide","narrow"),("sweet","sour")]
HOLD_OPP=[("black","white"),("left","right"),("good","bad"),("over","under"),("laugh","cry"),("first","last")]
rows=[]
for a,b in OPP:
    rows.append((f"What is the opposite of {a}?",f"The opposite of {a} is {b}.",b))
for a,b in OPP[:14]:
    rows.append((f"What word means the opposite of {b}?",f"{a[0].upper()+a[1:]} is the opposite of {b}.",a))
g("opposites","Good: names the true opposite word in a short sentence.",rows)
h([(f"What is the opposite of {a}?",f"The opposite of {a} is {b}.",b) for a,b in HOLD_OPP])

# ---- plurals
PL=[("cat","cats"),("dog","dogs"),("star","stars"),("book","books"),("tree","trees"),("bird","birds"),("fish","fish"),("mouse","mice"),("foot","feet"),("tooth","teeth"),("child","children"),("man","men"),("woman","women"),("box","boxes"),("bus","buses"),("dish","dishes"),("church","churches"),("baby","babies"),("puppy","puppies"),("leaf","leaves"),("wolf","wolves"),("sheep","sheep"),("goose","geese"),("cherry","cherries"),("moon","moons"),("flower","flowers"),("kitten","kittens"),("glass","glasses")]
HPL=[("hat","hats"),("fox","foxes"),("lady","ladies"),("knife","knives"),("ox","oxen")]
rows=[(f"What is the plural of {a}?",f"The plural of {a} is {b}.",b) for a,b in PL]
rows+=[(f"If there are two {b}, how many {a}s is that... what do we call one?",f"One is a {a}.",a) for a,b in PL[:0]]
rows+=[(f"What do we call more than one {a}?",f"More than one {a} is {b}.",b) for a,b in PL[:10]]
g("plurals","Good: gives the right plural word, including odd ones like mice and feet.",rows)
h([(f"What is the plural of {a}?",f"The plural of {a} is {b}.",b) for a,b in HPL])

# ---- rhymes
RH=[("cat","hat"),("dog","log"),("sun","fun"),("moon","spoon"),("star","car"),("tree","bee"),("bed","head"),("ball","wall"),("rain","train"),("night","light"),("cake","lake"),("fish","dish"),("bear","chair"),("book","look"),("hop","top"),("pig","wig"),("mouse","house"),("bell","well"),("snow","glow"),("ring","sing"),("cow","now"),("boat","coat"),("jam","ham"),("pen","hen"),("fly","sky")]
HRH=[("bug","hug"),("nest","best"),("fan","pan"),("knee","key"),("clock","rock")]
g("rhymes","Good: names one real rhyming word.",[(f"What rhymes with {a}?",f"{b[0].upper()+b[1:]} rhymes with {a}.",b) for a,b in RH]+[(f"Does {a} rhyme with {b}?",f"Yes, {a} and {b} rhyme.","yes") for a,b in RH[:10]]+[(f"Does {a} rhyme with {c}?",f"No, {a} and {c} do not rhyme.","no") for a,c in [("cat","dog"),("sun","moon"),("tree","ball"),("bed","fish"),("star","pig"),("rain","book")]])
h([(f"What rhymes with {a}?",f"{b[0].upper()+b[1:]} rhymes with {a}.",b) for a,b in HRH]+[("Does bug rhyme with rug?","Yes, bug and rug rhyme.","yes"),("Does tree rhyme with moon?","No, tree and moon do not rhyme.","no")])

# ---- a vs an
AN=[("apple","an"),("egg","an"),("orange","an"),("umbrella","an"),("elephant","an"),("ice cube","an"),("ant","an"),("owl","an"),("dog","a"),("cat","a"),("star","a"),("book","a"),("fish","a"),("house","a"),("moon","a"),("tree","a"),("pig","a"),("kitten","a")]
HAN=[("ostrich","an"),("igloo","an"),("hat","a"),("lamp","a")]
g("a and an","Good: picks a before a consonant sound and an before a vowel sound.",[(f"Do we say a {w} or an {w}?",f"We say {x} {w}.",f"\\b{x} {w}") for w,x in AN])
h([(f"Do we say a {w} or an {w}?",f"We say {x} {w}.",f"\\b{x} {w}") for w,x in HAN])

# ---- past tense
PT=[("run","ran"),("eat","ate"),("jump","jumped"),("go","went"),("see","saw"),("play","played"),("sit","sat"),("make","made"),("sleep","slept"),("walk","walked"),("give","gave"),("come","came"),("fall","fell"),("swim","swam"),("sing","sang"),("look","looked"),("take","took"),("draw","drew"),("fly","flew"),("write","wrote")]
HPT=[("drink","drank"),("hop","hopped"),("find","found"),("catch","caught")]
g("past tense","Good: gives the right past form of the verb.",[(f"What is the past of {a}?",f"The past of {a} is {b}.",b) for a,b in PT]+[(f"Yesterday I {b}. What is the word for now?",f"For now we say {a}.",a) for a,b in PT[:6]])
h([(f"What is the past of {a}?",f"The past of {a} is {b}.",b) for a,b in HPT])

# ---- synonyms and word meanings
VOC=[("tiny","Tiny means very, very small.","small"),("huge","Huge means very, very big.","big"),("glad","Glad means happy.","happy"),("quick","Quick means fast.","fast"),("sleepy","Sleepy means you want to sleep.","sleep"),("hungry","Hungry means you want to eat.","eat"),("thirsty","Thirsty means you want a drink.","drink"),("brave","Brave means not afraid to try.","afraid|try"),("gentle","Gentle means soft and kind.","soft|kind"),("noisy","Noisy means loud.","loud"),("shiny","Shiny means bright and sparkly.","bright|sparkl"),("fluffy","Fluffy means soft like a kitten's fur.","soft|fur"),("cozy","Cozy means warm and comfortable.","warm|comfort"),("empty","Empty means nothing is inside.","nothing"),("giant","A giant is something very big.","big"),("whisper","To whisper is to speak very softly.","soft"),("shout","To shout is to speak very loudly.","loud"),("friend","A friend is someone who likes you and is kind to you.","like|kind"),("curious","Curious means you want to learn about things.","learn"),("careful","Careful means you pay attention so nothing goes wrong.","attention|safe"),("sparkle","To sparkle is to shine with little flashes.","shine|flash"),("pretty","Pretty means nice to look at.","nice|look"),("ancient","Ancient means very, very old.","old"),("rough","Rough means not smooth.","smooth"),("calm","Calm means quiet and not upset.","quiet|upset")]
HVOC=[("enormous","Enormous means very, very big.","big"),("freezing","Freezing means very, very cold.","cold"),("silent","Silent means with no sound.","sound|quiet"),("delicious","Delicious means tastes very good.","tast|good")]
g("word meanings","Good: a short simple meaning in kid words.",[(f"What does {w} mean?",m,e) for w,m,e in VOC]+[(f"Can you tell me what '{w}' means?",m,e) for w,m,e in VOC[:8]])
h([(f"What does {w} mean?",m,e) for w,m,e in HVOC])
SYN=[("big","large"),("small","little"),("happy","glad"),("fast","quick"),("start","begin"),("end","finish"),("pretty","lovely"),("sad","unhappy"),("mad","angry"),("tired","sleepy"),("shut","close"),("hurry","rush")]
HSYN=[("rock","stone"),("kid","child"),("choose","pick")]
g("same meaning words","Good: gives a word with the same meaning.",[(f"What is another word for {a}?",f"Another word for {a} is {b}.",b) for a,b in SYN])
h([(f"What is another word for {a}?",f"Another word for {a} is {b}.",b) for a,b in HSYN])

# ---- sentences & grammar
g("sentences and punctuation","Good: short, true grammar answer.",[
("What goes at the end of a question?","A question mark.","question mark"),
("What goes at the end of a sentence that tells something?","A period, or a dot.","period|dot"),
("What mark shows excitement?","An exclamation mark.","exclamation"),
("What letter does a sentence start with?","A capital letter.","capital"),
("What is a sentence?","A group of words that tells a whole thought.","words|thought"),
("What is a noun?","A word for a person, place or thing.","person|place|thing"),
("What is a verb?","An action word, like run or jump.","action"),
("What is an adjective?","A word that tells more about a noun, like big or red.","noun|tells"),
("Is 'run' a noun or a verb?","Run is a verb. It's an action.","verb"),
("Is 'cat' a noun or a verb?","Cat is a noun. It's a thing.","noun"),
("Is 'jump' an action word?","Yes. Jump is an action word.","yes"),
("Is 'blue' an adjective?","Yes. Blue tells what color something is.","yes"),
("Is 'happy' an adjective?","Yes. It tells how someone feels.","yes"),
("Is 'table' a noun?","Yes. A table is a thing.","yes"),
("Is 'sing' a verb?","Yes. Sing is an action.","yes"),
("What is a word that names a person?","A noun, like girl or teacher.","noun"),
("What do we call the first word in a name?","A capital letter starts it. Names start with capitals.","capital"),
("Should the word Cory start with a capital letter?","Yes. Names start with capital letters.","yes"),
("Which one is a whole sentence: the cat sleeps, or just the cat?","The cat sleeps is a whole sentence.","sleeps"),
("Which is right: 'I am happy' or 'I is happy'?","I am happy.","am happy"),
("Which is right: 'She runs' or 'She run'?","She runs.","runs"),
("Which is right: 'They are here' or 'They is here'?","They are here.","are here"),
("Which is right: 'He has a ball' or 'He have a ball'?","He has a ball.","has a ball"),
("What is the word for 'I' and 'you' and 'we'?","They are pronouns.","pronoun"),
("What word means more than one of me?","We. That means me and others.","we"),
("What do we call a word like he or she?","A pronoun.","pronoun"),
("How many words are in 'The sun is warm'?","Four words.","four|\\b4\\b"),
("How many words are in 'I like cats'?","Three words.","three|\\b3\\b"),
("How many words are in 'Rawr'?","One word.","one|\\b1\\b"),
])
h([("Which is right: 'We are friends' or 'We is friends'?","We are friends.","are friends"),("Is 'soft' an adjective?","Yes. Soft tells how something feels.","yes"),("How many words are in 'Birds can fly'?","Three words.","three|\\b3\\b"),("What mark ends a question?","A question mark.","question mark"),("Is 'dance' a noun or a verb?","Dance is a verb.","verb")])

# ---- fill in short sentences (reading)
FILL=[("The cat sat on the ___.","mat","The cat sat on the mat."),("The sun is in the ___.","sky","The sun is in the sky."),("A fish lives in the ___.","water","A fish lives in the water."),("A bird can ___.","fly","A bird can fly."),("We sleep at ___.","night","We sleep at night."),("A dog says ___.","woof","A dog says woof."),("I brush my ___.","teeth","I brush my teeth."),("The moon comes out at ___.","night","The moon comes out at night."),("Rain falls from the ___.","sky|clouds|cloud","Rain falls from the clouds."),("A kitten says ___.","meow","A kitten says meow."),("Ice is ___.","cold","Ice is cold."),("Fire is ___.","hot","Fire is hot."),("We use our eyes to ___.","see","We use our eyes to see."),("We wear shoes on our ___.","feet","We wear shoes on our feet."),("Bees make ___.","honey","Bees make honey."),("The grass is ___.","green","The grass is green."),("A cow gives us ___.","milk","A cow gives us milk."),("We read a ___.","book","We read a book."),("A baby cat is a ___.","kitten","A baby cat is a kitten."),("Snow is ___.","white|cold","Snow is white.")]
g("finish the sentence","Good: a single fitting word that makes a true, sensible sentence.",[(f"Finish this: {s}",a,e) for s,e,a in FILL])
HFILL=[("The dog wags its ___.","tail","The dog wags its tail."),("We drink ___.","water","We drink water."),("A frog can ___.","hop|jump|swim","A frog can hop."),("The stars come out at ___.","night","The stars come out at night.")]
h([(f"Finish this: {s}",a,e) for s,e,a in HFILL])

READ=[("Read: 'Sam has a red ball.' What does Sam have?","Sam has a red ball.","ball"),("Read: 'Sam has a red ball.' What color is the ball?","The ball is red.","red"),("Read: 'The dog ran fast.' Who ran?","The dog ran.","dog"),("Read: 'The dog ran fast.' How did the dog run?","The dog ran fast.","fast"),("Read: 'Mia likes to paint.' What does Mia like?","Mia likes to paint.","paint"),("Read: 'A bird sat on a tree.' Where did the bird sit?","The bird sat on a tree.","tree"),("Read: 'It is cold, so Ben wears a coat.' Why does Ben wear a coat?","Because it is cold.","cold"),("Read: 'Lily has two cats and one dog.' How many cats does Lily have?","Lily has two cats.","two|\\b2\\b"),("Read: 'Tom ate an apple.' What did Tom eat?","Tom ate an apple.","apple"),("Read: 'The sun went down and the stars came out.' What came out?","The stars came out.","star"),("Read: 'Kim has a yellow hat.' Who has a hat?","Kim has a hat.","kim"),("Read: 'The fish swims in the pond.' Where does the fish swim?","In the pond.","pond"),("Read: 'Ava is sleepy, so she goes to bed.' Why does Ava go to bed?","Because she is sleepy.","sleepy"),("Read: 'Max has three red balloons.' How many balloons does Max have?","Max has three balloons.","three|\\b3\\b"),("Read: 'The kitten drank some milk.' What did the kitten drink?","The kitten drank milk.","milk"),("Read: 'Jo plays in the snow.' Where does Jo play?","Jo plays in the snow.","snow"),("Read: 'A red car stopped.' What color is the car?","The car is red.","red"),("Read: 'Pat feeds the ducks.' Who does Pat feed?","Pat feeds the ducks.","duck")]
g("short reading","Good: answers from the little sentence only, in a short reply.",READ)
h([("Read: 'Ana has a blue kite.' What color is the kite?","The kite is blue.","blue"),("Read: 'The cat sleeps on the bed.' Where does the cat sleep?","On the bed.","bed"),("Read: 'Leo has four toy cars.' How many cars does Leo have?","Leo has four cars.","four|\\b4\\b"),("Read: 'It rains, so Zoe takes an umbrella.' Why does Zoe take an umbrella?","Because it rains.","rain"),("Read: 'Dan kicked the ball.' What did Dan kick?","Dan kicked the ball.","ball")])

# ---- spelling, letters, syllables, days, months
SP=["cat","dog","sun","moon","star","fish","tree","book","milk","frog","bird","rain","cake","bed","hat"]
HSP=["pig","car","ball"]
def spell(w):return ", ".join(c.upper() for c in w)
g("spelling","Good: letters in order, separated.",[(f"How do you spell {w}?",f"{w} is spelled {spell(w)}.",spell(w).replace(", ",".*")) for w in SP])
h([(f"How do you spell {w}?",f"{w} is spelled {spell(w)}.",spell(w).replace(", ",".*")) for w in HSP])
SY=[("cat",1),("dog",1),("rabbit",2),("banana",3),("elephant",3),("table",2),("butterfly",3),("sun",1),("pizza",2),("kitten",2),("computer",3),("tree",1)]
HSY=[("pencil",2),("umbrella",3),("moon",1)]
NW={1:"one",2:"two",3:"three"}
g("syllables","Good: the right count of beats.",[(f"How many syllables are in {w}?",f"{w[0].upper()+w[1:]} has {NW[n]} syllable{'s' if n>1 else ''}.",f"{NW[n]}|\\b{n}\\b") for w,n in SY])
h([(f"How many syllables are in {w}?",f"{w[0].upper()+w[1:]} has {NW[n]} syllable{'s' if n>1 else ''}.",f"{NW[n]}|\\b{n}\\b") for w,n in HSY])
g("days and months","Good: the right day or month in order.",[
("What day comes after Monday?","Tuesday.","tuesday"),("What day comes after Tuesday?","Wednesday.","wednesday"),("What day comes after Wednesday?","Thursday.","thursday"),("What day comes after Thursday?","Friday.","friday"),("What day comes after Sunday?","Monday.","monday"),("What day comes before Friday?","Thursday.","thursday"),("What day comes before Sunday?","Saturday.","saturday"),("What day comes before Wednesday?","Tuesday.","tuesday"),("Which days are the weekend?","Saturday and Sunday.","saturday"),("What is the first day of the school week?","Monday.","monday"),
("What month comes after January?","February.","february"),("What month comes after March?","April.","april"),("What month comes after May?","June.","june"),("What month comes after July?","August.","august"),("What month comes after September?","October.","october"),("What month comes after November?","December.","december"),("What month comes before April?","March.","march"),("What month comes before August?","July.","july"),("What is the first month of the year?","January.","january"),("What is the last month of the year?","December.","december"),
("Name the four seasons.","Spring, summer, fall and winter.","spring"),("Which season is the coldest?","Winter.","winter"),("Which season is the warmest?","Summer.","summer"),("Which season comes after winter?","Spring.","spring"),("Which season comes after summer?","Fall, also called autumn.","fall|autumn"),
])
h([("What day comes after Saturday?","Sunday.","sunday"),("What day comes before Tuesday?","Monday.","monday"),("What month comes after June?","July.","july"),("What month comes before October?","September.","september"),("Which season comes after spring?","Summer.","summer")])

# ---- letters and sounds (distinct from lessons-003: vowels, alphabet order by position)
g("alphabet","Good: the right letter.",[
("How many letters are in the alphabet?","Twenty-six.","twenty-six|26"),("What are the vowels?","A, E, I, O and U.","a, e, i, o"),("Is B a vowel?","No. B is a consonant.","no|consonant"),("Is E a vowel?","Yes. E is a vowel.","yes|vowel"),("Is T a vowel or a consonant?","T is a consonant.","consonant"),("Is O a vowel?","Yes. O is a vowel.","yes"),("What is the last letter of the alphabet?","Z.","\\bz\\b"),("What is the first letter of the alphabet?","A.","\\ba\\b"),("What letter comes between B and D?","C.","\\bc\\b"),("What letter comes between M and O?","N.","\\bn\\b"),("What letter comes between R and T?","S.","\\bs\\b"),("What letter comes between H and J?","I.","\\bi\\b"),("What letter comes before Q?","P.","\\bp\\b"),("What letter comes before K?","J.","\\bj\\b"),("What letter comes after U?","V.","\\bv\\b"),("What letter comes after X?","Y.","\\by\\b"),("What letter does 'sun' begin with?","S.","\\bs\\b"),("What letter does 'moon' begin with?","M.","\\bm\\b"),("What letter does 'kitten' begin with?","K.","\\bk\\b"),("What letter does 'fish' end with?","H.","\\bh\\b"),("What letter does 'cat' end with?","T.","\\bt\\b"),("What is the first letter of 'apple'?","A.","\\ba\\b"),("What is the first letter of 'zebra'?","Z.","\\bz\\b"),("What sound does the letter S make?","Sss, like a snake.","s"),("What sound does the letter M make?","Mmm, like yummy.","m"),
])
h([("What letter comes between E and G?","F.","\\bf\\b"),("What letter comes before W?","V.","\\bv\\b"),("What is the first letter of 'owl'?","O.","\\bo\\b"),("Is D a vowel or a consonant?","D is a consonant.","consonant"),("What letter does 'dog' end with?","G.","\\bg\\b")])

# ---- rhyme-time / simple short stories & manners words
g("describing words","Good: a fitting simple word for what is asked.",[
("What color is the sky on a sunny day?","Blue.","blue"),("Name a word that describes ice.","Cold.","cold"),("Name a word that describes a feather.","Light, or soft.","light|soft"),("Name a word that describes a rock.","Hard.","hard"),("Name a word that describes a kitten.","Fluffy, or small.","fluffy|small|soft"),("Name a word that describes a lion's roar.","Loud.","loud"),("Name a word that describes honey.","Sweet.","sweet"),("Name a word that describes a lemon.","Sour.","sour"),("Name a word that describes a pillow.","Soft.","soft"),("Name a word that describes a turtle.","Slow.","slow"),("Name a word that describes a cheetah.","Fast.","fast"),("Name a word that describes the night sky.","Dark.","dark"),("Name a word that describes a mountain.","Tall, or big.","tall|big|high"),("Name a word that describes soup.","Warm, or hot.","warm|hot"),
])
h([("Name a word that describes a snowman.","Cold, or white.","cold|white"),("Name a word that describes a bunny's fur.","Soft.","soft"),("Name a word that describes a bee sting.","Sharp, or sore.","sharp|sore|hurt|ouch")])
