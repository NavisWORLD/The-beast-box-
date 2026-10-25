import random
G=[];H=[]
def g(topic,note,rows,subject="math"):G.append((subject,topic,note,rows))
def h(rows,subject="math"):H.extend((subject,q,a,e) for q,a,e in rows)
rnd=random.Random(5005)
def rx(n):return rf"\b{n}\b"
def comma(n):return f"{n:,}"
# ---- multiplication beyond the small tables (held pairs never trained)
HM=[(13,4),(12,12),(15,3),(25,4),(11,11),(18,2)]
hm={tuple(sorted(p)) for p in HM}
pairs=[(a,b) for a in range(2,21) for b in range(2,13) if tuple(sorted((a,b))) not in hm and (a>12 or b>9)]
rnd.shuffle(pairs);pairs=pairs[:60]
T=["What is {a} times {b}?","{a} x {b} = ?","What is {a} multiplied by {b}?","How much is {a} times {b}?"]
g("bigger multiplication","Good: the correct product in a short sentence.",[(T[i%4].format(a=a,b=b),f"{a} times {b} is {a*b}.",rx(a*b)) for i,(a,b) in enumerate(pairs)])
h([(f"What is {a} times {b}?",f"{a} times {b} is {a*b}.",rx(a*b)) for a,b in HM])
# ---- division
HD=[(48,6),(72,8),(100,4),(63,7),(121,11)]
hd=set(HD)
dv=[(a*b,b) for a in range(2,13) for b in range(2,13) if (a*b,b) not in hd];rnd.shuffle(dv);dv=dv[:50]
T=["What is {a} divided by {b}?","{a} / {b} = ?","How many times does {b} go into {a}?","What is {a} shared equally into {b} groups?"]
rows=[]
for i,(a,b) in enumerate(dv):
    q=T[i%4].format(a=a,b=b);rows.append((q,f"{a} divided by {b} is {a//b}.",rx(a//b)))
g("division","Good: the correct quotient in a short sentence.",rows)
h([(f"What is {a} divided by {b}?",f"{a} divided by {b} is {a//b}.",rx(a//b)) for a,b in HD])
# ---- two-digit addition / subtraction
HA=[(47,38),(65,27),(89,11),(54,46)];HS=[(92,48),(100,37),(71,29)]
ha=set(HA);hs=set(HS)
ad=[(rnd.randint(11,89),rnd.randint(11,89)) for _ in range(80)]
ad=[p for p in dict.fromkeys(ad) if p not in ha][:44]
g("two-digit adding","Good: the correct sum.",[(f"What is {a} plus {b}?",f"{a} plus {b} is {a+b}.",rx(a+b)) for a,b in ad])
sb=[(rnd.randint(40,99),rnd.randint(11,39)) for _ in range(80)]
sb=[p for p in dict.fromkeys(sb) if p not in hs][:40]
g("two-digit subtracting","Good: the correct difference.",[(f"What is {a} minus {b}?",f"{a} minus {b} is {a-b}.",rx(a-b)) for a,b in sb])
h([(f"What is {a} plus {b}?",f"{a} plus {b} is {a+b}.",rx(a+b)) for a,b in HA]+[(f"What is {a} minus {b}?",f"{a} minus {b} is {a-b}.",rx(a-b)) for a,b in HS])
# ---- place value
HP=[(582,"tens"),(4096,"hundreds")]
rows=[]
names=["ones","tens","hundreds"]
for n in [27,63,95,148,206,375,419,752,834,961,38,74,509,620,893]:
    s=str(n)
    for pos,nm in enumerate(names):
        if pos<len(s) and rnd.random()<.45 and (n,nm) not in HP:
            d=s[-1-pos];rows.append((f"What digit is in the {nm} place of {n}?",f"The digit in the {nm} place of {n} is {d}.",rf"\b{d}\b"))
g("place value","Good: names the right digit.",rows[:30])
h([("What digit is in the tens place of 582?","The digit in the tens place is 8.",r"\b8\b"),("What digit is in the hundreds place of 4096?","The digit in the hundreds place is 0.",r"\b0\b|zero")])
# ---- rounding
HR=[(46,10),(83,10),(350,100)]
rows=[]
for n in [12,17,24,28,33,35,41,49,52,58,61,66,75,77,84,91,96,13,27,38,44,55,69,72,88]:
    if (n,10) in HR:continue
    r=int(round(n/10+1e-9)) if n%10!=5 else n//10+1
    rows.append((f"What is {n} rounded to the nearest ten?",f"{n} rounded to the nearest ten is {r*10}.",rx(r*10)))
for n in [140,260,380,450,520,640,770,830,910,175,230,490]:
    r=(n+50)//100
    rows.append((f"What is {n} rounded to the nearest hundred?",f"{n} rounded to the nearest hundred is {r*100}.",rx(r*100)))
g("rounding","Good: rounds correctly (5 or more rounds up).",rows)
h([("What is 46 rounded to the nearest ten?","46 rounded to the nearest ten is 50.",r"\b50\b"),("What is 83 rounded to the nearest ten?","83 rounded to the nearest ten is 80.",r"\b80\b"),("What is 350 rounded to the nearest hundred?","350 rounded to the nearest hundred is 400.",r"\b400\b")])
# ---- fractions of a number, percent
HF=[(24,"half"),(36,"a third"),(40,"a quarter")]
den={"half":2,"a third":3,"a quarter":4}
rows=[]
for w,d in den.items():
    for k in range(2,13):
        n=d*k*(2 if d==2 else 1)
        if (n,w) in HF:continue
        rows.append((f"What is {w} of {n}?",f"{w[0].upper()+w[1:]} of {n} is {n//d}.",rx(n//d)))
g("fractions of numbers","Good: divides by the bottom number of the fraction.",rows)
h([(f"What is {w} of {n}?",f"{w[0].upper()+w[1:]} of {n} is {n//den[w]}.",rx(n//den[w])) for n,w in HF])
rows=[]
HPC=[(60,10),(80,50),(200,10)]
for n in [20,30,40,50,70,90,100,120,150,400]:
    for p in (10,50):
        if (n,p) in HPC:continue
        rows.append((f"What is {p} percent of {n}?",f"{p} percent of {n} is {n*p//100}.",rx(n*p//100)))
rows+=[(f"What is 25 percent of {n}?",f"25 percent of {n} is {n//4}.",rx(n//4)) for n in (8,12,16,20,40,60,80,100)]
g("percent","Good: the right part of the number.",rows)
h([(f"What is {p} percent of {n}?",f"{p} percent of {n} is {n*p//100}.",rx(n*p//100)) for n,p in HPC])
# ---- perimeter, area
HRA=[(7,3),(9,4)]
rows=[]
for a in range(2,16):
    b=rnd.randint(2,12)
    if (a,b) in HRA:continue
    rows.append((f"A rectangle is {a} long and {b} wide. What is its area?",f"The area is {a*b}.",rx(a*b)))
for a in range(2,14):
    b=rnd.randint(2,12)
    rows.append((f"A rectangle is {a} long and {b} wide. What is its perimeter?",f"The perimeter is {2*(a+b)}.",rx(2*(a+b))))
for s in range(2,13):rows.append((f"A square has sides of {s}. What is its area?",f"The area is {s*s}.",rx(s*s)))
g("perimeter and area","Good: area is length times width; perimeter is the distance around.",rows)
h([("A rectangle is 7 long and 3 wide. What is its area?","The area is 21.",r"\b21\b"),("A square has sides of 13. What is its perimeter?","The perimeter is 52.",r"\b52\b"),("A rectangle is 9 long and 4 wide. What is its perimeter?","The perimeter is 26.",r"\b26\b")])
# ---- sequences and skip counting
rows=[]
HSEQ=[(4,6),(3,9)]
for step,start in [(2,2),(3,3),(5,5),(10,10),(4,4),(6,6),(7,7),(9,9),(8,8),(11,11),(25,25),(50,50),(20,20),(15,15)]:
    for st in (start,):
        seq=[st+step*i for i in range(4)];rows.append((f"What comes next: {', '.join(map(str,seq))}?",f"The next number is {seq[-1]+step}.",rx(seq[-1]+step)))
    seq=[100-step*i for i in range(4)] if step<=20 else None
    if seq:rows.append((f"What comes next: {', '.join(map(str,seq))}?",f"The next number is {seq[-1]-step}.",rx(seq[-1]-step)))
for a,r in [(1,2),(2,2),(1,3),(3,2),(5,2)]:
    seq=[a*r**i for i in range(4)];rows.append((f"What comes next: {', '.join(map(str,seq))}?",f"The next number is {seq[-1]*r}.",rx(seq[-1]*r)))
g("number patterns","Good: finds the rule and gives the next number.",rows)
h([("What comes next: 12, 24, 36, 48?","The next number is 60.",r"\b60\b"),("What comes next: 1, 4, 9, 16?","The next number is 25.",r"\b25\b"),("What comes next: 90, 80, 70, 60?","The next number is 50.",r"\b50\b")])
# ---- squares, even/odd, factors, averages
HSQ=[7,11]
g("squares","Good: a number times itself.",[(f"What is {n} squared?",f"{n} squared is {n*n}.",rx(n*n)) for n in range(2,16) if n not in HSQ])
h([(f"What is {n} squared?",f"{n} squared is {n*n}.",rx(n*n)) for n in HSQ])
rows=[]
for a,b,c in [(2,4,6),(3,6,9),(5,10,15),(4,8,12),(10,20,30),(7,8,9),(6,12,18),(1,2,3),(10,15,20),(12,14,16),(2,6,10),(5,7,9)]:
    rows.append((f"What is the average of {a}, {b} and {c}?",f"The average is {(a+b+c)//3}.",rx((a+b+c)//3)))
g("averages","Good: add them up and divide by how many there are.",rows)
h([("What is the average of 4, 6 and 8?","The average is 6.",r"\b6\b|six"),("What is the average of 10, 20 and 60?","The average is 30.",r"\b30\b")])
rows=[]
for n,f in [(12,"1, 2, 3, 4, 6 and 12"),(10,"1, 2, 5 and 10"),(15,"1, 3, 5 and 15"),(18,"1, 2, 3, 6, 9 and 18"),(20,"1, 2, 4, 5, 10 and 20"),(16,"1, 2, 4, 8 and 16"),(9,"1, 3 and 9"),(14,"1, 2, 7 and 14")]:
    rows.append((f"What are the factors of {n}?",f"The factors of {n} are {f}.",f.split(",")[-1].split()[-1]))
for n in (2,3,5,7,11,13,17,19):rows.append((f"Is {n} a prime number?",f"Yes, {n} is a prime number.","yes|prime"))
for n in (4,6,9,15,21,25,27,33):rows.append((f"Is {n} a prime number?",f"No, {n} is not prime.","no|not"))
g("factors and primes","Good: correct factor lists and prime facts.",rows)
h([("What are the factors of 8?","The factors of 8 are 1, 2, 4 and 8.",r"\b8\b"),("Is 23 a prime number?","Yes, 23 is a prime number.","yes|prime"),("Is 39 a prime number?","No, 39 is not prime. It is 3 times 13.","no|not")])
# ---- word problems
NAMES=["Maya","Leo","Ana","Sam","Nia","Omar","Ruth","Ben","Zoe","Kai","Ivy","Tom"]
ITEMS=[("apples","basket"),("stickers","page"),("marbles","bag"),("cookies","plate"),("pencils","box"),("shells","bucket")]
rows=[]
HW=[("Maya has 5 bags with 6 marbles in each bag. How many marbles does she have?","She has 30 marbles.",r"\b30\b"),("Tom had 90 stickers and gave away 35. How many are left?","He has 55 stickers left.",r"\b55\b")]
for i in range(40):
    nm=NAMES[i%len(NAMES)];it,cont=ITEMS[i%len(ITEMS)];a=rnd.randint(3,9);b=rnd.randint(3,9);k=i%4
    if nm=="Maya" and it=="marbles" and a==5 and b==6:continue
    if k==0:rows.append((f"{nm} has {a} {cont}s with {b} {it} in each {cont}. How many {it} is that in all?",f"That is {a*b} {it}.",rx(a*b)))
    elif k==1:
        t=a*b+rnd.randint(5,20);rows.append((f"{nm} had {t} {it} and gave away {a*b}. How many {it} are left?",f"{nm} has {t-a*b} {it} left.",rx(t-a*b)))
    elif k==2:rows.append((f"{nm} shares {a*b} {it} equally among {a} friends. How many does each friend get?",f"Each friend gets {b}.",rx(b)))
    else:
        c=rnd.randint(10,40);rows.append((f"{nm} has {a*b} {it} and finds {c} more. How many {it} does {nm} have now?",f"{nm} has {a*b+c} {it} now.",rx(a*b+c)))
g("word problems, harder","Good: picks the right operation and answers with the number.",rows)
h(HW)
# ---- time, money, units, roman numerals, negatives
rows=[("How many minutes are in an hour?","There are 60 minutes in an hour.",r"\b60\b|sixty"),("How many seconds are in a minute?","There are 60 seconds in a minute.",r"\b60\b|sixty"),("How many hours are in a day?","There are 24 hours in a day.",r"\b24\b|twenty"),("How many days are in a week?","There are 7 days in a week.",r"\b7\b|seven"),("How many days are in a year?","There are 365 days in a normal year.",r"\b365\b"),("How many days are in a leap year?","A leap year has 366 days.",r"\b366\b"),("How many months are in a year?","There are 12 months in a year.",r"\b12\b|twelve"),("How many weeks are in a year?","There are 52 weeks in a year.",r"\b52\b"),("How many centimeters are in a meter?","There are 100 centimeters in a meter.",r"\b100\b|hundred"),("How many meters are in a kilometer?","There are 1000 meters in a kilometer.",r"\b1000\b|thousand|1,000"),("How many grams are in a kilogram?","There are 1000 grams in a kilogram.",r"\b1000\b|thousand|1,000"),("How many millimeters are in a centimeter?","There are 10 millimeters in a centimeter.",r"\b10\b|ten"),("How many inches are in a foot?","There are 12 inches in a foot.",r"\b12\b|twelve"),("How many feet are in a yard?","There are 3 feet in a yard.",r"\b3\b|three"),("How many ounces are in a pound?","There are 16 ounces in a pound.",r"\b16\b|sixteen"),("How many cups are in a quart?","There are 4 cups in a quart.",r"\b4\b|four"),("How many pennies are in a dollar?","There are 100 pennies in a dollar.",r"\b100\b|hundred"),("How many nickels make a quarter?","Five nickels make a quarter.",r"\b5\b|five"),("How many dimes make a dollar?","Ten dimes make a dollar.",r"\b10\b|ten"),("How many quarters make a dollar?","Four quarters make a dollar.",r"\b4\b|four"),("How many liters are in 2000 milliliters?","2000 milliliters is 2 liters.",r"\b2\b|two"),("How many minutes are in half an hour?","There are 30 minutes in half an hour.",r"\b30\b|thirty"),("How many minutes are in two hours?","There are 120 minutes in two hours.",r"\b120\b"),("How many hours are in two days?","There are 48 hours in two days.",r"\b48\b"),("How many sides does a hexagon have?","A hexagon has 6 sides.",r"\b6\b|six"),("How many sides does an octagon have?","An octagon has 8 sides.",r"\b8\b|eight"),("How many sides does a pentagon have?","A pentagon has 5 sides.",r"\b5\b|five"),("How many degrees are in a right angle?","A right angle is 90 degrees.",r"\b90\b|ninety"),("How many degrees are in a circle?","A full circle is 360 degrees.",r"\b360\b"),("How many corners does a cube have?","A cube has 8 corners.",r"\b8\b|eight"),("How many faces does a cube have?","A cube has 6 faces.",r"\b6\b|six"),("How many edges does a cube have?","A cube has 12 edges.",r"\b12\b|twelve")]
g("units, time, money, shapes","Good: the standard measurement fact.",rows)
h([("How many hours are in a week?","There are 168 hours in a week.",r"\b168\b"),("How many millimeters are in a meter?","There are 1000 millimeters in a meter.",r"\b1000\b|1,000|thousand"),("How many sides does a triangle have?","A triangle has 3 sides.",r"\b3\b|three"),("How many cents are in 3 dimes?","Three dimes are 30 cents.",r"\b30\b|thirty")])
RN=[(1,"I"),(2,"II"),(3,"III"),(4,"IV"),(5,"V"),(6,"VI"),(7,"VII"),(8,"VIII"),(9,"IX"),(10,"X"),(11,"XI"),(12,"XII"),(14,"XIV"),(15,"XV"),(19,"XIX"),(20,"XX"),(30,"XXX"),(40,"XL"),(50,"L"),(100,"C")]
HRN=[(16,"XVI"),(90,"XC")]
g("roman numerals","Good: the right Roman numeral or number.",[(f"What is {n} in Roman numerals?",f"{n} in Roman numerals is {r}.",r) for n,r in RN if n not in (4,9)]+[(f"What number is {r}?",f"{r} is {n}.",rx(n)) for n,r in RN[::2]])
h([(f"What is {n} in Roman numerals?",f"{n} in Roman numerals is {r}.",r) for n,r in HRN])
rows=[]
for a,b in [(3,5),(2,7),(1,4),(6,9),(0,3),(4,10),(5,8),(2,9),(7,12)]:
    rows.append((f"Which is smaller, negative {a} or negative {b}?" if False else f"What is {a} minus {b}?",f"{a} minus {b} is negative {b-a}.",rf"negative {b-a}|-{b-a}|minus {b-a}"))
for n in (1,3,5,8,10,15):rows.append((f"What is the temperature if it is {n} degrees below zero?",f"It is negative {n} degrees.",rf"negative {n}|-{n}|minus {n}"))
g("small negative numbers","Good: knows a result below zero is negative.",rows)
h([("What is 4 minus 9?","4 minus 9 is negative 5.",r"negative 5|-5|minus 5")])
# ---- order of operations, simple equations
rows=[];HE=[(3,4,2)]
for a,b,c in [(2,3,4),(5,2,3),(4,6,2),(1,5,5),(7,2,2),(3,3,3),(6,1,4),(8,2,3),(2,9,2),(10,3,2),(5,4,1)]:
    if (a,b,c)==(3,4,2):continue
    rows.append((f"What is {a} plus {b} times {c}?",f"{a} plus {b} times {c} is {a+b*c}, because we multiply first.",rx(a+b*c)))
for x,a in [(3,5),(4,7),(6,2),(8,9),(10,4),(2,12),(7,7),(9,6)]:
    rows.append((f"What number plus {a} makes {x+a}?",f"{x} plus {a} makes {x+a}.",rx(x)))
for x,a in [(3,4),(5,6),(2,8),(7,3),(9,9),(4,5)]:
    rows.append((f"What number times {a} makes {x*a}?",f"{x} times {a} makes {x*a}.",rx(x)))
g("order of operations and missing numbers","Good: multiplication before addition; finds the missing number.",rows)
h([("What is 3 plus 4 times 2?","3 plus 4 times 2 is 11, because we multiply first.",r"\b11\b"),("What number plus 8 makes 15?","7 plus 8 makes 15.",r"\b7\b|seven")])
# ---- comparing and ordering big numbers, odd/even of larger
rows=[]
for a,b in [(345,354),(1002,999),(5000,4999),(678,687),(1200,1020),(999,1000),(2500,2050),(8123,8132),(4040,4004),(7007,7070)]:
    big=max(a,b);rows.append((f"Which is bigger, {a} or {b}?",f"{big} is bigger.",rx(big)))
for a,b in [(310,301),(65,650),(3199,3200),(444,414)]:
    sm=min(a,b);rows.append((f"Which is smaller, {a} or {b}?",f"{sm} is smaller.",rx(sm)))
g("bigger numbers","Good: compares place by place.",rows)
h([("Which is bigger, 5050 or 5005?","5050 is bigger.",r"\b5050\b"),("Which is smaller, 721 or 712?","712 is smaller.",r"\b712\b")])
