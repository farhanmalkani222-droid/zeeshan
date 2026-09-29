"""First-contact onboarding: 4 short messages that mirror Ahmed bhai's usual pitch."""
import re
_SALAM = re.compile(r"\bassalam|salaam|salam[\W_]?ale?ku?m|salam\b", re.I)
_WALAIKUM = re.compile(r"\b(wa[\W_]?alai?kum|walaikum|walekum|walikum)", re.I)
_GREET = re.compile(r"^\s*(hi+|hello+|hey+|namaste|salaam|salam|assalam[\w\s\-o]*|walaikum[\w\s]*assalam|walaikum|walekum)"
                    r"\s*[\?\.! ]*\s*$", re.I)
_INTRO = re.compile(r"^\s*(details?|info|information|inquiry|enquiry|moq|minimum order|tap ke baare mein|nal ke baare mein)"
                    r"\s*[\?\.! ]*\s*$", re.I)

def opener(text):
    if _WALAIKUM.search(text): return "Assalam-o-alaikum!"
    if _SALAM.search(text):    return "Walaikum-assalam!"
    return "Assalam-o-alaikum!"

def mode(text, prior_user_count):
    """First contact only. 'greet' = bare salam/hi, 'intro' = customer asked for general details, else None."""
    if prior_user_count >= 1:
        return None
    if _GREET.match(text): return "greet"
    if _INTRO.match(text): return "intro"
    return None

def greeting(cfg, text):
    return [f"{opener(text)} {cfg['shop_name']} mein aapka swagat hai. Nal ke baare mein aapko kya jaanna hai?"]

def messages(cfg, text):
    o = opener(text)
    m1 = (f"{o} {cfg['shop_name']} mein aapka swagat hai. "
          f"Ek nal ki keemat ₹{cfg['price']} hai. Courier ke zariye All India delivery ho jaati hai, "
          f"jahan chahiye wahan.")
    m2 = (f"Hamara head office {cfg['head_office']} mein hai, factory {cfg['factory']} mein hai. "
          f"Maal courier ke zariye aap tak aa jaayega.")
    m3 = f"Nal pe {cfg['warranty']}"
    m4 = (f"Nal ABS material ka bana hai — saade plastic se 10 guna zyada mazboot, aur button aluminium ka hai, "
          f"toh tootne ki koi shikayat nahi. {cfg['price_compare']}")
    return [m1, m2, m3, m4]
