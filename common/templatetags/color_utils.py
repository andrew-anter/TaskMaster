from django import template

register = template.Library()

@register.filter
def contrast_color(hex_color):
    """
    Returns 'white' or 'black' depending on the brightness of the hex_color.
    """
    if not hex_color:
        return "black"
        
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return "black"
        
    try:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    except ValueError:
        return "black"
        
    # Brightness formula
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    
    return "white" if brightness < 128 else "black"
