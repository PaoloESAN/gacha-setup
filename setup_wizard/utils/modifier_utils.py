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
    inputs = get_modifier_inputs(modifier)
    outputs = get_modifier_outputs(modifier)
    
    # 1. Support for Blender 5+ mod.properties.inputs and mod.properties.outputs
    if inputs is not None or outputs is not None:
        clean_out_key = key[:-15] if key.endswith('_attribute_name') else key
        clean_out_key = clean_out_key[7:] if clean_out_key.startswith('Output_') else clean_out_key
        
        if outputs is not None:
            for k in [key, clean_out_key, f"Output_{clean_out_key}"]:
                if hasattr(outputs, k) or (hasattr(outputs, "keys") and k in outputs.keys()):
                    try:
                        out_item = getattr(outputs, k) if hasattr(outputs, k) else outputs[k]
                        set_property_field(out_item, 'attribute_name', value)
                        return
                    except Exception:
                        pass

        if inputs is not None:
            clean_inp_key = key[:-14] if key.endswith('_use_attribute') else key
            clean_inp_key = clean_inp_key[:-15] if clean_inp_key.endswith('_attribute_name') else clean_inp_key
            
            target_inp = None
            for k in [key, clean_inp_key]:
                if hasattr(inputs, k):
                    target_inp = getattr(inputs, k)
                    break
                elif hasattr(inputs, "keys") and k in inputs.keys():
                    try:
                        target_inp = inputs[k]
                        break
                    except Exception:
                        pass
                
            if not target_inp and hasattr(inputs, "keys"):
                try:
                    for ik in inputs.keys():
                        item = inputs[ik] if hasattr(inputs, "__getitem__") else getattr(inputs, ik, None)
                        if item and getattr(item, "name", "").lower() == clean_inp_key.lower():
                            target_inp = item
                            break
                except Exception:
                    pass
                    
            if target_inp:
                if key.endswith('_use_attribute'):
                    try:
                        set_property_field(target_inp, 'type', 'ATTRIBUTE' if value else 'VALUE')
                        return
                    except Exception:
                        pass
                else:
                    try:
                        set_property_field(target_inp, 'value', value)
                        return
                    except Exception:
                        try:
                            if isinstance(value, (tuple, list)) and hasattr(target_inp, "value"):
                                for idx, val in enumerate(value):
                                    target_inp.value[idx] = val
                                return
                        except Exception:
                            pass

    # 2. Support for Blender 4.0+ Geometry Nodes NodeGroup Interface
    if getattr(modifier, "type", None) == 'NODES' and hasattr(modifier, "node_group") and modifier.node_group:
        ng = modifier.node_group
        if hasattr(ng, "interface"):
            for item in ng.interface.items_tree:
                if getattr(item, "item_type", None) == 'SOCKET':
                    in_out = getattr(item, "in_out", None)
                    if in_out == 'INPUT':
                        if item.name == key or item.identifier == key:
                            try:
                                modifier[item.identifier] = value
                                return
                            except Exception:
                                pass
                    elif in_out == 'OUTPUT':
                        clean_key = key[:-15] if key.endswith('_attribute_name') else key
                        clean_key = clean_key[7:] if clean_key.startswith('Output_') else clean_key
                        if item.name == key or item.identifier == key or item.name == clean_key or item.identifier == clean_key:
                            try:
                                modifier[f"{item.identifier}_attribute_name"] = value
                                modifier[f"{item.name}_attribute_name"] = value
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
        if hasattr(ng, "outputs"):
            for out in ng.outputs:
                clean_key = key[:-15] if key.endswith('_attribute_name') else key
                clean_key = clean_key[7:] if clean_key.startswith('Output_') else clean_key
                if out.name == key or out.identifier == key or out.name == clean_key or out.identifier == clean_key:
                    try:
                        modifier[f"{out.identifier}_attribute_name"] = value
                        modifier[f"{out.name}_attribute_name"] = value
                        return
                    except Exception:
                        pass

    # 3. Safe fallback
    try:
        modifier[key] = value
    except (TypeError, AttributeError, KeyError):
        pass


