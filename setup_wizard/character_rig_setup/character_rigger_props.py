# Author: michael-gh1

import bpy

from bpy.types import Context, Operator, PropertyGroup
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty


class CharacterRiggerPropertyGroup(PropertyGroup):
    set_up_lighting_panel: BoolProperty(
        name=' Set Up Lighting Panel', 
        description='Import and Set Up Lighting Panel',
        default=True
    )
    allow_arm_ik_stretch: BoolProperty(
        name=' Allow Arm IK Stretch', 
        description='Allow Arm IK Stretch',
        default=False
    )
    allow_leg_ik_stretch: BoolProperty(
        name=' Allow Leg IK Stretch', 
        description='Allow Leg IK Stretch',
        default=False
    )
    use_arm_ik_poles: BoolProperty(
        name=' Use Arm IK Poles', 
        description='Use Arm IK Poles',
        default=False
    )
    use_leg_ik_poles: BoolProperty(
        name=' Use Leg IK Poles', 
        description='Use Leg IK Poles',
        default=False
    )
    add_children_of_constraints: BoolProperty(
        name=' Add Children of Constraints', 
        description='Add Children of Constraints',
        default=True
    )
    use_head_tracker: BoolProperty(
        name=' Use Head Tracker', 
        description='Use Head Tracker',
        default=False
    )
    enable_hair_clothes_physics: BoolProperty(
        name=' Hair & Clothes Physics',
        description='Apply Damped Track physics to Hair and Clothes bone chains',
        default=False
    )
    enable_hair_dress_physics: BoolProperty(
        name=' Hair & Clothes Physics',
        description='Apply Damped Track physics to Hair and Clothes bone chains',
        default=False
    )
    hair_physics_influence: FloatProperty(
        name=' Hair Influence',
        description='Damped Track influence for hair bone chains',
        min=0.0,
        max=1.0,
        default=0.7,
        step=5,
        precision=2
    )
    clothes_physics_influence: FloatProperty(
        name=' Clothes Influence',
        description='Damped Track influence for clothes bone chains',
        min=0.0,
        max=1.0,
        default=0.4,
        step=5,
        precision=2
    )
    dress_physics_influence: FloatProperty(
        name=' Clothes Influence',
        description='Damped Track influence for clothes bone chains',
        min=0.0,
        max=1.0,
        default=0.4,
        step=5,
        precision=2
    )

    @staticmethod
    def get_prop(context, prop_name):
        return getattr(context.scene.character_rigger_props, prop_name)

    @staticmethod
    def set_prop(context, prop_name, value):
        setattr(context.scene.character_rigger_props, prop_name, value)


class CharacterRiggerPropertyManager(PropertyGroup):
    @classmethod
    def register(cls):
        bpy.types.Scene.character_rigger_props = PointerProperty(type=CharacterRiggerPropertyGroup)

    @classmethod
    def unregister(cls):
        try:
            del bpy.types.Scene.character_rigger_props
        except AttributeError:
            pass
