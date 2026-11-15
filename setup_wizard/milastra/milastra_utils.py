import os


def parse_milastra_part_name(name: str):
    """Extract canonical part name from a Milastra Wonderland Beyd_Avatar_* asset name.

    Examples:
        'Beyd_Avatar_Girl_BaseBody_Common_01_Mat.001' -> 'Body'
        'Beyd_Avatar_Girl_Top_S0053_01_Mat' -> 'Top'
        'Beyd_Avatar_Girl_Hair_P0126_01_Tex_Diffuse.png' -> 'Hair'
    """
    if not name or not name.startswith("Beyd_Avatar_"):
        return None
    stem = os.path.splitext(name)[0]
    parts = stem.split("_")
    if len(parts) < 4:
        return None
    part = parts[3]
    if part == "BaseBody":
        return "Body"
    return part
