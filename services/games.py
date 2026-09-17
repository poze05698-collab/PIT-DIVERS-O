import random
def dice():return random.randint(1,6)
def coin():return random.choice(['cara','coroa'])
def ppp():return random.choice(['pedra','papel','tesoura'])
def parity():
 n=random.randint(1,100);return n,'par' if n%2==0 else 'impar'
def scramble():
 w=random.choice(['telegram','diversao','pitbull','futebol','amizade','cinema']); a=list(w); random.shuffle(a); return w,''.join(a)
def hangman():return random.choice(['telegram','futebol','cinema','brasil','diversao'])
