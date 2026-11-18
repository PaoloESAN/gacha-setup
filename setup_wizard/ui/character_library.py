"""Searchable saved-character picker for the main setup panel."""

from pathlib import Path

import bpy
from bpy.props import CollectionProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import Operator, OperatorFileListElement, PropertyGroup, UIList
from bpy_extras.io_utils import ImportHelper

from setup_wizard.domain.game_types import GameType
from setup_wizard.services import character_library as library


def selected_game(context):
    return getattr(context.scene, 'game_type_dropdown', GameType.GENSHIN_IMPACT.name)


def refresh_characters(context, selected_key=None):
    entries = library.read_catalog()
    wm = context.window_manager
    wm.gacha_saved_characters.clear()
    for entry in sorted(entries, key=lambda item: (item['name'].casefold(), item['filepath'])):
        game = entry.get('library_game', entry['game'])
        if game != selected_game(context) or not Path(entry['filepath']).is_file():
            continue
        item = wm.gacha_saved_characters.add()
        item.name, item.key = entry['name'], entry['key']
        item.game, item.filepath = game, entry['filepath']
        item.label = entry.get('label', Path(entry['filepath']).name)
    wm.gacha_library_index = next((i for i, item in enumerate(wm.gacha_saved_characters)
                                  if item.key == selected_key), 0)
    for window in wm.windows:
        for area in window.screen.areas:
            area.tag_redraw()


class GACHA_PG_SavedCharacter(PropertyGroup):
    key: StringProperty()
    game: StringProperty()
    filepath: StringProperty()
    label: StringProperty()


class GACHA_UL_SavedCharacters(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row()
        row.label(text=item.name, icon='OUTLINER_OB_ARMATURE')
        row.label(text=item.label)

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        search = context.window_manager.gacha_library_search
        flags = bpy.types.UI_UL_list.filter_items_by_name(
            search, self.bitflag_filter_item, items, 'name',
        ) if search else [self.bitflag_filter_item] * len(items)
        if search:
            labels = bpy.types.UI_UL_list.filter_items_by_name(
                search, self.bitflag_filter_item, items, 'label')
            flags = [name_flag | label_flag for name_flag, label_flag in zip(flags, labels)]
        return flags, []


class GACHA_OT_AddLibraryBlend(Operator, ImportHelper):
    """Add setup characters from selected .blend files without opening them"""
    bl_idname = 'gacha.add_library_blend'
    bl_label = 'Add .blend'
    filename_ext = '.blend'
    filter_glob: StringProperty(default='*.blend', options={'HIDDEN'})
    files: CollectionProperty(type=OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    game: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def invoke(self, context, event):
        self.game = selected_game(context)
        self.files.clear()
        return ImportHelper.invoke(self, context, event)

    def execute(self, context):
        paths = [Path(self.directory) / item.name for item in self.files] if self.files else [Path(self.filepath)]
        paths = list(dict.fromkeys(str(path.resolve()) for path in paths))
        game = self.game or selected_game(context)
        count = 0
        added_files = 0
        for path in paths:
            try:
                count += library.add_blend(path, game)
                added_files += 1
            except Exception as exc:
                self.report({'WARNING'}, f'{Path(path).name}: {exc}')
        try:
            refresh_characters(context)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        if not added_files:
            return {'CANCELLED'}
        self.report({'INFO'}, f'Added {count} character(s) from {added_files} .blend file(s) to the selected game.')
        return {'FINISHED'}


class GACHA_OT_RenameLibraryBlend(Operator):
    """Change the name displayed here for this .blend file"""
    bl_idname = 'gacha.rename_library_blend'
    bl_label = 'Rename .blend in Library'
    filepath: StringProperty(options={'HIDDEN'})
    label: StringProperty(name='Name')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        try:
            library.rename_blend(self.filepath, self.label)
            wm = context.window_manager
            key = wm.gacha_saved_characters[wm.gacha_library_index].key
            refresh_characters(context, key)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class GACHA_OT_RemoveLibraryBlend(Operator):
    """Remove this .blend from the list; the file on disk is kept"""
    bl_idname = 'gacha.remove_library_blend'
    bl_label = 'Remove from Library'
    filepath: StringProperty(options={'HIDDEN'})

    def execute(self, context):
        try:
            library.remove_blend(self.filepath)
            refresh_characters(context)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class GACHA_OT_SelectCharacter(Operator):
    """Append or link a character from a previously saved setup file"""
    bl_idname = 'gacha.select_character'
    bl_label = 'Select Character'
    bl_options = {'REGISTER', 'UNDO'}

    import_mode: EnumProperty(
        name='Import Mode',
        items=(('APPEND', 'Append', 'Add an independent editable copy'),
               ('LINK', 'Link', 'Add an instance linked to the source .blend')),
        default='APPEND', options={'SKIP_SAVE'},
    )

    def invoke(self, context, event):
        try:
            refresh_characters(context)
            context.window_manager.gacha_library_search = ''
            self.import_mode = 'APPEND'
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self, width=420, confirm_text='Import')

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout
        layout.row(align=True).prop(self, 'import_mode', expand=True)
        layout.prop(wm, 'gacha_library_search', text='', icon='VIEWZOOM')
        row = layout.row()
        row.template_list('GACHA_UL_SavedCharacters', '', wm, 'gacha_saved_characters',
                          wm, 'gacha_library_index', rows=7)
        controls = row.column(align=True)
        controls.operator_context = 'INVOKE_DEFAULT'
        controls.operator('gacha.add_library_blend', text='', icon='ADD')
        index = wm.gacha_library_index
        has_selection = 0 <= index < len(wm.gacha_saved_characters)
        remove = controls.column(align=True)
        remove.enabled = has_selection
        remove.operator_context = 'EXEC_DEFAULT'
        action = remove.operator('gacha.remove_library_blend', text='', icon='REMOVE')
        if has_selection:
            item = wm.gacha_saved_characters[index]
            action.filepath = item.filepath
            layout.label(text=item.filepath, icon='FILE_BLEND')
        else:
            layout.label(text='No saved characters for this game yet.', icon='INFO')
            layout.label(text='Use + to add a .blend file.')

    def execute(self, context):
        wm = context.window_manager
        index = wm.gacha_library_index
        if not 0 <= index < len(wm.gacha_saved_characters):
            self.report({'WARNING'}, 'No character selected. Set up and save a character first.')
            return {'CANCELLED'}
        item = wm.gacha_saved_characters[index]
        if selected_game(context) != item.game:
            self.report({'WARNING'}, 'Select a character from the visible list')
            return {'CANCELLED'}
        try:
            entry = next(entry for entry in library.read_catalog() if entry['key'] == item.key)
            library.append_character(entry, context, link=self.import_mode == 'LINK')
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, f'Added {entry["name"]}')
        return {'FINISHED'}


CLASSES = (GACHA_PG_SavedCharacter, GACHA_UL_SavedCharacters,
           GACHA_OT_AddLibraryBlend, GACHA_OT_RenameLibraryBlend,
           GACHA_OT_RemoveLibraryBlend, GACHA_OT_SelectCharacter)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.gacha_saved_characters = CollectionProperty(
        type=GACHA_PG_SavedCharacter, options={'SKIP_SAVE'})
    bpy.types.WindowManager.gacha_library_index = IntProperty(default=0, options={'SKIP_SAVE'})
    bpy.types.WindowManager.gacha_library_search = StringProperty(name='Search Characters', options={'SKIP_SAVE'})
    library.register()


def unregister():
    library.unregister()
    for name in ('gacha_saved_characters', 'gacha_library_index', 'gacha_library_search'):
        delattr(bpy.types.WindowManager, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
