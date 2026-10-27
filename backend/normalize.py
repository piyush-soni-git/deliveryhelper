"""
normalize.py - Text normalization module for Indian address entity resolution.
Rules:
- Lowercase text
- Remove punctuation
- Expand abbreviations via a configurable dictionary
- Transliterate Devanagari to Roman
- Collapse whitespace
- NEVER alter numbers (digits and alphanumeric identifiers remain strictly intact)
"""

import re
import unicodedata
from typing import Dict, Optional

# Indic transliteration
try:
    from indic_transliteration import sanscript
    INDIC_AVAILABLE = True
except ImportError:
    INDIC_AVAILABLE = False

# Mapping of Devanagari numerals to standard Arabic numerals
DEVANAGARI_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

# Common Hindi address keywords mapped to standard English forms
HINDI_ADDRESS_LEXICON: Dict[str, str] = {
    'फ्लैट': 'flat',
    'अपार्टमेंट': 'apartments',
    'अपार्टमेंट्स': 'apartments',
    'अपार्टमेंट्स': 'apartments',
    'मार्ग': 'road',
    'रोड': 'road',
    'सड़क': 'road',
    'रास्ता': 'road',
    'गली': 'street',
    'लेन': 'lane',
    'नगर': 'nagar',
    'कॉलोनी': 'colony',
    'सेक्टर': 'sector',
    'सोसायटी': 'society',
    'भवन': 'building',
    'टावर': 'tower',
    'नियर': 'near',
    'पास': 'near',
    'सामने': 'opposite',
    'मंजिल': 'floor',
    'फ्लोर': 'floor',
    'कमरा': 'room',
    'मकान': 'house',
    'प्लॉट': 'plot',
    'नंबर': 'no',
    'नं': 'no',
    'जयपुर': 'jaipur',
    'दिल्ली': 'delhi',
    'नई दिल्ली': 'new delhi',
    'मुंबई': 'mumbai',
    'बेंगलुरु': 'bengaluru',
    'बैंगलोर': 'bengaluru',
    'पुणे': 'pune',
    'चेन्नई': 'chennai',
    'कोलकाता': 'kolkata',
    'हैदराबाद': 'hyderabad',
    'अहमदाबाद': 'ahmedabad',
    'कमल': 'lotus',
}

# Default abbreviation expansion dictionary
DEFAULT_ABBREVIATIONS: Dict[str, str] = {
    # Housing & Unit
    r'\b(apt|apts|appt|appts|apartment|appartment|appartments)\b': 'apartments',
    r'\b(flt|flts)\b': 'flat',
    r'\b(bldg|bldng|buildg)\b': 'building',
    r'\b(soc|socty|societies)\b': 'society',
    r'\b(twr|twrs)\b': 'tower',
    r'\b(hse|hno|h-no)\b': 'house',
    r'\b(plt|plotno|plot-no)\b': 'plot',
    r'\b(rm|rmno)\b': 'room',
    r'\b(flr|floor)\b': 'floor',
    r'\b(no|nos|num|number)\b': 'no',
    
    # Roads & Pathways
    r'\b(rd|rds|marg|raasta|sadak)\b': 'road',
    r'\b(st|str|street)\b': 'street',
    r'\b(ln|lane)\b': 'lane',
    r'\b(ave|av|avenue)\b': 'avenue',
    r'\b(blvd|bldv)\b': 'boulevard',
    r'\b(hwy|highway)\b': 'highway',
    r'\b(bypass|by-pass)\b': 'bypass',
    r'\b(chowk|chk)\b': 'chowk',
    r'\b(cros|cross)\b': 'cross',
    
    # Localities & Landmarks
    r'\b(nr|n\.r\.|near to)\b': 'near',
    r'\b(opp|oppo|opposite to)\b': 'opposite',
    r'\b(adj|adjacent)\b': 'adjacent',
    r'\b(beh|behind)\b': 'behind',
    r'\b(sec|sect)\b': 'sector',
    r'\b(ngr|nagr)\b': 'nagar',
    r'\b(col|clny)\b': 'colony',
    r'\b(ext|extn|extention)\b': 'extension',
    r'\b(lyt|lay-out)\b': 'layout',
    r'\b(ph|phs)\b': 'phase',
    r'\b(blk|blck)\b': 'block',
    r'\b(ind|indl|indust)\b': 'industrial',
    r'\b(stn|sttn)\b': 'station',
    r'\b(dist|distt)\b': 'district',
    
    # Common Cities
    r'\b(bangalore|bengaluru|blr)\b': 'bengaluru',
    r'\b(bombay)\b': 'mumbai',
    r'\b(calcutta)\b': 'kolkata',
    r'\b(madras)\b': 'chennai',
    r'\b(jpr)\b': 'jaipur',
    r'\b(hyd)\b': 'hyderabad',
    r'\b(dlh|dli|nd)\b': 'delhi',
}


def convert_devanagari_digits(text: str) -> str:
    """Converts Devanagari numerals (०-९) to standard digits (0-9)."""
    return "".join(DEVANAGARI_DIGITS.get(ch, ch) for ch in text)


def transliterate_devanagari(text: str) -> str:
    """
    Transliterates Devanagari text to Roman English, first applying
    known domain dictionary mappings (e.g. मार्ग -> road, फ्लैट -> flat).
    """
    if not text:
        return ""
    
    # 1. Convert Devanagari numerals
    text = convert_devanagari_digits(text)
    
    # 2. Check for Devanagari characters
    has_devanagari = bool(re.search(r'[\u0900-\u097F]', text))
    if not has_devanagari:
        return text
    
    # 3. Apply domain dictionary replacements
    for dev_word, eng_replacement in HINDI_ADDRESS_LEXICON.items():
        text = text.replace(dev_word, eng_replacement)
    
    # 4. Transliterate any remaining Devanagari characters
    if INDIC_AVAILABLE:
        dev_tokens = re.findall(r'[\u0900-\u097F]+', text)
        for token in dev_tokens:
            try:
                # Use ITRANS scheme, lowercased
                roman = sanscript.transliterate(token, sanscript.DEVANAGARI, sanscript.ITRANS)
                roman = roman.lower()
                # Clean up typical ITRANS diacritics
                roman = re.sub(r'[\^~]', '', roman)
                text = text.replace(token, roman)
            except Exception:
                # Fallback: remove non-ascii if transliteration fails
                text = text.replace(token, '')
    else:
        # Fallback if indic_transliteration not available
        text = "".join(
            c for c in unicodedata.normalize('NFKD', text)
            if not unicodedata.combining(c)
        )
        
    return text


def expand_abbreviations(text: str, custom_dict: Optional[Dict[str, str]] = None) -> str:
    """
    Expands abbreviations in text using default and optional custom dictionary.
    Guarantees that numbers are never modified.
    """
    patterns = DEFAULT_ABBREVIATIONS.copy()
    if custom_dict:
        for k, v in custom_dict.items():
            pattern = rf'\b{re.escape(k)}\b'
            patterns[pattern] = v
            
    for pattern, replacement in patterns.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
    return text


def clean_punctuation(text: str) -> str:
    """
    Removes extraneous punctuation while strictly preserving:
    - Digits and numbers (0-9)
    - Flat/unit separators like hyphens or slashes between alphanumerics (e.g. A-101, 101/A, 12-B)
    """
    # Normalize common symbols: '#' to 'no ', '@' to 'at'
    text = re.sub(r'#', ' no ', text)
    
    # Preserve flat number patterns like A-101 or 101/2 by temporarily marking them,
    # or selectively replacing punctuation:
    # Replace all punctuation characters except hyphen/slash connecting alphanumeric tokens
    # Replace commas, semicolons, colons, brackets, quotes, dots with space
    text = re.sub(r'[,;:.\'"!()\[\]{}_+*&^%$@~`|?<>\\=]', ' ', text)
    
    # Replace hyphens and slashes that are NOT surrounded by alphanumeric characters
    # e.g., " - " or " / " -> " "
    text = re.sub(r'(?<![A-Za-z0-9])[-/]|[-/](?![A-Za-z0-9])', ' ', text)
    
    return text


def normalize_address(text: str, custom_abbreviations: Optional[Dict[str, str]] = None) -> str:
    """
    Full normalization pipeline for an Indian address:
    1. Transliterate Devanagari to Roman (Hindi lexicon + ITRANS)
    2. Convert Devanagari numerals to standard digits (NEVER alter numbers)
    3. Lowercase text
    4. Remove unnecessary punctuation while retaining alphanumeric identity
    5. Expand abbreviations via dictionary
    6. Collapse whitespace
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Step 1 & 2: Devanagari transliteration and numeral normalization
    norm = transliterate_devanagari(text)
    
    # Step 3: Lowercase
    norm = norm.lower()
    
    # Step 4: Remove punctuation
    norm = clean_punctuation(norm)
    
    # Step 5: Expand abbreviations
    norm = expand_abbreviations(norm, custom_dict=custom_abbreviations)
    
    # Step 6: Collapse whitespace
    norm = re.sub(r'\s+', ' ', norm).strip()
    
    return norm
