
def get_args(args):
    args_dict = dict()
    index = 1
    while index < len(args):
        key = args[index]
        value = args[index+1]
        args_dict[key] = value
        index += 2
        
    return args_dict

def get_mandatory_arg(args_dict, key):
    if key in args_dict:
        val = args_dict[key]
        print(f"SUPPLIED {key}={val}")
        return val
    else:
        print(f"Missing mandatory argument {key}")
        exit(1)

def get_mandatory_arg_validated(args_dict, key, allowed_values):
    if key in args_dict:
        val = args_dict[key]
        if val in allowed_values:
            print(f"SUPPLIED {key}={val}")
            return val
        else:
            print(f"SUPPLIED ILLEGAL VALUE {key}={val}. ALLOWED {allowed_values}")
            exit(1)
    else:
        print(f"Missing mandatory argument {key}")
        exit(1)

def get_optional_arg(args_dict, key, default_value):
    if key in args_dict:
        val = args_dict[key]
        print(f"SUPPLIED {key}={val}")
        return val
    else:
        print(f"DEFAULT {key}={default_value}")
        return default_value

def get_optional_arg_validated(args_dict, key, default_value, allowed_values):
    if key in args_dict:
        val = args_dict[key]
        if val in allowed_values:
            print(f"SUPPLIED {key}={val}")
            return val
        else:
            print(f"SUPPLIED ILLEGAL VALUE {key}={val}. ALLOWED {allowed_values}")
            exit(1)
    else:
        print(f"DEFAULT {key}={default_value}")
        return default_value

def is_true(val):
    if val.upper() == "TRUE":
        return True
    elif val.upper() == "FALSE":
        return False
    else:
        raise ValueError("Must be a boolean value")

def as_list(val):
    return val.split()