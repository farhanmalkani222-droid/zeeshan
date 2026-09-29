"""First-contact onboarding: 4 short messages that mirror Ahmed bhai's usual pitch."""
import re
_SALAM = re.compile(r"\bassalam|salaam|salam[\W_]?ale?ku?m|salam\b", re.I)
_WALAIKUM = re.compile(r"\b(wa[\W_]?alai?kum|walaikum|walekum|walikum)", re.I)
_ONBOARD = re.compile(
    r"^\s*("
    r"hi+|hello+|hey+|namaste|"
    r"salaam|salam|assalam[\w\s\-o]*|walaikum[\w\s]*assalam|walaikum|walekum|"
    r"price|rate|kimat|keemat|kitne|kitna|mrp|cost|inquiry|enquiry|info|"
    r"details?|moq|minimum order|order|buy|lena|chahiye|available|stock"
    r")\s*[\?\.! ]*\s*$",
    re.I)

def opener(text):
    if _WALAIKUM.search(text): return "Assalam-o-alaikum!"
    if _SALAM.search(text):    return "Walaikum-assalam!"
    return "Assalam-o-alaikum!"

def should_onboard(text, prior_user_count):
    """Fire only on a customer's first substantive message (short, generic)."""
    if prior_user_count >= 1:
        return False
    return bool(_ONBOARD.match(text))

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
