import random
G=[];H=[]
def g(topic,note,rows,subject="math"):G.append((subject,topic,note,rows))
def h(rows,subject="math"):H.extend((subject,q,a,e) for q,a,e in rows)
NW=["zero","one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen","twenty"]
def rx(n):return f"\\b{n}\\b"+(f"|{NW[n]}" if n<=20 else "")
rnd=random.Random(4004)
# held-out arithmetic facts (unordered pairs) never trained, nor their swaps
HADD=[(3,4),(6,5),(8,7),(9,9),(2,13),(11,6),(14,5),(10,10),(12,3),(7,6)]
HSUB=[(11,4),(15,8),(9,2),(18,9),(20,7),(13,5),(16,10),(12,6)]
heldpairs={tuple(sorted(p)) for p in HADD}
heldsub=set(HSUB)
add=[];sub=[]
for a in range(1,13):
    for b in range(1,13):
        if tuple(sorted((a,b))) in heldpairs: continue
        if a<=b: add.append((a,b))
for a in range(2,21):
    for b in range(1,a):
        if (a,b) in heldsub: continue
        sub.append((a,b))
rnd.shuffle(add);rnd.shuffle(sub)
add=add[:46];sub=sub[:40]
T=["What is {a} plus {b}?","{a} + {b} = ?","What is {a} and {b} together?","How much is {a} plus {b}?"]
rows=[]
for i,(a,b) in enumerate(add):
    if rnd.random()<.5:a,b=b,a
    q=T[i%4].format(a=a,b=b);rows.append((q,f"{a} plus {b} is {a+b}.",rx(a+b)))
g("adding","Good: the correct sum in a short sentence.",rows)
T2=["What is {a} minus {b}?","{a} - {b} = ?","What is {a} take away {b}?","How much is {a} minus {b}?"]
rows=[(T2[i%4].format(a=a,b=b),f"{a} minus {b} is {a-b}.",rx(a-b)) for i,(a,b) in enumerate(sub)]
g("subtracting","Good: the correct difference in a short sentence.",rows)
h([(f"What is {a} plus {b}?",f"{a} plus {b} is {a+b}.",rx(a+b)) for a,b in HADD])
h([(f"What is {a} minus {b}?",f"{a} minus {b} is {a-b}.",rx(a-b)) for a,b in HSUB])

# doubles, halves, times tables, even/odd
HDBL=[7,9,6];HHALF=[14,18];HTIM=[(3,4),(2,9),(5,6),(10,5),(4,5)]
dbl=[n for n in range(1,16) if n not in HDBL]
g("doubles and halves","Good: doubling is adding it to itself; halving splits into two equal parts.",[(f"What is double {n}?",f"Double {n} is {2*n}.",rx(2*n)) for n in dbl]+[(f"What is half of {2*n}?",f"Half of {2*n} is {n}.",rx(n)) for n in range(1,13) if 2*n not in HHALF])
h([(f"What is double {n}?",f"Double {n} is {2*n}.",rx(2*n)) for n in HDBL]+[(f"What is half of {n}?",f"Half of {n} is {n//2}.",rx(n//2)) for n in HHALF])
tm=[]
for t in (2,5,10):
    for k in range(1,11):
        if (t,k) in HTIM or (k,t) in HTIM: continue
        tm.append((f"What is {t} times {k}?",f"{t} times {k} is {t*k}.",rx(t*k)))
for a,b in [(3,3),(3,5),(4,4),(3,6),(4,6),(6,6),(3,7),(4,8)]:
    tm.append((f"What is {a} times {b}?",f"{a} times {b} is {a*b}.",rx(a*b)))
g("times tables","Good: the right product; times means groups of.",tm)
h([(f"What is {a} times {b}?",f"{a} times {b} is {a*b}.",rx(a*b)) for a,b in HTIM])
EO=[(n,"even") if n%2==0 else (n,"odd") for n in range(1,21)]
HEO=[7,16,13,20]
g("even and odd","Good: even numbers split into two equal groups, odd leave one over.",[(f"Is {n} even or odd?",f"{n} is {w}.",w) for n,w in EO if n not in HEO])
h([(f"Is {n} even or odd?",f"{n} is {'even' if n%2==0 else 'odd'}.","even" if n%2==0 else "odd") for n in HEO])

# counting
g("counting","Good: the next or previous number, counted in order.",
 [(f"What number comes after {n}?",f"{n+1}.",rx(n+1)) for n in (1,3,4,6,8,9,14,17,19,24,29,39,49,59,99)]+
 [(f"What number comes before {n}?",f"{n-1}.",rx(n-1)) for n in (2,4,6,9,11,13,16,20,30,50,70,100)]+
 [("Count from 1 to 5.","1, 2, 3, 4, 5.","1, 2, 3, 4, 5"),("Count from 1 to 10.","1, 2, 3, 4, 5, 6, 7, 8, 9, 10.","1, 2, 3, 4, 5, 6, 7, 8, 9, 10"),("Count backward from 5.","5, 4, 3, 2, 1.","5, 4, 3, 2, 1"),("Count backward from 10.","10, 9, 8, 7, 6, 5, 4, 3, 2, 1.","10, 9, 8, 7"),("Count by twos to 10.","2, 4, 6, 8, 10.","2, 4, 6, 8, 10"),("Count by fives to 25.","5, 10, 15, 20, 25.","5, 10, 15, 20"),("Count by tens to 50.","10, 20, 30, 40, 50.","10, 20, 30, 40"),("What comes next: 2, 4, 6, ?","8.",rx(8)),("What comes next: 5, 10, 15, ?","20.",rx(20)),("What comes next: 10, 20, 30, ?","40.",rx(40)),("What comes next: 1, 2, 3, ?","4.",rx(4)),("What comes next: 3, 6, 9, ?","12.",rx(12)),("What comes next: 10, 9, 8, ?","7.",rx(7)),("How many fingers on two hands?","Ten fingers.","ten|\\b10\\b"),("How many toes on two feet?","Ten toes.","ten|\\b10\\b"),("How many ears do you have?","Two ears.","two|\\b2\\b"),("How many eyes does a cat have?","Two eyes.","two|\\b2\\b"),("How many legs does a cat have?","Four legs.","four|\\b4\\b"),("How many legs does a bird have?","Two legs.","two|\\b2\\b"),("How many legs does a spider have?","Eight legs.","eight|\\b8\\b"),("How many legs does a bee have?","Six legs.","six|\\b6\\b"),("How many wheels does a bike have?","Two wheels.","two|\\b2\\b"),("How many wheels does a car have?","Four wheels.","four|\\b4\\b"),("How many days are in a week?","Seven days.","seven|\\b7\\b"),("How many sides does a triangle have?","Three sides.","three|\\b3\\b"),("How many fingers on one hand?","Five fingers.","five|\\b5\\b")])
h([("What number comes after 7?","8.",rx(8)),("What number comes after 19?","20.",rx(20)),("What number comes before 8?","7.",rx(7)),("What number comes before 40?","39.",rx(39)),("Count by twos to 6.","2, 4, 6.","2, 4, 6"),("What comes next: 4, 8, 12, ?","16.",rx(16)),("How many legs does a dog have?","Four legs.","four|\\b4\\b"),("How many paws does a kitten have?","Four paws.","four|\\b4\\b")])
g("number words","Good: matches the number word to its digit.",[(f"What number is {NW[n]}?",f"{NW[n][0].upper()+NW[n][1:]} is {n}.",rx(n)) for n in (1,2,3,4,5,6,8,9,10,11,12,13,15,20)]+[(f"How do you say {n} in words?",f"{n} is {NW[n]}.",NW[n]) for n in (2,5,7,9,10,14,16,18)])
h([("What number is seven?","Seven is 7.",rx(7)),("How do you say 12 in words?","12 is twelve.","twelve"),("What number is fourteen?","Fourteen is 14.",rx(14))])

# comparing
cmp=[];hc=[]
HCMP=[(8,3),(15,12),(6,10),(20,19)]
pairs=[(9,4),(2,7),(5,5),(12,8),(1,10),(14,6),(3,11),(13,17),(18,16),(7,9),(20,10),(4,2),(15,5),(6,1),(10,3),(19,12)]
for a,b in pairs:
    if a==b:
        cmp.append((f"Which is bigger, {a} or {b}?",f"They are the same. {a} equals {b}.","same|equal"));continue
    cmp.append((f"Which is bigger, {a} or {b}?",f"{max(a,b)} is bigger.",rx(max(a,b))))
    cmp.append((f"Which is smaller, {a} or {b}?",f"{min(a,b)} is smaller.",rx(min(a,b))))
for a,b in [(3,5),(8,2),(6,6),(10,9),(1,4)]:
    cmp.append((f"Is {a} more than {b}?","Yes, "+f"{a} is more than {b}." if a>b else ("No, they are the same." if a==b else f"No, {a} is less than {b}."),"yes" if a>b else "no"))
g("comparing numbers","Good: picks the right bigger or smaller number.",cmp)
h([(f"Which is bigger, {a} or {b}?",f"{max(a,b)} is bigger.",rx(max(a,b))) for a,b in HCMP]+[("Which is smaller, 11 or 14?","11 is smaller.",rx(11)),("Is 9 more than 12?","No, 9 is less than 12.","no"),("Are 7 and 7 the same?","Yes, they are the same.","yes|same")])
g("more and less","Good: the plain idea of more, less, most and least.",[("What is more, five apples or two apples?","Five apples is more.","five|\\b5\\b"),("What is less, ten stars or three stars?","Three stars is less.","three|\\b3\\b"),("Which has more legs, a cat or a bird?","A cat has more legs. It has four.","cat"),("Which is longer, a day or an hour?","A day is longer.","day"),("Which is taller, a mouse or an elephant?","An elephant is taller.","elephant"),("Which is heavier, a feather or a rock?","A rock is heavier.","rock"),("Which is faster, a turtle or a cheetah?","A cheetah is faster.","cheetah"),("Which is bigger, the sun or the moon?","The sun is bigger.","sun"),("Which is colder, ice or soup?","Ice is colder.","ice"),("Which is longer, a minute or a second?","A minute is longer.","minute"),("Which is smaller, an ant or a dog?","An ant is smaller.","ant"),("Which is heavier, a car or a cat?","A car is heavier.","car")])
h([("Which is taller, a giraffe or a cat?","A giraffe is taller.","giraffe"),("Which is lighter, a leaf or a brick?","A leaf is lighter.","leaf"),("Which is longer, a week or a day?","A week is longer.","week")])

# word problems
items=[("apples","apple"),("stars","star"),("fish","fish"),("toys","toy"),("cookies","cookie"),("balloons","balloon"),("birds","bird"),("flowers","flower"),("marbles","marble"),("books","book")]
names=["Sam","Mia","Leo","Ana","Ben","Zoe","Max","Kim","Pat","Jo"]
wp=[];hwp=[]
HWP=[(4,3,"Nia","kites"),(9,4,"Omar","pears")]
rnd2=random.Random(77)
for i in range(30):
    n=names[i%10];it=items[(i*3)%10][0]
    a=rnd2.randint(2,9);b=rnd2.randint(1,9)
    if (a,b) in [(w[0],w[1]) for w in HWP]:continue
    if i%2==0:
        wp.append((f"{n} has {a} {it}. Then {n} gets {b} more. How many {it} now?",f"{n} has {a+b} {it} now.",rx(a+b)))
    else:
        a=a+b
        wp.append((f"{n} has {a} {it}. {n} gives away {b}. How many {it} are left?",f"{n} has {a-b} {it} left.",rx(a-b)))
g("word problems","Good: reads the story, adds or takes away, and says the number.",wp)
h([("Nia has 4 kites. Then Nia gets 3 more. How many kites now?","Nia has 7 kites now.",rx(7)),("Omar has 9 pears. Omar gives away 4. How many pears are left?","Omar has 5 pears left.",rx(5)),("There are 6 birds on a wire and 5 more come. How many birds are there?","There are 11 birds.",rx(11)),("A cat has 8 treats and eats 2. How many treats are left?","It has 6 treats left.",rx(6)),("Two kittens have 4 paws each. How many paws is that?","Eight paws.",rx(8)),("A box holds 10 pens and 5 fall out. How many pens are still in the box?","Five pens.",rx(5))])
g("sharing and groups","Good: splits into equal parts or groups, with a simple answer.",[("If 2 friends share 6 cookies equally, how many does each get?","Each gets 3 cookies.",rx(3)),("If 2 friends share 8 grapes equally, how many does each get?","Each gets 4 grapes.",rx(4)),("If 2 kittens share 10 fish bites, how many does each get?","Each gets 5.",rx(5)),("There are 3 bags with 2 apples each. How many apples is that?","Six apples.",rx(6)),("There are 4 nests with 2 eggs each. How many eggs is that?","Eight eggs.",rx(8)),("There are 5 plates with 2 cookies each. How many cookies is that?","Ten cookies.",rx(10)),("If you have 1 apple and cut it in half, how many pieces do you have?","Two pieces.",rx(2)),("If you have 2 socks, how many feet can you cover?","Two feet.",rx(2)),("A pack has 5 stickers. How many in 2 packs?","Ten stickers.",rx(10)),("A pack has 3 stickers. How many in 3 packs?","Nine stickers.",rx(9)),("5 birds are in a tree and 2 fly away. How many are left?","Three birds.",rx(3)),("I have 7 stars and find 3 more. How many stars do I have?","Ten stars.",rx(10))])
h([("If 2 friends share 12 berries equally, how many does each get?","Each gets 6 berries.",rx(6)),("There are 3 boxes with 3 toys each. How many toys is that?","Nine toys.",rx(9))])

# shapes
SH=[("triangle",3,3),("square",4,4),("rectangle",4,4),("pentagon",5,5),("hexagon",6,6),("octagon",8,8)]
HSH=[("pentagon",5),("square",4)]
rows=[]
for s,sd,cn in SH:
    if s in ("pentagon","square"):continue
    rows.append((f"How many sides does a {s} have?",f"A {s} has {NW[sd]} sides.",rx(sd)))
rows+=[("How many corners does a triangle have?","Three corners.",rx(3)),("How many corners does a rectangle have?","Four corners.",rx(4)),("How many sides does a circle have?","A circle has no straight sides. It is round.","no|round|zero|\\b0\\b"),("Which shape is round?","A circle.","circle"),("What shape is a ball?","A ball is a sphere. It's round.","sphere|round"),("What shape is a box?","A box is a cube or a block.","cube|block|rectang"),("What shape is a pizza?","A pizza is a circle.","circle"),("What shape is a stop sign?","An octagon. It has eight sides.","octagon"),("What shape is a slice of pizza?","A triangle.","triangle"),("What shape is a door?","A rectangle.","rectangle"),("What shape is a window usually?","A square or a rectangle.","square|rectangle"),("What shape is the moon in a full moon?","Round, like a circle.","round|circle"),("What shape is an egg?","An egg is an oval.","oval"),("What shape has four equal sides?","A square.","square"),("What shape has three sides?","A triangle.","triangle"),("What shape has eight sides?","An octagon.","octagon"),("What shape is a die?","A cube.","cube"),("What shape is a can of soup?","A cylinder.","cylinder"),("What is a shape with five sides called?","A pentagon.","pentagon"),("What is a shape with six sides called?","A hexagon.","hexagon")]
g("shapes","Good: right shape name or side count.",rows)
h([("How many sides does a pentagon have?","Five sides.",rx(5)),("How many sides does a square have?","Four sides.",rx(4)),("What shape is a ball of yarn?","A sphere, or round.","sphere|round|ball"),("What shape has no corners?","A circle.","circle"),("What shape is a slice of watermelon, often?","A half circle, or a triangle.","circle|triangle|half")])

# time and money
g("time","Good: right time facts, short.",[("How many seconds are in a minute?","Sixty seconds.","sixty|\\b60\\b"),("How many minutes are in an hour?","Sixty minutes.","sixty|\\b60\\b"),("How many hours are in a day?","Twenty-four hours.","twenty-four|\\b24\\b"),("How many days are in a week?","Seven days.","seven|\\b7\\b"),("How many months are in a year?","Twelve months.","twelve|\\b12\\b"),("How many days are in a year?","Three hundred sixty-five days.","365|three hundred"),("How many weeks are in a year?","About fifty-two weeks.","52|fifty"),("How many hours do we sleep at night, about?","About eight or nine hours for kids.","eight|nine|\\b8\\b|\\b9\\b|ten"),("What do we call half an hour?","Thirty minutes.","thirty|\\b30\\b"),("What is a quarter of an hour?","Fifteen minutes.","fifteen|\\b15\\b"),("What time is it when the short hand is on 3 and the long hand on 12?","Three o'clock.","three|3"),("What time is it when both hands are on 12?","Twelve o'clock.","twelve|12"),("What time is half past two?","Two thirty.","two thirty|2:30|2.30"),("Does the sun come up in the morning or at night?","In the morning.","morning"),("Is breakfast in the morning or at night?","In the morning.","morning"),("What do we call the time between morning and night?","The afternoon, and the evening.","afternoon|evening"),("Which is longer, a minute or an hour?","An hour is longer.","hour"),("How many days are in February, usually?","Twenty-eight days.","28|twenty-eight"),("How many days are in a weekend?","Two days.","two|\\b2\\b"),("How many seasons are there in a year?","Four seasons.","four|\\b4\\b"),("What do we use to tell the time?","A clock, or a watch.","clock|watch"),("What day is it after today is Friday?","Saturday.","saturday"),("It is 5 o'clock. What time is it in one hour?","Six o'clock.","six|6"),("It is 2 o'clock. What time was it one hour ago?","One o'clock.","one|1"),("School starts in 3 days. After 1 day, how many days are left?","Two days.","two|\\b2\\b")])
h([("How many hours are in half a day?","Twelve hours.","twelve|\\b12\\b"),("What time is it when the short hand is on 9 and the long hand on 12?","Nine o'clock.","nine|9"),("How many minutes are in two hours?","One hundred twenty minutes.","120|hundred"),("It is 7 o'clock. What time is it in two hours?","Nine o'clock.","nine|9"),("How many days are in two weeks?","Fourteen days.","14|fourteen")])
g("money","Good: right coin value in cents.",[("How many cents are in a dollar?","One hundred cents.","100|hundred"),("How many cents is a penny?","One cent.","one|\\b1\\b"),("How many cents is a nickel?","Five cents.","five|\\b5\\b"),("How many cents is a dime?","Ten cents.","ten|\\b10\\b"),("How many cents is a quarter?","Twenty-five cents.","25|twenty-five"),("How many pennies make a nickel?","Five pennies.","five|\\b5\\b"),("How many nickels make a dime?","Two nickels.","two|\\b2\\b"),("How many dimes make a dollar?","Ten dimes.","ten|\\b10\\b"),("How many quarters make a dollar?","Four quarters.","four|\\b4\\b"),("Which is worth more, a dime or a nickel?","A dime is worth more.","dime")])
h([("How many pennies make a dime?","Ten pennies.","ten|\\b10\\b"),("Which is worth more, a quarter or a dime?","A quarter is worth more.","quarter"),("How many quarters make 50 cents?","Two quarters.","two|\\b2\\b")])
