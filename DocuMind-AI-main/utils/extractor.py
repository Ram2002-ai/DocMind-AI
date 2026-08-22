import re


def extract_information(text):

    info = {}

    # Email
    email = re.findall(
        r'[\w\.-]+@[\w\.-]+\.\w+',
        text
    )

    # Phone
    phone = re.findall(
        r'(\+?\d[\d\s-]{8,15}\d)',
        text
    )

    # Dates
    dates = re.findall(
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        text
    )

    info["Emails"] = email
    info["Phone Numbers"] = phone
    info["Dates"] = dates

    return info