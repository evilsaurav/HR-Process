import datetime

def format_reference_number(template: str, padding_width: int, number: int) -> str:
    num_str = str(number).zfill(padding_width)
    now = datetime.datetime.now()
    result = template.replace("{NUM}", num_str)
    result = result.replace("{YEAR}", str(now.year))
    result = result.replace("{MONTH}", str(now.month).zfill(2))
    return result
