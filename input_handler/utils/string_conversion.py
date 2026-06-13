# function that converts underscore separated string to uppercase camel case
def underscore_to_camel_case(s: str) -> str:
    return "".join(word.capitalize() for word in s.split("_"))
