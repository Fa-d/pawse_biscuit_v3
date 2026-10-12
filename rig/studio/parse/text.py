"""From what people type to clean tokens.

People type "heyyyy 😂😂", "Café vibes!!", "it's ok :)", "self-care", "thx u", "HAPPY BDAY".  Before any word is
looked up:

  * Unicode is normalised (full-width letters, ligatures), accents are dropped (café -> cafe, cumpleaños ->
    cumpleanos) and curly quotes and dashes become plain ones
  * emoticons (:) ;) :D <3 :'( -_- ^^ ...) and emoji become words the lexicon knows; an emoji nobody listed falls
    back to its Unicode name (🍕 SLICE OF PIZZA -> "pizza")
  * stretched words shrink back ("heyyyy" -> "hey", "sooo" -> "so", "cooool" -> "cool") and count as emphasis, so do
    words in capitals and exclamation marks
  * laughter in any spelling becomes "haha" ("hahahaha", "lolol", "lmaooo", "jajaja", "xD")
  * chat shorthand is spelt out ("thx" -> "thanks", "u" -> "you", "omw" -> "on my way", "idk" -> "i don't know")
  * clause breaks (, . ; ! ? and 'but') are kept as '|' so a 'not' never reaches past them
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

BREAK = "|"

# emoticons -> words (longest first when matching)
EMOTICONS = {
    ":')": "happy tears", ":'-)": "happy tears", ":'(": "crying", ":'-(": "crying", ";_;": "crying", "t_t": "crying", "t.t": "crying",
    ":-)": "smile", ":)": "smile", "(:": "smile", "=)": "smile", ":]": "smile", ":}": "smile", "^_^": "happy", "^^": "happy", "^.^": "happy",
    ":-d": "laughing", ":d": "laughing", "xd": "laughing", "x-d": "laughing", "=d": "laughing",
    ":-(": "sad", ":(": "sad", "):": "sad", "=(": "sad", ":[": "sad", ":c": "sad",
    ";-)": "wink", ";)": "wink", ";d": "wink",
    ":-p": "silly", ":p": "silly", ";p": "silly", "xp": "silly", ":b": "silly",
    ":-o": "surprised", ":o": "surprised", "o_o": "shocked", "o.o": "shocked", "0_0": "shocked", "o_0": "confused", "0_o": "confused",
    "o.0": "confused", ":/": "unsure", ":-/": "unsure", ":\\": "unsure", ":|": "unamused", ":-|": "unamused", "-_-": "unamused",
    "-.-": "unamused", ">:(": "angry", ">:-(": "angry", ">_<": "flustered", "><": "flustered", "x_x": "knocked out", "@_@": "dizzy",
    "<3": "love", "<33": "love", "<333": "love", "</3": "heartbroken", ":*": "kiss", ":-*": "kiss", ":3": "uwu", "uwu": "uwu", "owo": "owo",
    "u_u": "sad", "zzz": "zzz", "z_z": "sleepy", "-.-zzz": "sleepy", "\\o/": "cheering", "o/": "waving", "\\o": "waving",
    "¯\\_(ツ)_/¯": "shrug", "¯\\(ツ)/¯": "shrug",
}
_EMOTICON_RE = None          # built on first use from the folded keys (fold turns '¯' into a space)
_FOLDED_EMOTICONS = {}

# emoji -> words.  Everything not listed here is read by its Unicode name.
EMOJI = {
    "😀": "grinning", "😃": "happy", "😄": "happy", "😁": "grinning", "😆": "laughing", "😅": "nervous laugh", "🤣": "rolling laughing",
    "😂": "laughing tears", "🙂": "smile", "🙃": "silly", "😉": "wink", "😊": "warm smile", "😇": "angel", "🥰": "in love",
    "😍": "heart eyes", "🤩": "star struck", "😘": "blowing kiss", "😗": "kiss", "😚": "kiss", "😙": "kiss", "😋": "yummy",
    "😛": "tongue out", "😜": "silly wink", "🤪": "crazy silly", "😝": "tongue out", "🤑": "money", "🤗": "hug", "🤭": "giggle",
    "🫢": "oops", "🤫": "shh", "🤔": "thinking", "🫡": "salute", "🤐": "zipped", "🤨": "skeptical", "😐": "neutral", "😑": "unamused",
    "😶": "speechless", "😏": "smug", "😒": "unamused", "🙄": "eye roll", "😬": "nervous", "🤥": "lying", "😌": "relieved",
    "😔": "sad", "😪": "sleepy", "🤤": "drooling", "😴": "sleeping", "😷": "sick mask", "🤒": "sick", "🤕": "hurt", "🤢": "sick",
    "🤮": "sick", "🤧": "sneeze", "🥵": "hot", "🥶": "cold", "🥴": "dizzy", "😵": "knocked out", "😵‍💫": "dizzy", "🤯": "mind blown",
    "🤠": "cowboy", "🥳": "party", "🥸": "disguise", "😎": "cool", "🤓": "nerd", "🧐": "monocle", "😕": "confused", "😟": "worried",
    "🙁": "sad", "☹️": "sad", "😮": "surprised", "😯": "surprised", "😲": "shocked", "😳": "flustered", "🥺": "pleading", "🥹": "touched",
    "😦": "worried", "😧": "worried", "😨": "scared", "😰": "nervous", "😥": "sad", "😢": "crying", "😭": "sobbing", "😱": "screaming scared",
    "😖": "flustered", "😣": "struggling", "😞": "sad", "😓": "sweat", "😩": "tired", "😫": "tired", "🥱": "yawning", "😤": "huffy",
    "😡": "angry", "😠": "angry", "🤬": "furious", "😈": "mischief", "👿": "angry devil", "💀": "dead", "☠️": "dead", "💩": "poop",
    "🤡": "clown", "👻": "ghost", "👽": "alien", "🤖": "robot", "😺": "cat happy", "😸": "cat laughing", "😹": "cat laughing tears",
    "😻": "cat heart eyes", "😼": "cat smug", "😽": "cat kiss", "🙀": "cat shocked", "😿": "cat crying", "😾": "cat angry",
    "🙈": "hide eyes", "🙉": "cover ears", "🙊": "oops", "💋": "kiss", "💌": "love letter", "💘": "love", "💝": "gift heart",
    "💖": "sparkling heart", "💗": "love", "💓": "love", "💞": "hearts", "💕": "hearts", "💟": "love", "❣️": "love", "💔": "heartbroken",
    "❤️": "love", "❤": "love", "🧡": "love", "💛": "love", "💚": "love", "💙": "love", "💜": "love", "🤎": "love", "🖤": "love",
    "🤍": "love", "💯": "perfect", "💢": "angry", "💥": "boom", "💫": "dizzy", "💦": "sweat", "💨": "dash", "💬": "talking",
    "💭": "thinking", "💤": "zzz", "👋": "waving", "🤚": "hand up", "✋": "high five", "🖐️": "hand", "👌": "ok", "🤌": "chef kiss",
    "✌️": "peace sign", "✌": "peace sign", "🤞": "fingers crossed", "🤟": "love you", "🤘": "rock on", "🤙": "call me",
    "👈": "pointing", "👉": "pointing", "👆": "pointing up", "👇": "pointing down", "☝️": "pointing up", "☝": "pointing up",
    "👍": "thumbs up", "👎": "thumbs down", "✊": "fist", "👊": "fist bump", "🤛": "fist bump", "🤜": "fist bump", "👏": "clapping",
    "🙌": "cheering", "👐": "open arms", "🤲": "please", "🤝": "deal", "🙏": "please thank you", "💪": "strong flex", "🫶": "heart hands",
    "🫰": "love", "👀": "looking", "👁️": "looking", "🧠": "smart", "🫠": "melting", "🔥": "fire lit", "✨": "sparkles", "🌟": "star sparkle",
    "⭐": "star", "🌈": "rainbow", "☀️": "sunny", "🌞": "sunny", "🌙": "night", "🌛": "night", "⛈️": "storm", "🌧️": "rain", "☔": "rain umbrella",
    "❄️": "snow", "⛄": "snowman", "☃️": "snowman", "🌸": "flowers spring", "🌺": "flower", "🌻": "sunflower", "🌹": "rose", "💐": "flowers",
    "🍀": "lucky clover", "🎉": "party confetti", "🎊": "confetti", "🎈": "balloon", "🎁": "gift", "🎂": "birthday cake", "🍰": "cake",
    "🧁": "cupcake", "🎄": "christmas", "🎅": "santa", "🤶": "santa", "🎃": "halloween pumpkin", "🦇": "bat", "🕷️": "spider", "🎆": "fireworks",
    "🎇": "fireworks", "🧧": "lunar new year", "🏮": "lantern", "🪔": "diwali lamp", "🕌": "eid", "☪️": "eid", "🌙✨": "eid", "🕋": "eid",
    "🐣": "easter chick", "🥚": "easter egg", "🍀🍀": "lucky", "🎓": "graduation", "🏆": "trophy", "🥇": "medal", "🏅": "medal",
    "🎵": "music", "🎶": "music", "🎤": "singing microphone", "🎧": "headphones", "🎸": "guitar", "🎮": "gaming", "🕹️": "gaming",
    "📱": "phone", "💻": "laptop", "📚": "books study", "📖": "book reading", "✏️": "pencil", "📝": "writing notes", "📋": "clipboard",
    "💼": "work briefcase", "💰": "money", "💵": "money", "💸": "money spending", "🛍️": "shopping", "🛒": "shopping", "✈️": "travel plane",
    "🧳": "travel", "🏖️": "beach", "🏝️": "beach", "⚽": "soccer ball", "🏀": "basketball", "🏋️": "gym workout", "🧘": "meditating",
    "☕": "coffee", "🍵": "tea", "🧋": "boba", "🥤": "soda", "🍺": "cheers", "🍻": "cheers", "🥂": "cheers", "🍷": "cheers", "🍕": "pizza",
    "🍔": "burger", "🍟": "fries", "🌭": "hotdog", "🌮": "taco", "🍩": "donut", "🍪": "cookie", "🍫": "chocolate", "🍬": "candy",
    "🍭": "lollipop", "🍦": "ice cream", "🍨": "ice cream", "🍧": "ice cream", "🍉": "watermelon", "🍎": "apple", "🍌": "banana",
    "🍓": "strawberry", "🥕": "carrot", "🍜": "ramen noodles", "🍣": "sushi", "🍙": "rice ball", "🍚": "rice", "🥐": "croissant",
    "🍞": "bread", "🥪": "sandwich", "🍿": "popcorn", "🧀": "cheese", "🍳": "cooking", "🍽️": "dinner", "🐟": "fish", "🦴": "bone",
    "🍯": "honey", "🌶️": "spicy", "🤒🤧": "sick", "💊": "medicine", "🩹": "bandage", "🌡️": "thermometer", "😷🤒": "sick",
    "🐱": "cat", "🐈": "cat", "🐶": "dog", "🐕": "dog", "🦊": "fox", "🐻": "bear", "🐼": "panda", "🐰": "bunny", "🐇": "bunny", "🐯": "tiger",
    "🐨": "koala", "🐷": "pig", "🐸": "frog", "🐧": "penguin", "🦝": "raccoon", "🐭": "mouse", "🐹": "hamster", "🦁": "lion", "🐵": "monkey",
    "🐥": "chick", "🦄": "unicorn", "🐲": "dragon", "🦖": "dinosaur",
    "✅": "done", "☑️": "done", "✔️": "done", "❌": "no", "⛔": "no", "🚫": "no", "❓": "question", "❔": "question", "❗": "attention",
    "‼️": "attention", "⁉️": "surprised question", "⚠️": "warning", "🔔": "bell reminder", "⏰": "alarm", "⌛": "waiting", "⏳": "waiting",
    "🚀": "rocket", "🏃": "running", "🚶": "walking", "💃": "dancing", "🕺": "dancing", "🤸": "jumping", "🙆": "ok", "🙅": "no",
    "🤷": "shrug", "🤦": "facepalm", "🙋": "hello", "🙇": "bow sorry", "🧎": "please", "👑": "crown king", "🎩": "top hat", "🧢": "cap",
    "👒": "sun hat", "🎀": "bow", "👓": "glasses", "🕶️": "sunglasses", "🧣": "scarf", "🧤": "gloves", "🦺": "vest", "👔": "tie",
}
_EMOJI_RE = re.compile(
    "(?:[\U0001F1E6-\U0001F1FF]{2})"                                     # flags
    "|(?:[\u00a9\u00ae\u203c\u2049\u2122\u2139\u2194-\u21aa\u231a-\u23ff\u24c2\u25aa-\u27bf\u2934\u2935\u2b05-\u2b55\u3030\u303d\u3297\u3299"
    "\U0001F000-\U0001FAFF][\ufe0f\U0001F3FB-\U0001F3FF]?(?:\u200d[\u2600-\u27bf\U0001F000-\U0001FAFF][\ufe0f]?)*)")

# chat shorthand -> words.  Matched as whole tokens.
SHORTHAND = {
    "u": "you", "ur": "your", "r": "are", "ya": "you", "yall": "you all", "pls": "please", "plz": "please", "plox": "please",
    "thx": "thanks", "thnx": "thanks", "tnx": "thanks", "thanx": "thanks", "tq": "thank you", "tysm": "thank you so much",
    "tyvm": "thank you very much", "np": "no problem", "idk": "i don't know", "dunno": "don't know", "idc": "i don't care",
    "brb": "be right back", "gtg": "got to go", "g2g": "got to go", "ttyl": "talk to you later", "omw": "on my way", "otw": "on my way",
    "hbd": "happy birthday", "bday": "birthday", "b'day": "birthday", "gn": "good night", "gn8": "good night", "nite": "night",
    "gm": "good morning", "mornin": "morning", "nvm": "never mind", "smh": "facepalm", "ikr": "i know right", "fr": "for real",
    "ngl": "not gonna lie", "rn": "right now", "b4": "before", "gr8": "great", "l8r": "later", "l8": "late", "2day": "today",
    "2nite": "tonight", "tmrw": "tomorrow", "tmr": "tomorrow", "luv": "love", "lub": "love", "sry": "sorry", "srry": "sorry",
    "soz": "sorry", "cuz": "because", "coz": "because", "bc": "because", "grats": "congrats", "gz": "congrats", "gg": "good game",
    "wp": "well played", "ty": "thank you", "bro": "buddy", "sis": "buddy", "bestie": "buddy", "fam": "buddy", "wanna": "want to",
    "gonna": "going to", "gotta": "got to", "lemme": "let me", "gimme": "give me", "kinda": "kind of", "sorta": "sort of",
    "imma": "i am going to", "aint": "isn't", "ain't": "isn't", "yay": "yay", "yey": "yay", "yaay": "yay", "woot": "woohoo",
    "w00t": "woohoo", "xoxo": "xoxo", "xx": "kisses", "imy": "i miss you", "ily": "i love you", "ilysm": "i love you so much",
    "ty4": "thanks for", "wbu": "what about you", "hru": "how are you", "wyd": "what are you doing", "wassup": "what's up",
    "sup": "what's up", "yo": "hey", "hiya": "hiya", "heya": "hey", "hai": "hi", "helo": "hello", "hellooo": "hello", "byee": "bye",
    "cya": "see you", "c ya": "see you", "k": "ok", "kk": "ok", "okie": "okay", "okey": "okay", "oki": "okay", "okk": "ok", "okkk": "ok",
    "yea": "yeah", "yeh": "yeah", "ye": "yes", "ya'll": "you all", "nah": "nah", "nope": "nope", "omfg": "omg", "omgg": "omg",
    "wtf": "what the heck", "wth": "what the heck", "fml": "bad day", "ffs": "annoyed", "irl": "in real life", "tbh": "honestly", "imo": "honestly", "imho": "honestly",
    "asap": "hurry", "fomo": "left out", "yolo": "yolo", "wfh": "working from home", "ooo": "out of office", "afk": "away",
    "lmk": "let me know", "hmu": "hit me up", "dm": "dm", "pm": "dm", "bff": "best friend", "goat": "champion",
    "ez": "easy", "gl": "good luck", "hf": "have fun", "glhf": "good luck have fun", "gn8t": "good night", "nyt": "night",
}

LAUGH = re.compile(r"^(?:(?:a?h+a+)+h*|(?:h+e+)+h*|(?:h+i+){2,}|(?:j+a+){2,}j*|(?:j+e+){2,}|(?:k+){3,}|(?:w+k+){2,}w*|"
                   r"l+o+l+(?:o+l+)*|l+m+f*a+o+|r+o+f+l+|x+d+|kek+|tee+hee+|bwa+ha+(?:ha)*|muha+ha+(?:ha)*)$")
KEEP_POSSESSIVE = {"it's", "that's", "what's", "let's", "he's", "she's", "there's", "here's", "who's", "how's", "where's"}

# contractions are spelt out, so "don't", "dont" and "do not" are one phrase to the lexicon, and the 'not' in them
# negates.  Only spellings without the apostrophe that are not words themselves are listed ('ill', 'well', 'were',
# 'shell', 'its' and 'id' stay as typed).
CONTRACTIONS = {
    "can't": "can not", "cannot": "can not", "won't": "will not", "ain't": "is not", "shan't": "shall not", "let's": "let us",
    "y'all": "you all", "ya'll": "you all", "c'mon": "come on", "ma'am": "madam", "o'clock": "o'clock",
    "dont": "do not", "doesnt": "does not", "didnt": "did not", "isnt": "is not", "arent": "are not", "wasnt": "was not",
    "werent": "were not", "cant": "can not", "couldnt": "could not", "wont": "will not", "wouldnt": "would not",
    "shouldnt": "should not", "havent": "have not", "hasnt": "has not", "hadnt": "had not", "aint": "is not", "mustnt": "must not",
    "im": "i am", "ive": "i have", "youre": "you are", "youve": "you have", "youll": "you will", "theyre": "they are",
    "theyve": "they have", "thats": "that is", "whats": "what is", "lets": "let us", "hes": "he is", "shes": "she is",
    "theres": "there is", "heres": "here is", "wheres": "where is", "hows": "how is", "whos": "who is", "cmon": "come on",
    "yall": "you all", "wanna": "want to", "gonna": "going to", "gotta": "got to", "lemme": "let me", "gimme": "give me",
}
_SUFFIXES = (("n't", "not"), ("'m", "am"), ("'re", "are"), ("'ve", "have"), ("'ll", "will"), ("'d", "would"))


def expand(w):
    """One word -> the words it is short for ("don't" -> do not, "i'm" -> i am, "it's" -> it is)."""
    if w in CONTRACTIONS:
        return CONTRACTIONS[w].split()
    if "'" in w:
        for suf, full in _SUFFIXES:
            if w.endswith(suf) and len(w) > len(suf):
                return [w[: -len(suf)], full]
        if w in KEEP_POSSESSIVE:
            return [w[:-2], "us" if w == "let's" else "is"]
    return [w]


@dataclass
class Token:
    text: str               # normalised word, or '|' for a clause break
    raw: str                # what was typed
    emph: float = 0.0       # 0 plain; > 0 stretched, in capitals or an emoji repeated
    source: str = "word"    # word, emoji, emoticon, shorthand, laugh


def fold(s):
    """Accents off, compatibility forms normalised, typographic quotes and dashes made plain."""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'").replace("`", "'").replace("´", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("…", "...")
    out = []
    for ch in unicodedata.normalize("NFKD", s):
        if unicodedata.combining(ch) and not (0x0900 <= ord(ch) <= 0x0DFF):     # keep Indic vowel signs
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def emoji_words(e):
    """Words for one emoji: the table above, else its Unicode name ('SLICE OF PIZZA' -> 'slice of pizza')."""
    if e in EMOJI:
        return EMOJI[e]
    base = e.replace("\ufe0f", "")
    if base in EMOJI:
        return EMOJI[base]
    names = []
    for ch in base:
        if ch == "\u200d" or 0x1F3FB <= ord(ch) <= 0x1F3FF:
            continue
        try:
            names.append(unicodedata.name(ch).lower())
        except ValueError:
            pass
    words = " ".join(names)
    words = re.sub(r"\b(face|with|of|and|symbol|sign|emoji|black|white|medium|large|small|heavy)\b", " ", words)
    return " ".join(words.split())


def unstretch(word, known):
    """'heyyyy' -> 'hey': shrink runs of three or more letters; prefer a spelling the lexicon knows."""
    if not re.search(r"(.)\1\1", word):
        return word, False
    two = re.sub(r"(.)\1{2,}", r"\1\1", word)
    one = re.sub(r"(.)\1{2,}", r"\1", word)
    for cand in (one, two):
        if cand in known:
            return cand, True
    # runs of two may also be stretched ('sooo' -> 'soo' -> 'so')
    single = re.sub(r"(.)\1+", r"\1", word)
    if single in known:
        return single, True
    return two, True


def _emoticons():
    global _EMOTICON_RE
    if _EMOTICON_RE is None:
        for k, v in EMOTICONS.items():
            _FOLDED_EMOTICONS[fold(k).lower().strip()] = v
        keys = sorted(_FOLDED_EMOTICONS, key=len, reverse=True)
        _EMOTICON_RE = re.compile("|".join(re.escape(k) for k in keys))
    return _EMOTICON_RE


def tokenize(text, known=frozenset(), chat=True, listed=None):
    """Text -> [Token].  known: words the lexicon knows (to pick between spellings of stretched words).  listed: words
    the lexicon lists on their own (default: known); those are never read as shorthand or laughter ('omw' stays 'omw'
    when a template lists it).  chat=False reads text as written (no shorthand, laughter or stretching rules), which
    is how the lexicon's own phrases are read."""
    listed = known if listed is None else listed
    bangs = text.count("!")
    caps_words = {w.lower() for w in re.findall(r"\b[A-Z]{3,}\b", text)}
    t = fold(text)
    out = []
    pos = 0
    # emoji and emoticons first (they use punctuation that is about to be removed)
    pieces = []
    for m in _EMOJI_RE.finditer(t):
        pieces.append((m.start(), m.end(), "emoji", m.group(0)))
    tl = t.lower()
    for m in _emoticons().finditer(tl):
        a, b = m.span()
        if any(a < y and b > x for x, y, _, _ in pieces):
            continue
        before = tl[a - 1] if a > 0 else " "
        after = tl[b] if b < len(tl) else " "
        word_like = m.group(0)[0].isalpha() or m.group(0)[-1].isalpha()
        if word_like and (before.isalnum() or after.isalnum()):
            continue                                           # 'xd' inside 'boxdrop', ':p' in 'http://p'
        pieces.append((a, b, "emoticon", m.group(0)))
    pieces.sort()
    segs = []
    for a, b, kind, raw in pieces:
        if a < pos:
            continue
        segs.append(("text", t[pos:a]))
        segs.append((kind, raw))
        pos = b
    segs.append(("text", t[pos:]))
    last_emoji = None
    for kind, raw in segs:
        if kind == "emoji":
            words = emoji_words(raw)
            rep = 0.6 if last_emoji == raw else 0.0
            last_emoji = raw
            for w in words.split():
                out.append(Token(w, raw, rep, "emoji"))
            continue
        if kind == "emoticon":
            for w in _FOLDED_EMOTICONS[raw.lower()].split():
                out.append(Token(w, raw, 0.0, "emoticon"))
            last_emoji = None
            continue
        if raw.strip():
            last_emoji = None
        s = raw.lower()
        s = re.sub(r"[,.;!?]+|\s-\s|:\s|\bbut\b|\bthough\b|\balthough\b|\bhowever\b", f" {BREAK} ", s)
        s = re.sub(r"[\-_/+&~*#@()\[\]{}<>=\"]+", " ", s)
        s = "".join(ch if (ch in "'| " or unicodedata.category(ch)[0] in "LMN") else " " for ch in s)   # letters, marks, digits
        s = re.sub(r"(?<![a-z0-9])'|'(?![a-z])", " ", s)
        for w in s.split():
            if w == BREAK:
                out.append(Token(BREAK, w))
                continue
            if w.endswith("'s") and w not in KEEP_POSSESSIVE:
                w = w[:-2]
            emph = 0.6 if w in caps_words else 0.0
            if not chat or w in listed:          # a word the lexicon lists exactly is read as written
                for x in expand(w):
                    out.append(Token(x, w, emph))
                continue
            if LAUGH.match(w):
                out.append(Token("haha", w, emph + (0.4 if len(w) > 6 else 0.0), "laugh"))
                continue
            w2, stretched = unstretch(w, known)
            if stretched:
                emph += 0.5
            if w2 in SHORTHAND and w2 not in listed:
                for x in SHORTHAND[w2].split():
                    for y in expand(x):
                        out.append(Token(y, w, emph, "shorthand"))
                continue
            if LAUGH.match(w2) and w2 not in listed:
                out.append(Token("haha", w, emph, "laugh"))
                continue
            for x in expand(w2):
                out.append(Token(x, w, emph))
    # collapse repeated breaks
    clean = []
    for tok in out:
        if tok.text == BREAK and (not clean or clean[-1].text == BREAK):
            continue
        clean.append(tok)
    while clean and clean[-1].text == BREAK:
        clean.pop()
    return clean, bangs


def normalize(text):
    """v3 interface: the normalised prompt as one string ('|' marks clause breaks)."""
    toks, _ = tokenize(text)
    return " ".join(t.text for t in toks)
