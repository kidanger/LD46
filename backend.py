#!/usr/bin/env python3

import random
import sys
import traceback

import enchant
dictionary = enchant.Dict('en_US')

from colored import fg, bg, attr
import inflect

soundsrand = random.Random()

NS = 'ld46'

class NoMoreWordsException(Exception):
    pass

def parse_void(msg):
    msg = msg.replace('CLEAR', '')
    msg = msg.replace('BLUE', '')
    msg = msg.replace('GREEN', '')
    return msg

def RK(key):
    return NS + ':' + key

def get_redis_connection():
    from redis.client import Redis
    return Redis()

r = get_redis_connection()

def word_is_english(word):
    if not word:
        return False
    if '0' in word: return False
    if '1' in word: return False
    if '2' in word: return False
    if '3' in word: return False
    if '4' in word: return False
    if '5' in word: return False
    if '6' in word: return False
    if '7' in word: return False
    if '8' in word: return False
    if '9' in word: return False
    return dictionary.check(word)

def compare_words(target, proposed):
    if not target or not proposed:
        return False
    p = inflect.engine()
    def normalize(w):
        w = w.lower()
        # w = w.replace('z', 's')
        w = p.singular_noun(w) or w
        return w
    target = normalize(target)
    proposed = normalize(proposed)
    return p.compare(proposed, target)

def word_contains(w1, w2):
    def cut(w):
        if len(w) > 1 and w[-1] == 's':
            w = w[:-1]
        if len(w) > 1 and w[-1] == 'y':
            w = w[:-1]
        if len(w) > 1 and w[-1] == 'r':
            w = w[:-1]
        if len(w) > 1 and w[-1] == 'r':
            w = w[:-1]
        if len(w) > 1 and w[-1] == 'i':
            w = w[:-1]
        if len(w) > 1 and w[-1] == 'e':
            w = w[:-1]
        return w
    w1 = cut(w1)
    w2 = cut(w2)
    return w1.lower() in w2.lower() or w2.lower() in w1.lower()

def prepare_player(phash):
    if r.exists(RK(f'player_pages:guess:{phash}')):
        return
    tags = [t.decode('utf-8') for t in r.smembers(RK('tags'))]
    pages = [r.srandmember(RK(f'pages:tagged_{t}')) for t in tags]
    n = len(pages)
    nguess = n // 2
    nhelp = n - nguess
    for i in range(nguess):
        p = random.choice(list(pages))
        pages.remove(p)
        r.sadd(RK(f'player_pages:guess:{phash}'), p)
    for i in range(nhelp):
        p = random.choice(list(pages))
        pages.remove(p)
        r.sadd(RK(f'player_pages:help:{phash}'), p)
    print('PLAYER PREPARED')

def get_true_text(pageid):
    return r.hget(RK('texts:id_to_text'), pageid).decode('utf-8')

def get_word_for_page(pageid):
    return r.hget(RK('word_for_page'), pageid).decode('utf-8')

def add_page(pageid, text, tags):
    s1 = text.find('^')
    s2 = text.find('^', s1+1)
    word = text[s1+1:s2]
    ntext = text.replace(f'^{word}^', word)
    r.hset(RK('texts:id_to_text'), pageid, ntext)
    r.hset(RK('pages:seed'), pageid, random.randint(0, 99999))
    r.hset(RK('word_for_page'), pageid, word)
    r.sadd(RK('pages'), pageid)
    for t in tags:
        r.sadd(RK(f'pages:tagged_{t}'), pageid)

def get_random_word(phash, step):
    remainings = r.sdiff(RK(f'player_pages:{step}:{phash}'), RK(f'players_pages_completed:{phash}'))
    if len(remainings) == 0:
        return None
    word = random.choice(list(remainings)).decode('utf-8')
    return word

def get_pages():
    return [int(p) for p in r.smembers(RK('pages'))]

def setup():
    r.incr(RK('http_secret'))
    lines = open('pages').readlines()
    lines = [l.strip().replace('\\n', '\n') for l in lines if l.strip() and not l.strip().startswith('#')]
    tags = lines[::3]
    pages = lines[1::3]
    syns = lines[2::3]
    tags = [t.split(' ') for t in tags]
    syns = [s.split(' ') for s in syns]
    assert len(pages) == len(syns) == len(tags)
    for tag in tags:
        for t in tag:
            r.sadd(RK('tags'), t)
    for i, (tag, text, syns) in enumerate(zip(tags, pages, syns)):
        pageid = i+1
        add_page(pageid, text, tags=tag)
        for s in syns:
            r.hincrby(RK(f'proposed_words:for_page_{pageid}'), s, 1)
    for i in sorted(get_pages()):
        i = int(i)
        ircprint('', show_page(i))
        ircprint('', f'hints: {get_hint_for_page(i)}')

def reset():
    for k in r.keys(RK('*')):
        r.delete(k)
        print('del', k)

def ambiant_sound():
    sentence = soundsrand.choice((animal_sound, animal_sound, environnemental_sound))()
    return f'GREY({sentence})CLEAR'

def environnemental_sound():
    c = soundsrand.choice
    possibles = (
        '*whoosh*, the wind blows',
        '*whoosh whoosh*, the wind blows',
        '*fizz*, a nearby acid lake fizzes',
        '*fizz*, a nearby lava lake fizzes',
        '*bloop*, a nearby lava lake seems agitated',
        '*splash*, water drops periodically from the ceiling',
        '*plop*, water drops periodically from the ceiling',
        f'*{c((1,2,3))*"tick"}*, a timer seems running',
        '*tick tock*, goes the clock',
        'thunder rumbles outside',
        'lighting crackles outside',
        'an epic music is playing outside',
        'you hear a calming music',
        'you hear a charming music',
        'outside the cave, the sun sets',
        'outside the cave, the sun rises',
    )
    return f'{c(possibles)}.'.capitalize()

def animal_sound():
    c = soundsrand.choice
    p  = inflect.engine()
    where = (
        'in the distance, ',
        'far away, ',
        'nearby, ',
        'nearby, ',
        'you hear ',
        'you hear ',
        'you hear ',
        '',
        '',
        '',
        '',
        '',
    )
    animals = (  # https://en.wikipedia.org/wiki/List_of_animal_sounds
        ('bat', 'screeches'),
        ('bat', 'screeches'),
        ('bat', 'screeches'),
        ('bee', 'buzzes'),
        # ('antilope', 'snorts'),
        # ('badger', 'growls'),
        ('cat', 'meows'),
        ('cat', 'hisses'),
        ('cat', 'purrs'),
        ('chicken', 'clucks'),
        # ('chinchillas', 'squeaks'),
        ('cicadas', 'chirps'),
        ('cicadas', 'chirps'),
        ('cow', 'moos'),
        ('crow', 'caws'),
        ('dog', 'barks'),
        ('dog', 'howls'),
        ('dog', 'growls'),
        # ('dolphin', 'clicks'),
        ('donkey', 'brays'),
        # ('duck', 'quacks'),
        ('eagle', 'screechs'),
        ('elephant', 'trumpets'),
        ('fly', 'buzzes'),
        ('frog', 'croaks'),
        ('toad', 'ribbits'),
        ('goat', 'baas'),
        ('geese', 'honks'),
        ('geese', 'honks'),
        ('hornet', 'buzzes'),
        ('horse', 'neighs'),
        ('hyena', 'laughs'),
        ('magpie', 'chatters'),
        ('monkey', 'screams'),
        ('moose', 'bellows'),
        ('mosquito', 'buzzes'),
        ('mouse', 'squeaks'),
        ('owl', 'hoots'),
        ('owl', 'screeches'),
        ('parrot', 'squawks'),
        ('pig', 'oinks'),
        ('hog', 'grunts'),
        # ('pigeon', 'coos'),
        ('raccoon', 'trills'),
        ('rat', 'squeaks'),
        ('raven', 'caws'),
        ('sheep', 'bleats'),
        ('snail', 'munches'),
        ('snake', 'hisses'),
        ('snake', 'rattles'),
        ('bird', 'sings'),
        ('bird', 'tweets'),
        ('bird', 'chirps'),
        # ('swan', 'cries'),
        ('turkey', 'gobbles'),
        ('vulture', 'screams'),
        ('wolf', 'howls'),
        ('wolf', 'growls'),
    )
    hows = (
        '',
        '',
        '',
        '',
        '',
        ' loudly',
        ' elegantly',
        ' quietly',
        ' softly',
        ' happily',
        ' repeatedly',
        ' abruptly',
        ' melodically',
        ' joyfully',
        ' sadly',
        ' melodiously',
        ' suddenly',
        ' remarkably',
        ' vaguely',
        ' eerily',
        ' eerily',
        ' horribly',
        ' oddly',
        ' particularly',
        ' strangely',
        ' periodically',
        ' peacefully',
        ' aggressively',
    )
    animal, verb = c(animals)
    n = soundsrand.randint(1, 2)
    if n == 1:
        animal = p.a(animal)
    else:
        animal = p.plural(animal)
        verb = p.plural_verb(verb)
    return f'{c(where)}{animal} {verb}{c(hows)}.'.capitalize()

def intro_for_new_players(phash):
    return f'''
As you enter the small cave, you see a pile of old pages on the ground.
They look like they were ripped out of a book.
Some pages are well preserved, but others are hardly readable.
CLEAR
{ambiant_sound()}
CLEAR
On the pages, some of the words are glowing in a beautiful blue, but it seems that they are fading away.
You notice that some pages are annotated, probably by previous explorers.
CLEAR
{ambiant_sound()}
CLEAR
Your goal is to continue the annotation the pages, and start putting them together as a complete book.
Remember to do your best, this work is invaluable! You depend on others just as much as others will depend on you for their future explorations!
'''

def send_to_player(phash, msg):
    r.append(RK(f'send_to:{phash}'), msg + '\n')

def get_player_step(phash):
    n = int(r.hget(RK('player_steps'), phash) or 0)
    return 'help' if n % 2 == 0 else 'guess'

def advance_player_step(phash, silence=False):
    r.hincrby(RK('player_steps'), phash, 1)
    if not silence:
        send_to_player(phash, f'''
CLEAR
{ambiant_sound()}
CLEAR''')

def get_current_page_for_player(phash):
    pageid = r.hget(RK('player_pages:current'), phash)
    if pageid:
        pageid = int(pageid)
    return pageid

def get_and_set_new_page_for_player(phash, step):
    pageid = get_random_word(phash, step)
    if pageid:
        r.hset(RK('player_pages:current'), phash, pageid)
    return pageid

def remove_page_for_player(phash, pageid):
    r.sadd(RK(f'players_pages_completed:{phash}'), pageid)

def get_hint_for_page(pageid):
    proposed = r.hgetall(RK(f'proposed_words:for_page_{pageid}'))
    proposed = {k.decode('utf-8'): int(v) for k, v in proposed.items()}
    lproposed = [k for k, v in proposed.items()]
    lproposed = sorted(lproposed, key=lambda k: -proposed[k])
    p = inflect.engine()
    hint = p.join(list(f'GREEN{p}CLEAR ({proposed[p]})' for p in lproposed))
    return hint

def get_already_proposed_for_page(phash, pageid):
    ltried = r.lrange(RK(f'proposed_words:by_{phash}:for_page_{pageid}'), 0, -1)
    ltried = set([t.decode('utf-8') for t in ltried])
    p = inflect.engine()
    tried = p.join(list(ltried))
    return tried

def scramble_word(word):
    possibles = '-_??)(/\\'
    nword = ''
    for i, c in enumerate(word):
        nc = random.choice(possibles)
        nword += nc
    return nword

# this table is from nethack source code
nethack = {
        'A': "^",
        'B': "Pb[",
        'C': "(",
        'D': "|)[",
        'E': "|FL[_",
        'F': "|-",
        'G': "C(",
        'H': "|-",
        'I': "|",
        'K': "|<",
        'L': "|_",
        'M': "|",
        'N': "|\\",
        'O': "C(",
        'P': "F",
        'Q': "C(",
        'R': "PF",
        'T': "|",
        'U': "J",
        'V': "/\\",
        'W': "V/\\",
        'Z': "/",
        'b': "|",
        'd': "c|",
        'e': "c",
        'g': "c",
        'h': "n",
        'j': "i",
        'k': "|",
        'l': "|",
        'm': "nr",
        'n': "r",
        'o': "c",
        'q': "c",
        'w': "v",
        'y': "v",
        ':': ".",
        ';': ",:",
        ',': ".",
        '=': "-",
        '+': "-|",
        '*': "+",
        '@': "0",
        '0': "C(",
        '1': "|",
        '6': "o",
        '7': "/",
        '8': "3o",
}

def scramble_a_little(text, but_not=None):
    ltext = text.split(' ')
    for i, w in enumerate(ltext):
        if not w:
            continue
        if but_not and (compare_words(w, but_not) or but_not.lower() in w.lower()):
            continue
        while random.random() < 0.4:
            l = random.choice(w)
            newc = l
            if l in nethack:
                newc = random.choice(nethack[l])
            ltext[i] = w.replace(l, newc, 1)
    return ' '.join(ltext)

def show_page(pageid, **kwargs):
    word = get_word_for_page(pageid)
    text = get_true_text(pageid)
    return show_framedtext(text, word, **kwargs)

def show_framedtext(text, word, clear=False, pagenum=None, highlight=False):
    def nsp(n):
        t = ''
        for i in range(n):
            if random.random() < 0.07:
                t += random.choice('.,°`·')
            else:
                t += ' '
        return t
    text = scramble_a_little(text, word)
    ll = max(len(t) for t in text.split('\n'))
    scramble = (lambda x: x) if clear else scramble_word
    text = text.replace(word, 'BLUE'+scramble(word)+'CLEAR')
    scratchs = (
            '-', '|', '`', '\\', '/', '_', ' ',
            ')', ']', '=', '(', '"', '\'', '~',
            '1', '2', '3', '0',
    )
    if pagenum:
        pagestr = 'Page'
        pagenum = str(pagenum)
    else:
        pagestr = scramble_a_little('Page')
        pagenum = random.choice(scratchs) + random.choice(scratchs)
    hs, he = '', ''
    if highlight:
        hs, he = 'BLUE', 'CLEAR'
    page = f'''\
{hs} _{'_'*ll}_{he}
{hs}/{he} {pagestr} {pagenum}  {hs}{' '*(ll-7-len(pagenum))}`\\{he}
{hs}| {nsp(ll)} |{he}\n'''
    for t in text.split('\n'):
        pad = ll - len(parse_void(t))
        page += f'''{hs}|{he} {t} {' '*pad}{hs}|{he}\n'''
    page += f'''\
{hs}| {nsp(ll)} |{he}
{hs}\_{'_'*ll}_/{he}'''
    return page

def help_step(phash, msg):
    pageid = get_current_page_for_player(phash)

    if not pageid:
        pageid = get_and_set_new_page_for_player(phash, 'help')
        if not pageid:
            r.hset(RK('players:finished_help'), phash, 1)
            advance_player_step(phash, silence=True)
            return True
        send_to_player(phash, random.choice((
            'You pick one of the pages from the pile:',
            'You notice a particularly interesting page:',
            'Out of all remaining pages, you decide to pick this one:',
        )))
        page = show_page(pageid, clear=True)
        send_to_player(phash, page)
        send_to_player(phash, f'''The word BLUE{get_word_for_page(pageid)}CLEAR is starting to fade away, let's keep it strong!''')
        send_to_player(phash, random.choice((
            'How would like to annotate this page?',
            'Which annotation would you like to add?',
            'Which word would you like to add?',
        )))
        return False

    if not msg:
        return False

    # just for info, keep the proposition
    r.hincrby(RK(f'all_proposed_words:for_page_{pageid}'), msg, 1)

    if not word_is_english(msg):
        send_to_player(phash, random.choice((
            'This word is not in my dictionary. Try again.',
            'Does this word really exist? Try another one.',
        )))
        return False

    if len(msg) <= 2:
        send_to_player(phash, random.choice((
            'Use words with more than 2 letters. Try another one.',
            'This word is too short. Try a longer one.',
        )))
        return False

    curword = get_word_for_page(pageid)
    if word_contains(curword, msg) or compare_words(curword, msg):
        send_to_player(phash, random.choice((
            'This word is too close to the original one. Try a more different one.',
        )))
        return False

    remove_page_for_player(phash, pageid)
    send_to_player(phash, random.choice((
        f'Great! You proposed GREEN{msg}CLEAR to help people guess the word BLUE{curword.lower()}CLEAR!',
        f'You proposed GREEN{msg}CLEAR to help people guess the word BLUE{curword.lower()}CLEAR!',
        f'You carefully write GREEN{msg}CLEAR in the margin of the page.',
        f'You write GREEN{msg}CLEAR on the page.',
        f'You elegantly write GREEN{msg}CLEAR on the page.',
    )))
    others = r.hget(RK(f'proposed_words:for_page_{pageid}'), msg)
    if others:
        others = int(others)
        send_to_player(phash, random.choice((
            f'{others} persons proposed this word on the page.',
            f'Actually, {others} persons proposed this word on this page.',
        )))
    else:
        send_to_player(phash, random.choice((
            'You are the first to propose this word, yay!',
            'You are the first to propose this word, nice!',
            'This word was never proposed before.',
        )))
    r.hincrby(RK(f'proposed_words:for_page_{pageid}'), msg, 1)
    r.hdel(RK('player_pages:current'), phash)
    advance_player_step(phash)
    return True

def guess_step(phash, msg):
    pageid = get_current_page_for_player(phash)

    if not pageid:
        pageid = get_and_set_new_page_for_player(phash, 'guess')
        if not pageid:
            r.hset(RK('players:finished_guess'), phash, 1)
            advance_player_step(phash, silence=True)
            return True
        random.seed(int(r.hget(RK('pages:seed'), pageid)))
        page = show_page(pageid)
        send_to_player(phash, random.choice((
            'You pick one of the pages from the pile:',
            'You notice a particularly interesting page:',
            'Out of all remaining pages, you decide to pick this one:',
        )))
        send_to_player(phash, page)
        send_to_player(phash, f'''Annotated on the bottom:\n   {get_hint_for_page(pageid)}''')
        send_to_player(phash, f'Please find the right word to restore the power of this page.')
        return False

    if not msg:
        return False

    r.hincrby(RK(f'all_guessed_words:for_page_{pageid}'), msg, 1)

    if not word_is_english(msg):
        send_to_player(phash, random.choice((
            'This word is not in my dictionary. Try again.',
            'Does this word really exist? Try another one.',
        )))
        return False

    r.rpush(RK(f'proposed_words:by_{phash}:for_page_{pageid}'), msg)

    curword = get_word_for_page(pageid)
    if not compare_words(curword, msg):
        send_to_player(phash, random.choice((
            'Unfortunately, that is not the right word. Try again.',
            'Unfortunately, that is not the right word. Try again.',
            'Unfortunately, that is not the right word. Try again.',
            'You try writing the word on the paper, but it zaps you. Try another one.',
            'You don\'t even try to write the word, it is clearly wrong. Try again.',
        )))
        triedwords = get_already_proposed_for_page(phash, pageid)
        if triedwords:
            send_to_player(phash, random.choice((
                f'You already tried: {triedwords}.',
                f'Remember, you already tried: {triedwords}.',
                f'Remember that you already tried: {triedwords}.',
            )))
        # send_to_player(phash, 'You put the page down and will look at it later')
        # r.hdel(RK('player_pages:current'), phash)
        # advance_player_step(phash)
        return False

    send_to_player(phash, random.choice((
        f'You spell the word out loud, the page responds by glowing intensely.',
        f'While thinking about the word {msg}, the page suddenly glows.',
        f'You carefully write the word on the paper. You feel certain that this is the right word.',
    )))

    remove_page_for_player(phash, pageid)
    r.hdel(RK('player_pages:current'), phash)
    advance_player_step(phash)
    return True

def show_whole_book_for_player(phash):
    ppages = r.smembers(RK(f'player_pages:guess:{phash}')) | r.smembers(RK(f'player_pages:help:{phash}'))
    ppages = sorted([int(p) for p in list(ppages)])
    book = []
    for i, pageid in enumerate(ppages):
        page = show_page(pageid, clear=True, pagenum=i+1, highlight=True)
        book.append(page)
    return '\n'.join(book)

def player_game(phash, pmsg):
    if not r.hget(RK('intro:ok'), phash):
        prepare_player(phash)
        msg = intro_for_new_players(phash)
        send_to_player(phash, msg)
        r.hset(RK('intro:ok'), phash, 1)

    if not r.hget(RK('player_ended'), phash):
        steps = {'guess': guess_step, 'help': help_step}
        loop = True
        won = False
        while loop:
            if r.hget(RK('players:finished_guess'), phash) and r.hget(RK('players:finished_help'), phash):
                won = True
                break
            curstep = get_player_step(phash)
            loop = steps[curstep](phash, pmsg)
            pmsg = None
        if won:
            r.hset(RK('player_ended'), phash, 1)
            send_to_player(phash, 'Wonderful work, you\'ve completed all pages and you kept them alive.')
            send_to_player(phash, 'You take a proud look at the resulting book:')
            send_to_player(phash, show_whole_book_for_player(phash))
            send_to_player(phash, random.choice((
                'You exit the cave, a bit confused by the meaning of these texts.',
                'You leave the cave, wondering about the sanity of its writer.',
                'You think for a while about all that. After a few minutes, you leave the cave and go back to your work.',
                'You feel a great deal of responsability and decide to follow this exciting adventure!',
                'You do not really care about all that, but respect the point of view of the writer. You leave the cave.',
            )))
            send_to_player(phash, 'BLUEThank you for playing!CLEAR')
    else:
        send_to_player(phash, 'BLUEThank you for playing!CLEAR Your annotations certainly will help others!')

def player_retrieve_sendto(phash):
    msg = r.getset(RK(f'send_to:{phash}'), '') or ''
    if msg:
        msg = msg.decode('utf-8')
    return msg

def ircprint(phash, msg):
    def parse(msg):
        msg = msg.replace('CLEAR', fg(0))
        msg = msg.replace('BLUE', fg(4))
        msg = msg.replace('GREEN', fg(2))
        msg = msg.replace('GREY', fg(7))
        return msg
    for l in msg.split('\n'):
        if not l.strip(): continue
        print(f'{phash} -> {parse(l)}')

def player_receive(phash, msg):
    print(f'{attr(7)}{phash}{attr(0)+attr(4)} <- {msg}{attr(0)}')
    if msg.endswith('.'):
        msg = msg[:-1]
    if msg.endswith('!'):
        msg = msg[:-1]
    if msg.endswith(','):
        msg = msg[:-1]
    msg = msg.lower()
    player_game(phash, msg)

def player_disconnect(phash):
    r.hdel(RK('player_pages:current'), phash)

def test():
    print(f'\n\n\n\n{random.random()*1e8}\n')
    # reset()
    # setup()
    assert compare_words('Fly', 'flies')
    assert word_contains('harder', 'hardest')
    assert word_contains('live', 'living')
    assert not word_is_english('-')
    assert not word_is_english('test)')

    print('begin session')
    phash = 'localhost_kid'
    r.hdel(RK('intro:ok'), phash)
    player_disconnect(phash)
    player_receive(phash, 'hi')
    ircprint(phash, player_retrieve_sendto(phash))
    player_receive(phash, 'blabla')
    ircprint(phash, player_retrieve_sendto(phash))
    player_receive(phash, 'deep')
    ircprint(phash, player_retrieve_sendto(phash))

    ircprint(phash, ambiant_sound())
    ircprint(phash, ambiant_sound())
    ircprint(phash, ambiant_sound())
    ircprint(phash, ambiant_sound())
    ircprint(phash, ambiant_sound())
    ircprint(phash, ambiant_sound())
    ircprint(phash, ambiant_sound())
    ircprint(phash, ambiant_sound())

    if False:
        page = show_page(1)
        send_to_player(phash, page)
        page = show_page(2)
        send_to_player(phash, page)
        ircprint(phash, player_retrieve_sendto(phash))
    if True:
        ircprint(phash, show_whole_book_for_player(phash))

def cli_input():
    phash = 'kid2'
    player_disconnect(phash)
    player_receive(phash, 'hi')
    while True:
        ircprint(phash, player_retrieve_sendto(phash))
        str = input()
        player_receive(phash, str)

def main():
    global fg, bg, attr
    fg = lambda x: ''
    bg = lambda x: ''
    attr = lambda x: ''
    from flask import Flask
    from flask import abort, jsonify
    from flask import request
    app = Flask(__name__)
    @app.route('/pubmsg', methods=['POST'])
    def predict():
        try:
            if not request.json or 'what' not in request.json or 'who' not in request.json:
                abort(400)
            who = request.json['who']
            what = request.json['what']
            player_receive(who, what)
            # send_pages(who, get_true_text(0), 'sanctuary')
            msg = player_retrieve_sendto(who)
            return jsonify({'reply': msg}), 201
        except:
            traceback.print_exc(file=sys.stdout)
    app.run(port=5005, debug=True)

def http():
    global fg, bg, attr
    fg = lambda x: ''
    bg = lambda x: ''
    attr = lambda x: ''
    from flask import Flask
    from flask import abort, jsonify
    from flask import request, session
    app = Flask(__name__)
    app.secret_key = b'something secret' + r.get(RK('http_secret'))
    @app.route('/pubmsg', methods=['POST'])
    def predict():
        try:
            if not request.json or 'what' not in request.json: # or 'who' not in request.json:
                abort(400)
            what = request.json['what']
            ip = request.remote_addr
            if 'id' not in session:
                session['id'] = str(r.incr(RK('http_id')))
                print('created session for', ip, session['id'])
            who = session['id'] + '_' + ip
            player_receive(who, what)
            msg = player_retrieve_sendto(who)
            lmsg = []
            for l in msg.split('\n'):
                if not l.strip(): continue
                lmsg.append(l)
            msg = '\n'.join(lmsg) + '\n'
            return jsonify({'reply': msg}), 200
        except:
            traceback.print_exc(file=sys.stdout)
    @app.route('/')
    def index():
        try:
            return open('index.html').read()
        except:
            traceback.print_exc(file=sys.stdout)
    app.run(port=5004, debug=True)

if __name__ == '__main__':
    import fire
    fire.Fire({
        'main': main,
        'http': http,
        'input': cli_input,
        'test': test,
        'reset': reset,
        'setup': setup,
    })

