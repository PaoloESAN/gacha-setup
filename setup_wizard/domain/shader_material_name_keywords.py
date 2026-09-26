class ShaderMaterialNameKeywords:
    BODY = 'Body'

    BODY_DIFFUSE = 'Body_Diffuse'
    BODY1_DIFFUSE = 'Body1_Diffuse'
    BODY2_DIFFUSE = 'Body2_Diffuse'

    BODY_LIGHTMAP = 'Body_Lightmap'
    BODY1_LIGHTMAP = 'Body1_Lightmap'
    BODY2_LIGHTMAP = 'Body2_Lightmap'

    BODY_SHADOW_RAMP = 'Body_Shadow_Ramp'
    BODY01_SHADOW_RAMP = 'Body01_Shadow_Ramp'
    BODY1_SHADOW_RAMP = 'Body1_Shadow_Ramp'
    BODY02_SHADOW_RAMP = 'Body02_Shadow_Ramp'
    BODY2_SHADOW_RAMP = 'Body2_Shadow_Ramp'

    HAIR = 'Hair'
    NORMAL_MAP = 'Normal'  # Normal Map
    SKILLOBJ = 'SkillObj'
    # NOTE: must stay specific to Night Soul / NYX paint masks.
    # ['Tex', 'Mask'] matched ANY '*_Tex_*_Mask' file (ex. Vodyanitsa Tail_Mask
    # GelPlaneTex, pupil matcap masks) and assigned them as NYX masks globally.
    NIGHT_SOUL_MASK_IDENTIFIERS = ['Nyx', 'Mask']

    STOCKINGS_DETAILMAP = 'Stockings_Detailmap'

    RIBBON = 'Ribbon'
    TAIL = 'Tail'
    VEIL = 'Veil'
