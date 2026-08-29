# Author: michael-gh1

import bpy, re

from setup_wizard.domain.shader_material_names import JaredNytsPunishingGrayRavenShaderMaterialNames


class PunishingGrayRavenMaterialIdentifierService:
    def get_body_part_name(self, full_name):
        try:
            last_index_of_first_group_of_numbers = self.__find_second_group_of_numbers(full_name)

            if last_index_of_first_group_of_numbers:
                # If there's an exact match then use that name (no body part at end of material name)
                # Otherwise try getting the body part at the end of the material name
                mesh_body_part_name = \
                    self.__exact_material_name_match_check(full_name, last_index_of_first_group_of_numbers) or \
                    full_name[last_index_of_first_group_of_numbers + 1:]
                return mesh_body_part_name
        except:
            return None
        return None

    def __find_second_group_of_numbers(self, input_string):
        # Find the first occurrence of numbers
        match = re.search(r'\d+', input_string)
        len_first_match = len(match.group())
        
        if match:
            # Find the second occurrence of numbers starting from the end of the first match
            match = re.search(r'\d+', input_string[match.span()[1]:])
            
            if match:
                numbers = match.group()
                last_index = match.span()[1] + len_first_match
                return last_index
        return None

    # Handle materials that are exact matches with the texture names (Lamiya's Trident)
    def __exact_material_name_match_check(self, full_name, last_index_of_first_group_of_numbers):
        exact_match_material = bpy.data.materials.get(
            f'{JaredNytsPunishingGrayRavenShaderMaterialNames.MATERIAL_PREFIX}{full_name[:last_index_of_first_group_of_numbers + 1]}'
        )
        if exact_match_material:
            return full_name[:last_index_of_first_group_of_numbers + 1]
        return None

    # Search original materials for a user of the texture name
    def search_original_material_user_for_body_part_name(self, texture_name):
        try:
            last_index_of_first_group_of_numbers = self.__find_second_group_of_numbers(texture_name)
        except:
            return None

        base_texture_name = texture_name[:last_index_of_first_group_of_numbers + 1]
        original_materials = [material for material in bpy.data.materials if 
                              JaredNytsPunishingGrayRavenShaderMaterialNames.MATERIAL_PREFIX not in material.name]
        
        for original_material in original_materials:
            try:
                base_color_texture_image_name = original_material.node_tree.nodes.get('Principled BSDF').inputs.get('Base Color').links[0].from_node.image.name_full
            except:
                continue

            if f'{base_texture_name}.png' == base_color_texture_image_name:
                body_part_name = original_material.name[last_index_of_first_group_of_numbers + 1:]
                return body_part_name

        # No texture image found, check if Chibi material
        if original_material.name == 'XDefaultMaterial':
            return 'XDefaultMaterial'
        return None

    # Get "real" body part name via original texture for this material (Cloth01 using Cloth)
    def get_body_part_name_of_shared_material(self, material_name):
        # Eye and Eyes will run into some funky logic, just keep using original results from `get_body_part_name()`
        if 'Eye' in material_name:
            return None

        try:
            base_color_texture_image_name = bpy.data.materials.get(material_name).node_tree.nodes.get('Principled BSDF').inputs.get('Base Color').links[0].from_node.image.name_full
        except:
            return None
        base_color_texture_image_name = base_color_texture_image_name.replace('.png', '')

        try:
            last_index_of_first_group_of_numbers = self.__find_second_group_of_numbers(base_color_texture_image_name)
            if last_index_of_first_group_of_numbers is None:
                return None
        except:
            return None

        body_part_name = base_color_texture_image_name[last_index_of_first_group_of_numbers + 1:]
        return body_part_name


class WutheringWavesMaterialIdentifierService:
    @staticmethod
    def split_material_name(mat_name: str):
        """Extracts (base_part, version) from WuWa material name (MI_...)."""
        if mat_name.endswith("_SEETHRU"):
            mat_name = mat_name[:-8]
        elif " " in mat_name and mat_name.split(" ")[0].endswith("_SEETHRU"):
            parts_space = mat_name.split(" ")
            parts_space[0] = parts_space[0][:-8]
            mat_name = " ".join(parts_space)

        parts = mat_name.split("_", 2)
        if len(parts) < 2:
            return "", ""

        category_part = parts[1]

        if category_part in ["Npc", "NH", "NPC"]:
            if len(parts) > 2:
                remaining = parts[2]
                if "_" in remaining:
                    suffix = remaining.rsplit("_", 1)[-1]
                    if re.match(r"^\d+[A-Za-z]", suffix):
                        suffix = re.sub(r"^\d+", "", suffix)
                    return suffix, ""
                if re.match(r"^\d+[A-Za-z]", remaining):
                    return re.sub(r"^\d+", "", remaining), ""
                return remaining, ""
            base_part = category_part
            version = "_" + parts[2] if len(parts) > 2 else ""
            return base_part, version

        words = re.findall(r"[A-Z][a-z]*", category_part)
        if not words:
            return "", category_part if len(parts) <= 2 else "_" + parts[2]

        base_part = words[-1]
        try:
            version_start = category_part.rindex(base_part) + len(base_part)
            version = category_part[version_start:]
            if len(parts) > 2:
                version += "_" + parts[2]
        except ValueError:
            version = ""
        return base_part, version
