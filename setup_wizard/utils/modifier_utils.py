import bpy

def get_modifier_inputs(modifier):
    properties = getattr(modifier, "properties", None)
    if properties is not None:
        try:
            return properties["inputs"]
        except (KeyError, TypeError):
            pass
        if hasattr(properties, "inputs"):
            return properties.inputs
    return None

def get_modifier_outputs(modifier):
    properties = getattr(modifier, "properties", None)
    if properties is not None:
        try:
            return properties["outputs"]
        except (KeyError, TypeError):
            pass
        if hasattr(properties, "outputs"):
            return properties.outputs
    return None

def get_property_field(group, field):
    if hasattr(group, field):
        try:
            return getattr(group, field)
        except AttributeError:
            pass
    try:
        return group[field]
    except (KeyError, TypeError):
        return None

def set_property_field(group, field, value):
    try:
        group[field] = value
        return
    except (TypeError, KeyError):
        pass
        
    try:
        setattr(group, field, value)
    except AttributeError as e:
        raise e

def has_modifier_property(modifier, key):
    inputs = get_modifier_inputs(modifier)
    outputs = get_modifier_outputs(modifier)
    
    if inputs is not None:
        if key.startswith('Output_') and key.endswith('_attribute_name'):
            base_key = key[:-15]
            return outputs and base_key in outputs
            
        if key.endswith('_use_attribute'):
            base_key = key[:-14]
            return base_key in inputs
        elif key.endswith('_attribute_name'):
            base_key = key[:-15]
            return base_key in inputs
            
        return key in inputs
        
    # Safe fallback
    try:
        return key in modifier
    except (TypeError, AttributeError):
        return False

def get_modifier_property(modifier, key):
    inputs = get_modifier_inputs(modifier)
    outputs = get_modifier_outputs(modifier)
    
    if inputs is not None:
        if key.startswith('Output_') and key.endswith('_attribute_name'):
            base_key = key[:-15]
            if outputs and base_key in outputs:
                return get_property_field(outputs[base_key], 'attribute_name')
        
        if key.endswith('_use_attribute'):
            base_key = key[:-14]
            if base_key in inputs:
                t = get_property_field(inputs[base_key], 'type')
                return 1 if t == 'ATTRIBUTE' else 0
        elif key.endswith('_attribute_name'):
            base_key = key[:-15]
            if base_key in inputs:
                return get_property_field(inputs[base_key], 'attribute_name')
        
        if key in inputs:
            return get_property_field(inputs[key], 'value')
            
    # Safe fallback
    try:
        return modifier.get(key)
    except (TypeError, AttributeError):
        return None

def set_modifier_property(modifier, key, value):
    # Support for Blender 4.0+ and 5.0+ Geometry Nodes NodeGroup Interface
    if getattr(modifier, "type", None) == 'NODES' and hasattr(modifier, "node_group") and modifier.node_group:
        ng = modifier.node_group
        if hasattr(ng, "interface"):
            for item in ng.interface.items_tree:
                if getattr(item, "item_type", None) == 'SOCKET' and getattr(item, "in_out", None) == 'INPUT':
                    if item.name == key or item.identifier == key:
                        try:
                            modifier[item.identifier] = value
                            return
                        except Exception:
                            pass
        elif hasattr(ng, "inputs"):
            for inp in ng.inputs:
                if inp.name == key or inp.identifier == key:
                    try:
                        modifier[inp.identifier] = value
                        return
                    except Exception:
                        pass

    inputs = get_modifier_inputs(modifier)
    outputs = get_modifier_outputs(modifier)
    
    if inputs is not None:
        if key.startswith('Output_') and key.endswith('_attribute_name'):
            base_key = key[:-15]
            if outputs and base_key in outputs:
                set_property_field(outputs[base_key], 'attribute_name', value)
                return
        
        if key.endswith('_use_attribute'):
            base_key = key[:-14]
            if base_key in inputs:
                set_property_field(inputs[base_key], 'type', 'ATTRIBUTE' if value else 'VALUE')
                return
        elif key.endswith('_attribute_name'):
            base_key = key[:-15]
            if base_key in inputs:
                set_property_field(inputs[base_key], 'attribute_name', value)
                return
        
        if key in inputs:
            set_property_field(inputs[key], 'value', value)
            return
            
    # Safe fallback
    try:
        modifier[key] = value
    except (TypeError, AttributeError, KeyError):
        pass
