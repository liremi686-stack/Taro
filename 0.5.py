# main.py
import sys
import os
import html as _html

# ============================================================
# ПОДАВЛЕНИЕ ИНФОРМАЦИОННЫХ СООБЩЕНИЙ QT (в т.ч. ffmpeg)
# Должно быть ДО импорта любых модулей PyQt6!
# ============================================================
_existing = os.environ.get("QT_LOGGING_RULES", "")
_our_rules = "qt.multimedia.*=false;qt.qpa.*=false;*.debug=false"
os.environ["QT_LOGGING_RULES"] = (
    _existing + ";" + _our_rules if _existing else _our_rules
)

import math
import wave
import struct
import random
import tempfile
import traceback

from PyQt6.QtCore import qInstallMessageHandler, QtMsgType


def _qt_msg_handler(mode, context, message):
    if mode in (QtMsgType.QtDebugMsg, QtMsgType.QtInfoMsg):
        return
    low = message.lower()
    if "using qt multimedia with ffmpeg" in low:
        return
    if sys.stderr is not None:
        try:
            sys.stderr.write(f"[Qt] {message}\n")
        except Exception:
            pass


qInstallMessageHandler(_qt_msg_handler)
# ============================================================

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QGraphicsDropShadowEffect, QFrame,
    QComboBox, QSizePolicy, QLineEdit
)
from PyQt6.QtCore import (
    Qt, QRectF, QTimer, QPointF, QPropertyAnimation, QEasingCurve,
    pyqtProperty, QUrl
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QBrush, QLinearGradient,
    QRadialGradient, QShortcut, QKeySequence, QCursor
)

try:
    from PyQt6.QtMultimedia import QSoundEffect
    HAS_SOUND = True
except Exception:
    HAS_SOUND = False


# ============================================================
# УТИЛИТА: КРОССПЛАТФОРМЕННЫЙ ШРИФТ ЭМОДЗИ
# ============================================================
def make_emoji_font(point_size: float) -> QFont:
    f = QFont()
    f.setFamilies([
        "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji",
        "Symbola", "DejaVu Sans",
    ])
    f.setPointSizeF(point_size)
    return f


# ============================================================
# 1. ЗВУК — WAV генерируются лениво
# ============================================================
def _write_wav(path: str, samples, sr=44100):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(
            struct.pack("<h", max(-32767, min(32767, int(s))))
            for s in samples))


def _tone(freq, dur_ms, sr=44100):
    n = int(sr * dur_ms / 1000)
    out = []
    for i in range(n):
        t = i / sr
        attack = min(1.0, i / max(1, n * 0.08))
        release = 1.0 - i / n
        out.append(0.35 * attack * release * 32767 *
                   math.sin(2 * math.pi * freq * t))
    return out


def _chime(freq, dur_ms, sr=44100):
    n = int(sr * dur_ms / 1000)
    out = []
    for i in range(n):
        t = i / sr
        env = math.exp(-4.0 * i / n)
        s = (math.sin(2 * math.pi * freq * t)
             + 0.5 * math.sin(2 * math.pi * freq * 2.76 * t)
             + 0.25 * math.sin(2 * math.pi * freq * 5.40 * t))
        out.append(0.28 * env * 32767 * s / 1.75)
    return out


def _chord(freqs, dur_ms, sr=44100):
    n = int(sr * dur_ms / 1000)
    out = []
    for i in range(n):
        t = i / sr
        env = math.exp(-2.5 * i / n)
        s = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
        out.append(0.30 * env * 32767 * s)
    return out


class SoundPlayer:
    def __init__(self):
        self.enabled = True
        self.effects = {}
        if not HAS_SOUND:
            return
        d = os.path.join(tempfile.gettempdir(), "tarot_sounds_v1")
        os.makedirs(d, exist_ok=True)
        specs = {
            "flip":   ("flip.wav",   lambda: _tone(720, 70)),
            "reveal": ("reveal.wav", lambda: _chime(880, 320)),
            "final":  ("final.wav",  lambda: _chord([523, 659, 784, 1046], 700)),
        }
        for name, (fname, gen) in specs.items():
            path = os.path.join(d, fname)
            if not os.path.exists(path):
                try:
                    _write_wav(path, gen())
                except Exception:
                    continue
            eff = QSoundEffect()
            eff.setSource(QUrl.fromLocalFile(path))
            eff.setVolume(0.45)
            self.effects[name] = eff

    def play(self, name):
        if not self.enabled:
            return
        eff = self.effects.get(name)
        if eff is not None:
            eff.play()

    def stop_all(self):
        for eff in self.effects.values():
            try:
                eff.stop()
            except Exception:
                pass


# ============================================================
# 2. ИНТЕРНАЦИОНАЛИЗАЦИЯ
# ============================================================
LANG = {"current": "ru"}


def set_lang(code: str):
    LANG["current"] = code


def tr(key: str, **kw) -> str:
    lang_dict = T.get(LANG["current"], T["ru"])
    text = lang_dict.get(key) or T["ru"].get(key) or key
    return text.format(**kw) if kw else text


T = {
    "ru": {
        "win_title": "🔮 Таро — Расклады",
        "header": "✦  РАСКЛАД ТАРО  ✦",
        "spread_label": "Вид расклада:",
        "lang_label": "Язык:",
        "sound_tooltip": "Звук вкл/выкл",
        "question_placeholder": "Сформулируйте свой вопрос (необязательно)…",
        "btn_spread": "🎴   СДЕЛАТЬ РАСКЛАД",
        "btn_revealing": "✨   КАРТЫ РАСКЛАДЫВАЮТСЯ…",
        "btn_again": "🔄   НОВЫЙ РАСКЛАД",
        "fs_tooltip": "Полный экран (F11)",
        "placeholder": "🔮<br><br>Выберите расклад и нажмите<br>"
                       "<span style='color:#d4af37;font-weight:bold;'>"
                       "СДЕЛАТЬ РАСКЛАД</span>",
        "opening": "🕯️ Карты открываются…",
        "badge_upright": "▲ ПРЯМАЯ",
        "badge_reversed": "▼ ПЕРЕВЁРНУТА",
        "orient_upright": "прямая",
        "orient_reversed": "перевёрнутая",
        "sec_tolkovanie": "✦ ТОЛКОВАНИЕ РАСКЛАДА ✦",
        "sec_story": "📖 РАЗВЁРНУТАЯ ИСТОРИЯ",
        "sec_synthesis": "🔗 СИНТЕЗ РАСКЛАДА",
        "sec_advice": "💡 СОВЕТЫ",
        "sec_advice_day": "💡 СОВЕТ ДНЯ",
        "sec_answer": "✦ ОТВЕТ НА ВОПРОС ✦",
        "sec_feelings": "💗 ЧУВСТВА И ОТНОШЕНИЯ",
        "sec_compat": "🔗 СОВМЕСТИМОСТЬ И ПЕРСПЕКТИВА",
        "sec_analysis": "📊 АНАЛИЗ СИТУАЦИИ",
        "sec_strategy": "🎯 ОБЩАЯ СТРАТЕГИЯ",
        "sec_verdict": "🎯 ИТОГОВЫЙ ВЕРДИКТ",
        "sec_combos": "🔀 КОМБИНАЦИИ КАРТ",
        "sec_money": "💰 ФИНАНСОВЫЙ АНАЛИЗ",
        "sec_health": "🌿 ЭНЕРГИЯ И СОСТОЯНИЕ",
        "your_question": "Ваш вопрос",
        "answer_yes": "ДА",
        "answer_no": "НЕТ",
        "answer_maybe": "ВОЗМОЖНО",
        "conf_high": "уверенность: высокая",
        "conf_mid": "уверенность: средняя",
        "footer": "Карты Таро — инструмент для размышления, "
                  "а не приговор судьбы.<br>Ваша жизнь — в ваших руках. ✨",
        "q_yesno": "Карты дают утвердительный ответ. Вселенная "
                   "поддерживает ваш план, и ситуация складывается в вашу пользу.",
        "q_no": "Карты дают отрицательный ответ. Сейчас не время "
                "для этого шага — обстоятельства против вас.",
        "q_maybe": "Однозначного ответа нет. Исход зависит от ваших "
                   "действий и от того, насколько вы готовы приложить усилия.",
        "past_rev": "В прошлом ключевую роль сыграла перевёрнутая "
                    "карта {name}. Её энергия была заблокирована, что "
                    "привело к {meaning}.",
        "past_up": "Прошлое сформировала карта {name}, принёсшая в "
                   "вашу жизнь {meaning}.",
        "pres_rev": "Сейчас {name} в перевёрнутом положении "
                    "указывает на {meaning}. Настоящий момент требует "
                    "переосмысления: препятствие кроется внутри вас.",
        "pres_up": "Сегодня в центре внимания — {name}. Её прямая "
                   "энергия проявляется как {meaning}.",
        "fut_rev": "Будущее обещает перемены через {name}, но в "
                   "перевёрнутом положении: возможны {meaning}.",
        "fut_up": "В ближайшем будущем вас ждёт {name} — {meaning}.",
        "syn_3up": "Все три карты в прямом положении — крайне "
                   "благоприятный знак. Действуйте уверенно.",
        "syn_3rev": "Все карты перевёрнуты — сигнал остановиться и "
                    "пересмотреть свой путь.",
        "syn_2up": "Расклад в целом благоприятный: два аркана в "
                   "прямом положении против одного.",
        "syn_2rev": "Расклад носит предупреждающий характер: две "
                    "карты перевёрнуты против одной прямой.",
        "day_intro_up": "Сегодня вашим проводником станет карта "
                        "{name}. Её энергия приносит в вашу жизнь "
                        "{meaning}. Вселенная настроена к вам благосклонно.",
        "day_intro_rev": "Сегодняшний день проходит под энергией "
                         "перевёрнутой карты {name}. Её сила проявлена "
                         "не полностью: {meaning}. День потребует "
                         "осознанности.",
        "day_mood_up": "День благоприятен — действуйте уверенно.",
        "day_mood_rev": "День скорее требует осторожности, чем "
                        "решительных действий.",
    },
    "en": {
        "win_title": "🔮 Tarot — Spreads",
        "header": "✦  TAROT SPREAD  ✦",
        "spread_label": "Spread:",
        "lang_label": "Language:",
        "sound_tooltip": "Sound on/off",
        "question_placeholder": "Ask your question (optional)…",
        "btn_spread": "🎴   MAKE A SPREAD",
        "btn_revealing": "✨   CARDS ARE BEING DEALT…",
        "btn_again": "🔄   NEW SPREAD",
        "fs_tooltip": "Fullscreen (F11)",
        "placeholder": "🔮<br><br>Choose a spread and press<br>"
                       "<span style='color:#d4af37;font-weight:bold;'>"
                       "MAKE A SPREAD</span>",
        "opening": "🕯️ Cards are opening…",
        "badge_upright": "▲ UPRIGHT",
        "badge_reversed": "▼ REVERSED",
        "orient_upright": "upright",
        "orient_reversed": "reversed",
        "sec_tolkovanie": "✦ READING ✦",
        "sec_story": "📖 THE STORY",
        "sec_synthesis": "🔗 SYNTHESIS",
        "sec_advice": "💡 ADVICE",
        "sec_advice_day": "💡 ADVICE OF THE DAY",
        "sec_answer": "✦ ANSWER ✦",
        "sec_feelings": "💗 FEELINGS & RELATIONSHIP",
        "sec_compat": "🔗 COMPATIBILITY & OUTLOOK",
        "sec_analysis": "📊 SITUATION ANALYSIS",
        "sec_strategy": "🎯 OVERALL STRATEGY",
        "sec_verdict": "🎯 VERDICT",
        "sec_combos": "🔀 CARD COMBINATIONS",
        "sec_money": "💰 FINANCIAL ANALYSIS",
        "sec_health": "🌿 ENERGY & WELLBEING",
        "your_question": "Your question",
        "answer_yes": "YES",
        "answer_no": "NO",
        "answer_maybe": "MAYBE",
        "conf_high": "confidence: high",
        "conf_mid": "confidence: medium",
        "footer": "Tarot cards are a tool for reflection, "
                  "not a verdict of fate.<br>Your life is in your hands. ✨",
        "q_yesno": "The cards give a positive answer. The universe "
                   "supports your plan.",
        "q_no": "The cards give a negative answer. Now is not the "
                "time for this step.",
        "q_maybe": "There is no definitive answer. The outcome "
                   "depends on your actions.",
        "past_rev": "In the past, the reversed {name} played a key "
                    "role, leading to {meaning}.",
        "past_up": "The past was shaped by {name}, bringing {meaning}.",
        "pres_rev": "Right now {name} reversed points to {meaning}. "
                    "The obstacle is within you.",
        "pres_up": "Today the focus is {name}. Its upright energy "
                   "manifests as {meaning}.",
        "fut_rev": "The future promises changes through {name}, "
                   "reversed: {meaning}.",
        "fut_up": "Soon you will meet {name} — {meaning}.",
        "syn_3up": "All three cards are upright — a highly "
                   "favourable sign. Act boldly.",
        "syn_3rev": "All cards are reversed — a signal to stop "
                    "and reconsider.",
        "syn_2up": "The reading is mostly positive: two upright "
                   "cards vs one.",
        "syn_2rev": "A warning reading: two reversed cards vs one.",
        "day_intro_up": "Your guide today is {name}. Its energy "
                        "brings {meaning}.",
        "day_intro_rev": "Today passes under a reversed {name}. Its "
                         "power is blocked: {meaning}.",
        "day_mood_up": "The day is favourable — move with confidence.",
        "day_mood_rev": "A day for caution rather than bold moves.",
    },
}

POS = {
    "ru": {
        "past": "Прошлое", "present": "Настоящее", "future": "Будущее",
        "today": "Сегодня", "answer": "Ответ",
        "you": "Вы", "partner": "Партнёр", "relation": "Отношения",
        "situation": "Ситуация", "obstacle": "Препятствие",
        "advice": "Совет",
        "opt_a": "Вариант A", "opt_b": "Вариант B", "result": "Итог",
        "core": "Суть", "challenge": "Вызов", "roots": "Прошлое",
        "near": "Будущее", "outcome": "Итог",
        "income": "Доход", "expenses": "Расходы", "potential": "Потенциал",
        "body": "Тело", "mind": "Разум", "spirit": "Дух",
    },
    "en": {
        "past": "Past", "present": "Present", "future": "Future",
        "today": "Today", "answer": "Answer",
        "you": "You", "partner": "Partner", "relation": "Relationship",
        "situation": "Situation", "obstacle": "Obstacle",
        "advice": "Advice",
        "opt_a": "Option A", "opt_b": "Option B", "result": "Result",
        "core": "Core", "challenge": "Challenge", "roots": "Past",
        "near": "Near Future", "outcome": "Outcome",
        "income": "Income", "expenses": "Expenses", "potential": "Potential",
        "body": "Body", "mind": "Mind", "spirit": "Spirit",
    },
}


def pos_name(key: str) -> str:
    d = POS.get(LANG["current"], POS["ru"])
    return d.get(key) or POS["ru"].get(key, key)


# ============================================================
# 3. КАРТЫ — ПОЛНАЯ КОЛОДА 78 КАРТ
# ============================================================
CARDS = [
    # ============ СТАРШИЕ АРКАНЫ (22) ============
    ("fool", "🃏", 1,
     ("Шут",
      "новые начинания, спонтанность и свобода",
      "Не бойтесь начать что-то новое — сейчас самое подходящее время.",
      "безрассудство, нерешительность и страх первого шага",
      "Внимательно оцените риски, прежде чем действовать."),
     ("The Fool",
      "new beginnings, spontaneity and freedom",
      "Don't be afraid to start something new — now is the perfect time.",
      "recklessness, indecision and fear of the first step",
      "Carefully weigh the risks before acting.")),

    ("magician", "🎩", 1,
     ("Маг",
      "сила воли, мастерство и реализация идей",
      "У вас есть все ресурсы для достижения цели — действуйте!",
      "манипуляции, неуверенность и неиспользованный потенциал",
      "Пересмотрите свои намерения и верьте в собственные силы."),
     ("The Magician",
      "willpower, mastery and realisation of ideas",
      "You have all the resources to reach your goal — act!",
      "manipulation, insecurity and unused potential",
      "Revisit your intentions and believe in your own strength.")),

    ("priestess", "🌙", 0,
     ("Жрица",
      "интуиция, тайные знания и внутренний голос",
      "Прислушайтесь к интуиции — она подскажет верный путь.",
      "игнорирование интуиции и скрытые мотивы",
      "Не отмахивайтесь от внутренних сигналов — они важны."),
     ("The High Priestess",
      "intuition, hidden knowledge and the inner voice",
      "Listen to your intuition — it will show the way.",
      "ignored intuition and hidden motives",
      "Do not dismiss your inner signals — they matter.")),

    ("empress", "🌸", 1,
     ("Императрица",
      "изобилие, творчество, забота и рост",
      "Позвольте проектам расцвести — время благоприятствует.",
      "зависимость, творческий застой и пренебрежение собой",
      "Уделите время себе и своему внутреннему состоянию."),
     ("The Empress",
      "abundance, creativity, care and growth",
      "Let your projects bloom — the time favours you.",
      "dependency, creative block and self-neglect",
      "Take time for yourself and your inner state.")),

    ("emperor", "🏛️", 1,
     ("Император",
      "стабильность, авторитет и контроль",
      "Проявите дисциплину и организуйте свою жизнь.",
      "тирания, упрямство и потеря контроля",
      "Не будьте слишком жёстким — иногда гибкость важнее."),
     ("The Emperor",
      "stability, authority and control",
      "Show discipline and organise your life.",
      "tyranny, stubbornness and loss of control",
      "Don't be too rigid — sometimes flexibility matters more.")),

    ("hierophant", "⛪", 0,
     ("Иерофант",
      "традиции, духовность и наставничество",
      "Обратитесь за советом к опытному человеку.",
      "бунт против традиций и догматизм",
      "Не отвергайте чужой опыт полностью — в нём есть польза."),
     ("The Hierophant",
      "traditions, spirituality and mentorship",
      "Seek advice from an experienced person.",
      "rebellion against tradition and dogmatism",
      "Don't fully reject other people's experience.")),

    ("lovers", "💕", 1,
     ("Влюблённые",
      "любовь, гармония и важный выбор сердца",
      "Следуйте велению сердца — оно не обманет.",
      "разлад, разочарование и неверный выбор",
      "Не торопитесь с решением в отношениях."),
     ("The Lovers",
      "love, harmony and a heartfelt choice",
      "Follow your heart — it won't deceive you.",
      "discord, disappointment and a wrong choice",
      "Don't rush decisions in relationships.")),

    ("chariot", "🏇", 1,
     ("Колесница",
      "победа, движение и преодоление препятствий",
      "Сосредоточьтесь на цели и не сворачивайте с пути.",
      "потеря направления и отсутствие контроля",
      "Остановитесь и подумайте, куда вы на самом деле едете."),
     ("The Chariot",
      "victory, movement and overcoming obstacles",
      "Focus on your goal and don't veer off.",
      "loss of direction and lack of control",
      "Stop and think where you're really going.")),

    ("strength", "🦁", 1,
     ("Сила",
      "внутренняя сила, мужество и самоконтроль",
      "Мягкость и терпение дадут больше, чем агрессия.",
      "слабость, сомнения и потеря контроля над эмоциями",
      "Найдите источник своей внутренней силы — он есть."),
     ("Strength",
      "inner power, courage and self-control",
      "Gentleness and patience achieve more than aggression.",
      "weakness, doubt and loss of emotional control",
      "Find the source of your inner strength — it exists.")),

    ("hermit", "🕯️", -1,
     ("Отшельник",
      "мудрость, уединение и поиск истины",
      "Побудьте наедине с собой — ответы придут в тишине.",
      "изоляция, одиночество и замкнутость",
      "Не бойтесь просить поддержки у близких."),
     ("The Hermit",
      "wisdom, solitude and the search for truth",
      "Spend time alone — answers come in silence.",
      "isolation, loneliness and withdrawal",
      "Don't be afraid to ask your loved ones for support.")),

    ("wheel", "🎡", 1,
     ("Колесо Фортуны",
      "судьба, перемены к лучшему и удача",
      "Доверьтесь потоку событий — удача на вашей стороне.",
      "неудача и сопротивление переменам",
      "Примите перемены, даже если они кажутся неудачными."),
     ("Wheel of Fortune",
      "destiny, change for the better and luck",
      "Trust the flow of events — luck is on your side.",
      "misfortune and resistance to change",
      "Accept change, even if it seems unlucky.")),

    ("justice", "⚖️", 0,
     ("Справедливость",
      "правосудие, честность и баланс",
      "Поступайте по совести — правда восторжествует.",
      "несправедливость и уход от ответственности",
      "Признайте свои ошибки — это первый шаг к решению."),
     ("Justice",
      "fairness, honesty and balance",
      "Act in good conscience — the truth will prevail.",
      "injustice and evading responsibility",
      "Admit your mistakes — the first step to a solution.")),

    ("hanged", "🙃", -1,
     ("Повешенный",
      "пауза, жертва и новый взгляд",
      "Посмотрите на ситуацию с другой стороны.",
      "застой, бесполезные жертвы и упрямство",
      "Прекратите цепляться за то, что уже не работает."),
     ("The Hanged Man",
      "pause, sacrifice and a new perspective",
      "Look at the situation from another side.",
      "stagnation, useless sacrifice and stubbornness",
      "Stop clinging to what no longer works.")),

    ("death", "💀", -1,
     ("Смерть",
      "окончание, трансформация и перерождение",
      "Отпустите прошлое — на его месте вырастет новое.",
      "сопротивление переменам и страх неизвестного",
      "Не бойтесь перемен — они ведут к лучшему."),
     ("Death",
      "ending, transformation and rebirth",
      "Let go of the past — something new will grow.",
      "resistance to change and fear of the unknown",
      "Don't fear change — it leads to better things.")),

    ("temperance", "⚗️", 1,
     ("Умеренность",
      "баланс, терпение и исцеление",
      "Найдите золотую середину — не впадайте в крайности.",
      "дисбаланс, излишества и нетерпеливость",
      "Замедлитесь и приведите жизнь в равновесие."),
     ("Temperance",
      "balance, patience and healing",
      "Find the middle path — avoid extremes.",
      "imbalance, excess and impatience",
      "Slow down and bring your life into balance.")),

    ("devil", "😈", -1,
     ("Дьявол",
      "зависимость, соблазн и ограничения",
      "Осознайте свои оковы — многие из них созданы вами самими.",
      "освобождение и преодоление зависимости",
      "Вы сильнее, чем думаете — сбросьте путы!"),
     ("The Devil",
      "addiction, temptation and limitations",
      "Recognise your chains — most were forged by you.",
      "liberation and overcoming addiction",
      "You are stronger than you think — break free!")),

    ("tower", "🗼", -1,
     ("Башня",
      "внезапные перемены, кризис и разрушение старого",
      "Примите неизбежное — разрушение ведёт к обновлению.",
      "страх перемен и внутренние бури",
      "Не оттягивайте неизбежное — разберитесь с проблемой."),
     ("The Tower",
      "sudden change, crisis and destruction of the old",
      "Accept the inevitable — destruction brings renewal.",
      "fear of change and inner storms",
      "Don't postpone the inevitable — face the problem.")),

    ("star", "⭐", 1,
     ("Звезда",
      "надежда, вдохновение и исцеление",
      "Верьте в мечту — вселенная готовит вам подарок.",
      "потеря веры, разочарование и пессимизм",
      "Верните веру в себя — даже в темноте есть свет."),
     ("The Star",
      "hope, inspiration and healing",
      "Believe in your dream — the universe is preparing a gift.",
      "loss of faith, disappointment and pessimism",
      "Restore faith in yourself — even in darkness there is light.")),

    ("moon", "🌕", -1,
     ("Луна",
      "иллюзии, страхи и скрытое",
      "Не принимайте решений на эмоциях.",
      "рассеивание страхов и разоблачение обмана",
      "Истина выходит наружу — используйте это."),
     ("The Moon",
      "illusions, fears and the hidden",
      "Don't make decisions based on emotions.",
      "fears dispelled and deception revealed",
      "The truth comes out — use it.")),

    ("sun", "☀️", 1,
     ("Солнце",
      "радость, успех и жизненная энергия",
      "Наслаждайтесь моментом — удача улыбается вам.",
      "временные трудности и отложенная радость",
      "Солнце всё ещё светит — просто за тучами."),
     ("The Sun",
      "joy, success and life energy",
      "Enjoy the moment — luck smiles upon you.",
      "temporary difficulties and delayed joy",
      "The sun is still shining — just behind the clouds.")),

    ("judgement", "📯", 1,
     ("Суд",
      "возрождение, призвание и пробуждение",
      "Пришло время для судьбоносного выбора.",
      "сомнения и отказ от призвания",
      "Простите себя за прошлое и двигайтесь дальше."),
     ("Judgement",
      "rebirth, calling and awakening",
      "The time for a fateful choice has come.",
      "doubt and rejection of your calling",
      "Forgive yourself for the past and move on.")),

    ("world", "🌍", 1,
     ("Мир",
      "завершение, успех и исполнение желаний",
      "Цикл завершён — наслаждайтесь плодами своего труда.",
      "незавершённость и задержка",
      "Доведите дело до конца — не останавливайтесь."),
     ("The World",
      "completion, success and wish fulfilment",
      "The cycle is complete — enjoy the fruits of your labour.",
      "incompleteness and delay",
      "Finish what you started — don't stop halfway.")),

    # ==================================================================
    # МЛАДШИЕ АРКАНЫ — WANDS / ЖЕЗЛЫ
    # ==================================================================
    ("wands_ace", "🔥", 1,
     ("Туз Жезлов", "искра вдохновения, новый старт", "Действуйте смело — огонь зажжён.", "задержка и сомнения", "Дайте идее дозреть."),
     ("Ace of Wands", "spark of inspiration, a new start", "Act boldly — the fire is lit.", "delay and doubt", "Let the idea ripen.")),

    ("wands_2", "🔥", 0,
     ("Двойка Жезлов", "планирование, выбор пути", "Составьте план — время придёт скоро.", "нерешительность и топтание", "Хватит думать — сделайте шаг."),
     ("Two of Wands", "planning, choosing a path", "Make a plan — the time will come.", "indecision and stalling", "Stop thinking — take a step.")),

    ("wands_3", "🔥", 1,
     ("Тройка Жезлов", "расширение, дальний взгляд", "Смотрите вдаль — возможности рядом.", "задержка в реализации", "Запаситесь терпением — путь длиннее."),
     ("Three of Wands", "expansion, long-term vision", "Look ahead — opportunities are near.", "delayed realisation", "Be patient — the road is longer.")),

    ("wands_4", "🔥", 1,
     ("Четвёрка Жезлов", "праздник, дом, гармония", "Отпразднуйте успех с близкими.", "шаткий фундамент", "Укрепите дом, прежде чем бежать."),
     ("Four of Wands", "celebration, home, harmony", "Celebrate success with loved ones.", "shaky foundation", "Strengthen your base first.")),

    ("wands_5", "🔥", -1,
     ("Пятёрка Жезлов", "конкуренция, споры", "Не бойтесь борьбы — она закалит.", "избегание конфликта", "Не прячьтесь — конфликт нужно решить."),
     ("Five of Wands", "competition, arguments", "Don't fear the fight — it hardens you.", "avoiding conflict", "Face the conflict — don't hide.")),

    ("wands_6", "🔥", 1,
     ("Шестёрка Жезлов", "победа, признание", "Победа близка — примите лавры.", "отложенный триумф", "Победа придёт — но чуть позже."),
     ("Six of Wands", "victory, recognition", "Victory is near — accept the laurels.", "delayed triumph", "Victory will come — a bit later.")),

    ("wands_7", "🔥", 0,
     ("Семёрка Жезлов", "защита позиции, стойкость", "Стойте на своём — вы правы.", "сдача позиций под давлением", "Не отступайте — держитесь."),
     ("Seven of Wands", "defending position", "Stand your ground — you are right.", "giving up position", "Don't retreat — hold on.")),

    ("wands_8", "🔥", 1,
     ("Восьмёрка Жезлов", "стремительность, скорость", "Действуйте быстро — момент идеален.", "задержки и препятствия", "Замедлитесь и проверьте курс."),
     ("Eight of Wands", "swift movement, speed", "Act fast — the moment is perfect.", "delays and obstacles", "Slow down and check course.")),

    ("wands_9", "🔥", 0,
     ("Девятка Жезлов", "стойкость, испытание", "Вы у цели — ещё немного.", "усталость и подозрительность", "Отдохните, прежде чем продолжать."),
     ("Nine of Wands", "resilience, being tested", "You're almost there — hold on.", "exhaustion and suspicion", "Rest before continuing.")),

    ("wands_10", "🔥", -1,
     ("Десятка Жезлов", "перегруз, лишний груз", "Сбросьте лишнее — вы несёте много.", "сброс ноши, облегчение", "Вы близки к освобождению."),
     ("Ten of Wands", "overload, excess burden", "Drop the excess — you carry too much.", "laying down the load", "You're close to release.")),

    ("wands_page", "🔥", 1,
     ("Паж Жезлов", "энтузиазм, свежие идеи", "Свежие идеи уже в пути.", "неудачные новости", "Не принимайте новости близко к сердцу."),
     ("Page of Wands", "enthusiasm, fresh ideas", "Fresh ideas are on the way.", "bad news", "Don't take news too personally.")),

    ("wands_knight", "🔥", 1,
     ("Рыцарь Жезлов", "приключение, страсть", "Действуйте смело и ярко.", "опрометчивость и спешка", "Остудите пыл — подумайте."),
     ("Knight of Wands", "adventure, passion", "Act boldly and brightly.", "recklessness and haste", "Cool down — think first.")),

    ("wands_queen", "🔥", 1,
     ("Королева Жезлов", "харизма, тепло", "Ваша харизма — ваш козырь.", "ревность и неуверенность", "Не путайте страсть с ревностью."),
     ("Queen of Wands", "charisma, warmth", "Your charisma is your ace.", "jealousy and insecurity", "Don't confuse passion with jealousy.")),

    ("wands_king", "🔥", 1,
     ("Король Жезлов", "лидерство, видение", "Возглавьте — вы готовы.", "тирания и упрямство", "Слушайте других, не только себя."),
     ("King of Wands", "leadership, vision", "Lead — you are ready.", "tyranny and stubbornness", "Listen to others, not only yourself.")),

    # ==================================================================
    # МЛАДШИЕ АРКАНЫ — CUPS / КУБКИ
    # ==================================================================
    ("cups_ace", "🍷", 1,
     ("Туз Кубков", "новое чувство, открытое сердце", "Сердце открыто — примите любовь.", "закрытость и обида", "Не бойтесь открыться вновь."),
     ("Ace of Cups", "new love, open heart", "Your heart is open — accept love.", "closed heart and resentment", "Don't fear opening up again.")),

    ("cups_2", "🍷", 1,
     ("Двойка Кубков", "партнёрство, взаимность", "Союз обещает гармонию.", "разлад в паре", "Поговорите — не отдаляйтесь."),
     ("Two of Cups", "partnership, mutual love", "Union promises harmony.", "discord in the pair", "Talk — don't drift apart.")),

    ("cups_3", "🍷", 1,
     ("Тройка Кубков", "дружба, праздник", "Отпразднуйте с друзьями.", "сплетни и разлад", "Разберитесь, кто настоящий друг."),
     ("Three of Cups", "friendship, celebration", "Celebrate with friends.", "gossip and discord", "See who the real friend is.")),

    ("cups_4", "🍷", 0,
     ("Четвёрка Кубков", "апатия, скука", "Осмотритесь — рядом уже дар.", "пробуждение к новому", "Вы готовы принять подарок."),
     ("Four of Cups", "apathy, boredom", "Look around — a gift is near.", "awakening to the new", "You're ready to accept the gift.")),

    ("cups_5", "🍷", -1,
     ("Пятёрка Кубков", "утрата, печаль", "Позвольте себе грустить — но не застрять.", "принятие утраты", "Боль отступает — двигайтесь дальше."),
     ("Five of Cups", "loss, grief", "Allow grief — but don't get stuck.", "accepting the loss", "The pain recedes — move on.")),

    ("cups_6", "🍷", 1,
     ("Шестёрка Кубков", "ностальгия, детство", "Прошлое согревает — но живите сейчас.", "застревание в прошлом", "Отпустите вчерашний день."),
     ("Six of Cups", "nostalgia, childhood", "The past warms — but live now.", "stuck in the past", "Let go of yesterday.")),

    ("cups_7", "🍷", 0,
     ("Семёрка Кубков", "иллюзии, выбор", "Слишком много соблазнов — выберите главное.", "ясность и трезвость", "Туман рассеивается — вы видите суть."),
     ("Seven of Cups", "illusions, many choices", "Too many temptations — choose one.", "clarity and sobriety", "The fog clears — you see clearly.")),

    ("cups_8", "🍷", 0,
     ("Восьмёрка Кубков", "уход, поиск смысла", "Оставьте то, что не питает.", "возвращение к старому", "Возможно, стоит вернуться и понять."),
     ("Eight of Cups", "walking away, seeking meaning", "Leave what doesn't nourish you.", "returning to the old", "Perhaps return and understand.")),

    ("cups_9", "🍷", 1,
     ("Девятка Кубков", "довольство, исполнение желания", "Желание исполняется — наслаждайтесь.", "отложенное счастье", "Радость придёт чуть позже."),
     ("Nine of Cups", "contentment, wish fulfilled", "The wish is granted — enjoy.", "delayed happiness", "Joy will come a bit later.")),

    ("cups_10", "🍷", 1,
     ("Десятка Кубков", "полнота чувств, семья", "Разделите радость с близкими.", "разлад в семье", "Восстановите связь с родными."),
     ("Ten of Cups", "emotional fulfilment, family", "Share joy with loved ones.", "family discord", "Restore bonds with family.")),

    ("cups_page", "🍷", 1,
     ("Паж Кубков", "творчество, интуиция", "Дайте волю воображению.", "творческий блок", "Отпустите перфекционизм."),
     ("Page of Cups", "creativity, intuition", "Let imagination flow.", "creative block", "Let go of perfectionism.")),

    ("cups_knight", "🍷", 1,
     ("Рыцарь Кубков", "романтика, движение по чувству", "Следуйте за сердцем.", "переменчивость чувств", "Не путайте страсть с влюблённостью."),
     ("Knight of Cups", "romance, following heart", "Follow your heart.", "changing feelings", "Don't confuse passion with infatuation.")),

    ("cups_queen", "🍷", 1,
     ("Королева Кубков", "сострадание, чуткость", "Ваша чуткость — дар.", "эмоциональная зависимость", "Заботьтесь и о себе тоже."),
     ("Queen of Cups", "compassion, sensitivity", "Your sensitivity is a gift.", "emotional dependency", "Care for yourself too.")),

    ("cups_king", "🍷", 1,
     ("Король Кубков", "эмоциональная зрелость", "Держите баланс разума и чувств.", "манипуляции чувствами", "Не позволяйте играть вашими чувствами."),
     ("King of Cups", "emotional maturity", "Balance mind and feelings.", "emotional manipulation", "Don't let your feelings be played.")),

    # ==================================================================
    # МЛАДШИЕ АРКАНЫ — SWORDS / МЕЧИ
    # ==================================================================
    ("swords_ace", "⚔️", 1,
     ("Туз Мечей", "ясность, истина, прорыв", "Истина открыта — действуйте.", "путаница и ложь", "Проясните ситуацию, прежде чем действовать."),
     ("Ace of Swords", "clarity, truth, breakthrough", "The truth is clear — act.", "confusion and lies", "Clear things up before acting.")),

    ("swords_2", "⚔️", 0,
     ("Двойка Мечей", "тупик, сложный выбор", "Снимите повязку — сделайте выбор.", "решение принято", "Вы уже знаете ответ."),
     ("Two of Swords", "stalemate, hard choice", "Take off the blindfold — choose.", "decision made", "You already know the answer.")),

    ("swords_3", "⚔️", -1,
     ("Тройка Мечей", "боль, разрыв, правда", "Позвольте себе прожить боль.", "исцеление и заживление", "Рана затягивается — вы справитесь."),
     ("Three of Swords", "heartbreak, painful truth", "Allow yourself to feel the pain.", "healing and recovery", "The wound closes — you'll manage.")),

    ("swords_4", "⚔️", 0,
     ("Четвёрка Мечей", "покой, восстановление", "Отдохните — перезагрузка нужна.", "беспокойство и выгорание", "Вернитесь к отдыху — вы истощены."),
     ("Four of Swords", "rest, recovery", "Rest — you need a reset.", "restlessness and burnout", "Return to rest — you're drained.")),

    ("swords_5", "⚔️", -1,
     ("Пятёрка Мечей", "конфликт, цена победы", "Цена победы может быть высокой.", "перемирие и примирение", "Конфликт разрешим — идите навстречу."),
     ("Five of Swords", "conflict, cost of victory", "Victory's price may be too high.", "truce and reconciliation", "The conflict is solvable — reach out.")),

    ("swords_6", "⚔️", 1,
     ("Шестёрка Мечей", "переход, движение вперёд", "Переезд или смена курса — к лучшему.", "застрявший переход", "Не бойтесь двигаться вперёд."),
     ("Six of Swords", "transition, moving forward", "Move or change course — for the better.", "stuck transition", "Don't fear moving forward.")),

    ("swords_7", "⚔️", -1,
     ("Семёрка Мечей", "обман, хитрость", "Кто-то играет нечестно — берегитесь.", "разоблачение обмана", "Правда скоро откроется."),
     ("Seven of Swords", "deception, cunning", "Someone plays dirty — beware.", "deception revealed", "The truth will soon come out.")),

    ("swords_8", "⚔️", -1,
     ("Восьмёрка Мечей", "ограничения, самообман", "Вы сами создали свои оковы.", "освобождение от пут", "Разорвите путы — вы свободны."),
     ("Eight of Swords", "restriction, self-deception", "You built your own chains.", "release from chains", "Break the fetters — you're free.")),

    ("swords_9", "⚔️", -1,
     ("Девятка Мечей", "тревога, бессонница", "Страх больше, чем реальность.", "преодоление тревоги", "Кошмар закончился — вы в безопасности."),
     ("Nine of Swords", "anxiety, sleepless nights", "The fear is bigger than reality.", "overcoming anxiety", "The nightmare ended — you're safe.")),

    ("swords_10", "⚔️", -1,
     ("Десятка Мечей", "конец, дно, боль", "Худшее позади — рассвет близко.", "возрождение и новый цикл", "Начинается новое — с чистого листа."),
     ("Ten of Swords", "painful ending, rock bottom", "The worst is over — dawn is near.", "rebirth and a new cycle", "A new beginning — clean slate.")),

    ("swords_page", "⚔️", 0,
     ("Паж Мечей", "любопытство, наблюдательность", "Задавайте вопросы — это путь к истине.", "сплетни и болтливость", "Следите за словами — не сболтните лишнего."),
     ("Page of Swords", "curiosity, observation", "Ask questions — that's the path to truth.", "gossip and loose tongue", "Watch your words — don't say too much.")),

    ("swords_knight", "⚔️", 0,
     ("Рыцарь Мечей", "напор, прямота", "Действуйте решительно и прямо.", "агрессия и безрассудство", "Сбавьте тон — не рубите сплеча."),
     ("Knight of Swords", "drive, directness", "Act decisively and directly.", "aggression and recklessness", "Lower the tone — don't be rash.")),

    ("swords_queen", "⚔️", 1,
     ("Королева Мечей", "ясный ум, независимость", "Ваш ум — ваше главное оружие.", "холодность и резкость", "Откройте сердце — не только разум."),
     ("Queen of Swords", "clear mind, independence", "Your mind is your main weapon.", "coldness and sharpness", "Open your heart — not just your mind.")),

    ("swords_king", "⚔️", 1,
     ("Король Мечей", "интеллект, авторитет", "Ваше слово имеет вес — используйте его мудро.", "тирания разума", "Не давите — убеждайте."),
     ("King of Swords", "intellect, authority", "Your word carries weight — use it wisely.", "tyranny of reason", "Don't press — persuade.")),

    # ==================================================================
    # МЛАДШИЕ АРКАНЫ — PENTACLES / ПЕНТАКЛИ
    # ==================================================================
    ("pentacles_ace", "🪙", 1,
     ("Туз Пентаклей", "возможность, достаток, старт", "Дверь открыта — входите смело.", "упущенный шанс", "Не откладывайте — окно закроется."),
     ("Ace of Pentacles", "opportunity, prosperity", "The door is open — step in.", "missed chance", "Don't delay — the window closes.")),

    ("pentacles_2", "🪙", 0,
     ("Двойка Пентаклей", "баланс, жонглирование делами", "Удерживайте равновесие — не роняйте.", "перегруз и хаос", "Расставьте приоритеты."),
     ("Two of Pentacles", "balance, juggling priorities", "Keep the balance — don't drop anything.", "overload and chaos", "Set your priorities.")),

    ("pentacles_3", "🪙", 1,
     ("Тройка Пентаклей", "команда, мастерство", "Работайте сообща — вас оценят.", "плохая команда", "Выбирайте, с кем строить."),
     ("Three of Pentacles", "teamwork, craftsmanship", "Work together — you'll be valued.", "bad teamwork", "Choose whom to build with.")),

    ("pentacles_4", "🪙", 0,
     ("Четвёрка Пентаклей", "стабильность, экономия", "Сберегайте — но не скупитесь.", "скупость и страх потерь", "Отпустите хватку — не держите всё."),
     ("Four of Pentacles", "security, saving", "Save — but don't be stingy.", "greed and fear of loss", "Loosen your grip — don't hold it all.")),

    ("pentacles_5", "🪙", -1,
     ("Пятёрка Пентаклей", "нужда, трудности, изоляция", "Помощь рядом — постучите в дверь.", "выход из нужды", "Полоса неудач заканчивается."),
     ("Five of Pentacles", "hardship, isolation", "Help is near — knock on the door.", "coming out of hardship", "The bad streak ends.")),

    ("pentacles_6", "🪙", 1,
     ("Шестёрка Пентаклей", "щедрость, помощь", "Давайте — и получите больше.", "неравный обмен", "Проверьте, кто и что получает."),
     ("Six of Pentacles", "generosity, charity", "Give — and receive more.", "unequal exchange", "Check who gives and who receives.")),

    ("pentacles_7", "🪙", 1,
     ("Семёрка Пентаклей", "терпение, вложение", "Вложения дадут плоды — не спешите.", "сомнения в выборе", "Продолжайте — плоды близко."),
     ("Seven of Pentacles", "patience, investment", "Investments will pay off — don't rush.", "doubts about the choice", "Continue — the fruit is near.")),

    ("pentacles_8", "🪙", 1,
     ("Восьмёрка Пентаклей", "трудолюбие, обучение", "Учитесь и трудитесь — мастерство придёт.", "перфекционизм и выгорание", "Не бойтесь делать неидеально."),
     ("Eight of Pentacles", "diligence, skill", "Study and work — mastery will come.", "perfectionism and burnout", "Don't fear imperfection.")),

    ("pentacles_9", "🪙", 1,
     ("Девятка Пентаклей", "независимость, награда", "Наслаждайтесь плодами труда.", "показная роскошь", "Цените реальное, не показное."),
     ("Nine of Pentacles", "independence, reward", "Enjoy the fruits of your labour.", "showing off wealth", "Value the real, not the showy.")),

    ("pentacles_10", "🪙", 1,
     ("Десятка Пентаклей", "наследие, богатство семьи", "Прочное благополучие — разделите с семьёй.", "финансовые проблемы в семье", "Пересмотрите семейный бюджет."),
     ("Ten of Pentacles", "legacy, family wealth", "Solid prosperity — share with family.", "family financial problems", "Rethink the family budget.")),

    ("pentacles_page", "🪙", 1,
     ("Паж Пентаклей", "учёба, новое дело", "Учитесь — знание окупится.", "лень и прокрастинация", "Возьмитесь за учёбу всерьёз."),
     ("Page of Pentacles", "learning, new venture", "Study — knowledge pays off.", "laziness and procrastination", "Take study seriously.")),

    ("pentacles_knight", "🪙", 1,
     ("Рыцарь Пентаклей", "усердие, надёжность", "Упорный труд приносит результат.", "рутина и застой", "Внесите в дело немного страсти."),
     ("Knight of Pentacles", "diligence, reliability", "Hard work brings results.", "routine and stagnation", "Add a bit of passion to the work.")),

    ("pentacles_queen", "🪙", 1,
     ("Королева Пентаклей", "забота, практичность", "Практичность и забота — ваша сила.", "забвение себя в заботах", "Позаботьтесь и о себе."),
     ("Queen of Pentacles", "nurturing, practicality", "Practicality and care are your strength.", "self-neglect", "Take care of yourself too.")),

    ("pentacles_king", "🪙", 1,
     ("Король Пентаклей", "успех, деловая хватка", "Ваш опыт — источник благополучия.", "скряжество и упрямство", "Щедрость откроет новые двери."),
     ("King of Pentacles", "success, business acumen", "Your experience is a source of wealth.", "stinginess and stubbornness", "Generosity opens new doors.")),
]

CARD_BY_KEY = {c[0]: c for c in CARDS}


def card_info(key, lang, reversed_):
    c = CARD_BY_KEY[key]
    d = c[3] if lang == "ru" else c[4]
    if reversed_:
        return d[0], d[3], d[4]
    return d[0], d[1], d[2]


# ============================================================
# 4. КОМБИНАЦИИ КАРТ
# ============================================================
COMBOS = {
    ("death", "sun"): {
        "ru": "Смерть рядом с Солнцем — тяжёлый период завершается, "
              "впереди радость и облегчение.",
        "en": "Death next to the Sun — a heavy phase ends; joy ahead.",
    },
    ("tower", "star"): {
        "ru": "Башня и Звезда вместе: после краха приходит исцеление.",
        "en": "Tower with Star: healing follows the collapse.",
    },
    ("devil", "strength"): {
        "ru": "Дьявол и Сила — вы способны разорвать оковы зависимости.",
        "en": "Devil and Strength — you can break the chains.",
    },
    ("moon", "sun"): {
        "ru": "Луна и Солнце: иллюзии рассеиваются, приходит ясность.",
        "en": "Moon and Sun: illusions clear, clarity comes.",
    },
    ("hermit", "lovers"): {
        "ru": "Отшельник с Влюблёнными — пора выйти из уединения "
              "навстречу другому.",
        "en": "Hermit with Lovers — time to leave solitude for another.",
    },
    ("wheel", "justice"): {
        "ru": "Колесо Фортуны и Справедливость: судьба вмешается, "
              "но по заслугам.",
        "en": "Wheel and Justice: fate steps in, fairly.",
    },
    ("empress", "emperor"): {
        "ru": "Императрица и Император — гармония мужского и женского, "
              "прочный союз.",
        "en": "Empress and Emperor — balance of masculine and feminine.",
    },
    ("fool", "world"): {
        "ru": "Шут с Миром: смелое начало приведёт к полному успеху.",
        "en": "Fool with World: a bold start leads to full success.",
    },
    # Комбинации младших аркана
    ("swords_3", "cups_9"): {
        "ru": "Тройка Мечей и Девятка Кубков: боль сменяется радостью.",
        "en": "Three of Swords and Nine of Cups: pain turns to joy.",
    },
    ("pentacles_5", "sun"): {
        "ru": "Пятёрка Пентаклей с Солнцем: трудный период заканчивается.",
        "en": "Five of Pentacles with the Sun: the hard time ends.",
    },
    ("wands_ace", "pentacles_ace"): {
        "ru": "Два Туза — Жезлов и Пентаклей: вдохновение приносит доход.",
        "en": "Two Aces — Wands and Pentacles: inspiration brings income.",
    },
    ("cups_ace", "lovers"): {
        "ru": "Туз Кубков с Влюблёнными — новое глубокое чувство.",
        "en": "Ace of Cups with Lovers — a new deep feeling.",
    },
    ("swords_10", "star"): {
        "ru": "Десятка Мечей и Звезда: после дна приходит надежда.",
        "en": "Ten of Swords and Star: hope comes after rock bottom.",
    },
    ("wands_10", "temperance"): {
        "ru": "Десятка Жезлов с Умеренностью — пора снизить нагрузку.",
        "en": "Ten of Wands with Temperance — reduce the load.",
    },
}


def find_combos(keys, lang):
    out = []
    s = set(keys)
    for pair, txt in COMBOS.items():
        if pair[0] in s and pair[1] in s:
            out.append(txt.get(lang, txt["ru"]))
    return out


# ============================================================
# 5. РАСКЛАДЫ
# ============================================================
SPREADS = [
    {"id": "daily",
     "name": {"ru": "Карта дня", "en": "Card of the Day"},
     "hint": {"ru": "Энергия и совет на текущий день",
              "en": "Energy and advice for today"},
     "positions": ["today"]},

    {"id": "yesno",
     "name": {"ru": "Да или Нет", "en": "Yes or No"},
     "hint": {"ru": "Быстрый ответ на конкретный вопрос",
              "en": "A quick answer to a specific question"},
     "positions": ["answer"]},

    {"id": "ppf",
     "name": {"ru": "Прошлое · Настоящее · Будущее",
              "en": "Past · Present · Future"},
     "hint": {"ru": "Классический расклад на развитие ситуации",
              "en": "Classic spread on situation development"},
     "positions": ["past", "present", "future"]},

    {"id": "love",
     "name": {"ru": "Любовь", "en": "Love"},
     "hint": {"ru": "Чувства обоих и перспектива союза",
              "en": "Feelings of both and outlook of the union"},
     "positions": ["you", "partner", "relation"]},

    {"id": "career",
     "name": {"ru": "Карьера", "en": "Career"},
     "hint": {"ru": "Что происходит и как продвинуться",
              "en": "What's happening and how to advance"},
     "positions": ["situation", "obstacle", "advice"]},

    {"id": "money",
     "name": {"ru": "Деньги", "en": "Money"},
     "hint": {"ru": "Финансовая ситуация и потенциал",
              "en": "Financial situation and potential"},
     "positions": ["income", "expenses", "potential"]},

    {"id": "health",
     "name": {"ru": "Здоровье", "en": "Health"},
     "hint": {"ru": "Энергия тела, разума и духа",
              "en": "Energy of body, mind and spirit"},
     "positions": ["body", "mind", "spirit"]},

    {"id": "choice",
     "name": {"ru": "Выбор пути", "en": "Crossroads"},
     "hint": {"ru": "Помощь в принятии сложного решения",
              "en": "Help for a difficult decision"},
     "positions": ["opt_a", "opt_b", "result"]},

    {"id": "cross",
     "name": {"ru": "Кельтский крест", "en": "Celtic Cross"},
     "hint": {"ru": "Глубокий анализ ситуации",
              "en": "In-depth situation analysis"},
     "positions": ["core", "challenge", "roots", "near", "outcome"]},
]


# ============================================================
# 6. ВИДЖЕТ КАРТЫ
# ============================================================
class TarotCardWidget(QWidget):
    def __init__(self, w=200, h=340, sound_player=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(w, h)
        self.card_key = None
        self.is_reversed = False
        self.position_key = ""
        self._flip = 0.0
        self._show_face = False
        self._sound = sound_player

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(120, 80, 200, 150))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

        self._anim = QPropertyAnimation(self, b"flipProgress", self)
        self._anim.setDuration(480)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def get_flip(self) -> float:
        return self._flip

    def set_flip(self, v: float):
        self._flip = v
        self._show_face = v >= 0.5
        self.update()

    flipProgress = pyqtProperty(float, get_flip, set_flip)

    def reset(self):
        self._anim.stop()
        self.card_key = None
        self.is_reversed = False
        self.position_key = ""
        self._flip = 0.0
        self._show_face = False
        self.update()

    def stop_animation(self):
        self._anim.stop()

    def deal(self, card_key: str, position_key: str, reversed_: bool,
             play_sound: bool = True):
        self._anim.stop()
        self.card_key = card_key
        self.position_key = position_key
        self.is_reversed = reversed_
        self._flip = 0.0
        self._show_face = False
        self.update()

        if play_sound and self._sound is not None:
            self._sound.play("flip")

        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        scale = abs(math.cos(self._flip * math.pi))
        if scale < 0.02:
            p.end()
            return

        W, H = self.width(), self.height()
        p.translate(W / 2.0, 0.0)
        p.scale(scale, 1.0)
        p.translate(-W / 2.0, 0.0)

        rect = QRectF(3, 3, W - 6, H - 6)
        if self._show_face and self.card_key:
            self._paint_front(p, rect)
        else:
            self._paint_back(p, rect)
        p.end()

    def _paint_back(self, p, rect):
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(30, 20, 60))
        grad.setColorAt(0.5, QColor(48, 28, 88))
        grad.setColorAt(1.0, QColor(28, 18, 55))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(200, 168, 96), 2))
        p.drawRoundedRect(rect, 14, 14)

        radial = QRadialGradient(rect.center(), rect.width() * 0.6)
        radial.setColorAt(0, QColor(150, 110, 220, 90))
        radial.setColorAt(1, QColor(150, 110, 220, 0))
        p.setBrush(QBrush(radial))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 12, 12)

        p.save()
        p.setClipRect(rect.adjusted(6, 6, -6, -6))
        p.setPen(QPen(QColor(200, 168, 96, 40), 1))
        step = 14
        x0, y0 = int(rect.left()) - 200, int(rect.top()) - 200
        x1 = int(rect.right()) + 200
        y1 = int(rect.bottom()) + 200
        for i in range(x0, x1, step):
            p.drawLine(i, y0, i + 400, y0 + 400)
            p.drawLine(i, y1, i + 400, y1 - 400)
        p.restore()

        inner = rect.adjusted(10, 10, -10, -10)
        p.setPen(QPen(QColor(200, 168, 96, 200), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(inner, 10, 10)

        p.setPen(QColor(232, 214, 160))
        p.setFont(QFont("Arial", int(rect.width() * 0.26)))
        p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), "✦")

    def _paint_front(self, p, rect):
        h, w = rect.height(), rect.width()

        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(253, 249, 240))
        grad.setColorAt(0.5, QColor(248, 240, 222))
        grad.setColorAt(1.0, QColor(236, 222, 196))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(180, 140, 60), 2))
        p.drawRoundedRect(rect, 14, 14)

        radial = QRadialGradient(rect.center(), w * 0.75)
        radial.setColorAt(0, QColor(255, 240, 200, 110))
        radial.setColorAt(1, QColor(255, 240, 200, 0))
        p.setBrush(QBrush(radial))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 12, 12)

        inner = rect.adjusted(7, 7, -7, -7)
        p.setPen(QPen(QColor(200, 170, 100, 140), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(inner, 10, 10)

        p.setPen(QColor(140, 105, 50))
        p.setFont(QFont("Georgia", max(8, int(w * 0.045)), QFont.Weight.Bold))
        p.drawText(QRectF(rect.left(), rect.top() + h * 0.035, w, h * 0.06),
                   int(Qt.AlignmentFlag.AlignCenter),
                   f"— {pos_name(self.position_key).upper()} —")

        p.setPen(QPen(QColor(200, 170, 100, 150), 1))
        yd1 = rect.top() + h * 0.115
        p.drawLine(QPointF(rect.center().x() - w * 0.16, yd1),
                   QPointF(rect.center().x() + w * 0.16, yd1))

        sym_rect = QRectF(rect.left(), rect.top() + h * 0.13, w, h * 0.33)
        p.save()
        if self.is_reversed:
            sc = sym_rect.center()
            p.translate(sc); p.rotate(180); p.translate(-sc)
        p.setPen(QColor(40, 25, 10))
        p.setFont(make_emoji_font(max(22, int(w * 0.26))))
        c = CARD_BY_KEY[self.card_key]
        p.drawText(sym_rect, int(Qt.AlignmentFlag.AlignCenter), c[1])
        p.restore()

        name = card_info(self.card_key, LANG["current"], self.is_reversed)[0]
        name_rect = QRectF(rect.left() + 8, rect.top() + h * 0.50,
                           w - 16, h * 0.20)
        p.setPen(QColor(50, 35, 15))
        p.setFont(QFont("Georgia", max(9, int(w * 0.072)), QFont.Weight.Bold))
        p.drawText(name_rect,
                   int(Qt.AlignmentFlag.AlignCenter)
                   | int(Qt.TextFlag.TextWordWrap), name)

        p.setPen(QPen(QColor(200, 170, 100, 150), 1))
        yd2 = rect.top() + h * 0.735
        p.drawLine(QPointF(rect.center().x() - w * 0.17, yd2),
                   QPointF(rect.center().x() + w * 0.17, yd2))

        bh = max(20, h * 0.08)
        badge = QRectF(rect.left() + w * 0.11, rect.top() + h * 0.78,
                       w * 0.78, bh)
        if self.is_reversed:
            bcolor = QColor(175, 55, 65)
            btext = tr("badge_reversed")
        else:
            bcolor = QColor(60, 130, 80)
            btext = tr("badge_upright")
        p.setBrush(QBrush(bcolor))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(badge, bh / 2.6, bh / 2.6)
        p.setPen(QColor(255, 255, 255))
        p.setFont(QFont("Arial", max(8, int(w * 0.045)), QFont.Weight.Bold))
        p.drawText(badge, int(Qt.AlignmentFlag.AlignCenter), btext)


# ============================================================
# 7. ГЛАВНОЕ ОКНО
# ============================================================
class TarotApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("win_title"))
        self.resize(1120, 960)
        self.setMinimumSize(780, 640)

        self.current_spread = []
        self.card_widgets = []
        self._centered = False
        self._reveal_index = 0
        self._reveal_timer = None
        self.sound = SoundPlayer()
        self._last_question = ""

        self._build_ui()
        self._apply_spread(0)

        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, self.exit_fullscreen)
        QShortcut(QKeySequence("Ctrl+N"), self, self.make_spread)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._centered:
            cursor_pos = QCursor.pos()
            scr = QApplication.screenAt(cursor_pos)
            if scr is None:
                scr = QApplication.primaryScreen()
            avail = scr.availableGeometry()
            fg = self.frameGeometry()
            fg.moveCenter(avail.center())
            self.move(fg.topLeft())
            self._centered = True

    def closeEvent(self, event):
        self._stop_reveal_timer()
        for cw in self.card_widgets:
            if hasattr(cw, "stop_animation"):
                cw.stop_animation()
        super().closeEvent(event)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def exit_fullscreen(self):
        if self.isFullScreen() and not self.question.hasFocus():
            self.showNormal()

    def _stop_reveal_timer(self):
        if self._reveal_timer is not None:
            old = self._reveal_timer
            try:
                old.stop()
                old.timeout.disconnect()
            except (TypeError, RuntimeError):
                pass
            self._reveal_timer = None
            old.deleteLater()
        self._reveal_index = 0

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setObjectName("root")
        central.setStyleSheet("QWidget#root { background-color: #0d0819; }")

        root = QVBoxLayout(central)
        root.setContentsMargins(28, 18, 28, 18)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("header")
        header.setStyleSheet("""
            QFrame#header {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0  rgba(106, 79, 163, 0),
                    stop:0.5 rgba(140, 100, 220, 70),
                    stop:1  rgba(106, 79, 163, 0));
                border-radius: 12px;
            }
        """)
        hl = QVBoxLayout(header)
        hl.setContentsMargins(10, 10, 10, 10)
        hl.setSpacing(2)

        self.title_lbl = QLabel(tr("header"))
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setStyleSheet(
            "font-family: Georgia, serif; font-size: 25px; "
            "font-weight: bold; color: #e8d6a0; "
            "letter-spacing: 5px; background: transparent;")
        hl.addWidget(self.title_lbl)

        self.hint_lbl = QLabel("")
        self.hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_lbl.setStyleSheet(
            "color: #9a8ec0; font-size: 11px; "
            "letter-spacing: 1px; background: transparent;")
        hl.addWidget(self.hint_lbl)
        root.addWidget(header)

        ctrl = QFrame()
        ctrl.setStyleSheet("""
            QFrame {
                background-color: #16102a;
                border: 1px solid #2f2555;
                border-radius: 12px;
            }
        """)
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(14, 8, 14, 8)
        cl.setSpacing(10)

        self.spread_lbl = QLabel(tr("spread_label"))
        self.spread_lbl.setStyleSheet("color:#c8b8e0; font-family: Georgia, serif; "
                                      "font-size: 13px; border:none;")
        cl.addWidget(self.spread_lbl)

        self.spread_combo = QComboBox()
        self.spread_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.spread_combo.setStyleSheet("""
            QComboBox {
                background-color: #221a3d; color: #e8d6a0;
                border: 1px solid #4a3d70; border-radius: 8px;
                padding: 6px 12px; font-family: Georgia, serif;
                font-size: 13px; min-width: 240px;
            }
            QComboBox:hover { border-color: #d4af37; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #d4af37;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #221a3d; color: #e8d6a0;
                border: 1px solid #4a3d70;
                selection-background-color: #6a4fa3;
                padding: 4px; outline: none;
            }
        """)
        for sp in SPREADS:
            self.spread_combo.addItem(sp["name"][LANG["current"]], sp["id"])
        self.spread_combo.setCurrentIndex(0)
        self.spread_combo.currentIndexChanged.connect(self._on_spread_changed)
        cl.addWidget(self.spread_combo)

        cl.addStretch()

        self.btn_sound = QPushButton("🔊" if HAS_SOUND else "🔇")
        self.btn_sound.setFixedSize(40, 34)
        self.btn_sound.setToolTip(tr("sound_tooltip"))
        self.btn_sound.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sound.clicked.connect(self._toggle_sound)
        self.btn_sound.setEnabled(HAS_SOUND)
        cl.addWidget(self.btn_sound)

        self.lang_lbl = QLabel(tr("lang_label"))
        self.lang_lbl.setStyleSheet("color:#c8b8e0; font-family: Georgia, serif; "
                                    "font-size: 13px; border:none;")
        cl.addWidget(self.lang_lbl)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Русский", "ru")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_combo.setFixedWidth(120)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        cl.addWidget(self.lang_combo)

        self.btn_fs = QPushButton("⛶")
        self.btn_fs.setFixedSize(40, 34)
        self.btn_fs.setToolTip(tr("fs_tooltip"))
        self.btn_fs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fs.clicked.connect(self.toggle_fullscreen)
        cl.addWidget(self.btn_fs)

        self._style_ctrl_buttons(ctrl)
        root.addWidget(ctrl)

        self.question = QLineEdit()
        self.question.setPlaceholderText(tr("question_placeholder"))
        self.question.setStyleSheet("""
            QLineEdit {
                background-color: #16102a; color: #e8dcc0;
                border: 1px solid #2f2555; border-radius: 10px;
                padding: 10px 14px; font-family: Georgia, serif;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #d4af37; }
        """)
        root.addWidget(self.question)

        cards_wrap = QWidget()
        cards_wrap.setStyleSheet("background: transparent;")
        self.cards_row = QHBoxLayout(cards_wrap)
        self.cards_row.setContentsMargins(0, 6, 0, 6)
        self.cards_row.setSpacing(20)
        self.cards_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(cards_wrap)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn = QPushButton(tr("btn_spread"))
        self.btn.setFixedSize(320, 52)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6a4fa3, stop:1 #8b5ecb);
                color: #fff8e0; font-family: Georgia, serif;
                font-size: 15px; font-weight: bold;
                letter-spacing: 3px; border: 1px solid #a07fd8;
                border-radius: 14px; padding: 10px 26px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7e5fbb, stop:1 #a06fd8);
                border: 1px solid #d4af37;
            }
            QPushButton:pressed { background: #5a3f90; }
            QPushButton:disabled {
                background: #241c3d; color: #6b6390;
                border: 1px solid #3a2e5c;
            }
        """)
        self.btn.clicked.connect(self.make_spread)
        btn_row.addWidget(self.btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self.prediction = QTextEdit()
        self.prediction.setReadOnly(True)
        self.prediction.setMinimumHeight(220)
        self.prediction.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.prediction.setStyleSheet("""
            QTextEdit {
                background-color: #16102a; color: #e8dcc0;
                border: 1px solid #4a3d70; border-radius: 12px;
                padding: 18px; font-family: Georgia, serif;
                font-size: 13px;
                selection-background-color: #6a4fa3;
            }
            QScrollBar:vertical {
                background: #1a1530; width: 10px;
                border-radius: 5px; margin: 4px;
            }
            QScrollBar::handle:vertical {
                background: #6a4fa3; border-radius: 5px; min-height: 24px;
            }
            QScrollBar::handle:vertical:hover { background: #8b5ecb; }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical { background: transparent; }
        """)
        self.prediction.setHtml(self._placeholder_html())
        root.addWidget(self.prediction, 1)

    def _style_ctrl_buttons(self, parent):
        parent.setStyleSheet(parent.styleSheet() + """
            QPushButton {
                background-color: #221a3d; color: #d4af37;
                border: 1px solid #4a3d70; border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover { border-color: #d4af37; background-color:#2f2555; }
            QPushButton:disabled { color: #4a3d70; }
            QComboBox {
                background-color: #221a3d; color: #e8d6a0;
                border: 1px solid #4a3d70; border-radius: 8px;
                padding: 6px 10px; font-family: Georgia, serif;
                font-size: 13px;
            }
            QComboBox:hover { border-color: #d4af37; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #d4af37;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #221a3d; color: #e8d6a0;
                border: 1px solid #4a3d70;
                selection-background-color: #6a4fa3;
            }
        """)

    def _toggle_sound(self):
        self.sound.enabled = not self.sound.enabled
        self.btn_sound.setText("🔊" if self.sound.enabled else "🔇")
        if not self.sound.enabled:
            self.sound.stop_all()

    def _on_lang_changed(self):
        self._stop_reveal_timer()
        set_lang(self.lang_combo.currentData())
        self._refresh_static_texts()
        self._refresh_spread_combo()
        for cw in self.card_widgets:
            cw.reset()
        self.btn.setEnabled(True)
        self.btn.setText(tr("btn_spread"))
        self.prediction.setHtml(self._placeholder_html())

    def _refresh_static_texts(self):
        self.setWindowTitle(tr("win_title"))
        self.title_lbl.setText(tr("header"))
        self.spread_lbl.setText(tr("spread_label"))
        self.lang_lbl.setText(tr("lang_label"))
        self.question.setPlaceholderText(tr("question_placeholder"))
        self.btn.setText(tr("btn_spread"))
        self.btn_fs.setToolTip(tr("fs_tooltip"))
        self.btn_sound.setToolTip(tr("sound_tooltip"))
        self._refresh_hint()

    def _refresh_spread_combo(self):
        idx = self.spread_combo.currentIndex()
        if idx < 0:
            idx = 0
        self.spread_combo.blockSignals(True)
        self.spread_combo.clear()
        for sp in SPREADS:
            self.spread_combo.addItem(sp["name"][LANG["current"]], sp["id"])
        self.spread_combo.setCurrentIndex(idx)
        self.spread_combo.blockSignals(False)

    def _refresh_hint(self, index=None):
        if index is None:
            index = self.spread_combo.currentIndex()
        if index < 0 or index >= len(SPREADS):
            index = 0
        sp = SPREADS[index]
        self.hint_lbl.setText(sp["hint"][LANG["current"]].upper())

    def _on_spread_changed(self, index):
        if index < 0:
            return
        self._apply_spread(index)

    def _apply_spread(self, index):
        if index < 0 or index >= len(SPREADS):
            index = 0
        sp = SPREADS[index]
        self._refresh_hint(index)
        self._rebuild_cards(sp["positions"])
        self.btn.setEnabled(True)
        self.btn.setText(tr("btn_spread"))
        self.prediction.setHtml(self._placeholder_html())

    def _rebuild_cards(self, positions):
        self._stop_reveal_timer()
        while self.cards_row.count():
            item = self.cards_row.takeAt(0)
            w = item.widget()
            if w is not None:
                if hasattr(w, "stop_animation"):
                    w.stop_animation()
                w.hide()
                w.deleteLater()
        self.card_widgets = []

        n = len(positions)
        if n == 1:
            cw, ch, sp = 260, 440, 20
        elif n <= 3:
            cw, ch, sp = 200, 340, 20
        elif n <= 5:
            cw, ch, sp = 130, 220, 10
        else:
            cw, ch, sp = 110, 190, 8

        self.cards_row.setSpacing(sp)

        for _ in positions:
            card = TarotCardWidget(cw, ch, self.sound)
            self.card_widgets.append(card)
            self.cards_row.addWidget(card)

    def make_spread(self):
        if not self.btn.isEnabled():
            return
        idx = self.spread_combo.currentIndex()
        if idx < 0:
            idx = 0
        sp = SPREADS[idx]
        positions = sp["positions"]

        self._last_question = self.question.text().strip()

        self.btn.setEnabled(False)
        self.btn.setText(tr("btn_revealing"))

        for cw in self.card_widgets:
            cw.reset()
        self.prediction.setHtml(
            f'<div style="color:#9a8ec0; font-family:Georgia,serif; '
            f'text-align:center; padding-top:40px; font-size:14px;">'
            f'{tr("opening")}</div>')

        keys = random.sample(list(CARD_BY_KEY.keys()), len(positions))
        self.current_spread = []
        for key, pos in zip(keys, positions):
            rev = random.random() < 0.30
            self.current_spread.append((key, rev, pos))

        self._stop_reveal_timer()
        self._reveal_index = 0
        self._reveal_timer = QTimer(self)
        self._reveal_timer.timeout.connect(self._reveal_next)
        self._reveal_timer.start(500)

    def _reveal_next(self):
        if not self.current_spread:
            self._stop_reveal_timer()
            self.btn.setEnabled(True)
            self.btn.setText(tr("btn_spread"))
            return

        if self._reveal_index >= len(self.current_spread):
            self._stop_reveal_timer()
            self.prediction.setHtml(self._generate_prediction())
            if self.sound.enabled:
                self.sound.play("final")
            self.btn.setEnabled(True)
            self.btn.setText(tr("btn_again"))
            return

        if self._reveal_index >= len(self.card_widgets):
            self._stop_reveal_timer()
            self.btn.setEnabled(True)
            self.btn.setText(tr("btn_spread"))
            self.prediction.setHtml(self._placeholder_html())
            return

        key, rev, pos = self.current_spread[self._reveal_index]
        self.card_widgets[self._reveal_index].deal(key, pos, rev,
                                                   play_sound=True)
        self._reveal_index += 1

    # ============================================================
    # HTML-утилиты
    # ============================================================
    @staticmethod
    def _placeholder_html():
        return (f'<div style="color:#9a8ec0; font-family:Georgia,serif; '
                f'text-align:center; padding: 44px 20px; font-size: 14px; '
                f'line-height:1.7;">{tr("placeholder")}</div>')

    @staticmethod
    def _html_start():
        return ('<div style="font-family:Georgia,serif; color:#e8dcc0; '
                'font-size:13px; line-height:1.75;">')

    @staticmethod
    def _h_title(text):
        return (f'<div style="color:#d4af37; font-size:15px; '
                f'font-weight:bold; text-align:center; '
                f'letter-spacing:3px; margin: 4px 0 10px 0;">{text}</div>'
                f'<hr style="border:none; border-top:1px solid #4a3d70; '
                f'margin: 0 0 14px 0;">')

    @staticmethod
    def _h_section(text):
        return (f'<hr style="border:none; border-top:1px solid #4a3d70; '
                f'margin: 16px 0 10px 0;">'
                f'<div style="color:#d4af37; font-size:14px; '
                f'font-weight:bold; letter-spacing:2px; '
                f'margin: 0 0 8px 0;">{text}</div>')

    @staticmethod
    def _h_p(text, color="#e8dcc0"):
        return (f'<p style="color:{color}; margin: 0 0 10px 0; '
                f'text-align:justify;">{text}</p>')

    @staticmethod
    def _card_line(pos_k, key, rev):
        lang = LANG["current"]
        name = card_info(key, lang, rev)[0]
        orient = tr("orient_reversed") if rev else tr("orient_upright")
        ocol = "#e08080" if rev else "#80d090"
        return (f'<div style="margin: 0 0 8px 0;">'
                f'<span style="color:#d4af37; font-weight:bold;">'
                f'{pos_name(pos_k)}</span> — '
                f'<span style="color:#fff2c8; font-weight:bold;">'
                f'{name}</span> '
                f'<span style="color:{ocol}; font-size:11px; '
                f'font-style:italic;">({orient})</span></div>')

    @staticmethod
    def _combos_block(cards):
        keys = [k for k, _, _ in cards]
        combos = find_combos(keys, LANG["current"])
        if not combos:
            return ""
        H = [TarotApp._h_section(tr("sec_combos"))]
        for c in combos:
            H.append(f'<div style="margin: 0 0 6px 0;">'
                     f'<span style="color:#d4af37;">◆</span> {c}</div>')
        return "".join(H)

    @staticmethod
    def _advice_block(cards):
        H = [TarotApp._h_section(tr("sec_advice"))]
        for key, rev, pos in cards:
            advice = card_info(key, LANG["current"], rev)[2]
            H.append(f'<div style="margin:0 0 8px 0;">'
                     f'<span style="color:#d4af37;">●</span> '
                     f'<span style="color:#c8b8e0; font-weight:bold;">'
                     f'{pos_name(pos)}:</span> {advice}</div>')
        return "".join(H)

    @staticmethod
    def _footer_block():
        return (f'<hr style="border:none; border-top:1px solid #4a3d70; '
                f'margin: 14px 0 10px 0;">'
                f'<div style="color:#8a7fbf; font-size:11px; '
                f'text-align:center; font-style:italic; '
                f'line-height:1.6;">{tr("footer")}</div></div>')

    # ============================================================
    # ГЕНЕРАЦИЯ ПРЕДСКАЗАНИЯ
    # ============================================================
    def _generate_prediction(self):
        idx = self.spread_combo.currentIndex()
        if idx < 0:
            idx = 0
        sid = SPREADS[idx]["id"]
        cards = self.current_spread
        lang = LANG["current"]

        head = ""
        if self._last_question:
            safe_q = _html.escape(self._last_question)
            head = (f'<div style="color:#9a8ec0; font-style:italic; '
                    f'margin-bottom:10px;">{tr("your_question")}: '
                    f'«{safe_q}»</div>')

        if sid == "daily":
            body = self._pred_daily(cards, lang)
        elif sid == "yesno":
            body = self._pred_yesno(cards, lang)
        elif sid == "ppf":
            body = self._pred_ppf(cards, lang)
        elif sid == "love":
            body = self._pred_love(cards, lang)
        elif sid == "career":
            body = self._pred_three(cards, lang, "career")
        elif sid == "money":
            body = self._pred_three(cards, lang, "money")
        elif sid == "health":
            body = self._pred_three(cards, lang, "health")
        elif sid == "choice":
            body = self._pred_choice(cards, lang)
        elif sid == "cross":
            body = self._pred_cross(cards, lang)
        else:
            body = self._pred_generic(cards, lang)

        return self._html_start() + head + body + self._footer_block()

    def _pred_daily(self, cards, lang):
        key, rev, pos = cards[0]
        name, meaning, advice = card_info(key, lang, rev)
        H = [self._h_title(tr("sec_advice_day"))]
        H.append(self._card_line(pos, key, rev))

        if rev:
            intro = tr("day_intro_rev", name=f"<b>{name}</b>",
                       meaning=f"<b>{meaning}</b>")
            mood = tr("day_mood_rev")
            mc = "#e0a0a0"
        else:
            intro = tr("day_intro_up", name=f"<b>{name}</b>",
                       meaning=f"<b>{meaning}</b>")
            mood = tr("day_mood_up")
            mc = "#a8e0a8"

        H.append(self._h_p(intro))
        H.append(f'<div style="color:{mc}; text-align:center; '
                 f'font-style:italic; margin: 8px 0 10px 0;">{mood}</div>')
        H.append(self._h_section(tr("sec_advice")))
        H.append(self._h_p(advice, "#d4c8a0"))
        H.append(self._combos_block(cards))
        return "".join(H)

    def _pred_yesno(self, cards, lang):
        key, rev, pos = cards[0]
        name, meaning, advice = card_info(key, lang, rev)
        base = CARD_BY_KEY[key][2]
        val = -base if rev else base

        if val > 0:
            ans, ac = tr("answer_yes"), "#80d090"
            verdict = tr("q_yesno")
            conf = tr("conf_high")
        elif val < 0:
            ans, ac = tr("answer_no"), "#e08080"
            verdict = tr("q_no")
            conf = tr("conf_high")
        else:
            ans, ac = tr("answer_maybe"), "#e8c060"
            verdict = tr("q_maybe")
            conf = tr("conf_mid")

        H = [self._h_title(tr("sec_answer"))]
        H.append(f'<div style="text-align:center; font-size:44px; '
                 f'font-weight:bold; color:{ac}; letter-spacing:6px; '
                 f'margin: 0 0 4px 0;">{ans}</div>')
        H.append(f'<div style="text-align:center; color:#9a8ec0; '
                 f'font-size:11px; margin-bottom:14px;">{conf}</div>')
        H.append(self._h_p(verdict))
        H.append(self._card_line(pos, key, rev))
        if lang == "ru":
            H.append(self._h_p(f"Карта <b>{name}</b> раскрывает суть "
                               f"вопроса: <b>{meaning}</b>."))
        else:
            H.append(self._h_p(f"The card <b>{name}</b> reveals the "
                               f"essence: <b>{meaning}</b>."))
        H.append(self._h_section(tr("sec_advice")))
        H.append(self._h_p(advice, "#d4c8a0"))
        H.append(self._combos_block(cards))
        return "".join(H)

    def _pred_ppf(self, cards, lang):
        (kp, rp, _), (kn, rn, _), (kf, rf, _) = cards
        n_p = card_info(kp, lang, rp)[0]
        n_n = card_info(kn, lang, rn)[0]
        n_f = card_info(kf, lang, rf)[0]
        m_p = card_info(kp, lang, rp)[1]
        m_n = card_info(kn, lang, rn)[1]
        m_f = card_info(kf, lang, rf)[1]

        H = [self._h_title(tr("sec_tolkovanie"))]
        for k, r, p in cards:
            H.append(self._card_line(p, k, r))

        H.append(self._h_section(tr("sec_story")))
        H.append(self._h_p(tr("past_rev" if rp else "past_up",
                              name=f"<b>{n_p}</b>",
                              meaning=f"<b>{m_p}</b>")))
        H.append(self._h_p(tr("pres_rev" if rn else "pres_up",
                              name=f"<b>{n_n}</b>",
                              meaning=f"<b>{m_n}</b>")))
        H.append(self._h_p(tr("fut_rev" if rf else "fut_up",
                              name=f"<b>{n_f}</b>",
                              meaning=f"<b>{m_f}</b>")))

        up = sum(1 for _, r, _ in cards if not r)
        if up == 3:
            syn = tr("syn_3up")
        elif up == 0:
            syn = tr("syn_3rev")
        elif up == 2:
            syn = tr("syn_2up")
        else:
            syn = tr("syn_2rev")
        H.append(self._h_section(tr("sec_synthesis")))
        H.append(self._h_p(syn))

        H.append(self._advice_block(cards))
        H.append(self._combos_block(cards))
        return "".join(H)

    def _pred_love(self, cards, lang):
        (ky, ry, py), (kp, rp, pp), (kr, rr, pr) = cards
        H = [self._h_title(tr("sec_feelings"))]
        for k, r, p in cards:
            H.append(self._card_line(p, k, r))

        my = card_info(ky, lang, ry)[1]
        mp = card_info(kp, lang, rp)[1]
        mr = card_info(kr, lang, rr)[1]
        ny = card_info(ky, lang, ry)[0]
        np_ = card_info(kp, lang, rp)[0]
        nr = card_info(kr, lang, rr)[0]

        H.append(self._h_section(tr("sec_analysis")))
        if lang == "ru":
            H.append(self._h_p(
                f"<b>{pos_name(py)} ({ny}).</b> Сейчас вы находитесь "
                f"в состоянии <b>{my}</b>. "
                f"{'Ваша энергия открыта и активна.' if not ry else 'Энергия заблокирована: возможно, вы закрыты.'}"))
            H.append(self._h_p(
                f"<b>{pos_name(pp)} ({np_}).</b> Партнёр переживает "
                f"<b>{mp}</b>. "
                f"{'Он/она открыт(а) для диалога.' if not rp else 'Есть внутренние сомнения.'}"))
            H.append(self._h_p(
                f"<b>{pos_name(pr)} ({nr}).</b> Союз находится в фазе "
                f"<b>{mr}</b>. "
                f"{'Благоприятное время для укрепления связи.' if not rr else 'Есть напряжение, требующее внимания.'}"))
        else:
            H.append(self._h_p(
                f"<b>{pos_name(py)} ({ny}).</b> You are in a state of "
                f"<b>{my}</b>. "
                f"{'Your energy is open and active.' if not ry else 'Energy is blocked.'}"))
            H.append(self._h_p(
                f"<b>{pos_name(pp)} ({np_}).</b> The partner experiences "
                f"<b>{mp}</b>. "
                f"{'They are open to dialogue.' if not rp else 'There are inner doubts.'}"))
            H.append(self._h_p(
                f"<b>{pos_name(pr)} ({nr}).</b> The relationship is in "
                f"a phase of <b>{mr}</b>. "
                f"{'A favourable time to strengthen the bond.' if not rr else 'There is tension to address.'}"))

        up = sum(1 for _, r, _ in cards if not r)
        H.append(self._h_section(tr("sec_compat")))
        if up == 3:
            s = ("Три прямые карты — знак редкостной гармонии. "
                 "Оба настроены друг на друга." if lang == "ru"
                 else "Three upright cards — rare harmony. Both are "
                      "tuned to each other.")
        elif up == 0:
            s = ("Все три карты перевёрнуты — отношения проходят "
                 "кризис. Обе стороны закрыты." if lang == "ru"
                 else "All three reversed — the relationship is in "
                      "crisis. Both sides are closed.")
        elif up == 2:
            s = ("Двое открыты, одна карта перевёрнута — перекос. "
                 "Начните с того, кто закрыт." if lang == "ru"
                 else "Two upright, one reversed — imbalance. Start "
                      "with the closed one.")
        else:
            s = ("Большинство карт перевёрнуты: сейчас проверка, а не "
                 "награда." if lang == "ru"
                 else "Most cards reversed: this is a test, not a reward.")
        H.append(self._h_p(s))
        H.append(self._advice_block(cards))
        H.append(self._combos_block(cards))
        return "".join(H)

    def _pred_three(self, cards, lang, ctx):
        titles = {
            "career": "sec_analysis",
            "money": "sec_money",
            "health": "sec_health",
        }
        title_key = titles.get(ctx, "sec_analysis")

        H = [self._h_title(tr(title_key))]
        for k, r, p in cards:
            H.append(self._card_line(p, k, r))

        H.append(self._h_section(tr("sec_analysis")))
        for key, rev, pos in cards:
            n, m, _ = card_info(key, lang, rev)
            if lang == "ru":
                H.append(self._h_p(
                    f"<b>{pos_name(pos)} ({n}).</b> В этой позиции "
                    f"проявляется <b>{m}</b>."))
            else:
                H.append(self._h_p(
                    f"<b>{pos_name(pos)} ({n}).</b> This position "
                    f"reveals <b>{m}</b>."))

        up = sum(1 for _, r, _ in cards if not r)
        H.append(self._h_section(tr("sec_strategy")))
        if up == 3:
            st = ("Все карты прямые — ситуация крайне благоприятна. "
                  "Действуйте уверенно." if lang == "ru"
                  else "All upright — a highly favourable situation. "
                       "Act boldly.")
        elif up == 0:
            st = ("Все карты перевёрнуты — фаза застоя. Не форсируйте "
                  "события." if lang == "ru"
                  else "All reversed — stagnation. Don't force events.")
        elif up == 2:
            st = ("Ситуация рабочая, есть один проблемный аспект. "
                  "Сфокусируйтесь на нём." if lang == "ru"
                  else "Workable, but with one problematic aspect. "
                       "Focus there.")
        else:
            st = ("Не лучший момент для рискованных шагов. Сначала "
                  "наведите порядок." if lang == "ru"
                  else "Not the best time for risky moves. First, "
                       "clean up.")
        H.append(self._h_p(st))

        H.append(self._advice_block(cards))
        H.append(self._combos_block(cards))
        return "".join(H)

    def _pred_choice(self, cards, lang):
        (ka, ra, pa), (kb, rb, pb), (kr, rr, pr) = cards
        H = [self._h_title(tr("sec_analysis"))]
        for k, r, p in cards:
            H.append(self._card_line(p, k, r))

        ma = card_info(ka, lang, ra)
        mb = card_info(kb, lang, rb)
        mr = card_info(kr, lang, rr)

        H.append(self._h_section(tr("sec_analysis")))
        if lang == "ru":
            H.append(self._h_p(f"<b>{pos_name(pa)} ({ma[0]}).</b> Этот "
                               f"путь несёт <b>{ma[1]}</b>."))
            H.append(self._h_p(f"<b>{pos_name(pb)} ({mb[0]}).</b> Этот "
                               f"путь несёт <b>{mb[1]}</b>."))
            H.append(self._h_p(f"<b>{pos_name(pr)} ({mr[0]}).</b> "
                               f"Финальный вектор — <b>{mr[1]}</b>."))
        else:
            H.append(self._h_p(f"<b>{pos_name(pa)} ({ma[0]}).</b> This "
                               f"path brings <b>{ma[1]}</b>."))
            H.append(self._h_p(f"<b>{pos_name(pb)} ({mb[0]}).</b> This "
                               f"path brings <b>{mb[1]}</b>."))
            H.append(self._h_p(f"<b>{pos_name(pr)} ({mr[0]}).</b> Final "
                               f"vector — <b>{mr[1]}</b>."))

        sa = 1 if not ra else -1
        sb = 1 if not rb else -1
        sr = 1 if not rr else -1

        H.append(self._h_section(tr("sec_verdict")))
        if lang == "ru":
            if sa > sb and sr > 0:
                v = ("Карты склоняют к <b style='color:#a8e0a8;'>"
                     "Варианту A</b>. Путь гладкий, итог благоприятен.")
                c = "#a8e0a8"
            elif sb > sa and sr > 0:
                v = ("Карты склоняют к <b style='color:#a8e0a8;'>"
                     "Варианту B</b>. Путь гладкий, итог благоприятен.")
                c = "#a8e0a8"
            elif sa == sb and sr < 0:
                v = ("Ни один вариант не лучше. Карта итога перевёрнута "
                     "— не торопитесь.")
                c = "#e0a0a0"
            elif sa == sb:
                v = ("Оба варианта равны. Прислушайтесь к интуиции.")
                c = "#e8c060"
            else:
                better = "A" if sa > sb else "B"
                v = (f"Перевес у <b>Варианта {better}</b>, но карта "
                     f"итога перевёрнута — результат не гарантирован.")
                c = "#e8c060"
        else:
            if sa > sb and sr > 0:
                v = "Cards favour <b style='color:#a8e0a8;'>Option A</b>."
                c = "#a8e0a8"
            elif sb > sa and sr > 0:
                v = "Cards favour <b style='color:#a8e0a8;'>Option B</b>."
                c = "#a8e0a8"
            elif sa == sb and sr < 0:
                v = "Neither option is better. Don't rush."
                c = "#e0a0a0"
            elif sa == sb:
                v = "Both options are equal. Trust your intuition."
                c = "#e8c060"
            else:
                better = "A" if sa > sb else "B"
                v = (f"Option {better} has the edge, but the outcome "
                     f"is not guaranteed.")
                c = "#e8c060"
        H.append(f'<div style="color:{c}; text-align:justify; '
                 f'margin: 0 0 10px 0;">{v}</div>')

        H.append(self._advice_block(cards))
        H.append(self._combos_block(cards))
        return "".join(H)

    def _pred_cross(self, cards, lang):
        H = [self._h_title(tr("sec_tolkovanie"))]
        for k, r, p in cards:
            H.append(self._card_line(p, k, r))

        H.append(self._h_section(tr("sec_story")))
        for key, rev, pos in cards:
            n, m, _ = card_info(key, lang, rev)
            if lang == "ru":
                H.append(self._h_p(
                    f"<b>{pos_name(pos)} ({n}).</b> Энергия этой "
                    f"позиции — <b>{m}</b>."))
            else:
                H.append(self._h_p(
                    f"<b>{pos_name(pos)} ({n}).</b> Energy of this "
                    f"position — <b>{m}</b>."))

        up = sum(1 for _, r, _ in cards if not r)
        H.append(self._h_section(tr("sec_synthesis")))
        if up >= 4:
            bg = ("Расклад подчёркнуто светлый: почти все карты в "
                  "прямом положении. Вселенная благоволит вам."
                  if lang == "ru" else
                  "A distinctly bright spread: almost all cards "
                  "upright. The universe favours you.")
            c = "#a8e0a8"
        elif up <= 1:
            bg = ("Расклад омрачён: большинство карт перевёрнуты. "
                  "Сейчас вы в фазе спада."
                  if lang == "ru" else
                  "A darkened spread: most cards reversed. You are "
                  "in a downturn.")
            c = "#e0a0a0"
        else:
            bg = ("Баланс прямых и перевёрнутых карт: смешанная "
                  "картина, результат зависит от ваших действий."
                  if lang == "ru" else
                  "A mix of upright and reversed cards: outcome "
                  "depends on your choices.")
            c = "#e8c060"
        H.append(f'<div style="color:{c}; text-align:justify;">{bg}</div>')

        H.append(self._advice_block(cards))
        H.append(self._combos_block(cards))
        return "".join(H)

    def _pred_generic(self, cards, lang):
        H = [self._h_title(tr("sec_tolkovanie"))]
        for k, r, p in cards:
            H.append(self._card_line(p, k, r))
        H.append(self._advice_block(cards))
        H.append(self._combos_block(cards))
        return "".join(H)


# ============================================================
# ЗАПУСК
# ============================================================
def _excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    if sys.stderr is not None:
        try:
            sys.stderr.write(f"[CRASH]\n{tb}\n")
        except Exception:
            pass


def main():
    sys.excepthook = _excepthook
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TarotApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()