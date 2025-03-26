import pdfplumber
import pandas as pd
import re
from validator import DynamicValidator

def suggest_regex_from_text(rule_text):
    rule_text = str(rule_text).lower().strip()

    if "rounded whole dollar amount" in rule_text:
        return r'^\d+$'  # Only digits, no symbols or decimal points

    if re.search(r'five[\s\-]?digit zip', rule_text) or "zip code" in rule_text:
        return r'^\d{5}$'  # US ZIP Code: Exactly 5 digits

    elif re.search(r'international.*postal code', rule_text):
        return r'^[A-Za-z0-9\- ]+$'  # International Postal Code: Alphanumeric + hyphens

    # ✅ Amount Validation
    elif "must be numeric" in rule_text or "amount" in rule_text:
        if "must be positive" in rule_text:
            return r'^(?!-)\d+(\.\d{1,2})?$'  # Positive numbers only, with up to 2 decimals
        elif "no decimals" in rule_text:
            return r'^\d+$'  # Whole numbers only (no decimals)
        elif "can be negative" in rule_text:
            return r'^-?\d+(\.\d{1,2})?$'  # Allows negative values (^-?\d+$)
        else:
            return r'^\d+(\.\d{1,2})?$'  # Default: Numeric, up to 2 decimals

    if re.search(r'\b5[\s\-]?digit', rule_text):
        return r'^\d{5}$'
    elif "2 letter country code" in rule_text:
        return r'^[A-Z]{2}$'
    elif re.search(r'zip\+4|postal code.*5.*4', rule_text):
        return r'^\d{5}-\d{4}$'

    elif re.search(r'date format.*yyyy[\-/.]?mm[\-/.]?dd', rule_text):
        return r'^\d{4}-\d{2}-\d{2}$'
    elif "alphanumeric" in rule_text:
        return r'^[A-Za-z0-9]+$'
    elif "must not contain" in rule_text:
        forbidden_chars = []
        if "comma" in rule_text: forbidden_chars.append(",")
        if "carriage return" in rule_text: forbidden_chars.append("\r")
        if "line feed" in rule_text: forbidden_chars.append("\n")
        # if "unprintable" in rule_text:forbidden_chars.append("\x00-\x1f")
        if "unprintable" in rule_text: forbidden_chars.extend(["\x00", "\x1f"])

        # char_class = "".join([re.escape(c) for c in forbidden_chars])
        forbidden_chars = [c for c in forbidden_chars if c.strip() and c not in [" ", "\x1f", "\x00"]]
        if not forbidden_chars:
            print("⚠️ No forbidden characters found, skipping regex creation.")
            return None  # No forbidden characters, no regex needed
        escaped_chars = [re.escape(c) for c in forbidden_chars]

        # ✅ Make sure '-' is at the end to avoid invalid character ranges
        if "-" in escaped_chars:
            escaped_chars.remove("-")
            escaped_chars.append(r"\-")  # Explicitly escape '-'

        char_class = "".join(escaped_chars)

        if not char_class.strip():
            print("⚠️ No valid characters for regex, skipping rule.")
            return None

        regex = rf'^[^{char_class}]*$'
        try:
            re.compile(regex)  # Validate regex
            return regex
        except re.error as e:
            print(f"⚠️ Invalid regex for rule '{rule_text}': {regex} — {e}")
            return None
        else:
            return None  # Skip if no forbidden characters

    return None


def generate_validation_config(rules_df):
    config_entries = []
    config_entries_df = pd.DataFrame(config_entries)

    for col in rules_df.columns:
        sample_val = rules_df[col].dropna().astype(str).iloc[0] if not rules_df[col].dropna().empty else ""

    if sample_val.isdigit():
        regex = r"\d+"
        description = "Numeric value"
    elif sample_val.isalpha():
        regex = r"[A-Za-z]+"
        description = "Alphabetic text"
    elif sample_val.isalnum():
        regex = r"[A-Za-z0-9]+"
        description = "Alphanumeric text"
    else:
        regex = r".*"
        description = "Free text or mixed characters"

    for _, rule in rules_df.iterrows():
        field = str(rule.get('Field Name', '')).strip()
        rule_text = str(rule.get('Allowable Values', '')).strip()
        suggested_regex = suggest_regex_from_text(rule_text)
        pattern = str(rule['Allowable Values']).strip()
        # if field == "Customer ID" and pattern.startswith("^[^,\\"):
        #  pattern = r"^[^,\r\n\x00-\x1f]*$"

        config_entries.append({
            "Field Name": field,
            "Original Rule": rule_text,
            "Suggested Regex": suggested_regex or "N/A"
        })

    return pd.DataFrame(config_entries)

def read_pdf(uploaded_pdf):
    # def extract_tables_from_pdf(pdf_file):
    # === Page Range (pages 167–213) ===
    start_page = 167 - 1  # pdfplumber uses zero-based indexing
    end_page = 218 - 1

    # === List to Store Extracted Rules ===
    rules_extracted = []
    with pdfplumber.open(uploaded_pdf) as pdf:
        for i in range(start_page, end_page + 1):
            page = pdf.pages[i]
            tables = page.extract_tables()
            for table in tables:
                for row in table[1:]:  # Skip header row
                    if len(row) == 5:
                        # Extract and clean data
                        field_name_raw = row[1]
                        description = str(row[3]).strip()
                        allowable_values = str(row[4]).strip()
                        field_name = field_name_raw.split('\n')[0].strip()

                        # Append extracted data
                        rules_extracted.append({
                            "Field Name": field_name,
                            "Description": description,
                            "Allowable Values": allowable_values
                        })
    rules_df = pd.DataFrame(rules_extracted)
    validation_df = generate_validation_config(rules_df)
    validator = DynamicValidator(validation_df)
    return validator